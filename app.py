import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import io
import pytz
import base64
from supabase import create_client, Client
from docito_editor_component import mostrar_editor_docito

# V8: preço do cento personalizável somente para Ninho Temático.
# Dependências: streamlit, Pillow, pytz, supabase.
# Mantenha logo.png e as fontes na mesma pasta deste arquivo.
# Mantenha SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit.
BASE_DIR = Path(__file__).resolve().parent


def carregar_fonte(tamanho, negrito=False):
    nome = "DejaVuSans-Bold.ttf" if negrito else "DejaVuSans.ttf"
    for caminho in (BASE_DIR / nome, nome):
        try:
            return ImageFont.truetype(str(caminho), tamanho)
        except OSError:
            pass
    return ImageFont.load_default()


def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_peso(gramas):
    if gramas >= 1000:
        numero = f"{gramas / 1000:.3f}".rstrip("0").rstrip(".")
        return numero.replace(".", ",") + "kg"
    return f"{int(gramas)}g"


def largura_texto(draw, texto, fonte):
    bbox = draw.textbbox((0, 0), texto, font=fonte)
    return bbox[2] - bbox[0]


def altura_linha_fonte(draw, fonte):
    bbox = draw.textbbox((0, 0), "Ag", font=fonte)
    return bbox[3] - bbox[1] + 7


def quebrar_texto_largura(draw, texto, fonte, largura_max):
    linhas = []
    for bloco in str(texto).strip().splitlines():
        atual = ""
        for palavra in bloco.split():
            teste = f"{atual} {palavra}" if atual else palavra
            if largura_texto(draw, teste, fonte) <= largura_max:
                atual = teste
            else:
                if atual:
                    linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return linhas or [""]


def calcular_desconto(valor_base, desconto_str):
    if not desconto_str:
        return 0.0, ""
    texto = str(desconto_str).strip().lower().replace(" ", "")
    try:
        if "%" in texto:
            percentual = float(texto.replace("%", "").replace("-", "").replace(",", "."))
            return min(valor_base * percentual / 100, valor_base), f"{percentual:.0f}%"
        valor = float(texto.replace("r$", "").replace("-", "").replace(".", "").replace(",", "."))
        desconto = min(valor, valor_base)
        return desconto, formatar_real(desconto)
    except (ValueError, TypeError):
        return 0.0, ""


CATALOGO = {
    "Brigadeiro de Chocolate": {"tipo": "unitario", "preco_cento": 125.00},
    "Brigadeiro de Ninho": {"tipo": "unitario", "preco_cento": 125.00},
    "Beijinho": {"tipo": "unitario", "preco_cento": 130.00},
    "Meio a Meio": {"tipo": "unitario", "preco_cento": 130.00},
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
    "Ninho Temático": {"tipo": "unitario", "preco_cento": 160.00},
    "Aplique": {"tipo": "unitario", "preco_cento": 150.00, "preco_unitario": 1.50, "conta_como_doce": False},
    "Brigadeiro de Chocolate em massa": {"tipo": "kg", "preco_kg": 84.90},
    "Brigadeiro de Chocolate Branco": {"tipo": "unitario", "preco_cento": 150.00},
    "Brigadeiro de Ninho com Rosetas Coloridas e Apliques de Pasta Americana": {
        "tipo": "unitario", "preco_cento": 160.00,
    },
}

REGRAS_PRECO_DOCES = {
    125.00: {"unitario_ate_25": 1.50, 40: 58.90, 50: 68.90, 75: 98.90, 90: 116.90, 100: 125.00},
    130.00: {"unitario_ate_25": 1.50, 40: 59.90, 50: 71.90, 75: 104.90, 90: 123.90, 100: 130.00},
    150.00: {"unitario_ate_25": 2.00, 40: 77.90, 50: 82.90, 75: 117.90, 90: 140.90, 100: 150.00},
    160.00: {"unitario_ate_25": 2.00, 40: 78.90, 50: 85.00, 75: 124.90, 90: 148.90, 100: 160.00},
}


def interpolar(valor_inicial, valor_final, posicao):
    return valor_inicial + (valor_final - valor_inicial) * posicao


def calcular_valor_unitario_doces(preco_cento, quantidade_total_doces):
    preco_cento = round(float(preco_cento), 2)
    qtd = max(int(quantidade_total_doces), 1)
    regra = REGRAS_PRECO_DOCES.get(preco_cento)
    if regra is None or qtd >= 100:
        return preco_cento / 100
    if qtd <= 25:
        return float(regra["unitario_ate_25"])
    pontos = [(25, float(regra["unitario_ate_25"]))]
    pontos.extend((n, float(regra[n]) / n) for n in (40, 50, 75, 90, 100))
    for (inicio, valor_inicio), (fim, valor_fim) in zip(pontos, pontos[1:]):
        if qtd <= fim:
            return interpolar(valor_inicio, valor_fim, (qtd - inicio) / (fim - inicio))
    return preco_cento / 100


def calcular_preco_doces(preco_cento, qtd):
    qtd = max(int(qtd), 1)
    return round(calcular_valor_unitario_doces(preco_cento, qtd) * qtd, 2)


def item_eh_aplique(item):
    return item.get("conta_como_doce") is False or str(item.get("produto", "")).strip().casefold() == "aplique"


def item_eh_ninho_tematico(item):
    return str(item.get("produto", "")).strip().casefold() == "ninho temático"


def calcular_total_doces_pedido(itens):
    return sum(int(it.get("qtd", 0)) for it in itens if it.get("tipo") == "unitario" and not item_eh_aplique(it))


def calcular_subtotal_item(item, quantidade_total_doces=None):
    if item["tipo"] == "unitario":
        qtd = int(item["qtd"])
        if item_eh_aplique(item):
            bruto = float(item.get("preco_unitario") or 1.50) * qtd
        elif item_eh_ninho_tematico(item) and item.get("preco_manual", False):
            bruto = float(item["preco_cento"]) / 100 * qtd
        else:
            total_doces = max(int(quantidade_total_doces or qtd), 1)
            bruto = calcular_valor_unitario_doces(item["preco_cento"], total_doces) * qtd
        bruto = round(bruto, 2)
    else:
        bruto = float(item["preco_kg"]) / 1000 * int(item["gramas"])
    desconto, descricao = calcular_desconto(bruto, item.get("desconto", ""))
    return bruto, desconto, descricao, bruto - desconto


def gerar_texto_item(item):
    quantidade = f"{item['qtd']}un" if item["tipo"] == "unitario" else formatar_peso(item["gramas"])
    texto = f"{quantidade} - {item['produto']}"
    if item_eh_ninho_tematico(item):
        detalhes = str(item.get("detalhes", "")).strip()
        if detalhes:
            texto += f" | Detalhes: {detalhes}"
    return texto


def calcular_total_embalagens_pedido(embalagem_pedido):
    if embalagem_pedido.get("descricao", "").strip() and embalagem_pedido.get("valor", 0) > 0:
        return float(embalagem_pedido["valor"])
    return 0.0


def calcular_total_embalagens_especiais(embalagens_especiais):
    return sum(float(emb["qtd"]) * float(emb["valor_unit"]) for emb in embalagens_especiais)


def calcular_total_adicionais(adicionais):
    return sum(float(ad["valor"]) for ad in adicionais)


def calcular_resumo(itens, embalagem_pedido, embalagens_especiais, adicionais, desconto_geral):
    qtd = calcular_total_doces_pedido(itens)
    calculos = [calcular_subtotal_item(it, qtd) for it in itens]
    emb = calcular_total_embalagens_pedido(embalagem_pedido)
    especiais = calcular_total_embalagens_especiais(embalagens_especiais)
    extras = calcular_total_adicionais(adicionais)
    subtotal = sum(it[0] for it in calculos) + emb + especiais + extras
    desc_itens = sum(it[1] for it in calculos)
    desc_geral, _ = calcular_desconto(subtotal - desc_itens, desconto_geral)
    return {
        "total_doces": qtd,
        "total_gramas": sum(int(it["gramas"]) for it in itens if it["tipo"] != "unitario"),
        "total_emb_pedido": emb, "total_emb_especiais": especiais,
        "total_adicionais": extras, "subtotal": subtotal,
        "desconto_itens": desc_itens, "desconto_geral": desc_geral,
        "total": subtotal - desc_itens - desc_geral,
    }


# Persistência: preco_manual e preco_cento ficam dentro dos itens JSON,
# sem precisar criar colunas novas no Supabase.
def normalizar_orcamento(registro):
    registro = dict(registro or {})
    dados = registro.get("dados")
    if not isinstance(dados, dict):
        dados = {}
    for campo, padrao in (
        ("itens", []), ("embalagem_pedido", {"descricao": "", "valor": 0.0}),
        ("embalagens_especiais", []), ("adicionais", []),
    ):
        registro[campo] = registro.get(campo) or dados.get(campo) or padrao
    for campo in ("observacao", "desconto_geral"):
        if registro.get(campo) is None:
            registro[campo] = dados.get(campo, "")
    try:
        registro["numero"] = int(registro.get("numero", 0))
    except (TypeError, ValueError):
        registro["numero"] = 0
    try:
        valor = registro.get("total")
        registro["total"] = float(dados.get("total", 0) if valor is None else valor)
    except (TypeError, ValueError):
        registro["total"] = 0.0
    return registro


def preparar_registro_supabase(novo_registro):
    registro = dict(novo_registro)
    registro["numero"] = int(registro["numero"])
    registro["cliente"] = str(registro["cliente"]).strip()
    registro["data_entrega"] = str(registro["data_entrega"])
    if not registro["cliente"]:
        raise ValueError("O nome da cliente não pode ficar vazio.")
    for campo in ("itens", "embalagens_especiais", "adicionais"):
        registro[campo] = list(registro.get(campo) or [])
    registro["embalagem_pedido"] = dict(registro.get("embalagem_pedido") or {"descricao": "", "valor": 0.0})
    for campo in ("observacao", "desconto_geral"):
        registro[campo] = str(registro.get(campo) or "")
    registro["total"] = round(float(registro.get("total", 0)), 2)
    registro["dados"] = {campo: registro[campo] for campo in (
        "itens", "embalagem_pedido", "embalagens_especiais", "adicionais",
        "observacao", "desconto_geral", "total",
    )}
    return registro


def carregar_historico_supabase():
    try:
        resposta = supabase.table("orcamentos").select("*").order("numero", desc=True).execute()
        return [normalizar_orcamento(it) for it in (resposta.data or [])]
    except Exception as e:
        st.error(f"Erro ao buscar dados do Supabase: {e}")
        return []


def obter_proximo_numero():
    resposta = supabase.table("orcamentos").select("numero").order("numero", desc=True).limit(1).execute()
    return max(234, int(resposta.data[0]["numero"]) + 1) if resposta.data else 234


def salvar_orcamento_supabase(novo_registro):
    try:
        resposta = supabase.table("orcamentos").insert(preparar_registro_supabase(novo_registro)).execute()
        if not resposta.data:
            raise RuntimeError("O Supabase não confirmou a inclusão.")
        return resposta.data[0]
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return None


def atualizar_orcamento_supabase(orcamento_id, registro_atualizado):
    try:
        if not orcamento_id:
            raise ValueError("Identificador do orçamento não encontrado.")
        resposta = supabase.table("orcamentos").update(
            preparar_registro_supabase(registro_atualizado)
        ).eq("id", str(orcamento_id)).execute()
        if not resposta.data:
            raise RuntimeError("O Supabase não confirmou a atualização.")
        return resposta.data[0]
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return None


def gerar_imagem(cliente, data_entrega, itens, numero_orcamento,
                 desconto_geral_str="", embalagem_pedido=None,
                 embalagens_especiais=None, adicionais=None, observacao=""):
    embalagem_pedido = embalagem_pedido or {"descricao": "", "valor": 0.0}
    embalagens_especiais = embalagens_especiais or []
    adicionais = adicionais or []
    observacao = str(observacao or "")
    r = calcular_resumo(itens, embalagem_pedido, embalagens_especiais, adicionais, desconto_geral_str)
    W = 700
    fundo, marrom = (255, 195, 153), (65, 38, 30)
    destaque, desconto_cor = (210, 80, 30), (180, 40, 40)
    cinza, secao = (140, 140, 140), (120, 70, 50)
    quantidade_linhas = len(itens) + len(embalagens_especiais) + len(adicionais) + int(r["total_emb_pedido"] > 0)
    tamanho, espaco = (18, 42) if quantidade_linhas <= 8 else ((16, 36) if quantidade_linhas <= 12 else (14, 30))
    medida = ImageDraw.Draw(Image.new("RGB", (W, 100), "white"))
    linhas = []
    for item in itens:
        bruto, desc, desc_texto, total = calcular_subtotal_item(item, r["total_doces"])
        nome = gerar_texto_item(item)
        if desc_texto:
            nome += f" (-{desc_texto})"
        detalhe = f"Original: {formatar_real(bruto)} | Desconto: -{formatar_real(desc)}" if desc > 0 else None
        linhas.append([nome, formatar_real(total), marrom, False, detalhe])
    if r["total_emb_pedido"] > 0:
        linhas.append([f"Embalagem do pedido - {embalagem_pedido['descricao']}", formatar_real(r["total_emb_pedido"]), secao, True, None])
    for emb in embalagens_especiais:
        linhas.append([f"Embalagem especial - {emb['qtd']}x {emb['descricao']}", formatar_real(float(emb["qtd"]) * float(emb["valor_unit"])), secao, False, None])
    for ad in adicionais:
        linhas.append([f"Adicional - {ad['descricao']}", formatar_real(float(ad["valor"])), secao, False, None])
    preparadas = []
    for nome, valor, cor, negrito, detalhe in linhas:
        fonte = carregar_fonte(tamanho, negrito)
        partes = quebrar_texto_largura(medida, nome, fonte, 473)
        altura_linha = altura_linha_fonte(medida, fonte)
        altura = max(espaco, len(partes) * altura_linha + (24 if detalhe else 0) + 8)
        preparadas.append((partes, valor, cor, fonte, detalhe, altura_linha, altura))
    clientes = quebrar_texto_largura(medida, f"CLIENTE: {cliente.upper()}", carregar_fonte(18, True), 600)
    extra_cliente = max(0, len(clientes) - 1) * 28
    obs = quebrar_texto_largura(medida, observacao, carregar_fonte(14), 600) if observacao.strip() else []
    y_inicio = 280 + extra_cliente
    y_fim = y_inicio + sum(it[6] for it in preparadas)
    y_total = y_fim + 35 + (30 if r["total_doces"] > 0 else 0) + (35 if r["total_gramas"] > 0 else 5)
    for chave, incremento in (("total_emb_pedido", 30), ("total_emb_especiais", 25), ("total_adicionais", 25), ("desconto_itens", 35), ("desconto_geral", 35)):
        if r[chave] > 0:
            y_total += incremento
    if obs:
        y_total += 85 + len(obs) * 22
    y_total += 75
    rodape = max(980, y_total + 205)
    img = Image.new("RGB", (W, rodape + 190), "white")
    draw = ImageDraw.Draw(img)

    def texto(x, y, conteudo, tam=18, bold=False, cor=marrom):
        draw.text((x, y), str(conteudo), font=carregar_fonte(tam, bold), fill=cor)

    def direita(y, conteudo, tam=18, bold=True, cor=marrom):
        fonte = carregar_fonte(tam, bold)
        draw.text((650 - largura_texto(draw, conteudo, fonte), y), conteudo, font=fonte, fill=cor)

    draw.rectangle((0, 0, W, 110), fill=fundo)
    try:
        with Image.open(BASE_DIR / "logo.png") as original:
            logo = original.convert("RGBA")
        logo.thumbnail((130, 100), Image.Resampling.LANCZOS)
        img.paste(logo, ((W - logo.width) // 2, (110 - logo.height) // 2), logo)
    except (OSError, ValueError):
        titulo = "DOCITO DOCERIA"
        texto((W - largura_texto(draw, titulo, carregar_fonte(30, True))) // 2, 40, titulo, 30, True)
    texto(50, 140, f"ORÇAMENTO Nº {numero_orcamento:03d}", 26, True)
    for i, parte in enumerate(clientes):
        texto(50, 190 + i * 28, parte, 18, True)
    texto(50, 220 + extra_cliente, f"ENTREGA: {data_entrega.strftime('%d/%m/%Y')}", 18, True, destaque)
    draw.line((50, 255 + extra_cliente, 650, 255 + extra_cliente), fill=fundo, width=3)
    y = y_inicio
    for partes, valor, cor, fonte, detalhe, altura_linha, altura in preparadas:
        for i, parte in enumerate(partes):
            draw.text((50, y + i * altura_linha), parte, font=fonte, fill=cor)
        direita(y, valor, tamanho, False, cor)
        if detalhe:
            texto(65, y + len(partes) * altura_linha, detalhe, max(tamanho - 4, 11), False, cinza)
        y += altura
    draw.line((50, y + 15, 650, y + 15), fill=fundo, width=3)
    y += 35
    if r["total_doces"] > 0:
        texto(50, y, f"TOTAL DE DOCES: {r['total_doces']}", 18, True)
        y += 30
    if r["total_gramas"] > 0:
        texto(50, y, f"PESO TOTAL: {formatar_peso(r['total_gramas'])}", 18, True)
        y += 35
    else:
        y += 5
    texto(50, y, "Subtotal", 18, True)
    direita(y, formatar_real(r["subtotal"]))
    for chave, titulo, incremento in (("total_emb_pedido", "Embalagem do pedido", 30), ("total_emb_especiais", "Embalagens especiais", 25), ("total_adicionais", "Adicionais", 25)):
        if r[chave] > 0:
            y += incremento
            texto(50, y, titulo, 14, False, cinza)
            direita(y, formatar_real(r[chave]), 14, False, cinza)
    for chave, titulo in (("desconto_itens", "Desconto por itens"), ("desconto_geral", "Desconto geral")):
        if r[chave] > 0:
            y += 35
            texto(50, y, titulo, 18, True, desconto_cor)
            direita(y, "-" + formatar_real(r[chave]), 18, True, desconto_cor)
    if obs:
        y += 40
        draw.line((50, y, 650, y), fill=fundo, width=2)
        y += 20
        texto(50, y, "OBSERVAÇÃO", 16, True)
        y += 25
        for parte in obs:
            texto(50, y, parte, 14)
            y += 22
    y += 50
    draw.line((50, y, 650, y), fill=fundo, width=2)
    y += 25
    texto(50, y, "TOTAL DO PEDIDO", 24, True)
    direita(y, formatar_real(r["total"]), 28, True, destaque)
    texto(50, y + 50, "FORMAS DE PAGAMENTO", 16, True)
    texto(50, y + 75, "Pix | Dinheiro | Cartão | Criptomoedas", 16)
    texto(50, y + 100, "Cartão em até 12x com acréscimo da maquininha.", 14)
    texto(50, y + 125, "Data reservada mediante confirmação do pedido.", 14)
    agora = datetime.now(pytz.timezone("America/Sao_Paulo"))
    direita(rodape - 25, f"Gerado em: {agora.strftime('%d/%m/%Y %H:%M')} | Validade: 15 dias", 11, False, (160, 160, 160))
    draw.rectangle((0, rodape, W, img.height), fill=fundo)
    for i, aviso in enumerate(("• Forminhas 4 pétalas (brancas) inclusas.", "• Forminhas decorativas fornecidas pelo cliente", "  terão custo adicional por caixa extra utilizada.")):
        texto(45, rodape + 15 + i * 22, aviso, 15)
    draw.line((45, rodape + 85, 655, rodape + 85), fill=marrom, width=1)
    contato = "Instagram: @docito_doceria123 | WhatsApp: (37) 99996-5194"
    texto((W - largura_texto(draw, contato, carregar_fonte(14, True))) // 2, rodape + 97, contato, 14, True)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


OPCOES_PAGINAS = ["✍️ Criar Novo Orçamento", "🔍 Buscar e Histórico", "🍬 Projetos de Doces"]


def hoje_brasil():
    return datetime.now(pytz.timezone("America/Sao_Paulo")).date()


def estado_inicial():
    return {
        "pagina_ativa": OPCOES_PAGINAS[0], "carrinho": [], "item_counter": 0,
        "cliente_input": "", "data_entrega_input": hoje_brasil(),
        "desconto_geral": "", "observacao": "",
        "embalagem_pedido": {"descricao": "", "valor": 0.0},
        "embalagens_especiais": [], "adicionais": [],
        "emb_pedido_desc_input": "", "emb_pedido_valor_input": 0.0,
        "editando_id": None, "editando_numero": None, "ultimo_resultado": None,
    }


def limpar_widgets_itens():
    for chave in list(st.session_state.keys()):
        if chave.startswith(("edit_qtd_", "desc_item_", "preco_edit_", "peso_edit_", "unidade_edit_")):
            del st.session_state[chave]


def limpar_orcamento():
    limpar_widgets_itens()
    st.session_state.update(estado_inicial())


def carregar_orcamento_para_edicao(orcamento):
    limpar_widgets_itens()
    o = normalizar_orcamento(orcamento)
    try:
        data = datetime.strptime(str(o.get("data_entrega", ""))[:10], "%Y-%m-%d").date()
    except ValueError:
        data = hoje_brasil()
    itens = [{**it, "id": uuid4().hex} for it in o["itens"] if isinstance(it, dict)]
    embalagem = dict(o["embalagem_pedido"])
    st.session_state.update({
        "pagina_ativa": OPCOES_PAGINAS[0], "editando_id": o.get("id"),
        "editando_numero": o["numero"], "cliente_input": str(o.get("cliente") or ""),
        "data_entrega_input": data, "carrinho": itens, "item_counter": len(itens),
        "desconto_geral": str(o.get("desconto_geral") or ""),
        "observacao": str(o.get("observacao") or ""), "embalagem_pedido": embalagem,
        "emb_pedido_desc_input": str(embalagem.get("descricao") or ""),
        "emb_pedido_valor_input": float(embalagem.get("valor") or 0),
        "embalagens_especiais": [dict(it) for it in o["embalagens_especiais"]],
        "adicionais": [dict(it) for it in o["adicionais"]], "ultimo_resultado": None,
    })


def invalidar_imagem():
    st.session_state.ultimo_resultado = None


def aplicar_preco_ninho(indice, chave):
    item = st.session_state.carrinho[indice]
    if item_eh_ninho_tematico(item):
        item["preco_cento"] = float(st.session_state[chave])
        item["preco_manual"] = True
        invalidar_imagem()


def sincronizar_peso(indice, item_id):
    gramas = int(st.session_state.carrinho[indice]["gramas"])
    st.session_state[f"peso_edit_kg_{item_id}"] = gramas / 1000
    st.session_state[f"peso_edit_g_{item_id}"] = gramas


def mostrar_resultado(resultado, chave):
    st.image(resultado["imagem"])
    c1, c2 = st.columns(2)
    c1.download_button(
        "📥 Baixar Orçamento", data=resultado["imagem"],
        file_name=f"Docito_N{resultado['numero']:03d}_{resultado['cliente']}.png",
        mime="image/png", key=f"download_{chave}",
    )
    with c2:
        codificado = base64.b64encode(resultado["imagem"]).decode()
        st.components.v1.html(f"""
        <button onclick="copyImage()" style="width:100%;background:#d86a2b;color:white;border:0;padding:10px;border-radius:8px;cursor:pointer;font-weight:600;">📋 Copiar imagem</button>
        <script>
        async function copyImage() {{
            try {{
                const response = await fetch("data:image/png;base64,{codificado}");
                const blob = await response.blob();
                await navigator.clipboard.write([new ClipboardItem({{"image/png": blob}})]);
                alert("Imagem copiada! Agora é só colar no WhatsApp.");
            }} catch (err) {{
                alert("Seu navegador pode não permitir copiar imagem. Use o botão de baixar.");
            }}
        }}
        </script>
        """, height=55)


def tela_criacao():
    if st.session_state.editando_id:
        st.info(f"✏️ Editando o orçamento Nº {int(st.session_state.editando_numero):03d}. O número será mantido.")
        st.button("Cancelar edição e criar novo orçamento", on_click=limpar_orcamento)
    c1, c2 = st.columns(2)
    cliente = c1.text_input("Nome da Cliente", key="cliente_input", on_change=invalidar_imagem)
    entrega = c2.date_input("Data da Entrega", key="data_entrega_input", on_change=invalidar_imagem)
    st.divider()
    st.subheader("Adicionar produtos")
    nome = st.selectbox("Produto", list(CATALOGO))
    produto = CATALOGO[nome]
    preco = produto.get("preco_cento")
    detalhes_ninho = ""
    if nome == "Ninho Temático":
        preco = st.number_input("Preço do cento — Ninho Temático (R$)", min_value=0.01, value=160.00, step=5.0, format="%.2f", key="preco_ninho_tematico")
        detalhes_ninho = st.text_input(
            "Detalhes",
            placeholder="Ex.: Bananas de Pijamas — ejetores",
            key="detalhes_ninho_tematico",
        )
        st.caption(f"Valor por unidade: {formatar_real(preco / 100)}. Calculado proporcionalmente à quantidade.")
    if produto["tipo"] == "unitario":
        c1, c2, c3 = st.columns([2, 1, 2])
        c1.text_input("Tipo de cobrança", value="Por unidade", disabled=True, key="tipo_unitario")
        qtd = c2.number_input("Qtd", min_value=1, value=50, step=1, key="qtd_novo_unitario")
        desc = c3.text_input("Desconto Item", placeholder="Ex.: 10% ou R$2", key="desconto_novo_unitario")
        if st.button("➕ Adicionar produto"):
            st.session_state.carrinho.append({
                "id": uuid4().hex, "produto": nome, "tipo": "unitario", "qtd": int(qtd),
                "preco_cento": float(preco), "preco_unitario": produto.get("preco_unitario"),
                "conta_como_doce": produto.get("conta_como_doce", True),
                "preco_manual": nome == "Ninho Temático", "desconto": desc.strip(),
                "detalhes": detalhes_ninho.strip() if nome == "Ninho Temático" else "",
            })
            invalidar_imagem()
            st.rerun()
    else:
        c1, c2, c3, c4 = st.columns([2.2, 1, 1.2, 1.5])
        c1.text_input("Tipo de cobrança", value=f"Por peso ({formatar_real(produto['preco_kg'])}/kg)", disabled=True, key="tipo_kg")
        unidade = c2.selectbox("Unidade", ["kg", "g"], key="unidade_nova")
        if unidade == "kg":
            peso = c3.number_input("Quantidade", min_value=0.1, value=1.0, step=0.1, format="%.3f", key="peso_novo_kg")
            gramas = int(round(peso * 1000))
        else:
            gramas = c3.number_input("Quantidade", min_value=100, value=1000, step=50, key="peso_novo_g")
        desc = c4.text_input("Desconto Item", placeholder="Ex.: 10% ou R$2", key="desconto_novo_kg")
        if st.button("➕ Adicionar produto em massa"):
            st.session_state.carrinho.append({"id": uuid4().hex, "produto": nome, "tipo": "kg", "gramas": int(gramas), "preco_kg": produto["preco_kg"], "desconto": desc.strip()})
            invalidar_imagem()
            st.rerun()
    st.divider()
    st.subheader("Embalagem do pedido (opcional)")
    c1, c2 = st.columns([3, 1.2])
    emb_desc = c1.text_input("Descrição da embalagem do pedido", placeholder="Ex.: Pote premium / Caixa especial", key="emb_pedido_desc_input")
    emb_valor = c2.number_input("Valor", min_value=0.0, step=0.5, format="%.2f", key="emb_pedido_valor_input")
    if st.button("Salvar embalagem do pedido"):
        st.session_state.embalagem_pedido = {"descricao": emb_desc.strip(), "valor": float(emb_valor)}
        invalidar_imagem()
        st.rerun()
    st.divider()
    st.subheader("Embalagens especiais/unitárias (opcional)")
    c1, c2, c3 = st.columns([2.5, 1, 1.2])
    emb_desc = c1.text_input("Descrição", placeholder="Ex.: Caixa premium / Pote individual", key="emb_esp_desc")
    emb_qtd = c2.number_input("Qtd", min_value=1, value=1, step=1, key="emb_esp_qtd")
    emb_valor = c3.number_input("Valor unit.", min_value=0.0, value=0.0, step=0.5, format="%.2f", key="emb_esp_valor")
    if st.button("➕ Adicionar embalagem especial"):
        if emb_desc.strip() and emb_valor > 0:
            st.session_state.embalagens_especiais.append({"descricao": emb_desc.strip(), "qtd": int(emb_qtd), "valor_unit": float(emb_valor)})
            invalidar_imagem()
            st.rerun()
        else:
            st.warning("Informe a descrição e um valor maior que zero.")
    for i, emb in enumerate(st.session_state.embalagens_especiais):
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{emb['qtd']}x {emb['descricao']}** — {formatar_real(float(emb['qtd']) * float(emb['valor_unit']))}")
        if c2.button("❌", key=f"del_emb_{i}"):
            st.session_state.embalagens_especiais.pop(i)
            invalidar_imagem()
            st.rerun()
    st.divider()
    st.subheader("Adicionais (opcional)")
    c1, c2 = st.columns([3, 1.2])
    ad_desc = c1.text_input("Descrição do adicional", placeholder="Ex.: Caixa extra / Taxa de entrega", key="adicional_desc")
    ad_valor = c2.number_input("Valor do adicional", min_value=0.0, value=0.0, step=0.5, format="%.2f", key="adicional_valor")
    if st.button("➕ Adicionar adicional"):
        if ad_desc.strip() and ad_valor > 0:
            st.session_state.adicionais.append({"descricao": ad_desc.strip(), "valor": float(ad_valor)})
            invalidar_imagem()
            st.rerun()
        else:
            st.warning("Informe a descrição e um valor maior que zero.")
    for i, ad in enumerate(st.session_state.adicionais):
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{ad['descricao']}** — {formatar_real(float(ad['valor']))}")
        if c2.button("❌", key=f"del_ad_{i}"):
            st.session_state.adicionais.pop(i)
            invalidar_imagem()
            st.rerun()
    st.divider()
    st.subheader("Observação (opcional)")
    st.text_area("Observação do orçamento", key="observacao", placeholder="Ex.: Produto enviado em embalagem especial para consumo de colher.", on_change=invalidar_imagem)
    st.divider()
    st.subheader("Desconto geral do pedido")
    st.text_input("Desconto Geral", key="desconto_geral", placeholder="Ex.: 10% ou R$20", on_change=invalidar_imagem)
    tem_conteudo = st.session_state.carrinho or calcular_total_embalagens_pedido(st.session_state.embalagem_pedido) > 0 or st.session_state.embalagens_especiais or st.session_state.adicionais
    if not tem_conteudo:
        return
    st.subheader("🛒 Itens Selecionados")
    st.caption("A faixa dos doces usa a quantidade total do pedido. O Ninho Temático com preço personalizado usa o valor informado.")
    total_doces = calcular_total_doces_pedido(st.session_state.carrinho)
    for i, item in enumerate(st.session_state.carrinho):
        if not item.get("id"):
            item["id"] = uuid4().hex
        item_id = item["id"]
        bruto, _, _, final = calcular_subtotal_item(item, total_doces)
        alterou = False
        if item["tipo"] == "unitario":
            c1, c2, c3, c4 = st.columns([3, 1, 1.4, 0.5])
            c1.write(f"**{item['produto']}**  \n{item['qtd']}un | {formatar_real(bruto)} → **{formatar_real(final)}**")
            qtd = c2.number_input("Qtd", min_value=1, value=int(item["qtd"]), key=f"edit_qtd_{item_id}", label_visibility="collapsed")
            desc = c3.text_input("Desconto", value=item.get("desconto", ""), key=f"desc_item_{item_id}", placeholder="10% ou R$2", label_visibility="collapsed")
            if qtd != item["qtd"]:
                item["qtd"] = int(qtd)
                alterou = True
            if item_eh_ninho_tematico(item):
                chave = f"preco_edit_{item_id}"
                st.number_input("Preço do cento deste Ninho Temático (R$)", min_value=0.01, value=float(item.get("preco_cento", 160)), step=5.0, format="%.2f", key=chave, on_change=aplicar_preco_ninho, args=(i, chave))
                if item.get("preco_manual", False):
                    st.caption(f"Preço personalizado: {formatar_real(float(item['preco_cento']))} o cento.")
                else:
                    st.caption("Este item antigo ainda usa a tabela progressiva. Ao alterar o preço acima, passa a usar preço proporcional.")
                detalhes = st.text_input(
                    "Detalhes deste Ninho Temático",
                    value=str(item.get("detalhes", "")),
                    placeholder="Ex.: Bananas de Pijamas — ejetores",
                    key=f"detalhes_edit_{item_id}",
                )
                if detalhes.strip() != str(item.get("detalhes", "")).strip():
                    item["detalhes"] = detalhes.strip()
                    alterou = True
        else:
            c1, unidade_col, c2, c3, c4 = st.columns([2.4, 1, 1.2, 1.4, 0.5])
            c1.write(f"**{item['produto']}**  \n{formatar_peso(item['gramas'])} | {formatar_real(bruto)} → **{formatar_real(final)}**")
            unidade = unidade_col.selectbox("Unidade", ["kg", "g"], index=0 if item["gramas"] % 1000 == 0 else 1, key=f"unidade_edit_{item_id}", label_visibility="collapsed", on_change=sincronizar_peso, args=(i, item_id))
            if unidade == "kg":
                peso = c2.number_input("Quantidade", min_value=0.1, value=float(item["gramas"] / 1000), step=0.1, format="%.3f", key=f"peso_edit_kg_{item_id}", label_visibility="collapsed")
                gramas = int(round(peso * 1000))
            else:
                gramas = c2.number_input("Quantidade", min_value=100, value=int(item["gramas"]), step=50, key=f"peso_edit_g_{item_id}", label_visibility="collapsed")
            desc = c3.text_input("Desconto", value=item.get("desconto", ""), key=f"desc_item_{item_id}", placeholder="10% ou R$2", label_visibility="collapsed")
            if gramas != item["gramas"]:
                item["gramas"] = int(gramas)
                alterou = True
        if desc.strip() != item.get("desconto", ""):
            item["desconto"] = desc.strip()
            alterou = True
        if c4.button("❌", key=f"del_item_{item_id}"):
            st.session_state.carrinho.pop(i)
            invalidar_imagem()
            st.rerun()
        if alterou:
            invalidar_imagem()
            st.rerun()
    r = calcular_resumo(st.session_state.carrinho, st.session_state.embalagem_pedido, st.session_state.embalagens_especiais, st.session_state.adicionais, st.session_state.desconto_geral)
    st.divider()
    st.subheader("Resumo")
    if r["total_doces"] > 0:
        st.write(f"**Total de doces:** {r['total_doces']}")
    if r["total_gramas"] > 0:
        st.write(f"**Peso total:** {formatar_peso(r['total_gramas'])}")
    for campo, titulo in (("total_emb_pedido", "Embalagem do pedido"), ("total_emb_especiais", "Embalagens especiais"), ("total_adicionais", "Adicionais")):
        if r[campo] > 0:
            st.write(f"**{titulo}:** {formatar_real(r[campo])}")
    st.write(f"**Subtotal:** {formatar_real(r['subtotal'])}")
    for campo, titulo in (("desconto_itens", "Desconto por itens"), ("desconto_geral", "Desconto geral")):
        if r[campo] > 0:
            st.write(f"**{titulo}:** -{formatar_real(r[campo])}")
    if st.session_state.observacao.strip():
        st.write(f"**Observação:** {st.session_state.observacao.strip()}")
    st.write(f"## Total final: {formatar_real(r['total'])}")
    st.button("LIMPAR TUDO", type="secondary", on_click=limpar_orcamento)
    registro_atual = {
        "cliente": cliente.strip(), "data_entrega": entrega.isoformat(),
        "desconto_geral": st.session_state.desconto_geral.strip(),
        "embalagem_pedido": dict(st.session_state.embalagem_pedido),
        "embalagens_especiais": [dict(it) for it in st.session_state.embalagens_especiais],
        "adicionais": [dict(it) for it in st.session_state.adicionais],
        "observacao": st.session_state.observacao.strip(),
        "itens": [dict(it) for it in st.session_state.carrinho], "total": round(float(r["total"]), 2),
    }
    botao = "SALVAR ALTERAÇÕES E GERAR IMAGEM" if st.session_state.editando_id else "GERAR IMAGEM FINAL"
    if st.button(botao, type="primary", use_container_width=True):
        if not cliente.strip():
            st.warning("Por favor, preencha o nome da cliente!")
        else:
            modo_edicao = bool(st.session_state.editando_id)
            with st.spinner("Gerando e salvando orçamento no Supabase..."):
                try:
                    numero = int(st.session_state.editando_numero) if modo_edicao else obter_proximo_numero()
                    imagem = gerar_imagem(cliente, entrega, st.session_state.carrinho, numero, st.session_state.desconto_geral, st.session_state.embalagem_pedido, st.session_state.embalagens_especiais, st.session_state.adicionais, st.session_state.observacao)
                    registro = {"numero": numero, **registro_atual}
                    salvo = atualizar_orcamento_supabase(st.session_state.editando_id, registro) if modo_edicao else salvar_orcamento_supabase(registro)
                except Exception as e:
                    st.error(f"Não foi possível gerar o orçamento: {e}")
                    salvo = None
                if salvo is not None:
                    st.session_state.editando_id = salvo.get("id") or st.session_state.editando_id
                    st.session_state.editando_numero = numero
                    st.session_state.ultimo_resultado = {
                        "imagem": imagem.getvalue(), "numero": numero, "cliente": cliente.strip(),
                        "registro": registro_atual,
                        "mensagem": f"Orçamento Nº {numero:03d} {'atualizado' if modo_edicao else 'arquivado'}!",
                    }
                    st.rerun()
    resultado = st.session_state.ultimo_resultado
    if resultado and resultado.get("registro") == registro_atual:
        st.success(resultado["mensagem"])
        mostrar_resultado(resultado, "atual")


def tela_historico():
    st.subheader("📚 Histórico de Orçamentos Arquivados")
    historico = carregar_historico_supabase()
    if not historico:
        st.info("Nenhum orçamento encontrado no Supabase.")
        return
    busca = st.text_input("Buscar por número ou nome do cliente", placeholder="Ex.: 234 ou Maria").strip()
    filtrados = [o for o in historico if not busca or (busca.isdigit() and int(busca) == o["numero"]) or busca.casefold() in str(o.get("cliente", "")).casefold()]
    if not filtrados:
        st.warning("Nenhum registro encontrado para essa pesquisa.")
    for o in filtrados:
        identificador = str(o.get("id") or o["numero"])
        with st.expander(f"📋 Nº {o['numero']:03d} — {str(o.get('cliente', '')).upper()} | Total: {formatar_real(o['total'])}"):
            st.write(f"**Data de Entrega:** {o['data_entrega']}")
            if str(o.get("observacao") or "").strip():
                st.write(f"**Observação:** {o['observacao']}")
            st.caption("Resumo dos Itens do Pedido:")
            for item in o["itens"]:
                if not isinstance(item, dict):
                    continue
                st.write("• " + gerar_texto_item(item))
                if item_eh_ninho_tematico(item) and item.get("preco_manual", False):
                    st.caption(f"Preço personalizado: {formatar_real(float(item['preco_cento']))} o cento.")
            c1, c2 = st.columns(2)
            c1.button(f"✏️ Editar Nº {o['numero']:03d}", key=f"editar_{identificador}", use_container_width=True, on_click=carregar_orcamento_para_edicao, args=(o,))
            chave = f"visualizando_{identificador}"
            if c2.button(f"🖼️ Visualizar Nº {o['numero']:03d}", key=f"visualizar_{identificador}", use_container_width=True):
                st.session_state[chave] = True
            if st.session_state.get(chave, False):
                try:
                    entrega = datetime.strptime(str(o["data_entrega"])[:10], "%Y-%m-%d").date()
                except ValueError:
                    entrega = hoje_brasil()
                try:
                    imagem = gerar_imagem(o["cliente"], entrega, o["itens"], o["numero"], o.get("desconto_geral", ""), o["embalagem_pedido"], o["embalagens_especiais"], o["adicionais"], o.get("observacao", ""))
                    mostrar_resultado({"imagem": imagem.getvalue(), "numero": o["numero"], "cliente": o["cliente"]}, identificador)
                except Exception as e:
                    st.error(f"Não foi possível visualizar este orçamento: {e}")


def tela_projetos():
    st.subheader("🍬 Projetos de Doces Personalizados")
    st.caption("Monte a caixa, guarde a biblioteca neste navegador e exporte a apresentação em PNG ou PDF.")
    mostrar_editor_docito()


def main():
    global supabase
    # O iframe acompanha a largura da página. A coluna centralizada acionava
    # o modo móvel do editor mesmo em monitores grandes.
    pagina = st.session_state.get("pagina_ativa", OPCOES_PAGINAS[0])
    st.set_page_config(
        page_title="Docito Doceria - Orçamentos", page_icon="🍰",
        layout="wide" if pagina == OPCOES_PAGINAS[2] else "centered",
    )
    try:
        supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error("Erro ao conectar ao Supabase. Confira SUPABASE_URL e SUPABASE_KEY nos Secrets do Streamlit.")
        st.exception(e)
        st.stop()
    for chave, valor in estado_inicial().items():
        if chave not in st.session_state:
            st.session_state[chave] = valor
    if (BASE_DIR / "logo.png").exists():
        st.image(str(BASE_DIR / "logo.png"), width=100)
    else:
        st.title("🍰 DOCITO DOCERIA")
    st.title("Gerador de Orçamentos")
    st.caption("V8 — Ninho Temático com preço personalizado")
    st.radio("Navegação", OPCOES_PAGINAS, key="pagina_ativa", horizontal=True, label_visibility="collapsed")
    if st.session_state.pagina_ativa == OPCOES_PAGINAS[0]:
        tela_criacao()
    elif st.session_state.pagina_ativa == OPCOES_PAGINAS[1]:
        tela_historico()
    else:
        tela_projetos()


if __name__ == "__main__":
    main()
