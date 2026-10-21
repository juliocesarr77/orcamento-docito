from copy import deepcopy
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4
from pathlib import Path
from streamlit.testing.v1 import AppTest
import docito_auth as auth

import app
import docito_catalog as catalog
import docito_gestao as gestao
import docito_settings as settings


class ImportacaoGestaoTests(unittest.TestCase):
    def setUp(self):
        self.config = catalog.configuracao_padrao()
        self.central_id = str(uuid4())
        self.tabela_json = {
            "version": 1, "source": "docito-gestao", "policy_version": 1,
            "generated_at": "2026-10-21T19:00:00Z",
            "products": [{"id": self.central_id, "name": "Nome próprio na Gestão", "unit": "un", "price_cents": "150"}],
        }

    def tabela(self, dados=None):
        return gestao.carregar_tabela_gestao(json.dumps(dados or self.tabela_json).encode())

    def test_import_only_updates_mapped_prices_and_keeps_catalogue_structure(self):
        before = deepcopy(self.config)
        local_id = self.config["doces"][0]["id"]
        updated, preview = gestao.preparar_importacao(self.config, self.tabela(), {self.central_id: local_id})
        self.assertEqual(self.config, before)
        self.assertEqual(updated["doces"][0]["preco"], 150)
        self.assertEqual(updated["doces"][0]["nome"], before["doces"][0]["nome"])
        self.assertEqual(updated["doces"][0]["id"], local_id)
        self.assertEqual(updated["doces"][1:], before["doces"][1:])
        self.assertEqual(updated["faixas"], before["faixas"])
        self.assertEqual(len(preview), 1)
        self.assertEqual(preview[0]["Cobrança"], "Cento")
        self.assertEqual(updated, catalog.validar_configuracao(updated))

    def test_converts_cents_per_unit_for_cent_and_unit_and_rejects_kg(self):
        aplique = next(p for p in self.config["doces"] if p["cobranca"] == "Unidade")
        updated, _ = gestao.preparar_importacao(self.config, self.tabela(), {self.central_id: aplique["id"]})
        self.assertEqual(next(p for p in updated["doces"] if p["id"] == aplique["id"])["preco"], 1.5)
        kg = next(p for p in self.config["doces"] if p["cobranca"] == "kg")
        with self.assertRaisesRegex(ValueError, "kg"):
            gestao.preparar_importacao(self.config, self.tabela(), {self.central_id: kg["id"]})
        data = deepcopy(self.tabela_json); data["products"][0]["price_cents"] = 10000000
        with self.assertRaisesRegex(ValueError, "limite"):
            gestao.preparar_importacao(self.config, self.tabela(data), {self.central_id: self.config["doces"][0]["id"]})

    def test_rejects_invalid_or_ambiguous_files(self):
        for price in (0, -1, True, 1.5, "1.50", "NaN", 100000000001):
            data = deepcopy(self.tabela_json); data["products"][0]["price_cents"] = price
            with self.subTest(price=price), self.assertRaises(ValueError): self.tabela(data)
        cases = []
        data = deepcopy(self.tabela_json); data["products"].append(deepcopy(data["products"][0])); cases.append(data)
        data = deepcopy(self.tabela_json); data["products"][0]["unit"] = "kg"; cases.append(data)
        data = deepcopy(self.tabela_json); data["products"][0]["id"] = "not-id"; cases.append(data)
        data = deepcopy(self.tabela_json); data["generated_at"] = "2026-10-21"; cases.append(data)
        data = deepcopy(self.tabela_json); data["version"] = True; cases.append(data)
        data = deepcopy(self.tabela_json); data["policy_version"] = 2; cases.append(data)
        for data in cases:
            with self.assertRaises(ValueError): self.tabela(data)
        for raw in (b'{"version":1,"version":2}', b"[]", b"{broken", b" " * (gestao.MAX_ARQUIVO + 1)):
            with self.assertRaises(ValueError): gestao.carregar_tabela_gestao(raw)

    def test_mapping_never_guesses_by_name_and_rejects_duplicate_targets(self):
        data = deepcopy(self.tabela_json)
        data["products"][0]["name"] = self.config["doces"][0]["nome"]
        with self.assertRaisesRegex(ValueError, "Associe"):
            gestao.preparar_importacao(self.config, self.tabela(data), {})
        second_id = str(uuid4())
        data["products"].append({**data["products"][0], "id": second_id})
        # Identical names are harmless because the mapping uses distinct UUIDs.
        local_a, local_b = self.config["doces"][0]["id"], self.config["doces"][1]["id"]
        updated, _ = gestao.preparar_importacao(self.config, self.tabela(data), {self.central_id: local_a, second_id: local_b})
        self.assertEqual(updated["doces"][0]["gestao_id"], self.central_id)
        with self.assertRaisesRegex(ValueError, "apenas um"):
            gestao.preparar_importacao(self.config, self.tabela(data), {self.central_id: local_a, second_id: local_a})
        with self.assertRaises(ValueError):
            gestao.preparar_importacao(self.config, self.tabela(), {self.central_id: str(uuid4())})

    def test_saved_accepted_and_in_progress_quotes_keep_prices_and_old_bands(self):
        old_item = {"tipo": "unitario", "produto": "Brigadeiro de Chocolate", "qtd": 50, "preco_cento": 125}
        snap_item = {**old_item, "regra_preco": deepcopy(catalog.REGRAS_PADRAO[125])}
        accepted = {"status": "aceito", "dados": {"itens": [deepcopy(snap_item)]}}
        cart = [deepcopy(snap_item)]
        before_accepted, before_cart = deepcopy(accepted), deepcopy(cart)
        data = deepcopy(self.tabela_json); data["products"][0]["price_cents"] = 125
        updated, _ = gestao.preparar_importacao(self.config, self.tabela(data), {self.central_id: self.config["doces"][0]["id"]})
        converted, rules = catalog.montar_catalogo(updated)
        product = converted[self.config["doces"][0]["nome"]]
        self.assertTrue(product["preco_proporcional"])
        self.assertEqual(product["gestao_id"], self.central_id)
        self.assertIn(125, rules)
        # Importing 125 cents/un produces R$125/cento, which coincides with a legacy band.
        new_item = {**old_item, "preco_cento": product["preco_cento"], "regra_preco": None}
        with patch.object(app, "REGRAS_PRECO_DOCES", rules):
            self.assertEqual(app.calcular_subtotal_item(new_item)[0], 62.5)
            self.assertEqual(app.calcular_subtotal_item(old_item)[0], 68.9)
            self.assertEqual(app.calcular_subtotal_item(snap_item)[0], 68.9)
        self.assertEqual(accepted, before_accepted)
        self.assertEqual(cart, before_cart)

    def test_application_snapshots_new_item_without_coincident_legacy_band(self):
        data = deepcopy(self.tabela_json); data["products"][0]["price_cents"] = 125
        updated, _ = gestao.preparar_importacao(self.config, self.tabela(data), {self.central_id: self.config["doces"][0]["id"]})
        client = Mock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {"configuracao": updated, "revisao": 9}
        identity = auth.Identidade("julio.goiano@gmail.com", "subject", 9999999999)
        with patch.object(auth, "identidade_atual", return_value=identity), patch("supabase.create_client", return_value=client):
            at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
            at.secrets["SUPABASE_URL"] = "https://example.supabase.co"
            at.secrets["SUPABASE_KEY"] = "test-only"
            at.run()
            self.assertFalse(at.exception)
            next(b for b in at.button if b.label == "➕ Adicionar produto").click().run()
            self.assertFalse(at.exception)
            item = at.session_state["carrinho"][0]
            self.assertIsNone(item["regra_preco"])
            self.assertEqual(item["produto_id"], self.config["doces"][0]["id"])
            self.assertEqual(item["gestao_product_id"], self.central_id)
            self.assertEqual(app.calcular_subtotal_item(item)[0], 62.5)

    def test_import_save_uses_revision_and_never_writes_quotes(self):
        updated, _ = gestao.preparar_importacao(self.config, self.tabela(), {self.central_id: self.config["doces"][0]["id"]})
        client = Mock()
        response = client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value
        response.data = []
        with patch.object(settings, "exigir_acesso", return_value=SimpleNamespace(email="test@docito.invalid")):
            with self.assertRaises(settings.CatalogoAlterado): settings.salvar_configuracao(client, updated, 7)
        client.table.assert_called_once_with("docito_configuracoes")
        client.table.return_value.update.return_value.eq.return_value.eq.assert_called_with("revisao", 7)

    def test_explicit_confirmation_saves_prepared_config_with_expected_revision(self):
        fake_file = io.BytesIO(json.dumps(self.tabela_json).encode())
        save = Mock()
        state = {}
        with patch("docito_auth.exigir_acesso"), patch("streamlit.file_uploader", return_value=fake_file), patch("streamlit.selectbox", return_value=self.config["doces"][0]["id"]), patch("streamlit.checkbox", return_value=True), patch("streamlit.button", return_value=True), patch("streamlit.dataframe"), patch("streamlit.subheader"), patch("streamlit.caption"), patch("streamlit.write"), patch("streamlit.info"), patch("streamlit.rerun") as rerun, patch("streamlit.session_state", state):
            gestao.mostrar_importacao(Mock(), self.config, 3, save)
        save.assert_called_once()
        self.assertEqual(save.call_args.args[2], 3)
        self.assertEqual(save.call_args.args[1]["doces"][0]["preco"], 150)
        self.assertTrue(save.call_args.args[1]["doces"][0]["preco_proporcional"])
        self.assertTrue(state["_catalogo_salvo"])
        rerun.assert_called_once_with(scope="app")

    def test_preview_does_not_save_without_confirmation(self):
        fake_file = io.BytesIO(json.dumps(self.tabela_json).encode())
        save = Mock()
        with patch("docito_auth.exigir_acesso"), patch("streamlit.file_uploader", return_value=fake_file), patch("streamlit.selectbox", return_value=self.config["doces"][0]["id"]), patch("streamlit.checkbox", return_value=False), patch("streamlit.button", return_value=True), patch("streamlit.dataframe") as dataframe, patch("streamlit.subheader"), patch("streamlit.caption"), patch("streamlit.write"), patch("streamlit.info"):
            gestao.mostrar_importacao(Mock(), self.config, 3, save)
        save.assert_not_called()
        self.assertEqual(dataframe.call_args.args[0][0]["Novo preço (R$)"], 150)


if __name__ == "__main__":
    unittest.main()
