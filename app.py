import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import io
import pytz
from pathlib import Path
import base64
import re

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


def calcular_desconto(valor_base, desconto_str):
    """
    Aceita:
    - 10%
    - -10%
    - R$2
    - -R$2
    - 2
    - 2,50

    Retorna:
    desconto_aplicado (float), descricao_formatada (str)
    """
    if not desconto_str:
        return 0.0, ""

    texto = str(desconto_str).strip().lower()
    if not texto:
        return 0.0, ""

    # Remove espaços
    texto = texto.replace(" ", "")

    try:
        # Desconto percentual
        if "%" in texto:
            numero = texto.replace("%", "").replace("-", "").replace(",", ".")
            percentual = float(numero)
            desconto = valor_base * (percentual / 100)
            desconto = min(desconto, valor_base)
            return desconto, f"{percentual:.0f}%"

        # Desconto em reais
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
    "Brigadeiro Chocolate": 125.00,
    "Brigadeiro Ninho": 125.00,
    "Beijinho": 125.00,
    "Meio a Meio": 125.00,
    "Bicho de Pé": 125.00,
    "Moranguinho": 125.00,
    "Cajuzinho": 130.00,
    "Ninho com Nutella": 150.00,
    "Churros": 150.00,
    "Ferrero Rocher": 150.00,
    "Maracujá": 150.00,
    "Limão": 150.00,
    "Maçãzinha": 150.00,
    "Olho de Sogra": 150.00,
    "Oreo": 150.00,
    "Meio Amargo": 160.00,
    "Romeu e Julieta": 185.00,
    "Red Velvet": 185.00,
    "Ninho Temático": 160.00,
    "Aplique": 150.00,
}


def gerar_imagem(cliente, data_entrega, itens, desconto_geral_str=""):
    W = 700
    num_itens = len(itens)

    if num_itens <= 8:
        tam_fonte_item = 18
        espaco_linha = 42
    elif num_itens <= 12:
        tam_fonte_item = 16
        espaco_linha = 36
    else:
        tam_fonte_item = 14
        espaco_linha = 30

    altura_cabecalho = 110
    altura_rodape = 150
    margem_inferior = 20

    cor_fundo_logo = (255, 195, 153)
    cor_marrom_logo = (65, 38, 30)
    cor_destaque = (210, 80, 30)
    cor_desconto = (180, 40, 40)
    cor_cinza = (140, 140, 140)

    y_pos = altura_cabecalho + 30
    y_itens_inicio = y_pos + 140
    y_itens_fim = y_itens_inicio + (num_itens * espaco_linha)

    y_fim_conteudo = y_itens_fim + 300
    y_topo_rodape = max(y_fim_conteudo + 80, 900)
    H = y_topo_rodape + altura_rodape + margem_inferior

    img = Image.new("RGB", (W, int(H)), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # --- CABEÇALHO ---
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

    # --- DADOS DO CLIENTE ---
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

    # --- LISTA DE ITENS ---
    y_itens = y_itens_inicio
    total_bruto = 0
    total_desconto_itens = 0
    total_doces = 0
    fonte_item = carregar_fonte(tam_fonte_item)

    for item in itens:
        subtotal_bruto = (item["preco_cento"] / 100) * item["qtd"]
        desconto_item_valor, desconto_item_desc = calcular_desconto(
            subtotal_bruto, item.get("desconto", "")
        )
        subtotal_final = subtotal_bruto - desconto_item_valor

        total_bruto += subtotal_bruto
        total_desconto_itens += desconto_item_valor
        total_doces += item["qtd"]

        texto_item = f"{item['qtd']}un - {item['produto']}"
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

    total_com_desconto_itens = total_bruto - total_desconto_itens
    desconto_geral_valor, desconto_geral_desc = calcular_desconto(
        total_com_desconto_itens, desconto_geral_str
    )
    total_final = total_com_desconto_itens - desconto_geral_valor

    # --- TOTAIS ---
    draw.line((50, y_itens + 15, 650, y_itens + 15), fill=cor_fundo_logo, width=3)

    draw.text(
        (50, y_itens + 35),
        f"TOTAL DE DOCES: {total_doces}",
        fill=cor_marrom_logo,
        font=carregar_fonte(18, True),
    )

    draw.text(
        (50, y_itens + 70),
        "Subtotal",
        fill=cor_marrom_logo,
        font=carregar_fonte(18, True),
    )
    draw.text(
        (520, y_itens + 70),
        formatar_real(total_bruto),
        fill=cor_marrom_logo,
        font=carregar_fonte(18, True),
    )

    draw.text(
        (50, y_itens + 105),
        "Desconto por itens",
        fill=cor_desconto,
        font=carregar_fonte(18, True),
    )
    draw.text(
        (520, y_itens + 105),
        f"-{formatar_real(total_desconto_itens)}",
        fill=cor_desconto,
        font=carregar_fonte(18, True),
    )

    draw.text(
        (50, y_itens + 140),
        "Desconto geral",
        fill=cor_desconto,
        font=carregar_fonte(18, True),
    )
    draw.text(
        (520, y_itens + 140),
        f"-{formatar_real(desconto_geral_valor)}",
        fill=cor_desconto,
        font=carregar_fonte(18, True),
    )

    draw.line((50, y_itens + 180, 650, y_itens + 180), fill=cor_fundo_logo, width=2)

    draw.text(
        (50, y_itens + 205),
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
        (x_total, y_itens + 205),
        texto_total,
        fill=cor_destaque,
        font=fonte_total
    )

    # --- FORMAS DE PAGAMENTO ---
    draw.text(
        (50, y_itens + 255),
        "FORMAS DE PAGAMENTO",
        fill=cor_marrom_logo,
        font=carregar_fonte(16, True)
    )

    draw.text(
        (50, y_itens + 280),
        "Pix | Dinheiro | Cartão | Crypto",
        fill=cor_marrom_logo,
        font=carregar_fonte(16)
    )

    draw.text(
        (50, y_itens + 305),
        "Cartão em até 12x (juros da maquininha)",
        fill=cor_marrom_logo,
        font=carregar_fonte(14)
    )

    draw.text(
        (50, y_itens + 330),
        "Reserva mediante confirmação.",
        fill=cor_marrom_logo,
        font=carregar_fonte(14)
    )

    # --- VALIDADE ---
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

    # --- RODAPÉ ---
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

col_c1, col_c2 = st.columns(2)
with col_c1:
    cliente = st.text_input("Nome da Cliente")
with col_c2:
    data_ent = st.date_input("Data da Entrega", value=datetime.now())

st.divider()

c1, c2, c3, c4 = st.columns([3, 1, 1.3, 1])
with c1:
    p = st.selectbox("Produto", list(CATALOGO.keys()))
with c2:
    q = st.number_input("Qtd", min_value=1, value=50)
with c3:
    desconto_novo_item = st.text_input("Desconto Item", placeholder="Ex.: 10% ou R$2")
with c4:
    st.write(" ")
    if st.button("➕ Adicionar"):
        st.session_state.carrinho.append(
            {
                "produto": p,
                "qtd": int(q),
                "preco_cento": CATALOGO[p],
                "desconto": desconto_novo_item.strip(),
            }
        )
        st.rerun()

st.divider()

st.subheader("Desconto geral do pedido")
desconto_geral = st.text_input(
    "Desconto Geral",
    value=st.session_state.desconto_geral,
    placeholder="Ex.: 10% ou R$20"
)
st.session_state.desconto_geral = desconto_geral

if st.session_state.carrinho:
    st.subheader("🛒 Itens Selecionados")

    h_col1, h_col2, h_col3, h_col4 = st.columns([3, 1, 1.4, 0.5])
    h_col1.caption("Produto")
    h_col2.caption("Qtd")
    h_col3.caption("Desconto")
    h_col4.write("")

    total_bruto_preview = 0
    total_desc_itens_preview = 0

    for i, item in enumerate(st.session_state.carrinho):
        col_prod, col_qtd, col_desc, col_bt = st.columns([3, 1, 1.4, 0.5])

        subtotal_bruto = (item["preco_cento"] / 100) * item["qtd"]
        desconto_item_valor, _ = calcular_desconto(subtotal_bruto, item.get("desconto", ""))
        subtotal_final = subtotal_bruto - desconto_item_valor

        total_bruto_preview += subtotal_bruto
        total_desc_itens_preview += desconto_item_valor

        col_prod.write(
            f"**{item['produto']}**  \n"
            f"{formatar_real(subtotal_bruto)} → **{formatar_real(subtotal_final)}**"
        )

        nova_qtd = col_qtd.number_input(
            "Qtd",
            min_value=1,
            value=int(item["qtd"]),
            key=f"edit_{i}",
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

    total_apos_itens_preview = total_bruto_preview - total_desc_itens_preview
    desconto_geral_preview, _ = calcular_desconto(
        total_apos_itens_preview, st.session_state.desconto_geral
    )
    total_final_preview = total_apos_itens_preview - desconto_geral_preview

    st.divider()
    st.subheader("Resumo")
    st.write(f"**Subtotal:** {formatar_real(total_bruto_preview)}")
    st.write(f"**Desconto por itens:** -{formatar_real(total_desc_itens_preview)}")
    st.write(f"**Desconto geral:** -{formatar_real(desconto_geral_preview)}")
    st.write(f"## Total final: {formatar_real(total_final_preview)}")

    if st.button("LIMPAR TUDO", type="secondary"):
        st.session_state.carrinho = []
        st.session_state.desconto_geral = ""
        st.rerun()

    if st.button("GERAR IMAGEM FINAL", type="primary", use_container_width=True):
        if cliente.strip():
            with st.spinner("Gerando orçamento..."):
                res = gerar_imagem(
                    cliente,
                    data_ent,
                    st.session_state.carrinho,
                    st.session_state.desconto_geral
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
