"""Google OIDC e autorização do lado do servidor, antes de qualquer dado privado."""

from dataclasses import dataclass
from math import isfinite
from time import time

import streamlit as st

EMAILS_AUTORIZADOS = frozenset({
    "gerusa041188@gmail.com",
    "julio.goiano@gmail.com",
})
GOOGLE_METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"
REDIRECT_URI = "https://docito.streamlit.app/oauth2callback"


@dataclass(frozen=True)
class Identidade:
    email: str
    subject: str
    expires_at: float


def validar_identidade(claims, client_id, agora=None):
    """Streamlit/Authlib valida assinatura e nonce; aqui validamos a autorização."""
    agora = time() if agora is None else agora
    if not claims.get("is_logged_in") or not client_id:
        return None
    email = claims.get("email")
    if not isinstance(email, str) or email.strip().lower() not in EMAILS_AUTORIZADOS:
        return None
    if claims.get("email_verified") is not True:
        return None
    if claims.get("iss") not in ("https://accounts.google.com", "accounts.google.com"):
        return None
    audience = claims.get("aud")
    if not (audience == client_id or isinstance(audience, list) and client_id in audience):
        return None
    if claims.get("azp", client_id) != client_id:
        return None
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        return None
    try:
        exp, iat = float(claims["exp"]), float(claims["iat"])
    except (KeyError, ValueError, TypeError, OverflowError):
        return None
    if not isfinite(exp) or not isfinite(iat) or exp <= agora or iat > agora + 60 or exp <= iat:
        return None
    return Identidade(email.strip().lower(), subject, exp)


def configuracao_google():
    try:
        auth = st.secrets["auth"]
        google = auth["google"]
        if auth["redirect_uri"] != REDIRECT_URI:
            return None
        cookie_secret = auth["cookie_secret"]
        if not isinstance(cookie_secret, str) or len(cookie_secret) < 32 or cookie_secret.startswith("SUBSTITUA"):
            return None
        if google["server_metadata_url"] != GOOGLE_METADATA_URL:
            return None
        if not google["client_id"].endswith(".apps.googleusercontent.com") or google["client_id"].startswith("SUBSTITUA"):
            return None
        if not isinstance(google["client_secret"], str) or not google["client_secret"] or google["client_secret"].startswith("SUBSTITUA"):
            return None
        return google
    except (KeyError, TypeError, AttributeError, FileNotFoundError):
        return None


def identidade_atual():
    config = configuracao_google()
    if config is None:
        return None
    return validar_identidade(dict(st.user), config["client_id"])


def limpar_sessao():
    for chave in list(st.session_state):
        del st.session_state[chave]


def sair():
    limpar_sessao()
    st.logout()


def exigir_acesso():
    """Também protege callbacks, diálogos e operações de banco em cada execução."""
    identidade = identidade_atual()
    if identidade is None:
        limpar_sessao()
        st.error("Sua sessão não está autorizada. Entre novamente com o Google.")
        st.stop()
    return identidade


def mostrar_login(logo=None):
    identidade = identidade_atual()
    if identidade is not None:
        if st.session_state.get("_docito_subject") != identidade.subject:
            limpar_sessao()
            st.session_state["_docito_subject"] = identidade.subject
        return identidade

    limpar_sessao()
    if logo is not None and logo.exists():
        st.image(str(logo), width=110)
    st.title("Bem-vindo à Docito 🍰")
    st.write("Entre com sua conta Google para acessar seus orçamentos e projetos de doces.")
    st.caption("Acesso restrito às contas autorizadas.")
    if dict(st.user).get("is_logged_in", False):
        st.warning("Esta conta não está autorizada ou a sessão expirou.")
        st.button("Usar outra conta Google", on_click=sair, type="primary")
    else:
        configurado = configuracao_google() is not None
        if st.button("Entrar com Google", type="primary", disabled=not configurado):
            st.login("google")
        if not configurado:
            st.info("O acesso privado está sendo configurado. Volte em breve.")
    st.stop()
