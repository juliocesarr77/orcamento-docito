import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import io
import pytz

def carregar_fonte(tamanho, negrito=False):
    fonte = "DejaVuSans-Bold.ttf" if negrito else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(fonte, tamanho)
    except:
        return ImageFont.load_default()

# --- 1. CONFIGURAÇÕES DA PÁGINA ---
st.set_page_config(page_title="Docito Doceria - Orçamentos", page_icon="🍰")

# --- 2. TABELA DE PREÇOS (CATÁLOGO) ---
CATALOGO = {
    "Brigadeiro Chocolate": 125.00, "Brigadeiro Ninho": 125.00,
    "Beijinho": 125.00, "Meio a Meio": 125.00,
    "Bicho de Pé": 125.00, "Moranguinho": 125.00,
    "Cajuzinho": 130.00, "Ninho com Nutella": 150.00,
    "Churros": 150.00, "Ferrero Rocher": 150.00,
    "Maracujá": 150.00, "Limão": 150.00,
    "Maçãzinha": 150.00, "Olho de Sogra": 150.00,
    "Oreo": 150.00, "Meio Amargo": 160.00,
    "Romeu e Julieta": 185.00, "Red Velvet": 185.00,
    "Ninho Temático": 160.00, "Aplique": 150.00
}

# --- 3. LÓGICA DE GERAÇÃO DA IMAGEM ---
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
    altura_dados_cliente = 220
    altura_rodape = 150
    H_dinamico = altura_cabecalho + altura_dados_cliente + (num_itens * espaco_linha) + altura_rodape
    H = max(H_dinamico, 800)

    cor_fundo_logo = (255, 195, 153)
    cor_marrom_logo = (65, 38, 30)
    cor_destaque = (210, 80, 30)
    
    img = Image.new('RGB', (W, int(H)), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # --- CABEÇALHO ---
    draw.rectangle([0, 0, W, altura_cabecalho], fill=cor_fundo_logo)
    try:
        logo = Image.open("logo.png").convert("RGBA")
        tamanho_logo = 130
        logo = logo.resize((tamanho_logo, tamanho_logo))
        pos_x = (W - tamanho_logo) // 2
        pos_y = (altura_cabecalho - tamanho_logo) // 2
        img.paste(logo, (pos_x, pos_y), logo)
    except:
        draw.text((180, 40), "DOCITO DOCERIA", fill=cor_marrom_logo, font=carregar_fonte(30, True))

    # --- DADOS DO CLIENTE ---
    y_pos = altura_cabecalho + 30
    draw.text((50, y_pos), "ORÇAMENTO DE DOCES", fill=cor_marrom_logo, font=carregar_fonte(26, True))
    draw.text((50, y_pos + 50), f"CLIENTE: {cliente.upper()}", fill=cor_marrom_logo, font=carregar_fonte(18, True))
    draw.text((50, y_pos + 80), f"ENTREGA: {data_entrega.strftime('%d/%m/%Y')}", fill=cor_destaque, font=carregar_fonte(18, True))
    draw.line((50, y_pos + 115, 550, y_pos + 115), fill=cor_fundo_logo, width=3)
    
    # --- LISTA DE ITENS ---
    y_itens = y_pos + 140
    total_geral = 0
    fonte_item = carregar_fonte(tam_fonte_item)
    
    for item in itens:
        subtotal = (item['preco_cento'] / 100) * item['qtd']
        total_geral += subtotal
        draw.text((50, y_itens), f"{item['qtd']}un - {item['produto']}", fill=cor_marrom_logo, font=fonte_item)
        draw.text((450, y_itens), f"R$ {subtotal:>8.2f}", fill=cor_marrom_logo, font=fonte_item)
        y_itens += espaco_linha
    
    # --- TOTAL ---
    draw.line((50, y_itens + 15, 550, y_itens + 15), fill=cor_fundo_logo, width=3)
    draw.text((50, y_itens + 35), "TOTAL DO PEDIDO", fill=cor_marrom_logo, font=carregar_fonte(22, True))
    draw.text((400, y_itens + 35), f"R$ {total_geral:.2f}", fill=cor_destaque, font=carregar_fonte(24, True))

    # --- VALIDADE COM FUSO HORÁRIO BRASIL ---
    fuso_br = pytz.timezone('America/Sao_Paulo')
    agora = datetime.now(fuso_br)
    texto_v = f"Gerado em: {agora.strftime('%d/%m/%Y %H:%M')} | Validade: 15 dias"
    fonte_v = carregar_fonte(11)
    bbox_v = draw.textbbox((0, 0), texto_v, font=fonte_v)
    largura_v = bbox_v[2] - bbox_v[0]
    draw.text((W - largura_v - 50, H - 155), texto_v, fill=(160, 160, 160), font=fonte_v)

    # --- RODAPÉ ---
    draw.rectangle([0, H-135, W, H], fill=cor_fundo_logo)
    avisos = [
        "• Forminhas 4 pétalas (branca) inclusas.",
        "• Forminhas decorativas fornecidas pelo cliente",
        "  terão custo adicional por caixa extra utilizada."
    ]
    for i, aviso in enumerate(avisos):
        draw.text((45, H-120 + (i*22)), aviso, fill=cor_marrom_logo, font=carregar_fonte(15))

    y_linha = H - 55
    draw.line((45, y_linha, 555, y_linha), fill=cor_marrom_logo, width=1)

    # --- CONTATOS CENTRALIZADOS ---
    contatos = "Instagram: @docito_doceria123 | WhatsApp: (37) 99996-5194"
    fonte_contatos = carregar_fonte(14, True)
    bbox_contatos = draw.textbbox((0, 0), contatos, font=fonte_contatos)
    largura_contatos = bbox_contatos[2] - bbox_contatos[0]
    pos_x_contatos = (W - largura_contatos) // 2
    draw.text((pos_x_contatos, y_linha + 12), contatos, fill=cor_marrom_logo, font=fonte_contatos)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

# --- 4. INTERFACE STREAMLIT ---
try:
    st.image("logo.png", width=100)
except:
    st.title("🍰 DOCITO DOCERIA")

st.title("Gerador de Orçamentos")

if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

col_c1, col_c2 = st.columns(2)
with col_c1:
    cliente = st.text_input("Nome da Cliente")
with col_c2:
    data_ent = st.date_input("Data da Entrega", value=datetime.now())

st.divider()

# --- ADICIONAR ITEM ---
c1, c2, c3 = st.columns([3, 1, 1])
with c1:
    p = st.selectbox("Produto", list(CATALOGO.keys()))
with c2:
    q = st.number_input("Qtd", min_value=1, value=50)
with c3:
    st.write(" ")
    if st.button("➕ Adicionar"):
        st.session_state.carrinho.append({"produto": p, "qtd": q, "preco_cento": CATALOGO[p]})
        st.rerun()

# --- LISTAGEM E EDIÇÃO ---
if st.session_state.carrinho:
    st.subheader("🛒 Itens Selecionados")
    
    # Cabeçalho da Lista
    h_col1, h_col2, h_col3 = st.columns([3, 1, 0.5])
    h_col1.caption("Produto")
    h_col2.caption("Qtd (Editar)")
    h_col3.write("")

    for i, item in enumerate(st.session_state.carrinho):
        col_prod, col_qtd, col_bt = st.columns([3, 1, 0.5])
        
        col_prod.write(f"**{item['produto']}**")
        
        # Campo de edição de quantidade
        nova_qtd = col_qtd.number_input(
            "Qtd", 
            min_value=1, 
            value=int(item['qtd']), 
            key=f"edit_{i}", 
            label_visibility="collapsed"
        )
        
        # Se a quantidade mudar, atualiza e recarrega
        if nova_qtd != item['qtd']:
            st.session_state.carrinho[i]['qtd'] = nova_qtd
            st.rerun()

        # Botão para excluir item
        if col_bt.button("❌", key=f"del_{i}"):
            st.session_state.carrinho.pop(i)
            st.rerun()
    
    st.divider()
    
    if st.button("LIMPAR TUDO", type="secondary"):
        st.session_state.carrinho = []
        st.rerun()

    if st.button("GERAR IMAGEM FINAL", type="primary", use_container_width=True):
        if cliente:
            with st.spinner('Gerando orçamento...'):
                res = gerar_imagem(cliente, data_ent, st.session_state.carrinho)
                st.image(res)
                st.download_button("📥 Baixar Orçamento", res, f"Docito_{cliente}.png", "image/png")
        else:
            st.warning("Por favor, preencha o nome da cliente!")









