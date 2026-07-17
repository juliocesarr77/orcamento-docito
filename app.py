import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import io
import pytz
from pathlib import Path
import base64
from supabase import create_client, Client # Importando o Supabase

BASE_DIR = Path(__file__).resolve().parent

# --- CONEXÃO COM O SUPABASE ---
# Certifique-se de adicionar SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit Cloud
try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    st.error("Erro ao conectar com as chaves do Supabase. Verifique os Secrets do Streamlit.")

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


def largura_texto(draw, texto, fonte):
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    return bbox[2] - bbox[0]


def altura_linha_fonte(draw, fonte):
    bbox = draw.textbbox((0, 0), "Ag", font=fonte)
    return (bbox[3] - bbox[1]) + 7


def quebrar_texto_largura(draw, texto, fonte, largura_max):
    texto = str(texto).strip()
    if not texto:
        return [""]
    linhas_finais = []

    for bloco in texto.splitlines():
        palavras = bloco.split()
        if not palavras:
            linhas_finais.append("")
            continue
        linha_atual = ""
        for palavra in palavras:
            teste = palabra if not linha_atual else f"{linha_atual} {palavra}"
            if largura_texto(draw, teste, fonte) <= largura_max:
                linha_atual = teste
            else:
                if linha_atual:
                    linhas_finais.append(linha_atual)
                linha_atual = palavra
        if linha_atual:
            linhas_finais.append(linha_atual)
    return linhas_finais or [""]


def calcular_desconto(valor_base, desconto_str):
    if not desconto_str:
        return 0.0, ""
    texto = str(desconto_str).strip().lower().replace(" ", "")
    try:
        if "%" in texto:
            numero = texto.replace("%", "").replace("-", "").replace(",", ".")
            percentual = float(numero)
            desconto = valor_base * (percentual / 100)
            return min(desconto, valor_base), f"{percentual:.0f}%"
        texto_limpo = (
            texto.replace("r$", "")
            .replace("-", "")
            .replace(".", "")
            .replace(",", ".")
        )
        valor = float(texto_limpo)
        return min(valor, valor_base), formatar_real(min(valor, valor_base))
    except Exception:
        return 0.0, ""


# --- FUNÇÕES DE HISTÓRICO ADAPTADAS PARA SUPABASE ---
def carregar_historico_supabase():
    try:
        # Busca todos os orçamentos ordenados pelo número
        response = supabase.table("orcamentos").select("*").order("numero", descending=False).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Erro ao buscar dados do Supabase: {e}")
        return []


def salvar_orcamento_supabase(novo_registro):
    try:
        supabase.table("orcamentos").insert(novo_registro).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Supabase: {e}")
        return False


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
    "Brigadeiro de Chocolate Branco": {"tipo": "unitario", "preco_cento": 150.00},
    "Brigadeiro de Ninho com Rosetas Coloridas e Apliques de Pasta Americana": {
        "tipo": "unitario",
        "preco_cento": 160.00,
    },
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
    if (
        embalagem_pedido.get("descricao", "").strip()
        and embalagem_pedido.get("valor", 0) > 0
    ):
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
    numero_orcamento,
    desconto_geral_str="",
    embalagem_pedido=None,
    embalagens_especiais=None,
    adicionais=None,
    observacao="",
):
    embalagem_pedido = embalagem_pedido or {"descricao": "", "valor": 0.0}
    embalagens_especiais = embalagens_especiais or []
    adicionais = adicionais or []

    W = 700
    total_linhas = len(itens) + len(embalagens_especiais) + len(adicionais)
    if (
        embalagem_pedido.get("descricao", "").strip()
        and embalagem_pedido.get("valor", 0) > 0
    ):
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

    x_desc = 50
    x_preco_direita = 650
    x_preco_min = 535
    largura_desc = x_preco_min - x_desc - 12

    fonte_item_previa = carregar_fonte(tam_fonte_item)
    img_medida = Image.new("RGB", (W, 100), color=(255, 255, 255))
    draw_medida = ImageDraw.Draw(img_medida)

    def altura_bloco_orcamento(texto, tem_detalhe=False, fonte=None, largura=None):
        fonte = fonte or fonte_item_previa
        largura = largura or largura_desc
        linhas = quebrar_texto_largura(draw_medida, texto, fonte, largura)
        altura_linha = altura_linha_fonte(draw_medida, fonte)
        extra = 24 if tem_detalhe else 0
        return max(espaco_linha, len(linhas) * altura_linha + extra + 8)

    total_altura_itens = 0
    for item in itens:
        _, _, desconto_item_desc, _ = calcular_subtotal_item(item)
        texto_prev = gerar_texto_item(item)
        if desconto_item_desc:
            texto_prev += f" (-{desconto_item_desc})"
        total_altura_itens += altura_bloco_orcamento(
            texto_prev, tem_detalhe=bool(desconto_item_desc)
        )

    if (
        embalagem_pedido.get("descricao", "").strip()
        and embalagem_pedido.get("valor", 0) > 0
    ):
        texto_prev = f"Embalagem do pedido - {embalagem_pedido['descricao']}"
        total_altura_itens += altura_bloco_orcamento(
            texto_prev, fonte=carregar_fonte(tam_fonte_item, True)
        )

    for emb in embalagens_especiais:
        texto_prev = f"Embalagem especial - {emb['qtd']}x {emb['descricao']}"
        total_altura_itens += altura_bloco_orcamento(texto_prev)

    for ad in adicionais:
        texto_prev = f"Adicional - {ad['descricao']}"
        total_altura_itens += altura_bloco_orcamento(texto_prev)

    altura_obs = 0
    if observacao.strip():
        fonte_obs_previa = carregar_fonte(14)
        linhas_obs_previas = quebrar_texto_largura(
            draw_medida, observacao.strip(), fonte_obs_previa, 600
        )
        altura_obs = 40 + (len(linhas_obs_previas) * 22)

    y_pos = altura_cabecalho + 30
    y_itens_inicio = y_pos + 140
    y_itens_fim = y_itens_inicio + total_altura_itens

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
            font=carregar_fonte(30, True),
        )

    # DADOS
    draw.text(
        (50, y_pos),
        f"ORÇAMENTO Nº {numero_orcamento:03d}",
        fill=cor_marrom_logo,
        font=carregar_fonte(26, True),
    )
    draw.text(
        (50, y_pos + 50),
        f"CLIENTE: {cliente.upper()}",
        fill=cor_marrom_logo,
        font=carregar_fonte(18, True),
    )
    draw.text(
        (50, y_pos + 80),
        f"ENTREGA: {data_entrega.strftime('%d/%m/%Y')}",
        fill=cor_destaque,
        font=carregar_fonte(18, True),
    )
    draw.line((50, y_pos + 115, 650, y_pos + 115), fill=cor_fundo_logo, width=3)

    # ITENS PRINCIPAIS
    y_itens = y_itens_inicio
    total_bruto_itens = 0
    total_desconto_itens = 0
    total_doces = 0
    total_gramas = 0
    fonte_item = carregar_fonte(tam_fonte_item)

    def desenhar_linha_com_preco(
        y,
        texto,
        texto_valor,
        cor_texto,
        fonte_texto,
        cor_valor=None,
        fonte_valor=None,
        detalhe_desc=None,
    ):
        cor_valor = cor_valor or cor_texto
        fonte_valor = fonte_valor or fonte_texto
        linhas = quebrar_texto_largura(draw, texto, fonte_texto, largura_desc)
        altura_linha = altura_linha_fonte(draw, fonte_texto)

        for i, linha in enumerate(linhas):
            draw.text(
                (x_desc, y + (i * altura_linha)),
                linha,
                fill=cor_texto,
                font=fonte_texto,
            )

        bbox_valor = draw.textbbox((0, 0), texto_valor, font=fonte_valor)
        largura_valor = bbox_valor[2] - bbox_valor[0]
        draw.text(
            (x_preco_direita - largura_valor, y),
            texto_valor,
            fill=cor_valor,
            font=fonte_valor,
        )
        altura_usada = len(linhas) * altura_linha
        if detalhe_desc:
            draw.text(
                (x_desc + 15, y + altura_usada),
                detalhe_desc,
                fill=cor_cinza,
                font=carregar_fonte(max(tam_fonte_item - 4, 11)),
            )
            altura_usada += 24
        return y + max(espaco_linha, altura_usada + 8)

    for item in itens:
        (
            subtotal_bruto,
            desconto_item_valor,
            desconto_item_desc,
            subtotal_final,
        ) = calcular_subtotal_item(item)
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

        detalhe_desc = None
        if desconto_item_valor > 0:
            detalhe_desc = (
                f"Original: {formatar_real(subtotal_bruto)} | "
                f"Desconto: -{formatar_real(desconto_item_valor)}"
            )

        y_itens = desenhar_linha_com_preco(
            y=y_itens,
            texto=texto_item,
            texto_valor=texto_valor,
            cor_texto=cor_marrom_logo,
            fonte_texto=fonte_item,
            detalhe_desc=detalhe_desc,
        )

    # EMBALAGEM DO PEDIDO
    total_emb_pedido = calcular_total_embalagens_pedido(embalagem_pedido)
    if total_emb_pedido > 0:
        y_itens = desenhar_linha_com_preco(
            y=y_itens,
            texto=f"Embalagem do pedido - {embalagem_pedido['descricao']}",
            texto_valor=formatar_real(total_emb_pedido),
            cor_texto=cor_secao,
            fonte_texto=carregar_fonte(tam_fonte_item, True),
            cor_valor=cor_secao,
            fonte_valor=fonte_item,
        )

    # EMBALAGENS ESPECIAIS
    for emb in embalagens_especiais:
        total_emb_item = float(emb["qtd"]) * float(emb["valor_unit"])
        texto = f"Embalagem especial - {emb['qtd']}x {emb['descricao']}"
        texto_valor = formatar_real(total_emb_item)
        y_itens = desenhar_linha_com_preco(
            y=y_itens,
            texto=texto,
            texto_valor=texto_valor,
            cor_texto=cor_secao,
            fonte_texto=fonte_item,
        )

    # ADICIONAIS
    for ad in adicionais:
        texto = f"Adicional - {ad['descricao']}"
        texto_valor = formatar_real(float(ad["valor"]))
        y_itens = desenhar_linha_com_preco(
            y=y_itens,
            texto=texto,
            texto_valor=texto_valor,
            cor_texto=cor_secao,
            fonte_texto=fonte_item,
        )

    total_emb_especiais = calcular_total_embalagens_especiais(embalagens_especiais)
    total_adicionais = calcular_total_adicionais(adicionais)

    total_bruto_general = (
        total_bruto_itens + total_emb_pedido + total_emb_especiais + total_adicionais
    )
    total_com_desconto_itens = total_bruto_general - total_desconto_itens
    desconto_geral_valor, _ = calcular_desconto(
        total_com_desconto_itens, desconto_geral_str
    )
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
        formatar_real(total_bruto_general),
        fill=cor_marrom_logo,
        font=carregar_fonte(18, True),
    )

    if total_emb_pedido > 0:
        y_resumo += 30
        draw.text(
            (50, y_resumo), "Embalagem do pedido", fill=cor_cinza, font=carregar_fonte(14)
        )
        draw.text(
            (520, y_resumo),
            formatar_real(total_emb_pedido),
            fill=cor_cinza,
            font=carregar_fonte(14),
        )

    if total_emb_especiais > 0:
        y_resumo += 25
        draw.text(
            (50, y_resumo),
            "Embalagens especiais",
            fill=cor_cinza,
            font=carregar_fonte(14),
        )
        draw.text(
            (520, y_resumo),
            formatar_real(total_emb_especiais),
            fill=cor_cinza,
            font=carregar_fonte(14),
        )

    if total_adicionais > 0:
        y_resumo += 25
        draw.text(
            (50, y_resumo), "Adicionais", fill=cor_cinza, font=carregar_fonte(14)
        )
        draw.text(
            (520, y_resumo),
            formatar_real(total_adicionais),
            fill=cor_cinza,
            font=carregar_fonte(14),
        )

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
        fonte_obs = carregar_fonte(14)
        linhas_obs = quebrar_texto_largura(draw, observacao.strip(), fonte_obs, 600)
        for linha in linhas_obs:
            draw.text((50, y_resumo), linha, fill=cor_marrom_logo, font=fonte_obs)
            y_resumo += 22

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
    draw.text(
        (650 - largura_total, y_resumo),
        texto_total,
        fill=cor_destaque,
        font=fonte_total,
    )

    # PAGAMENTO
    draw.text(
        (50, y_resumo + 50),
        "FORMAS DE PAGAMENTO",
        fill=cor_marrom_logo,
        font=carregar_fonte(16, True),
    )
    draw.text(
        (50, y_resumo + 75),
        "Pix | Dinheiro | Cartão | Criptomoedas",
        fill=cor_marrom_logo,
        font=carregar_fonte(16),
    )
    draw.text(
        (50, y_resumo + 100),
        "Cartão em até 12x com acréscimo da maquininha.",
        fill=cor_marrom_logo,
        font=carregar_fonte(14),
    )
    draw.text(
        (50, y_resumo + 125),
        "Data reservada mediante confirmação do pedido.",
        fill=cor_marrom_logo,
        font=carregar_fonte(14),
    )

    # VALIDADE
    fuso_br = pytz.timezone("America/Sao_Paulo")
    agora = datetime.now(fuso_br)
    texto_v = f"Gerado em: {agora.strftime('%d/%m/%Y %H:%M')} | Validade: 15 dias"
    fonte_v = carregar_fonte(11)
    bbox_v = draw.textbbox((0, 0), texto_v, font=fonte_v)
    draw.text(
        (W - (bbox_v[2] - bbox_v[0]) - 50, y_topo_rodape - 25),
        texto_v,
        fill=(160, 160, 160),
        font=fonte_v,
    )

    # RODAPÉ
    draw.rectangle([0, y_topo_rodape, W, H], fill=cor_fundo_logo)
    avisos = [
        "• Forminhas 4 pétalas (brancas) inclusas.",
        "• Forminhas decorativas fornecidas pelo cliente",
        "  terão custo adicional por caixa extra utilizada.",
    ]
    for i, aviso in enumerate(avisos):
        draw.text(
            (45, y_topo_rodape + 15 + (i * 22)),
            aviso,
            fill=cor_marrom_logo,
            font=carregar_fonte(15),
        )

    y_linha = y_topo_rodape + 85
    draw.line((45, y_linha, 655, y_linha), fill=cor_marrom_logo, width=1)
    contatos = "Instagram: @docito_doceria123 | WhatsApp: (37) 99996-5194"
    fonte_contatos = carregar_fonte(14, True)
    bbox_contatos = draw.textbbox((0, 0), contatos, font=fonte_contatos)
    draw.text(
        ((W - (bbox_contatos[2] - bbox_contatos[0])) // 2, y_linha + 12),
        contatos,
        fill=cor_marrom_logo,
        font=fonte_contatos,
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

tab_novo, tab_busca = st.tabs(["✍️ Criar Novo Orçamento", "🔍 Buscar e Histórico"])

if "carrinho" not in st.session_state:
    st.session_state.carrinho = []
if "item_counter" not in st.session_state:
    st.session_state.item_counter = 0
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

# ABA 1: CRIAÇÃO DE NOVO ORÇAMENTO
with tab_novo:
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cliente = st.text_input("Nome da Cliente")
    with col_c2:
        data_ent = st.date_input("Data da Entrega", value=datetime.now().date())

    st.divider()
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
                st.session_state.item_counter += 1
                st.session_state.carrinho.append({
                    "id": f"prod_{st.session_state.item_counter}",
                    "produto": produto_selecionado,
                    "tipo": "unitario",
                    "qtd": int(qtd_unit),
                    "preco_cento": dados_produto["preco_cento"],
                    "desconto": desconto_novo_item.strip(),
                })
                st.rerun()
    else:
        c1, c2, c3, c4, c5 = st.columns([2.2, 1.2, 1.2, 1.3, 1])
        with c1:
            st.text_input("Tipo de cobrança", value=f"Por peso ({formatar_real(dados_produto['preco_kg'])}/kg)", disabled=True, key="tipo_kg")
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
                st.session_state.item_counter += 1
                st.session_state.carrinho.append({
                    "id": f"prod_{st.session_state.item_counter}",
                    "produto": produto_selecionado,
                    "tipo": "kg",
                    "gramas": int(gramas_item),
                    "preco_kg": dados_produto["preco_kg"],
                    "desconto": desconto_novo_item.strip(),
                })
                st.rerun()

    st.divider()
    st.subheader("Embalagem do pedido (opcional)")
    e1, e2, e3 = st.columns([3, 1.2, 1])
    with e1:
        emb_pedido_desc = st.text_input("Descrição da embalagem do pedido", value=st.session_state.embalagem_pedido["descricao"], placeholder="Ex.: Pote premium / Caixa especial")
    with e2:
        emb_pedido_valor = st.number_input("Valor", min_value=0.0, value=float(st.session_state.embalagem_pedido["valor"]), step=0.5, format="%.2f")
    with e3:
        st.write(" ")
        if st.button("Salvar embalagem do pedido"):
            st.session_state.embalagem_pedido = {
                "descricao": emb_pedido_desc.strip(),
                "valor": float(emb_pedido_valor),
            }
            st.rerun()

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
                st.session_state.embalagens_especiais.append({
                    "descricao": emb_esp_desc.strip(),
                    "qtd": int(emb_esp_qtd),
                    "valor_unit": float(emb_esp_valor),
                })
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
                st.session_state.adicionais.append({
                    "descricao": adicional_desc.strip(),
                    "valor": float(adicional_valor),
                })
                st.rerun()

    if st.session_state.adicionais:
        st.caption("Adicionais adicionados")
        for i, ad in enumerate(st.session_state.adicionais):
            c1, c2 = st.columns([5, 1])
            c1.write(f"**{ad['descricao']}** — {formatar_real(float(ad['valor']))}")
            if c2.button("❌", key=f"del_ad_{i}"):
                st.session_state.adicionais.pop(i)
                st.rerun()

    st.divider()
    st.subheader("Observação (opcional)")
    observacao = st.text_area("Observação do orçamento", value=st.session_state.observacao, placeholder="Ex.: Produto enviado em embalagem especial para consumo de colher.")
    st.session_state.observacao = observacao

    st.divider()
    st.subheader("Desconto geral do pedido")
    desconto_geral = st.text_input("Desconto Geral", value=st.session_state.desconto_geral, placeholder="Ex.: 10% ou R$20")
    st.session_state.desconto_geral = desconto_geral

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
            item_id = item.get("id", f"fallback_{i}")

            if item["tipo"] == "unitario":
                total_doces_preview += item["qtd"]
                col_prod, col_qtd, col_desc, col_bt = st.columns([3, 1, 1.4, 0.5])
                col_prod.write(f"**{item['produto']}**  \n{item['qtd']}un | {formatar_real(subtotal_bruto)} → **{formatar_real(subtotal_final)}**")
                nova_qtd = col_qtd.number_input("Qtd", min_value=1, value=int(item["qtd"]), key=f"edit_qtd_{item_id}", label_visibility="collapsed")
                novo_desc = col_desc.text_input("Desconto", value=item.get("desconto", ""), key=f"desc_{item_id}", placeholder="10% ou R$2", label_visibility="collapsed")
                
                alterou = False
                if nova_qtd != item["qtd"]:
                    st.session_state.carrinho[i]["qtd"] = int(nova_qtd)
                    alterou = True
                if novo_desc != item.get("desconto", ""):
                    st.session_state.carrinho[i]["desconto"] = novo_desc.strip()
                    alterou = True
                if alterou:
                    st.rerun()
                if col_bt.button("❌", key=f"del_{item_id}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()
            else:
                total_gramas_preview += item["gramas"]
                col_prod, col_unid, col_qtd, col_desc, col_bt = st.columns([2.4, 1, 1.2, 1.4, 0.5])
                col_prod.write(f"**{item['produto']}**  \n{formatar_peso(item['gramas'])} | {formatar_real(subtotal_bruto)} → **{formatar_real(subtotal_final)}**")
                unidade_edit = col_unid.selectbox("Unidade", ["kg", "g"], index=0 if item["gramas"] % 1000 == 0 else 1, key=f"unidade_edit_{item_id}", label_visibility="collapsed")
                
                if unidade_edit == "kg":
                    valor_padrao = item["gramas"] / 1000
                    novo_valor_peso = col_qtd.number_input("Quantidade", min_value=0.1, value=float(valor_padrao), step=0.1, format="%.3f", key=f"peso_kg_{item_id}", label_visibility="collapsed")
                    novas_gramas = int(round(novo_valor_peso * 1000))
                else:
                    novo_valor_peso = col_qtd.number_input("Quantidade", min_value=100, value=int(item["gramas"]), step=50, key=f"peso_g_{item_id}", label_visibility="collapsed")
                    novas_gramas = int(novo_valor_peso)

                novo_desc = col_desc.text_input("Desconto", value=item.get("desconto", ""), key=f"desc_kg_{item_id}", placeholder="10% ou R$2", label_visibility="collapsed")
                
                alterou = False
                if novas_gramas != item["gramas"]:
                    st.session_state.carrinho[i]["gramas"] = int(novas_gramas)
                    alterou = True
                if novo_desc != item.get("desconto", ""):
                    st.session_state.carrinho[i]["desconto"] = novo_desc.strip()
                    alterou = True
                if alterou:
                    st.rerun()
                if col_bt.button("❌", key=f"del_kg_{item_id}"):
                    st.session_state.carrinho.pop(i)
                    st.rerun()

        total_emb_pedido_preview = calcular_total_embalagens_pedido(st.session_state.embalagem_pedido)
        total_emb_especiais_preview = calcular_total_embalagens_especiais(st.session_state.embalagens_especiais)
        total_adicionais_preview = calcular_total_adicionais(st.session_state.adicionais)

        total_bruto_preview = total_bruto_preview_itens + total_emb_pedido_preview + total_emb_especiais_preview + total_adicionais_preview
        total_apos_itens_preview = total_bruto_preview - total_desc_itens_preview
        desconto_geral_preview, _ = calcular_desconto(total_apos_itens_preview, st.session_state.desconto_geral)
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
            st.session_state.item_counter = 0
            st.session_state.desconto_geral = ""
            st.session_state.embalagem_pedido = {"descricao": "", "valor": 0.0}
            st.session_state.embalagens_especiais = []
            st.session_state.adicionais = []
            st.session_state.observacao = ""
            st.rerun()

        if st.button("GERAR IMAGEM FINAL", type="primary", use_container_width=True):
            if cliente.strip():
                with st.spinner("Gerando e salvando orçamento no Supabase..."):
                    # Busca o histórico do Supabase para saber qual o próximo número sequencial
                    historico = carregar_historico_supabase()
                    proximo_numero = max([o["numero"] for o in historico]) + 1 if historico else 1

                    res = gerar_imagem(
                        cliente=cliente,
                        data_entrega=data_ent,
                        itens=st.session_state.carrinho,
                        numero_orcamento=proximo_numero,
                        desconto_geral_str=st.session_state.desconto_geral,
                        embalagem_pedido=st.session_state.embalagem_pedido,
                        embalagens_especiais=st.session_state.embalagens_especiais,
                        adicionais=st.session_state.adicionais,
                        observacao=st.session_state.observacao,
                    )

                    # Estrutura exata para persistir no Supabase
                    novo_registro = {
                        "numero": proximo_numero,
                        "cliente": cliente.strip(),
                        "data_entrega": data_ent.strftime("%Y-%m-%d"),
                        "desconto_geral": st.session_state.desconto_geral,
                        "embalagem_pedido": st.session_state.embalagem_pedido,
                        "embalagens_especiais": st.session_state.embalagens_especiais,
                        "adicionais": st.session_state.adicionais,
                        "observacao": st.session_state.observacao,
                        "itens": st.session_state.carrinho,
                        "total": float(total_final_preview),
                    }
                    
                    # Salva no banco de dados definitivo do Supabase
                    sucesso = salvar_orcamento_supabase(novo_registro)

                    if sucesso:
                        st.success(f"Orçamento Nº {proximo_numero:03d} arquivado permanentemente!")
                        st.image(res)

                        col_b1, col_b2 = st.columns(2)
                        with col_b1:
                            st.download_button(
                                "📥 Baixar Orçamento",
                                res,
                                f"Docito_N{proximo_numero:03d}_{cliente.strip()}.png",
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

# ABA 2: HISTÓRICO E BUSCA DE ORÇAMENTOS
with tab_busca:
    st.subheader("📚 Histórico de Orçamentos Arquivados")
    
    # Puxa os dados direto do Supabase em tempo real
    historico_salvo = carregar_historico_supabase()

    if not historico_salvo:
        st.info("Nenhum orçamento encontrado no Supabase.")
    else:
        termo_busca = st.text_input("Buscar por número ou nome do cliente", placeholder="Ex.: 1 ou Maria")

        orcamentos_filtrados = []
        for o in historico_salvo:
            if termo_busca.strip():
                if termo_busca.strip().isdigit() and int(termo_busca.strip()) == o["numero"]:
                    orcamentos_filtrados.append(o)
                elif termo_busca.lower() in o.get("cliente", "").lower():
                    orcamentos_filtrados.append(o)
            else:
                orcamentos_filtrados.append(o)

        if not orcamentos_filtrados:
            st.warning("Nenhum registro encontrado para essa pesquisa.")
        else:
            for o in reversed(orcamentos_filtrados):
                with st.expander(f"📋 Nº {o['numero']:03d} — {o['cliente'].upper()} | Total: {formatar_real(o['total'])}"):
                    st.write(f"**Data de Entrega:** {o['data_entrega']}")
                    if o.get("observacao", "").strip():
                        st.write(f"**Observação:** {o['observacao']}")

                    st.caption("Resumo dos Itens do Pedido:")
                    for it in o.get("itens", []):
                        if it["tipo"] == "unitario":
                            st.write(f"• {it['qtd']}un de {it['produto']}")
                        else:
                            st.write(f"• {formatar_peso(it['gramas'])} de {it['produto']}")

                    if st.button(f"🖼️ Visualizar/Re-gerar Imagem Nº {o['numero']:03d}", key=f"regerar_{o['numero']}_supabase"):
                        try:
                            dt_ent_antigo = datetime.strptime(o["data_entrega"], "%Y-%m-%d").date()
                        except Exception:
                            dt_ent_antigo = datetime.now().date()

                        with st.spinner("Buscando e renderizando dados do Supabase..."):
                            res_antigo = gerar_imagem(
                                cliente=o["cliente"],
                                data_entrega=dt_ent_antigo,
                                itens=o["itens"],
                                numero_orcamento=o["numero"],
                                desconto_geral_str=o.get("desconto_geral", ""),
                                embalagem_pedido=o.get("embalagem_pedido"),
                                embalagens_especiais=o.get("embalagens_especiais"),
                                adicionais=o.get("adicionais"),
                                observacao=o.get("observacao", ""),
                            )
                            st.image(res_antigo)
                            st.download_button(
                                "📥 Baixar este Orçamento",
                                res_antigo,
                                f"Docito_N{o['numero']:03d}_{o['cliente']}.png",
                                "image/png",
                                key=f"dl_antigo_{o['numero']}_sup",
                            )
