"""Editor Docito incorporado ao Streamlit, sem depender de um servidor externo."""

import base64
import json
import mimetypes
from functools import lru_cache
from pathlib import Path

import streamlit.components.v1 as components


EDITOR_DIR = Path(__file__).resolve().parent / "editor"


def _data_url(path):
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


@lru_cache(maxsize=1)
def _editor_html():
    page = (EDITOR_DIR / "index.html").read_text(encoding="utf-8")
    css = (EDITOR_DIR / "editor.css").read_text(encoding="utf-8")
    image_tools = (EDITOR_DIR / "image-tools.js").read_text(encoding="utf-8")
    presentation = (EDITOR_DIR / "presentation.js").read_text(encoding="utf-8")
    editor = (EDITOR_DIR / "editor.js").read_text(encoding="utf-8")
    assets = {
        "logo-docito.png": _data_url(EDITOR_DIR / "logo-docito.png"),
        "logo-header.png": _data_url(EDITOR_DIR / "logo-header.png"),
    }
    for font in (EDITOR_DIR / "fonts").glob("*.otf"):
        assets[f"fonts/{font.name}"] = _data_url(font)

    page = page.replace('<link rel="stylesheet" href="editor.css">', f"<style>{css}</style>")
    page = page.replace('src="logo-docito.png"', f'src="{assets["logo-docito.png"]}"')
    page = page.replace(
        '<script src="image-tools.js"></script><script src="presentation.js"></script><script src="editor.js"></script>',
        "<script>"
        f"window.DOCITO_ASSETS={json.dumps(assets, ensure_ascii=False)};"
        "window.DOCITO_EMBED_CONFIG={cloud:false,sample:null,logo:window.DOCITO_ASSETS['logo-docito.png']};"
        f"{image_tools}\n{presentation}\n{editor}"
        "</script>",
    )
    return page


def mostrar_editor_docito():
    """Exibe o editor completo; biblioteca e projetos continuam no navegador da usuária."""
    components.html(_editor_html(), height=1750, scrolling=True)
