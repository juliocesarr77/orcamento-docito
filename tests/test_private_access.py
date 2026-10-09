import io
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

from streamlit.testing.v1 import AppTest

import docito_auth as auth
import docito_catalog as catalog
import docito_settings as settings
import app


CLIENT_ID = "123-test.apps.googleusercontent.com"
AUTH_CONFIG = {"auth": {
    "redirect_uri": auth.REDIRECT_URI, "cookie_secret": "abcdef0123456789" * 4,
    "google": {"client_id": CLIENT_ID, "client_secret": "test-secret",
               "server_metadata_url": auth.GOOGLE_METADATA_URL},
}}


def claims(email="julio.goiano@gmail.com"):
    return {"is_logged_in": True, "email": email, "email_verified": True,
            "iss": "https://accounts.google.com", "aud": CLIENT_ID,
            "sub": "google-subject", "iat": 950, "exp": 1200}


class IdentityTests(unittest.TestCase):
    def test_only_two_verified_accounts(self):
        self.assertEqual(auth.EMAILS_AUTORIZADOS,
                         {"gerusa041188@gmail.com", "julio.goiano@gmail.com"})
        for email in auth.EMAILS_AUTORIZADOS:
            self.assertEqual(auth.validar_identidade(claims(email), CLIENT_ID, 1000).email, email)

    def test_denies_forged_unverified_and_expired_identity(self):
        rejected = [
            {"is_logged_in": False}, {"email": "attacker@gmail.com"},
            {"email": "julio.goiano+alias@gmail.com"}, {"email": "julio.goiano@gmail.com.attacker.test"},
            {"email_verified": False}, {"email_verified": "true"},
            {"iss": "https://attacker.test"}, {"aud": "other-client"},
            {"aud": ["other-client"]}, {"azp": "other-client"},
            {"exp": 1000}, {"exp": 999}, {"exp": float("nan")},
            {"exp": float("inf")}, {"iat": 1061}, {"iat": float("nan")},
            {"sub": ""}, {"sub": "x" * 256}, {"email": None},
        ]
        for changed in rejected:
            with self.subTest(changed=changed):
                self.assertIsNone(auth.validar_identidade({**claims(), **changed}, CLIENT_ID, 1000))
        for field in ("exp", "iat", "sub", "email", "iss", "aud"):
            incomplete = claims(); incomplete.pop(field)
            self.assertIsNone(auth.validar_identidade(incomplete, CLIENT_ID, 1000))

    def test_accepts_normalized_email_and_valid_audience_list(self):
        c = {**claims("JULIO.GOIANO@GMAIL.COM"), "aud": [CLIENT_ID], "azp": CLIENT_ID}
        self.assertIsNotNone(auth.validar_identidade(c, CLIENT_ID, 1000))

    def test_bad_or_example_auth_configuration_fails_closed(self):
        configs = [{}, {"auth": {}}, deepcopy(AUTH_CONFIG), deepcopy(AUTH_CONFIG), deepcopy(AUTH_CONFIG)]
        configs[2]["auth"]["cookie_secret"] = "SUBSTITUA" * 10
        configs[3]["auth"]["redirect_uri"] = "https://attacker.test/oauth2callback"
        configs[4]["auth"]["google"]["server_metadata_url"] = "https://attacker.test/metadata"
        for config in configs:
            with patch.object(auth.st, "secrets", config):
                self.assertIsNone(auth.configuracao_google())
        with patch.object(auth.st, "secrets", AUTH_CONFIG):
            self.assertEqual(auth.configuracao_google()["client_id"], CLIENT_ID)


class CatalogueTests(unittest.TestCase):
    def test_prefills_every_original_product_and_price(self):
        config = catalog.configuracao_padrao()
        converted, rules = catalog.montar_catalogo(config)
        self.assertEqual(len(converted), 20)
        for name, original in catalog.CATALOGO_PADRAO.items():
            for field, value in original.items():
                self.assertEqual(converted[name][field], value, (name, field))
        self.assertEqual(rules, catalog.REGRAS_PADRAO)

    def test_add_edit_delete_and_reload(self):
        config = catalog.configuracao_padrao()
        removed = config["doces"].pop(0)["nome"]
        config["doces"][0].update(nome="Ninho novo", preco=175)
        config["doces"].append({"nome": "Trufa", "preco": 4.5, "cobranca": "Unidade"})
        validated = catalog.validar_configuracao(config)
        converted, _ = catalog.montar_catalogo(validated)
        self.assertNotIn(removed, converted)
        self.assertEqual(converted["Ninho novo"]["preco_cento"], 175)
        self.assertEqual(converted["Trufa"]["preco_unitario"], 4.5)
        self.assertEqual(validated, catalog.validar_configuracao(validated))

    def test_rejects_invalid_prices_duplicates_and_inconsistent_bands(self):
        for value in (None, 0, -1, float("inf"), float("nan"), "wrong", True, 100000):
            config = catalog.configuracao_padrao(); config["doces"][0]["preco"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                catalog.validar_configuracao(config)
        config = catalog.configuracao_padrao(); config["doces"][1]["nome"] = config["doces"][0]["nome"].upper()
        with self.assertRaises(ValueError): catalog.validar_configuracao(config)
        config = catalog.configuracao_padrao(); config["faixas"][0]["100"] = 126
        with self.assertRaises(ValueError): catalog.validar_configuracao(config)

    def test_saving_conflict_does_not_overwrite_another_session(self):
        client = Mock()
        client.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
        identity = SimpleNamespace(email="julio.goiano@gmail.com")
        with patch.object(settings, "exigir_acesso", return_value=identity):
            with self.assertRaises(settings.CatalogoAlterado):
                settings.salvar_configuracao(client, catalog.configuracao_padrao(), 7)
        client.table.return_value.update.return_value.eq.return_value.eq.assert_called_with("revisao", 7)

    def test_price_changes_preserve_old_and_current_quotes(self):
        item_old = {"tipo": "unitario", "produto": "Beijinho", "qtd": 50, "preco_cento": 130}
        item_snapshot = {**item_old, "regra_preco": {str(k): v for k, v in catalog.REGRAS_PADRAO[130].items()}}
        with patch.object(app, "REGRAS_PRECO_DOCES", {130: {"unitario_ate_25": 9, 40: 300, 50: 400, 75: 500, 90: 600, 100: 700}}):
            self.assertAlmostEqual(app.calcular_subtotal_item(item_old)[0], 71.90)
            self.assertAlmostEqual(app.calcular_subtotal_item(item_snapshot)[0], 71.90)
        proportional = {**item_old, "regra_preco": None}
        self.assertEqual(app.calcular_subtotal_item(proportional)[0], 65)

    def test_unit_price_and_renamed_themed_sweet(self):
        item = {"produto": "Trufa", "tipo": "unitario", "qtd": 10,
                "cobranca": "Unidade", "preco_unitario": 4.5, "preco_cento": 450, "conta_como_doce": True}
        self.assertEqual(app.calcular_subtotal_item(item)[0], 45)
        themed = {**item, "produto": "Tema novo", "cobranca": "Cento", "tematico": True,
                  "preco_manual": True, "preco_cento": 180}
        self.assertTrue(app.item_eh_ninho_tematico(themed))
        self.assertEqual(app.calcular_subtotal_item(themed)[0], 18)


class AppGateTests(unittest.TestCase):
    def test_public_page_without_oauth_never_connects_to_database(self):
        with patch.object(auth.st, "secrets", {}), patch("supabase.create_client") as client:
            at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
        self.assertFalse(at.exception)
        self.assertIn("Bem-vindo", at.title[0].value)
        self.assertEqual([b.label for b in at.button], ["Entrar com Google"])
        self.assertTrue(at.button[0].disabled)
        self.assertFalse(at.radio)
        client.assert_not_called()

    def test_unauthorized_google_account_cannot_read_saved_state(self):
        unauthorized = claims("attacker@gmail.com")
        with patch.object(auth.st, "secrets", AUTH_CONFIG), patch.object(auth.st, "user", unauthorized), patch("supabase.create_client") as client:
            at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
            at.session_state["cliente_input"] = "PRIVATE CUSTOMER"
            at.session_state["carrinho"] = [{"produto": "private"}]
            at.run()
        self.assertFalse(at.exception)
        self.assertFalse(at.text_input)
        self.assertFalse(at.radio)
        self.assertIn("não está autorizada", at.warning[0].value)
        self.assertNotIn("cliente_input", at.session_state)
        client.assert_not_called()

    def test_each_database_operation_and_callback_rechecks_access(self):
        from streamlit.runtime.scriptrunner import StopException
        operations = [
            lambda: app.carregar_historico_supabase(), lambda: app.obter_proximo_numero(),
            lambda: app.salvar_orcamento_supabase({}), lambda: app.atualizar_orcamento_supabase("id", {}),
            lambda: app.carregar_orcamento_para_edicao({}), lambda: app.aplicar_preco_ninho(0, "key"),
            lambda: settings.carregar_configuracao(Mock()),
            lambda: settings.salvar_configuracao(Mock(), catalog.configuracao_padrao(), 1),
        ]
        for operation in operations:
            with self.subTest(operation=operation), patch.object(auth, "identidade_atual", return_value=None), patch.object(auth, "limpar_sessao"), patch.object(auth.st, "error"), patch.object(auth.st, "stop", side_effect=StopException):
                with self.assertRaises(StopException): operation()

    def test_authenticated_home_and_prefilled_settings_render(self):
        config = catalog.configuracao_padrao()
        client = Mock()
        client.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value.data = {
            "configuracao": config, "revisao": 1}
        identity = auth.Identidade("julio.goiano@gmail.com", "subject", 9999999999)
        with patch.object(auth, "identidade_atual", return_value=identity), patch("supabase.create_client", return_value=client):
            at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"))
            at.secrets["SUPABASE_URL"] = "https://example.supabase.co"
            at.secrets["SUPABASE_KEY"] = "test-only"
            at.run()
            self.assertFalse(at.exception)
            self.assertIn("⚙️", [b.label for b in at.button])
            self.assertEqual(len(at.selectbox[0].options), 20)
            at.button(key="abrir_configuracoes").click().run()
            self.assertFalse(at.exception)
            self.assertEqual(len(at.dataframe), 2)
            self.assertEqual(len(at.dataframe[0].value), 20)

    def test_private_quote_preview_uses_no_public_media_endpoint(self):
        image = io.BytesIO()
        app.Image.new("RGB", (2, 2)).save(image, "PNG")
        result = {"imagem": image.getvalue(), "numero": 234, "cliente": '</script><script>alert("x")</script>'}
        with patch.object(app, "exigir_acesso"), patch.object(app.st, "image") as public_image, patch.object(app.st, "download_button") as public_download, patch.object(app.st.components.v1, "html") as inline:
            app.mostrar_resultado(result, "test")
        public_image.assert_not_called()
        public_download.assert_not_called()
        markup = inline.call_args.args[0]
        self.assertIn("data:image/png;base64,", markup)
        self.assertNotIn(result["cliente"], markup)
        self.assertNotIn("/media/", markup)


if __name__ == "__main__":
    unittest.main()
