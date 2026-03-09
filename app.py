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


st.set_page_config(page_title="Docito Doceria - Orçamentos", page_icon="🍰")

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


def gerar_imagem(cliente, data_entrega, itens):
    W = 600
    num_itens = len(itens)

    if num_itens <= 8:
        tam_fonte_item = 18
        espaco_linha = 35
    elif num_itens <= 12:
        tam_fonte_item = 16
        espaco_linha = 30
    else:
        tam_fonte_item = 14
        espaco_linha = 25

    altura_cabecalho = 110
    altura_rodape = 135
    margem_inferior = 20

    cor_fundo_logo = (255, 195, 153)
    cor_marrom_logo = (65, 38, 30)
    cor_destaque = (210, 80, 30)

    # --- CÁLCULO ROBUSTO DA ALTURA ---
    y_pos = altura_cabecalho + 30
    y_itens_inicio = y_pos + 140
    y_itens_fim = y_itens_inicio + (num_itens * espaco_linha)

    # Último elemento do bloco de conteúdo antes da área "Gerado em..."
    y_fim_conteudo = y_itens_fim + 200  # reserva para total + pagamento + reserva

    # Topo do rodapé precisa ficar abaixo do conteúdo
    # com folga para o "Gerado em..."
    y_topo_rodape = max(y_fim_conteudo + 80, 760)

    # Altura total da imagem
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
            (180, 40),
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
    draw.line((50, y_pos + 115, 550, y_pos + 115), fill=cor_fundo_logo, width=3)

    # --- LISTA DE ITENS ---
    y_itens = y_itens_inicio
    total_geral = 0
    total_doces = 0
    fonte_item = carregar_fonte(tam_fonte_item)

    for item in itens:
        subtotal = (item["preco_cento"] / 100) * item["qtd"]
        total_geral += subtotal
        total_doces += item["qtd"]

        texto_item = f"{item['qtd']}un - {item['produto']}"
        texto_valor = f"R$ {subtotal:.2f}"

        draw.text((50, y_itens), texto_item, fill=cor_marrom_logo, font=fonte_item)

        bbox_valor = draw.textbbox((0, 0), texto_valor, font=fonte_item)
        largura_valor = bbox_valor[2] - bbox_valor[0]
        x_valor = 550 - largura_valor
        draw.text((x_valor, y_itens), texto_valor, fill=cor_marrom_logo, font=fonte_item)

        y_itens += espaco_linha

    # --- TOTAL ---
    draw.line((50, y_itens + 15, 550, y_itens + 15), fill=cor_fundo_logo, width=3)

    draw.text(
        (50, y_itens + 35),
        f"TOTAL DE DOCES: {total_doces}",
        fill=cor_marrom_logo,
        font=carregar_fonte(18, True),
    )

    draw.text(
        (50, y_itens + 70),
        "TOTAL DO PEDIDO",
        fill=cor_marrom_logo,
        font=carregar_fonte(22, True),
    )

    texto_total = f"R$ {total_geral:.2f}"
    fonte_total = carregar_fonte(24, True)
    bbox_total = draw.textbbox((0, 0), texto_total, font=fonte_total)
    largura_total = bbox_total[2] - bbox_total[0]
    x_total = 550 - largura_total

    draw.text(
        (x_total, y_itens + 70),
        texto_total,
        fill=cor_destaque,
        font=fonte_total
    )

    draw.line((50, y_itens + 110, 550, y_itens + 110), fill=cor_fundo_logo, width=2)

    # --- FORMAS DE PAGAMENTO ---
    draw.text(
        (50, y_itens + 125),
        "FORMAS DE PAGAMENTO",
        fill=cor_marrom_logo,
        font=carregar_fonte(16, True)
    )

    draw.text(
        (50, y_itens + 150),
        "Pix | Dinheiro | Cartão | Crypto",
        fill=cor_marrom_logo,
        font=carregar_fonte(16)
    )

    draw.text(
        (50, y_itens + 175),
        "Cartão em até 12x (juros da maquininha)",
        fill=cor_marrom_logo,
        font=carregar_fonte(14)
    )

    draw.text(
        (50, y_itens + 200),
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

    # Posiciona acima do rodapé, com segurança
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

    y_linha = y_topo_rodape + 80
    draw.line((45, y_linha, 555, y_linha), fill=cor_marrom_logo, width=1)

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


try:
    st.image(str(BASE_DIR / "logo.png"), width=100)
except Exception:
    st.title("🍰 DOCITO DOCERIA")

st.title("Gerador de Orçamentos")

if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

col_c1, col_c2 = st.columns(2)
with col_c1:
    cliente = st.text_input("Nome da Cliente")
with col_c2:
    data_ent = st.date_input("Data da Entrega", value=datetime.now())

st.divider()

c1, c2, c3 = st.columns([3, 1, 1])
with c1:
    p = st.selectbox("Produto", list(CATALOGO.keys()))
with c2:
    q = st.number_input("Qtd", min_value=1, value=50)
with c3:
    st.write(" ")
    if st.button("➕ Adicionar"):
        st.session_state.carrinho.append(
            {"produto": p, "qtd": int(q), "preco_cento": CATALOGO[p]}
        )
        st.rerun()

if st.session_state.carrinho:
    st.subheader("🛒 Itens Selecionados")

    h_col1, h_col2, h_col3 = st.columns([3, 1, 0.5])
    h_col1.caption("Produto")
    h_col2.caption("Qtd (Editar)")
    h_col3.write("")

    for i, item in enumerate(st.session_state.carrinho):
        col_prod, col_qtd, col_bt = st.columns([3, 1, 0.5])

        col_prod.write(f"**{item['produto']}**")

        nova_qtd = col_qtd.number_input(
            "Qtd",
            min_value=1,
            value=int(item["qtd"]),
            key=f"edit_{i}",
            label_visibility="collapsed",
        )

        if nova_qtd != item["qtd"]:
            st.session_state.carrinho[i]["qtd"] = int(nova_qtd)
            st.rerun()

        if col_bt.button("❌", key=f"del_{i}"):
            st.session_state.carrinho.pop(i)
            st.rerun()

    st.divider()

    if st.button("LIMPAR TUDO", type="secondary"):
        st.session_state.carrinho = []
        st.rerun()

    if st.button("GERAR IMAGEM FINAL", type="primary", use_container_width=True):
        if cliente.strip():
            with st.spinner("Gerando orçamento..."):
                res = gerar_imagem(cliente, data_ent, st.session_state.carrinho)
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
