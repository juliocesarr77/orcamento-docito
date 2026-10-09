"""Catálogo privado no Supabase, com proteção contra salvamentos simultâneos."""

import streamlit as st

from docito_auth import exigir_acesso
from docito_catalog import validar_configuracao, TIPOS_COBRANCA, COLUNAS_FAIXA


class CatalogoAlterado(RuntimeError):
    pass


def carregar_configuracao(client):
    exigir_acesso()
    resposta = client.table("docito_configuracoes").select("configuracao,revisao").eq("id", "catalogo").single().execute()
    row = resposta.data
    return validar_configuracao(row["configuracao"]), int(row["revisao"])


def salvar_configuracao(client, config, revisao):
    identidade = exigir_acesso()
    config = validar_configuracao(config)
    resposta = client.table("docito_configuracoes").update({
        "configuracao": config, "revisao": revisao + 1, "atualizado_por": identidade.email,
    }).eq("id", "catalogo").eq("revisao", revisao).execute()
    if not resposta.data:
        raise CatalogoAlterado("O catálogo foi alterado em outra sessão. Feche as configurações e abra novamente antes de salvar.")
    return config


@st.dialog("Configurações da Docito", width="large")
def mostrar_configuracoes(client, config, revisao):
    exigir_acesso()
    st.write("Edite os doces e preços. Use a última linha para adicionar e selecione uma linha para excluir.")
    st.caption("Os orçamentos já salvos mantêm seus produtos e preços. As alterações valem para os próximos itens adicionados.")
    with st.form("configurar_catalogo"):
        doces = st.data_editor(config["doces"], num_rows="dynamic", hide_index=True,
            key=f"doces_config_{revisao}", width="stretch",
            column_config={
                "id": None,
                "nome": st.column_config.TextColumn("Doce / produto", required=True, max_chars=140),
                "cobranca": st.column_config.SelectboxColumn("Cobrança", options=TIPOS_COBRANCA, required=True),
                "preco": st.column_config.NumberColumn("Preço (R$)", min_value=0.01, max_value=99999.99, step=0.01, format="R$ %.2f", required=True),
                "conta_como_doce": st.column_config.CheckboxColumn("Conta no total de doces", default=True),
                "tematico": st.column_config.CheckboxColumn("Permite tema e preço personalizado", default=False),
            })
        st.caption("Cento: preço de 100 doces. Unidade: preço por peça (como aplique). kg: preço de 1 kg.")
        with st.expander("Preços por quantidade"):
            st.write("As faixas atuais já estão preenchidas. Um preço de cento sem faixa é calculado proporcionalmente.")
            faixas = st.data_editor(config["faixas"], num_rows="dynamic", hide_index=True,
                key=f"faixas_config_{revisao}", width="stretch",
                column_config={
                    "preco_cento": st.column_config.NumberColumn("Preço do cento", min_value=0.01, step=0.01, format="R$ %.2f", required=True),
                    "unitario_ate_25": st.column_config.NumberColumn("Unidade até 25", min_value=0.01, step=0.01, format="R$ %.2f", required=True),
                    **{str(n): st.column_config.NumberColumn(f"Total de {n}", min_value=0.01, step=0.01, format="R$ %.2f", required=True) for n in COLUNAS_FAIXA},
                })
        salvar = st.form_submit_button("Salvar alterações", type="primary")
    if salvar:
        try:
            salvar_configuracao(client, {"versao": 1, "doces": doces, "faixas": faixas}, revisao)
        except (ValueError, CatalogoAlterado) as exc:
            st.warning(str(exc))
        except Exception:
            st.error("Não foi possível salvar o catálogo. Tente novamente.")
        else:
            st.session_state["_catalogo_salvo"] = True
            st.rerun(scope="app")
