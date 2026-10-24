import json
import unittest
from unittest.mock import patch
import app
from docito_backup import encrypt_recovery,verify_recovery

class BackupContactTests(unittest.TestCase):
    def test_encrypted_backup_roundtrip_and_wrong_key(self):
        bundle={"format":"docito-orcamento-recovery","version":1,"tables_json":{"orcamentos":'[{"total":123.4500000001}]',"docito_configuracoes":"[]"},"private_sealed":"pacote sintético selado"}
        secret="senha-sintetica-grande-123"
        encrypted=encrypt_recovery(bundle,secret)
        self.assertNotIn(b"123.4500000001",encrypted)
        self.assertEqual(verify_recovery(encrypted,secret),{"orcamentos":1,"docito_configuracoes":0})
        with self.assertRaises(ValueError):verify_recovery(encrypted,"outra-senha-grande-123")
        changed=json.loads(encrypted);changed["iterations"]=99999999
        with self.assertRaises(ValueError):verify_recovery(json.dumps(changed).encode(),secret)

    def test_contact_only_enters_json_and_is_recovered(self):
        quote={"numero":123,"cliente":"Cliente teste","data_entrega":"2026-11-01","itens":[],"total":10,"contato":{"telefone":"11999990000","email":"test@example.invalid","endereco":"Endereço teste","modalidade":"delivery","horario":"14h"}}
        saved=app.preparar_registro_supabase(quote)
        self.assertNotIn("contato",saved)
        self.assertEqual(saved["dados"]["contato"]["telefone"],"11999990000")
        self.assertEqual(app.normalizar_orcamento(saved)["contato"]["endereco"],"Endereço teste")
        quote["contato"]["telefone"]="1"*41
        with self.assertRaises(ValueError):app.preparar_registro_supabase(quote)

    def test_edit_preserves_source_line_ids(self):
        state={}
        quote={"id":"q-test","numero":12,"cliente":"Cliente teste","data_entrega":"2026-11-01","itens":[{"id":"stable-a","produto":"Doce"},{"produto":"Outro"}],"total":10,"dados":{}}
        with patch.object(app,"exigir_acesso"),patch.object(app.st,"session_state",state):
            app.carregar_orcamento_para_edicao(quote)
        self.assertEqual([i["id"]for i in state["carrinho"]],["stable-a","line-2"])
        self.assertEqual(state["contato_telefone"],"")
