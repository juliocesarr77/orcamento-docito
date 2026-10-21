"""Importação revisada de preços; não consulta nem altera orçamentos históricos."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
import json
from uuid import UUID

from docito_catalog import validar_configuracao

MAX_ARQUIVO = 256 * 1024


def _objeto_sem_duplicatas(pares):
    objeto = {}
    for chave, valor in pares:
        if chave in objeto:
            raise ValueError("O arquivo contém campos JSON duplicados.")
        objeto[chave] = valor
    return objeto


def _uuid(valor):
    try:
        return str(UUID(str(valor)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("O arquivo contém um identificador de produto inválido.") from None


def carregar_tabela_gestao(conteudo):
    if isinstance(conteudo, str):
        conteudo = conteudo.encode("utf-8")
    if not isinstance(conteudo, bytes) or not 1 <= len(conteudo) <= MAX_ARQUIVO:
        raise ValueError("Selecione um arquivo JSON de até 256 KB.")
    try:
        tabela = json.loads(conteudo.decode("utf-8-sig"), object_pairs_hook=_objeto_sem_duplicatas)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError("O arquivo não contém um JSON válido.") from None
    if (not isinstance(tabela, dict) or type(tabela.get("version")) is not int
            or tabela["version"] != 1 or tabela.get("source") != "docito-gestao"
            or type(tabela.get("policy_version")) is not int or tabela["policy_version"] != 1):
        raise ValueError("Use uma tabela de preços versão 1 exportada pelo Docito Gestão.")
    gerado_em = tabela.get("generated_at")
    try:
        data = datetime.fromisoformat(gerado_em.replace("Z", "+00:00"))
        if data.tzinfo is None or data.utcoffset() is None:
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        raise ValueError("A tabela precisa informar a data de exportação com fuso horário.") from None
    produtos = tabela.get("products")
    if not isinstance(produtos, list) or not 1 <= len(produtos) <= 200:
        raise ValueError("A tabela deve conter entre 1 e 200 produtos.")
    ids, resultado = set(), []
    for produto in produtos:
        if not isinstance(produto, dict):
            raise ValueError("Há um produto inválido na tabela.")
        identificador = _uuid(produto.get("id"))
        if identificador in ids:
            raise ValueError("Há produtos com o mesmo identificador na tabela.")
        ids.add(identificador)
        nome = produto.get("name")
        if not isinstance(nome, str) or not nome.strip() or len(nome) > 150 or any(ord(c) < 32 for c in nome):
            raise ValueError("Há um nome de produto inválido na tabela.")
        if produto.get("unit") != "un":
            raise ValueError("Esta integração aceita apenas preços por unidade do Gestão.")
        preco = produto.get("price_cents")
        if isinstance(preco, str) and preco.isascii() and preco.isdigit() and len(preco) <= 12:
            preco = int(preco)
        if type(preco) is not int or not 1 <= preco <= 100000000000:
            raise ValueError("O preço deve ser um número inteiro positivo de centavos por unidade.")
        resultado.append({"id": identificador, "name": nome.strip(), "unit": "un", "price_cents": preco})
    return {"version": 1, "source": "docito-gestao", "policy_version": 1,
            "generated_at": data.astimezone(timezone.utc).isoformat(), "products": resultado, "sha256": sha256(conteudo).hexdigest()}


def preparar_importacao(config, tabela, mapeamentos):
    """Produz nova configuração e prévia sem mutar a configuração ou carrinho."""
    atual = validar_configuracao(config)
    novo = deepcopy(atual)
    locais = {produto["id"]: produto for produto in novo["doces"]}
    centrais = {produto["id"]: produto for produto in tabela["products"]}
    if not isinstance(mapeamentos, dict) or not mapeamentos:
        raise ValueError("Associe pelo menos um produto da Gestão a um produto existente.")
    if len(set(mapeamentos.values())) != len(mapeamentos):
        raise ValueError("Cada produto do orçamento pode receber apenas um produto da Gestão.")
    previa = []
    for central_id, local_id in mapeamentos.items():
        if central_id not in centrais or local_id not in locais:
            raise ValueError("Uma associação aponta para um produto inexistente. Refaça a revisão.")
        central, local = centrais[central_id], locais[local_id]
        if local["cobranca"] == "kg":
            raise ValueError("Um preço por unidade não pode atualizar um produto cobrado por kg.")
        if local.get("gestao_id") not in (None, central_id):
            raise ValueError("Este produto já está associado a outro ID da Gestão.")
        outro = next((p for p in novo["doces"] if p.get("gestao_id") == central_id and p["id"] != local_id), None)
        if outro:
            raise ValueError("Este ID da Gestão já está associado a outro produto do orçamento.")
        # Centavos/unidade * 100 unidades / 100 centavos = reais/cento.
        preco = Decimal(central["price_cents"]) if local["cobranca"] == "Cento" else Decimal(central["price_cents"]) / 100
        if not Decimal("0.01") <= preco <= Decimal("99999.99"):
            raise ValueError(f"O novo preço de {local['nome']} excede o limite do orçamento (R$ 99.999,99).")
        previa.append({"Produto da Gestão": central["name"], "ID da Gestão": central_id,
                       "Produto do orçamento": local["nome"], "ID do orçamento": local_id,
                       "Cobrança": local["cobranca"], "Preço atual (R$)": local["preco"],
                       "Novo preço (R$)": float(preco), "Regra nova": "Proporcional, sem faixas"})
        local.update(preco=float(preco), gestao_id=central_id, preco_proporcional=True)
    novo["importacao_gestao"] = {"gerado_em": tabela["generated_at"], "sha256": tabela["sha256"]}
    return validar_configuracao(novo), previa


def mostrar_importacao(client, config, revisao, salvar):
    import streamlit as st
    from docito_auth import exigir_acesso

    exigir_acesso()
    st.subheader("Importar preços do Docito Gestão")
    st.caption("Exporte a tabela aprovada no Gestão. Associe os produtos pelos IDs e revise os preços. Os itens já adicionados e os orçamentos salvos mantêm seus valores.")
    arquivo = st.file_uploader("Tabela de preços do Gestão (.json)", type=["json"], max_upload_size=1, key=f"gestao_arquivo_{revisao}")
    if arquivo is None:
        return
    try:
        tabela = carregar_tabela_gestao(arquivo.getvalue())
    except ValueError as exc:
        st.warning(str(exc))
        return
    st.write(f"Exportada em: {tabela['generated_at']}")
    if config.get("importacao_gestao", {}).get("gerado_em", "") > tabela["generated_at"]:
        st.warning("A configuração atual registra uma exportação mais recente. Confira a data antes de continuar.")
    st.info("Os preços importados são proporcionais à quantidade. As faixas antigas continuam disponíveis para os outros produtos.")
    locais = {p["id"]: p for p in config["doces"] if p["cobranca"] != "kg"}
    opcoes = [None, *locais]
    mapa = {}
    for produto in tabela["products"]:
        conhecido = next((p["id"] for p in config["doces"] if p.get("gestao_id") == produto["id"]), None)
        rotulo = f"{produto['name']} · ID {produto['id']} · R$ {produto['price_cents'] / 100:.2f}/un"
        escolhido = st.selectbox(rotulo, opcoes, index=opcoes.index(conhecido) if conhecido in opcoes else 0,
            format_func=lambda identificador: "Não importar este produto" if identificador is None else f"{locais[identificador]['nome']} · {locais[identificador]['cobranca']} · ID {identificador}",
            key=f"gestao_mapa_{revisao}_{tabela['sha256']}_{produto['id']}")
        if escolhido:
            mapa[produto["id"]] = escolhido
    try:
        preparado, previa = preparar_importacao(config, tabela, mapa)
    except ValueError as exc:
        st.warning(str(exc))
        return
    st.dataframe(previa, hide_index=True, width="stretch")
    mapa_hash = sha256(json.dumps(mapa, sort_keys=True).encode()).hexdigest()
    revisado = st.checkbox("Revisei os produtos, as cobranças e os preços acima.", key=f"gestao_revisado_{revisao}_{tabela['sha256']}_{mapa_hash}")
    if st.button("Aplicar somente os preços associados", type="primary", disabled=not revisado, key=f"gestao_aplicar_{revisao}") and revisado:
        try:
            # The existing save performs an authenticated compare-and-swap by revision.
            salvar(client, preparado, revisao)
        except Exception as exc:
            from docito_settings import CatalogoAlterado
            if isinstance(exc, (ValueError, CatalogoAlterado)):
                st.warning(str(exc))
            else:
                st.error("Não foi possível importar os preços. Tente novamente.")
        else:
            st.session_state["_catalogo_salvo"] = True
            st.rerun(scope="app")
