import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import io
import pytz
from pathlib import Path
import base64

BASE_DIR = Path(__file__).resolve().parent


def carregar_fonte(tamanho, negrito=False):
    try:
        nome_fonte = "DejaVuSans-Bold.ttf" if negrito else "DejaVuSans.ttf"
        caminho_fonte = BASE_DIR / nome_fonte
        return ImageFont.truetype(str(caminho_fonte), tamanho)
    except Exception:
        return ImageFont.load_default()


def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_peso(gramas):
    if gramas >= 1000:
        kg = gramas / 1000
        if kg.is_integer():
            return f"{int(kg)}kg"
        return f"{kg:.3f}kg".replace(".", ",").rstrip("0").rstrip(",")
    return f"{int(gramas)}g"


def calcular_desconto(valor_base, desconto_str):
    if not desconto_str:
        return 0.0, ""

    texto = str(desconto_str).strip().lower()
    if not texto:
        return 0.0, ""

    texto = texto.replace(" ", "")

    try:
        if "%" in texto:
            numero = texto.replace("%", "").replace("-", "").replace(",", ".")
            percentual = float(numero)
            desconto = valor_base * (percentual / 100)
            desconto = min(desconto, valor_base)
            return desconto, f"{percentual:.0f}%"

        texto_limpo = (
            texto.replace("r$", "")
            .replace("-", "")
            .replace(".", "")
            .replace(",", ".")
        )

        valor = float(texto_limpo)
        desconto = min(valor, valor_base)
        return desconto, formatar_real(desconto)

    except Exception:
        return 0.0, ""


CATALOGO = {
    "Brigadeiro de Chocolate": {"tipo": "unitario", "preco_cento": 125.00},
    "Brigadeiro de Ninho": {"tipo": "unitario", "preco_cento": 125.00},
    "Beijinho": {"tipo": "unitario", "preco_cento": 125.00},
    "Meio a Meio": {"tipo": "unitario", "preco_cento": 125.00},
    "Bicho de Pé": {"tipo": "unitario", "preco_cento": 125.00},
    "Moranguinho": {"tipo": "unitario", "preco_cento": 125.00},
    "Cajuzinho": {"tipo": "unitario", "preco_cento": 130.00},
    "Ninho com Nutella": {"tipo": "unitario", "preco_cento": 150.00},
    "Churros": {"tipo": "unitario", "preco_cento": 150.00},
    "Ferrero Rocher": {"tipo": "unitario", "preco_cento": 150.00},
    "Maracujá": {"tipo": "unitario", "preco_cento": 150.00},
    "Limão": {"tipo": "unitario", "preco_cento": 150.00},
    "Maçãzinha": {"tipo": "unitario", "preco_cento": 150.00},
    "Olho de Sogra": {"tipo": "unitario", "preco_cento": 150.00},
    "Oreo": {"tipo": "unitario", "preco_cento": 150.00},
    "Meio Amargo": {"tipo": "unitario", "preco_cento": 160.00},
    "Romeu e Julieta": {"tipo": "unitario", "preco_cento": 185.00},
    "Red Velvet": {"tipo": "unitario", "preco_cento": 185.00},
    "Ninho Temático": {"tipo": "unitario", "preco_cento": 160.00},
    "Aplique": {"tipo": "unitario", "preco_cento": 150.00},
    "Brigadeiro de Chocolate em massa": {"tipo": "kg", "preco_kg": 84.90},
}


def calcular_subtotal_item(item):
    if item["tipo"] == "unitario":
        subtotal_bruto = (item["preco_cento"] / 100) * item["qtd"]
    else:
        subtotal_bruto = (item["preco_kg"] / 1000) * item["gramas"]

    desconto_item_valor, desconto_item_desc = calcular_desconto(
        subtotal_bruto, item.get("desconto", "")
    )
    subtotal_final = subtotal_bruto - desconto_item_valor

    return subtotal_bruto, desconto_item_valor, desconto_item_desc, subtotal_final


def gerar_texto_item(item):
    if item["tipo"] == "unitario":
        return f"{item['qtd']}un - {item['produto']}"
    else:
        return f"{formatar_peso(item['gramas'])} - {item['produto']}"


def calcular_total_embalagens_pedido(embalagem_pedido):
    if embalagem_pedido.get("descricao", "").strip() and embalagem_pedido.get("valor", 0) > 0:
        return float(embalagem_pedido["valor"])
    return 0.0


def calcular_total_embalagens_especiais(embalagens_especiais):
    total = 0.0
    for emb in embalagens_especiais:
        total += float(emb["qtd"]) * float(emb["valor_unit"])
    return total


def calcular_total_adicionais(adicionais):
    total = 0.0
    for ad in adicionais:
        total += float(ad["valor"])
    return total


def gerar_imagem(
    cliente,
    data_entrega,
    itens,
    desconto_geral_str="",
    embalagem_pedido=None,
    embalagens_especiais=None,
    adicionais=None,
    observacao=""
):
    embalagem_pedido = embalagem_pedido or {"descricao": "", "valor": 0.0}
    embalagens_especiais = embalagens_especiais or []
    adicionais = adicionais or []

    W = 700
    total_linhas = len(itens) + len(embalagens_especiais) + len(adicionais)
    if embalagem_pedido.get("descricao", "").strip() and embalagem_pedido.get("valor", 0) > 0:
        total_linhas += 1

    if total_linhas <= 8:
        tam_fonte_item = 18
        espaco_linha = 42
    elif total_linhas <= 12:
        tam_fonte_item = 16
        espaco_linha = 36
    else:
        tam_fonte_item = 14
        espaco_linha = 30

    altura_cabecalho = 110
    altura_rodape = 170
    margem_inferior = 20

    cor_fundo_logo = (255, 195, 153)
    cor_marrom_logo = (65, 38, 30)
    cor_destaque = (210, 80, 30)
    cor_desconto = (180, 40, 40)
    cor_cinza = (140, 140, 140)
    cor_secao = (120, 70, 50)

    altura_obs = 0
    if observacao.strip():
        linhas_obs = 2 if len(observacao.strip()) > 75 else 1
        altura_obs = 40 + (linhas_obs * 22)

    y_pos = altura_cabecalho + 30
    y_itens_inicio = y_pos + 140
    y_itens_fim = y_itens_inicio + (total_linhas * espaco_linha)

    y_fim_conteudo = y_itens_fim + 370 + altura_obs
    y_topo_rodape = max(y_fim_conteudo + 80, 980)
    H = y_topo_rodape + altura_rodape + margem_inferior

    img = Image.new("RGB", (W, int(H)), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # CABEÇALHO
    draw.rectangle([0, 0, W, altura_cabecalho], fill=cor_fundo_logo)
    try:
        caminho_logo = BASE_DIR / "logo.png"
        logo = Image.open(caminho_logo).convert("RGBA")
        tamanho_logo = 130
        logo = logo.resize((tamanho_logo, tamanho_logo))
        pos_x = (W - tamanho_logo) // 2
        pos_y = (altura_cabecalho - tamanho_logo) // 2
        img.paste(logo, (pos_x, pos_y), logo)
    except Exception:
        draw.text(
            (220, 40),
            "DOCITO DOCERIA",
            fill=cor_marrom_logo,
            font=carregar_fonte(30, True)
        )

    # DADOS
    draw.text(
        (50, y_pos),
        "ORÇAMENTO DE DOCES",
        fill=cor_marrom_logo,
        font=carregar_fonte(26, True)
    )
    draw.text(
        (50, y_pos + 50),
        f"CLIENTE: {cliente.upper()}",
        fill=cor_marrom_logo,
        font=carregar_fonte(18, True)
    )
    draw.text(
        (50, y_pos + 80),
        f"ENTREGA: {data_entrega.strftime('%d/%m/%Y')}",
        fill=cor_destaque,
        font=carregar_fonte(18, True)
    )
    draw.line((50, y_pos + 115, 650, y_pos + 115), fill=cor_fundo_logo, width=3)

    # ITENS PRINCIPAIS
    y_itens = y_itens_inicio
    total_bruto_itens = 0
    total_desconto_itens = 0
    total_doces = 0
    total_gramas = 0
    fonte_item = carregar_fonte(tam_fonte_item)

    for item in itens:
        subtotal_bruto, desconto_item_valor, desconto_item_desc, subtotal_final = calcular_subtotal_item(item)

        total_bruto_itens += subtotal_bruto
        total_desconto_itens += desconto_item_valor

        if item["tipo"] == "unitario":
            total_doces += item["qtd"]
        else:
            total_gramas += item["gramas"]

        texto_item = gerar_texto_item(item)
        if desconto_item_desc:
            texto_item += f" (-{desconto_item_desc})"

        texto_valor = formatar_real(subtotal_final)

        draw.text((50, y_itens), texto_item, fill=cor_marrom_logo, font=fonte_item)

        bbox_valor = draw.textbbox((0, 0), texto_valor, font=fonte_item)
        largura_valor = bbox_valor[2] - bbox_valor[0]
        x_valor = 650 - largura_valor
        draw.text((x_valor, y_itens), texto_valor, fill=cor_marrom_logo, font=fonte_item)

        if desconto_item_valor > 0:
            detalhe_desc = f"Original: {formatar_real(subtotal_bruto)} | Desconto: -{formatar_real(desconto_item_valor)}"
            draw.text(
                (65, y_itens + 20),
                detalhe_desc,
                fill=cor_cinza,
                font=carregar_fonte(max(tam_fonte_item - 4, 11))
            )

        y_itens += espaco_linha

    # EMBALAGEM DO PEDIDO
    total_emb_pedido = calcular_total_embalagens_pedido(embalagem_pedido)
    if total_emb_pedido > 0:
        draw.text(
            (50, y_itens),
            f"Embalagem do pedido - {embalagem_pedido['descricao']}",
            fill=cor_secao,
            font=carregar_fonte(tam_fonte_item, True)
        )
        texto_valor = formatar_real(total_emb_pedido)
        bbox_valor = draw.textbbox((0, 0), texto_valor, font=fonte_item)
        largura_valor = bbox_valor[2] - bbox_valor[0]
        draw.text((650 - largura_valor, y_itens), texto_valor, fill=cor_secao, font=fonte_item)
        y_itens += espaco_linha

    # EMBALAGENS ESPECIAIS
    for emb in embalagens_especiais:
        total_emb_item = float(emb["qtd"]) * float(emb["valor_unit"])
        texto = f"Embalagem especial - {emb['qtd']}x {emb['descricao']}"
        texto_valor = formatar_real(total_emb_item)

        draw.text((50, y_itens), texto, fill=cor_secao, font=fonte_item)
        bbox_valor = draw.textbbox((0, 0), texto_valor, font=fonte_item)
        largura_valor = bbox_valor[2] - bbox_valor[0]
        draw.text((650 - largura_valor, y_itens), texto_valor, fill=cor_secao, font=fonte_item)

        y_itens += espaco_linha

    # ADICIONAIS
    for ad in adicionais:
        texto = f"Adicional - {ad['descricao']}"
        texto_valor = formatar_real(float(ad["valor"]))

        draw.text((50, y_itens), texto, fill=cor_secao, font=fonte_item)
        bbox_valor = draw.textbbox((0, 0), texto_valor, font=fonte_item)
        largura_valor = bbox_valor[2] - bbox_valor[0]
        draw.text((650 - largura_valor, y_itens), texto_valor, fill=cor_secao, font=fonte_item)

        y_itens += espaco_linha

    total_emb_especiais = calcular_total_embalagens_especiais(embalagens_especiais)
    total_adicionais = calcular_total_adicionais(adicionais)

    total_bruto_geral = total_bruto_itens + total_emb_pedido + total_emb_especiais + total_adicionais
    total_com_desconto_itens = total_bruto_geral - total_desconto_itens
    desconto_geral_valor, _ = calcular_desconto(total_com_desconto_itens, desconto_geral_str)
    total_final = total_com_desconto_itens - desconto_geral_valor

    # RESUMO
    draw.line((50, y_itens + 15, 650, y_itens + 15), fill=cor_fundo_logo, width=3)
    y_resumo = y_itens + 35

    if total_doces > 0:
        draw.text(
            (50, y_resumo),
            f"TOTAL DE DOCES: {total_doces}",
            fill=cor_marrom_logo,
            font=carregar_fonte(18, True),
        )
        y_resumo += 30

    if total_gramas > 0:
        draw.text(
            (50, y_resumo),
            f"PESO TOTAL: {formatar_peso(total_gramas)}",
            fill=cor_marrom_logo,
            font=carregar_fonte(18, True),
        )
        y_resumo += 35
    else:
        y_resumo += 5

    draw.text(
        (50, y_resumo),
        "Subtotal",
        fill=cor_marrom_logo,
        font=carregar_fonte(18, True),
    )
    draw.text(
        (520, y_resumo),
        formatar_real(total_bruto_geral),
        fill=cor_marrom_logo,
        font=carregar_fonte(18, True),
    )

    if total_emb_pedido > 0:
        y_resumo += 30
        draw.text((50, y_resumo), "Embalagem do pedido", fill=cor_cinza, font=carregar_fonte(14))
        draw.text((520, y_resumo), formatar_real(total_emb_pedido), fill=cor_cinza, font=carregar_fonte(14))

    if total_emb_especiais > 0:
        y_resumo += 25
        draw.text((50, y_resumo), "Embalagens especiais", fill=cor_cinza, font=carregar_fonte(14))
        draw.text((520, y_resumo), formatar_real(total_emb_especiais), fill=cor_cinza, font=carregar_fonte(14))

    if total_adicionais > 0:
        y_resumo += 25
        draw.text((50, y_resumo), "Adicionais", fill=cor_cinza, font=carregar_fonte(14))
        draw.text((520, y_resumo), formatar_real(total_adicionais), fill=cor_cinza, font=carregar_fonte(14))

    if total_desconto_itens > 0:
        y_resumo += 35
        draw.text(
            (50, y_resumo),
            "Desconto por itens",
            fill=cor_desconto,
            font=carregar_fonte(18, True),
        )
        draw.text(
            (520, y_resumo),
            f"-{formatar_real(total_desconto_itens)}",
            fill=cor_desconto,
            font=carregar_fonte(18, True),
        )

    if desconto_geral_valor > 0:
        y_resumo += 35
        draw.text(
            (50, y_resumo),
            "Desconto geral",
            fill=cor_desconto,
            font=carregar_fonte(18, True),
        )
        draw.text(
            (520, y_resumo),
            f"-{formatar_real(desconto_geral_valor)}",
            fill=cor_desconto,
            font=carregar_fonte(18, True),
        )

    if observacao.strip():
        y_resumo += 40
        draw.line((50, y_resumo, 650, y_resumo), fill=cor_fundo_logo, width=2)
        y_resumo += 20
        draw.text(
            (50, y_resumo),
            "OBSERVAÇÃO",
            fill=cor_marrom_logo,
            font=carregar_fonte(16, True),
        )
        y_resumo += 25
        draw.text(
            (50, y_resumo),
            observacao.strip(),
            fill=cor_marrom_logo,
            font=carregar_fonte(14),
        )

    y_resumo += 50
    draw.line((50, y_resumo, 650, y_resumo), fill=cor_fundo_logo, width=2)

    y_resumo += 25
    draw.text(
        (50, y_resumo),
        "TOTAL DO PEDIDO",
        fill=cor_marrom_logo,
        font=carregar_fonte(24, True),
    )

    texto_total = formatar_real(total_final)
    fonte_total = carregar_fonte(28, True)
    bbox_total = draw.textbbox((0, 0), texto_total, font=fonte_total)
    largura_total = bbox_total[2] - bbox_total[0]
    x_total = 650 - largura_total

    draw.text(
        (x_total, y_resumo),
        texto_total,
        fill=cor_destaque,
        font=fonte_total
    )

    # PAGAMENTO
    draw.text(
        (50, y_resumo + 50),
        "FORMAS DE PAGAMENTO",
        fill=cor_marrom_logo,
        font=carregar_fonte(16, True)
    )

    draw.text(
        (50, y_resumo + 75),
        "Pix | Dinheiro | Cartão | Criptomoedas",
        fill=cor_marrom_logo,
        font=carregar_fonte(16)
    )

    draw.text(
        (50, y_resumo + 100),
        "Cartão em até 12x (juros da maquininha)",
        fill=cor_marrom_logo,
        font=carregar_fonte(14)
    )

    draw.text(
        (50, y_resumo + 125),
        "Reserva mediante confirmação.",
        fill=cor_marrom_logo,
        font=carregar_fonte(14)
    )

    # VALIDADE
    fuso_br = pytz.timezone("America/Sao_Paulo")
    agora = datetime.now(fuso_br)
    texto_v = f"Gerado em: {agora.strftime('%d/%m/%Y %H:%M')} | Validade: 15 dias"
    fonte_v = carregar_fonte(11)
    bbox_v = draw.textbbox((0, 0), texto_v, font=fonte_v)
    largura_v = bbox_v[2] - bbox_v[0]

    draw.text(
        (W - largura_v - 50, y_topo_rodape - 25),
        texto_v,
        fill=(160, 160, 160),
        font=fonte_v
    )

    # RODAPÉ
    draw.rectangle([0, y_topo_rodape, W, H], fill=cor_fundo_logo)

    avisos = [
        "• Forminhas 4 pétalas (branca) inclusas.",
        "• Forminhas decorativas fornecidas pelo cliente",
        "  terão custo adicional por caixa extra utilizada.",
    ]
    for i, aviso in enumerate(avisos):
        draw.text(
            (45, y_topo_rodape + 15 + (i * 22)),
            aviso,
            fill=cor_marrom_logo,
            font=carregar_fonte(15)
        )

    y_linha = y_topo_rodape + 85
    draw.line((45, y_linha, 655, y_linha), fill=cor_marrom_logo, width=1)

    contatos = "Instagram: @docito_doceria123 | WhatsApp: (37) 99996-5194"
    fonte_contatos = carregar_fonte(14, True)
    bbox_contatos = draw.textbbox((0, 0), contatos, font=fonte_contatos)
    largura_contatos = bbox_contatos[2] - bbox_contatos[0]
    pos_x_contatos = (W - largura_contatos) // 2

    draw.text(
        (pos_x_contatos, y_linha + 12),
        contatos,
        fill=cor_marrom_logo,
        font=fonte_contatos
    )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


st.set_page_config(page_title="Docito Doceria - Orçamentos", page_icon="🍰")

try:
    st.image(str(BASE_DIR / "logo.png"), width=100)
except Exception:
    st.title("🍰 DOCITO DOCERIA")

st.title("Gerador de Orçamentos")

if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

if "desconto_geral" not in st.session_state:
    st.session_state.desconto_geral = ""

if "embalagem_pedido" not in st.session_state:
    st.session_state.embalagem_pedido = {"descricao": "", "valor": 0.0}

if "embalagens_especiais" not in st.session_state:
    st.session_state.embalagens_especiais = []

if "adicionais" not in st.session_state:
    st.session_state.adicionais = []

if "observacao" not in st.session_state:
    st.session_state.observacao = ""

col_c1, col_c2 = st.columns(2)
with col_c1:
    cliente = st.text_input("Nome da Cliente")
with col_c2:
    data_ent = st.date_input("Data da Entrega", value=datetime.now())

st.divider()

# PRODUTOS
st.subheader("Adicionar produtos")
produto_selecionado = st.selectbox("Produto", list(CATALOGO.keys()))
dados_produto = CATALOGO[produto_selecionado]

if dados_produto["tipo"] == "unitario":
    c1, c2, c3, c4 = st.columns([3, 1, 1.3, 1])

    with c1:
        st.text_input("Tipo de cobrança", value="Por unidade", disabled=True, key="tipo_unitario")
    with c2:
        qtd_unit = st.number_input("Qtd", min_value=1, value=50, step=1)
    with c3:
        desconto_novo_item = st.text_input("Desconto Item", placeholder="Ex.: 10% ou R$2", key="desc_item_unit")
    with c4:
        st.write(" ")
        if st.button("➕ Adicionar produto"):
            st.session_state.carrinho.append(
                {
                    "produto": produto_selecionado,
                    "tipo": "unitario",
                    "qtd": int(qtd_unit),
                    "preco_cento": dados_produto["preco_cento"],
                    "desconto": desconto_novo_item.strip(),
                }
            )
            st.rerun()

else:
    c1, c2, c3, c4, c5 = st.columns([2.2, 1.2, 1.2, 1.3, 1])

    with c1:
        st.text_input(
            "Tipo de cobrança",
            value=f"Por peso ({formatar_real(dados_produto['preco_kg'])}/kg)",
            disabled=True,
            key="tipo_kg"
        )
    with c2:
        unidade_peso = st.selectbox("Unidade", ["kg", "g"], key="unidade_nova")
    with c3:
        if unidade_peso == "kg":
            valor_peso = st.number_input("Quantidade", min_value=0.1, value=1.0, step=0.1, format="%.3f", key="peso_novo_kg")
            gramas_item = int(round(valor_peso * 1000))
        else:
            valor_peso = st.number_input("Quantidade", min_value=100, value=1000, step=50, key="peso_novo_g")
            gramas_item = int(valor_peso)
    with c4:
        desconto_novo_item = st.text_input("Desconto Item", placeholder="Ex.: 10% ou R$2", key="desc_kg_novo")
    with c5:
        st.write(" ")
        if st.button("➕ Adicionar produto em massa"):
            st.session_state.carrinho.append(
                {
                    "produto": produto_selecionado,
                    "tipo": "kg",
                    "gramas": int(gramas_item),
                    "preco_kg": dados_produto["preco_kg"],
                    "desconto": desconto_novo_item.strip(),
                }
            )
            st.rerun()

st.divider()

# EMBALAGEM DO PEDIDO
st.subheader("Embalagem do pedido (opcional)")
e1, e2, e3 = st.columns([3, 1.2, 1])
with e1:
    emb_pedido_desc = st.text_input(
        "Descrição da embalagem do pedido",
        value=st.session_state.embalagem_pedido["descricao"],
        placeholder="Ex.: Pote premium / Caixa especial"
    )
with e2:
    emb_pedido_valor = st.number_input(
        "Valor",
        min_value=0.0,
        value=float(st.session_state.embalagem_pedido["valor"]),
        step=0.5,
        format="%.2f"
    )
with e3:
    st.write(" ")
    if st.button("Salvar embalagem do pedido"):
        st.session_state.embalagem_pedido = {
            "descricao": emb_pedido_desc.strip(),
            "valor": float(emb_pedido_valor),
        }
        st.rerun()

# EMBALAGENS ESPECIAIS
st.divider()
st.subheader("Embalagens especiais/unitárias (opcional)")
ee1, ee2, ee3, ee4 = st.columns([2.5, 1, 1.2, 1])
with ee1:
    emb_esp_desc = st.text_input("Descrição", placeholder="Ex.: Caixa premium / Pote individual", key="emb_esp_desc")
with ee2:
    emb_esp_qtd = st.number_input("Qtd", min_value=1, value=1, step=1, key="emb_esp_qtd")
with ee3:
    emb_esp_valor = st.number_input("Valor unit.", min_value=0.0, value=0.0, step=0.5, format="%.2f", key="emb_esp_valor")
with ee4:
    st.write(" ")
    if st.button("➕ Adicionar embalagem especial"):
        if emb_esp_desc.strip() and emb_esp_valor > 0:
            st.session_state.embalagens_especiais.append(
                {
                    "descricao": emb_esp_desc.strip(),
                    "qtd": int(emb_esp_qtd),
                    "valor_unit": float(emb_esp_valor),
                }
            )
            st.rerun()

if st.session_state.embalagens_especiais:
    st.caption("Embalagens especiais adicionadas")
    for i, emb in enumerate(st.session_state.embalagens_especiais):
        c1, c2 = st.columns([5, 1])
        total_emb = float(emb["qtd"]) * float(emb["valor_unit"])
        c1.write(f"**{emb['qtd']}x {emb['descricao']}** — {formatar_real(total_emb)}")
        if c2.button("❌", key=f"del_emb_{i}"):
            st.session_state.embalagens_especiais.pop(i)
            st.rerun()

# ADICIONAIS
st.divider()
st.subheader("Adicionais (opcional)")
a1, a2, a3 = st.columns([3, 1.2, 1])
with a1:
    adicional_desc = st.text_input("Descrição do adicional", placeholder="Ex.: Caixa extra / Taxa de entrega", key="adicional_desc")
with a2:
    adicional_valor = st.number_input("Valor do adicional", min_value=0.0, value=0.0, step=0.5, format="%.2f", key="adicional_valor")
with a3:
    st.write(" ")
    if st.button("➕ Adicionar adicional"):
        if adicional_desc.strip() and adicional_valor > 0:
            st.session_state.adicionais.append(
                {
                    "descricao": adicional_desc.strip(),
                    "valor": float(adicional_valor),
                }
            )
            st.rerun()

if st.session_state.adicionais:
    st.caption("Adicionais adicionados")
    for i, ad in enumerate(st.session_state.adicionais):
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{ad['descricao']}** — {formatar_real(float(ad['valor']))}")
        if c2.button("❌", key=f"del_ad_{i}"):
            st.session_state.adicionais.pop(i)
            st.rerun()

# OBSERVAÇÃO
st.divider()
st.subheader("Observação (opcional)")
observacao = st.text_area(
    "Observação do orçamento",
    value=st.session_state.observacao,
    placeholder="Ex.: Produto enviado em embalagem especial para consumo de colher."
)
st.session_state.observacao = observacao

# DESCONTO GERAL
st.divider()
st.subheader("Desconto geral do pedido")
desconto_geral = st.text_input(
    "Desconto Geral",
    value=st.session_state.desconto_geral,
    placeholder="Ex.: 10% ou R$20"
)
st.session_state.desconto_geral = desconto_geral

# RESUMO
tem_conteudo = (
    st.session_state.carrinho
    or (st.session_state.embalagem_pedido.get("descricao", "").strip() and st.session_state.embalagem_pedido.get("valor", 0) > 0)
    or st.session_state.embalagens_especiais
    or st.session_state.adicionais
)

if tem_conteudo:
    st.subheader("🛒 Itens Selecionados")

    total_bruto_preview_itens = 0
    total_desc_itens_preview = 0
    total_doces_preview = 0
    total_gramas_preview = 0

    for i, item in enumerate(st.session_state.carrinho):
        subtotal_bruto, desconto_item_valor, _, subtotal_final = calcular_subtotal_item(item)

        total_bruto_preview_itens += subtotal_bruto
        total_desc_itens_preview += desconto_item_valor

        if item["tipo"] == "unitario":
            total_doces_preview += item["qtd"]

            col_prod, col_qtd, col_desc, col_bt = st.columns([3, 1, 1.4, 0.5])

            col_prod.write(
                f"**{item['produto']}**  \n"
                f"{item['qtd']}un | {formatar_real(subtotal_bruto)} → **{formatar_real(subtotal_final)}**"
            )

            nova_qtd = col_qtd.number_input(
                "Qtd",
                min_value=1,
                value=int(item["qtd"]),
                key=f"edit_qtd_{i}",
                label_visibility="collapsed",
            )

            novo_desc = col_desc.text_input(
                "Desconto",
                value=item.get("desconto", ""),
                key=f"desc_{i}",
                placeholder="10% ou R$2",
                label_visibility="collapsed",
            )

            alterou = False

            if nova_qtd != item["qtd"]:
                st.session_state.carrinho[i]["qtd"] = int(nova_qtd)
                alterou = True

            if novo_desc != item.get("desconto", ""):
                st.session_state.carrinho[i]["desconto"] = novo_desc.strip()
                alterou = True

            if alterou:
                st.rerun()

            if col_bt.button("❌", key=f"del_{i}"):
                st.session_state.carrinho.pop(i)
                st.rerun()

        else:
            total_gramas_preview += item["gramas"]

            col_prod, col_unid, col_qtd, col_desc, col_bt = st.columns([2.4, 1, 1.2, 1.4, 0.5])

            col_prod.write(
                f"**{item['produto']}**  \n"
                f"{formatar_peso(item['gramas'])} | {formatar_real(subtotal_bruto)} → **{formatar_real(subtotal_final)}**"
            )

            unidade_edit = col_unid.selectbox(
                "Unidade",
                ["kg", "g"],
                index=0 if item["gramas"] % 1000 == 0 else 1,
                key=f"unidade_edit_{i}",
                label_visibility="collapsed",
            )

            if unidade_edit == "kg":
                valor_padrao = item["gramas"] / 1000
                novo_valor_peso = col_qtd.number_input(
                    "Quantidade",
                    min_value=0.1,
                    value=float(valor_padrao),
                    step=0.1,
                    format="%.3f",
                    key=f"peso_kg_{i}",
                    label_visibility="collapsed",
                )
                novas_gramas = int(round(novo_valor_peso * 1000))
            else:
                novo_valor_peso = col_qtd.number_input(
                    "Quantidade",
                    min_value=100,
                    value=int(item["gramas"]),
                    step=50,
                    key=f"peso_g_{i}",
                    label_visibility="collapsed",
                )
                novas_gramas = int(novo_valor_peso)

            novo_desc = col_desc.text_input(
                "Desconto",
                value=item.get("desconto", ""),
                key=f"desc_kg_{i}",
                placeholder="10% ou R$2",
                label_visibility="collapsed",
            )

            alterou = False

            if novas_gramas != item["gramas"]:
                st.session_state.carrinho[i]["gramas"] = int(novas_gramas)
                alterou = True

            if novo_desc != item.get("desconto", ""):
                st.session_state.carrinho[i]["desconto"] = novo_desc.strip()
                alterou = True

            if alterou:
                st.rerun()

            if col_bt.button("❌", key=f"del_kg_{i}"):
                st.session_state.carrinho.pop(i)
                st.rerun()

    total_emb_pedido_preview = calcular_total_embalagens_pedido(st.session_state.embalagem_pedido)
    total_emb_especiais_preview = calcular_total_embalagens_especiais(st.session_state.embalagens_especiais)
    total_adicionais_preview = calcular_total_adicionais(st.session_state.adicionais)

    total_bruto_preview = (
        total_bruto_preview_itens
        + total_emb_pedido_preview
        + total_emb_especiais_preview
        + total_adicionais_preview
    )

    total_apos_itens_preview = total_bruto_preview - total_desc_itens_preview
    desconto_geral_preview, _ = calcular_desconto(
        total_apos_itens_preview, st.session_state.desconto_geral
    )
    total_final_preview = total_apos_itens_preview - desconto_geral_preview

    st.divider()
    st.subheader("Resumo")

    if total_doces_preview > 0:
        st.write(f"**Total de doces:** {total_doces_preview}")

    if total_gramas_preview > 0:
        st.write(f"**Peso total:** {formatar_peso(total_gramas_preview)}")

    if total_emb_pedido_preview > 0:
        st.write(f"**Embalagem do pedido:** {formatar_real(total_emb_pedido_preview)}")

    if total_emb_especiais_preview > 0:
        st.write(f"**Embalagens especiais:** {formatar_real(total_emb_especiais_preview)}")

    if total_adicionais_preview > 0:
        st.write(f"**Adicionais:** {formatar_real(total_adicionais_preview)}")

    st.write(f"**Subtotal:** {formatar_real(total_bruto_preview)}")

    if total_desc_itens_preview > 0:
        st.write(f"**Desconto por itens:** -{formatar_real(total_desc_itens_preview)}")

    if desconto_geral_preview > 0:
        st.write(f"**Desconto geral:** -{formatar_real(desconto_geral_preview)}")

    if st.session_state.observacao.strip():
        st.write(f"**Observação:** {st.session_state.observacao.strip()}")

    st.write(f"## Total final: {formatar_real(total_final_preview)}")

    if st.button("LIMPAR TUDO", type="secondary"):
        st.session_state.carrinho = []
        st.session_state.desconto_geral = ""
        st.session_state.embalagem_pedido = {"descricao": "", "valor": 0.0}
        st.session_state.embalagens_especiais = []
        st.session_state.adicionais = []
        st.session_state.observacao = ""
        st.rerun()

    if st.button("GERAR IMAGEM FINAL", type="primary", use_container_width=True):
        if cliente.strip():
            with st.spinner("Gerando orçamento..."):
                res = gerar_imagem(
                    cliente=cliente,
                    data_entrega=data_ent,
                    itens=st.session_state.carrinho,
                    desconto_geral_str=st.session_state.desconto_geral,
                    embalagem_pedido=st.session_state.embalagem_pedido,
                    embalagens_especiais=st.session_state.embalagens_especiais,
                    adicionais=st.session_state.adicionais,
                    observacao=st.session_state.observacao
                )
                st.image(res)

                col_b1, col_b2 = st.columns(2)

                with col_b1:
                    st.download_button(
                        "📥 Baixar Orçamento",
                        res,
                        f"Docito_{cliente.strip()}.png",
                        "image/png",
                    )

                with col_b2:
                    img_base64 = base64.b64encode(res.getvalue()).decode()

                    copy_script = f"""
                    <button onclick="copyImage()" style="
                        width: 100%;
                        background-color: #d86a2b;
                        color: white;
                        border: none;
                        padding: 0.6rem 1rem;
                        border-radius: 0.5rem;
                        cursor: pointer;
                        font-size: 14px;
                        font-weight: 600;
                    ">
                        📋 Copiar imagem
                    </button>

                    <script>
                    async function copyImage() {{
                        try {{
                            const response = await fetch("data:image/png;base64,{img_base64}");
                            const blob = await response.blob();
                            const item = new ClipboardItem({{"image/png": blob}});
                            await navigator.clipboard.write([item]);
                            alert("Imagem copiada! Agora é só colar no WhatsApp.");
                        }} catch (err) {{
                            alert("Seu navegador pode não permitir copiar imagem diretamente. Use o botão de baixar.");
                        }}
                    }}
                    </script>
                    """
                    st.components.v1.html(copy_script, height=55)
        else:
            st.warning("Por favor, preencha o nome da cliente!")
