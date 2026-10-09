"""Catálogo e validação de configurações da Docito."""

from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4, uuid5, UUID, NAMESPACE_URL
import unicodedata

CATALOGO_PADRAO = {
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

REGRAS_PADRAO = {
    125.00: {"unitario_ate_25": 1.50, 40: 58.90, 50: 68.90, 75: 98.90, 90: 116.90, 100: 125.00},
    130.00: {"unitario_ate_25": 1.50, 40: 59.90, 50: 71.90, 75: 104.90, 90: 123.90, 100: 130.00},
    150.00: {"unitario_ate_25": 2.00, 40: 77.90, 50: 82.90, 75: 117.90, 90: 140.90, 100: 150.00},
    160.00: {"unitario_ate_25": 2.00, 40: 78.90, 50: 85.00, 75: 124.90, 90: 148.90, 100: 160.00},
}

COLUNAS_FAIXA = (40, 50, 75, 90, 100)
TIPOS_COBRANCA = ("Cento", "Unidade", "kg")


def configuracao_padrao():
    doces = []
    for nome, produto in CATALOGO_PADRAO.items():
        cobranca = "kg" if produto["tipo"] == "kg" else "Unidade" if "preco_unitario" in produto else "Cento"
        doces.append({
            "id": str(uuid5(NAMESPACE_URL, "docito:produto:" + nome)),
            "nome": nome, "cobranca": cobranca,
            "preco": produto["preco_kg"] if cobranca == "kg" else produto["preco_unitario"] if cobranca == "Unidade" else produto["preco_cento"],
            "conta_como_doce": produto.get("conta_como_doce", produto["tipo"] != "kg"),
            "tematico": nome == "Ninho Temático",
        })
    faixas = [{"preco_cento": preco, "unitario_ate_25": regra["unitario_ate_25"],
               **{str(n): regra[n] for n in COLUNAS_FAIXA}} for preco, regra in REGRAS_PADRAO.items()]
    return {"versao": 1, "doces": doces, "faixas": faixas}


def _preco(valor, campo):
    try:
        if isinstance(valor, bool):
            raise ValueError
        numero = Decimal(str(valor))
        if not numero.is_finite() or not Decimal("0.01") <= numero <= Decimal("99999.99"):
            raise ValueError
        return float(numero.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{campo}: informe um valor entre R$ 0,01 e R$ 99.999,99.") from None


def _booleano(valor, padrao):
    if valor is None:
        return padrao
    if not isinstance(valor, bool):
        raise ValueError("As opções de doce e tema devem estar marcadas ou desmarcadas.")
    return valor


def validar_configuracao(config):
    if not isinstance(config, dict) or config.get("versao") != 1:
        raise ValueError("Formato de catálogo inválido.")
    doces, faixas = config.get("doces"), config.get("faixas")
    if not isinstance(doces, list) or not 1 <= len(doces) <= 200:
        raise ValueError("Mantenha entre 1 e 200 produtos no catálogo.")
    if not isinstance(faixas, list) or len(faixas) > 100:
        raise ValueError("A tabela de faixas aceita até 100 linhas.")
    resultado, nomes, ids = [], set(), set()
    for linha in doces:
        if not isinstance(linha, dict):
            raise ValueError("Produto inválido.")
        nome = linha.get("nome")
        if not isinstance(nome, str) or not nome.strip() or len(nome.strip()) > 140 or any(ord(c) < 32 for c in nome):
            raise ValueError("Informe um nome de produto com até 140 caracteres.")
        nome = nome.strip()
        comparacao = unicodedata.normalize("NFC", nome).casefold()
        if comparacao in nomes:
            raise ValueError(f"O produto {nome} aparece mais de uma vez.")
        nomes.add(comparacao)
        cobranca = linha.get("cobranca")
        if cobranca not in TIPOS_COBRANCA:
            raise ValueError(f"Escolha Cento, Unidade ou kg para {nome}.")
        try:
            identificador = str(UUID(str(linha["id"]))) if linha.get("id") else str(uuid4())
        except (ValueError, TypeError):
            raise ValueError("Identificador de produto inválido.") from None
        if identificador in ids:
            raise ValueError("Há produtos com o mesmo identificador.")
        ids.add(identificador)
        tematico = _booleano(linha.get("tematico"), False)
        if tematico and cobranca != "Cento":
            raise ValueError(f"Produtos com tema devem ter cobrança por cento: {nome}.")
        resultado.append({"id": identificador, "nome": nome, "cobranca": cobranca,
                          "preco": _preco(linha.get("preco"), nome),
                          "conta_como_doce": _booleano(linha.get("conta_como_doce"), cobranca != "kg"),
                          "tematico": tematico})
    faixas_validas, precos = [], set()
    for linha in faixas:
        if not isinstance(linha, dict):
            raise ValueError("Faixa inválida.")
        preco = _preco(linha.get("preco_cento"), "Preço do cento na faixa")
        if preco in precos:
            raise ValueError("Cada preço do cento deve aparecer uma vez na tabela de faixas.")
        precos.add(preco)
        unitario = _preco(linha.get("unitario_ate_25"), "Unidade até 25 doces")
        totais = {str(n): _preco(linha.get(str(n)), f"Total de {n} doces") for n in COLUNAS_FAIXA}
        valores = [unitario * 25] + list(totais.values())
        if any(a > b + 0.001 for a, b in zip(valores, valores[1:])) or totais["100"] != preco:
            raise ValueError("Os totais das faixas devem ser crescentes e o total de 100 deve ser igual ao preço do cento.")
        faixas_validas.append({"preco_cento": preco, "unitario_ate_25": unitario, **totais})
    return {"versao": 1, "doces": resultado, "faixas": faixas_validas}


def montar_catalogo(config):
    config = validar_configuracao(config)
    catalogo = {}
    for doce in config["doces"]:
        tipo, preco = doce["cobranca"], doce["preco"]
        produto = {"tipo": "kg" if tipo == "kg" else "unitario", "cobranca": tipo,
                   "conta_como_doce": doce["conta_como_doce"], "tematico": doce["tematico"]}
        if tipo == "kg":
            produto["preco_kg"] = preco
        else:
            produto["preco_cento"] = preco * 100 if tipo == "Unidade" else preco
            if tipo == "Unidade":
                produto["preco_unitario"] = preco
        catalogo[doce["nome"]] = produto
    regras = {r["preco_cento"]: {"unitario_ate_25": r["unitario_ate_25"],
              **{n: r[str(n)] for n in COLUNAS_FAIXA}} for r in config["faixas"]}
    return catalogo, regras

