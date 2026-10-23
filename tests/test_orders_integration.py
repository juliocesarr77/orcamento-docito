from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from streamlit.testing.v1 import AppTest
import docito_orders as orders


def panel():
    import streamlit as st
    from docito_orders import mostrar_integracao
    mostrar_integracao(st.session_state.client, {"id": "quote-test", "revisao": 1})


class QuoteApprovalTests(unittest.TestCase):
    def run_panel(self, state):
        client = Mock()
        client.rpc.return_value.execute.return_value.data = state
        at = AppTest.from_function(panel)
        at.session_state.client = client
        return at, client

    def test_first_approval_needs_customer_confirmation_and_sends_exact_revision(self):
        at, client = self.run_panel({"status": "draft", "revision": 1, "approved_revision": 0, "synced_revision": 0})
        with patch.object(orders, "exigir_acesso", return_value=SimpleNamespace(email="julio.goiano@gmail.com")):
            at.run()
            self.assertFalse(at.exception)
            self.assertTrue(at.button[0].disabled)
            self.assertFalse(any(c.args[0] == "docito_approve_quote" for c in client.rpc.call_args_list))
            at.checkbox[0].check().run()
            self.assertFalse(at.button[0].disabled)
            at.button[0].click().run()
        approvals = [c for c in client.rpc.call_args_list if c.args[0] == "docito_approve_quote"]
        self.assertEqual(len(approvals), 1)
        self.assertEqual(approvals[0].args[1], {"p_id": "quote-test", "p_revision": 1, "p_actor": "julio.goiano@gmail.com"})

    def test_saved_edit_stays_draft_and_retry_never_approves_it(self):
        at, client = self.run_panel({"status": "integrated", "revision": 2, "approved_revision": 1, "synced_revision": 1})
        with patch.object(orders, "exigir_acesso", return_value=SimpleNamespace(email="gerusa041188@gmail.com")):
            at.run()
            self.assertIn("Edição ainda não aprovada", at.warning[0].value)
            self.assertEqual(at.button[0].label, "Aprovar edição e atualizar Gestão")
            self.assertTrue(at.button[0].disabled)
            at.button[1].click().run()
        self.assertFalse(any(c.args[0] == "docito_approve_quote" for c in client.rpc.call_args_list))
        self.assertTrue(any(c.args[0] == "docito_quote_status" and c.args[1]["p_retry"] for c in client.rpc.call_args_list))

    def test_unauthorized_identity_never_reaches_database(self):
        client = Mock()
        with patch.object(orders, "exigir_acesso", side_effect=RuntimeError("unauthorized")):
            with self.assertRaises(RuntimeError):
                orders.mostrar_integracao(client, {"id": "test", "revisao": 1})
        client.rpc.assert_not_called()


def history_panel():
    import streamlit as st
    import app
    app.supabase = st.session_state.client
    app.tela_historico()


class QuoteHistoryPerformanceTests(unittest.TestCase):
    def test_closed_history_does_not_query_each_integration(self):
        import app
        client = Mock()
        client.table.return_value.select.return_value.order.return_value.execute.return_value.data = [
            {"id": "q1", "numero": 123, "cliente": "Exemplo 1", "data_entrega": "2026-11-01", "itens": [], "total": 10, "revisao": 1},
            {"id": "q2", "numero": 124, "cliente": "Exemplo 2", "data_entrega": "2026-11-02", "itens": [], "total": 10, "revisao": 1},
        ]
        client.rpc.return_value.execute.return_value.data = {"status": "draft", "revision": 1, "approved_revision": 0, "synced_revision": 0}
        at = AppTest.from_function(history_panel)
        at.session_state.client = client
        with patch.object(app, "exigir_acesso"), patch.object(orders, "exigir_acesso", return_value=SimpleNamespace(email="julio.goiano@gmail.com")):
            at.run()
            self.assertFalse(at.exception)
            client.rpc.assert_not_called()
            next(b for b in at.button if b.key == "gestao_toggle_q1").click().run()
            self.assertFalse(at.exception)
        client.rpc.assert_called_once_with("docito_quote_status", {"p_id": "q1", "p_retry": False})
