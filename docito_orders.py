"""Explicit approval of a saved quote. Delivery lives in the database outbox."""
import streamlit as st
from docito_auth import exigir_acesso


def mostrar_integracao(client, quote):
    identidade = exigir_acesso()
    quote_id = quote.get("id")
    revision = quote.get("revisao")
    if not quote_id or revision is None:
        return
    st.divider()
    st.markdown("**Agendamento na Gestão**")
    try:
        state = client.rpc("docito_quote_status", {"p_id": str(quote_id), "p_retry": False}).execute().data
        status = state.get("status", "draft")
        approved = int(state.get("approved_revision") or 0)
        synced = int(state.get("synced_revision") or 0)
        current = int(state["revision"])
        if synced >= current and status == "integrated":
            st.success(f"Integrado à Gestão · revisão {current}.")
        elif current > approved:
            if approved:
                st.warning(f"Edição ainda não aprovada. A Gestão mantém a revisão aprovada {approved}.")
            else:
                st.info("Aprove somente depois da autorização do cliente. O envio agenda a encomenda; não registra venda, pagamento ou baixa de estoque.")
        else:
            st.warning(f"Integração pendente · revisão aprovada {approved}.")
        if state.get("error"):
            st.error(str(state["error"]))
        if current > approved:
            confirmed = st.checkbox("O cliente autorizou esta versão do orçamento", key=f"confirm_gestao_{quote_id}_{current}")
            label = "Aprovar edição e atualizar Gestão" if approved else "Aprovar e agendar na Gestão"
            if st.button(label, disabled=not confirmed, key=f"approve_gestao_{quote_id}_{current}"):
                exigir_acesso()
                client.rpc("docito_approve_quote", {"p_id": str(quote_id), "p_revision": current, "p_actor": identidade.email}).execute()
                st.rerun()
        if approved:
            if st.button("Atualizar situação / tentar novamente", key=f"retry_gestao_{quote_id}"):
                exigir_acesso()
                client.rpc("docito_quote_status", {"p_id": str(quote_id), "p_retry": True}).execute()
                st.rerun()
        st.caption("Editar e salvar o orçamento cria um rascunho. Somente a aprovação desta edição autoriza atualizar a encomenda. O envio pode levar cerca de um minuto.")
    except Exception:
        st.error("Não foi possível consultar ou enviar a integração. Atualize o histórico e tente novamente; seu orçamento permanece salvo.")
