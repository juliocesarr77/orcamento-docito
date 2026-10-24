"""Owner-triggered recovery export. No plaintext export or automatic messages."""
import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from docito_auth import exigir_acesso


def encrypt_recovery(bundle, password):
    if not isinstance(password, str) or not 16 <= len(password) <= 200:
        raise ValueError("Use uma senha de 16 a 200 caracteres.")
    salt, iv = os.urandom(16), os.urandom(12)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000, 32)
    ciphertext = AESGCM(key).encrypt(iv, json.dumps(bundle, ensure_ascii=False).encode(), None)
    b64 = lambda data: base64.b64encode(data).decode("ascii")
    return json.dumps({"format":"docito-encrypted","version":1,"cipher":"AES-256-GCM","kdf":"PBKDF2-SHA256","iterations":310000,"salt":b64(salt),"iv":b64(iv),"ciphertext":b64(ciphertext)}).encode()


def verify_recovery(raw, password):
    if not isinstance(raw, bytes) or len(raw)>30*1024*1024:
        raise ValueError("Use um arquivo de até 30 MB.")
    envelope = json.loads(raw)
    if (envelope.get("format")!="docito-encrypted" or envelope.get("version")!=1
            or envelope.get("cipher")!="AES-256-GCM" or envelope.get("kdf")!="PBKDF2-SHA256" or envelope.get("iterations")!=310000):
        raise ValueError("Formato não reconhecido.")
    try:
        salt, iv = base64.b64decode(envelope["salt"],validate=True), base64.b64decode(envelope["iv"],validate=True)
        if len(salt)!=16 or len(iv)!=12 or not 16<=len(password)<=200:
            raise ValueError("Formato ou senha inválidos.")
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt,310000,32)
        bundle = json.loads(AESGCM(key).decrypt(iv,base64.b64decode(envelope["ciphertext"],validate=True),None))
    except Exception:
        raise ValueError("Senha incorreta ou arquivo corrompido.") from None
    if bundle.get("format")!="docito-orcamento-recovery" or bundle.get("version")!=1 or not bundle.get("private_sealed"):
        raise ValueError("Use o backup do Docito Orçamento.")
    tables = bundle.get("tables_json", {})
    if set(tables)!={"orcamentos","docito_configuracoes"}:
        raise ValueError("Conteúdo incompleto.")
    counts = {}
    for name, content in tables.items():
        rows = json.loads(content)
        if not isinstance(rows,list):
            raise ValueError("Tabela inválida.")
        counts[name] = len(rows)
    return counts


def mostrar_backup(client):
    import streamlit as st
    identity = exigir_acesso()
    if identity.email!="julio.goiano@gmail.com":
        return
    with st.expander("Backup criptografado e recuperação"):
        st.caption("Guarde esta cópia e o backup da Gestão fora do sistema. Inclui orçamentos, catálogo e configuração selada da integração. Acesso Google e chaves da plataforma são administrados separadamente.")
        with st.form("docito_backup_export", clear_on_submit=True):
            password = st.text_input("Senha de recuperação (16 a 200 caracteres)",type="password",max_chars=200)
            confirm = st.text_input("Confirmar senha de recuperação",type="password",max_chars=200)
            requested = st.form_submit_button("Preparar backup criptografado")
        if requested:
            try:
                identity = exigir_acesso()
                if identity.email!="julio.goiano@gmail.com" or password!=confirm or not 16<=len(password)<=200:
                    raise ValueError("Confira as duas senhas; use pelo menos 16 caracteres.")
                bundle = client.rpc("docito_quote_backup",{"p_actor":identity.email,"p_passphrase":password}).execute().data
                encrypted = encrypt_recovery(bundle,password)
                # Inline Blob avoids creating a public Streamlit /media download URL.
                encoded = base64.b64encode(encrypted).decode("ascii")
                filename = "docito-orcamento-"+datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")+".docito"
                import streamlit.components.v1 as components
                components.html('<button id="download">Baixar backup criptografado</button><script>document.getElementById("download").onclick=()=>{const bytes=Uint8Array.from(atob("'+encoded+'"),c=>c.charCodeAt(0));const url=URL.createObjectURL(new Blob([bytes],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download="'+filename+'";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};</script>',height=65)
                st.success("Arquivo preparado. Guarde a senha separadamente; sem ela a cópia não pode ser recuperada.")
            except ValueError as exc:
                st.error(str(exc))
            except Exception:
                st.error("Não foi possível preparar o backup completo. Nenhum arquivo parcial foi oferecido.")
        with st.form("docito_backup_verify",clear_on_submit=True):
            file = st.file_uploader("Conferir backup salvo (.docito)",type=["docito"],max_upload_size=30)
            password = st.text_input("Senha do arquivo salvo",type="password",max_chars=200)
            verify = st.form_submit_button("Verificar integridade sem restaurar")
        if verify:
            try:
                if file is None:
                    raise ValueError("Selecione o arquivo.")
                counts = verify_recovery(file.getvalue(),password)
                st.success(f"Integridade conferida: {counts['orcamentos']} orçamentos e {counts['docito_configuracoes']} registro(s) de catálogo. Nenhum dado do sistema foi alterado.")
            except Exception:
                st.error("Não foi possível verificar. Confira o arquivo e a senha; nenhum dado foi alterado.")
