from inspect import Attribute

from cryptography.exceptions import InvalidSignature, InvalidTag
from fastapi import APIRouter, HTTPException
from schemas import AssinarRequest, GerarChaveRequest, VerificarRequest, CifrarRequest, DecifrarRequest
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from hsm import sessao_hsm, gerar_par_no_cofre, assinar_no_cofre, verificar_no_cofre
from pkcs11 import Attribute, ObjectClass

router = APIRouter(prefix="/chaves", tags=["chaves"])
os.makedirs("chaves", exist_ok=True)

# _______________Parte 1_____________________________

@router.post("/rsa")
def gerar_par_de_chaves(dados: GerarChaveRequest):
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    publica = privada.public_key()
    privada_pem = privada.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    publica_pem = publica.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    with open(f"chaves/{dados.nome}_privada.pem", "wb") as privada_arquivo:
        privada_arquivo.write(privada_pem)
    with open(f"chaves/{dados.nome}_publica.pem", "wb") as publica_arquivo:
        publica_arquivo.write(publica_pem)
    return {"message": "Par de chaves RSA gerado com sucesso"}

@router.post("/assinar")
def assinar(dados: AssinarRequest):
    try:
        with open(f"chaves/{dados.nome}_privada.pem", "rb") as privada_arquivo: 
            privada_pem = privada_arquivo.read()
        privada = serialization.load_pem_private_key(privada_pem, password=None)
        texto_bytes = dados.texto.encode("utf-8")
        assinatura = privada.sign(texto_bytes, padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        assinatura_b64 = base64.b64encode(assinatura).decode("utf-8")
        return {"assinatura": assinatura_b64}
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail="Chave privada não encontrada. Gere o par de chaves primeiro."
        )

@router.post("/verificar")
def verificar(dados: VerificarRequest):
    try:
        with open(f"chaves/{dados.nome}_publica.pem", "rb") as publica_arquivo: 
            publica_pem = publica_arquivo.read()
        publica = serialization.load_pem_public_key(publica_pem)
        texto_bytes = dados.texto_assinado.encode("utf-8")
        publica.verify(base64.b64decode(dados.assinatura_b64), texto_bytes, padding.PSS( 
        mgf=padding.MGF1(hashes.SHA256()), 
        salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        return {"valida": True}
    except InvalidSignature:
        return {"valida": False}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chave pública não encontrada. Gere o par de chaves primeiro.")

@router.post("/aes")
def gerar_chave_aes(dados: GerarChaveRequest):
    chave_aes = os.urandom(32) 
    with open(f"chaves/{dados.nome}_aes.key", "wb") as chave_arquivo:
        chave_arquivo.write(chave_aes)
    return {"message": "Chave AES gerada com sucesso"}

@router.post("/cifrar")
def cifrar(dados: CifrarRequest):
    try:
        with open(f"chaves/{dados.nome}_aes.key", "rb") as chave_arquivo:
            chave = chave_arquivo.read()
        nonce = os.urandom(12)
        aesgcm = AESGCM(chave)
        cifrado = aesgcm.encrypt(nonce, dados.texto.encode("utf-8"), None)
        cifrado_b64 = base64.b64encode(cifrado).decode("utf-8")
        nonce_b64 = base64.b64encode(nonce).decode("utf-8")
        return {"cifrado": cifrado_b64, "nonce": nonce_b64}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chave AES não encontrada. Gere a chave primeiro.")

@router.post("/decifrar")
def decifrar(dados: DecifrarRequest):
    try:
        with open(f"chaves/{dados.nome}_aes.key", "rb") as chave_arquivo:
            chave = chave_arquivo.read() 
        aesgcm = AESGCM(chave)
        textoCifrado = base64.b64decode(dados.texto_cifrado)
        nonce = base64.b64decode(dados.nonce)
        decifrado = aesgcm.decrypt(nonce, textoCifrado, None)
        return {"texto": decifrado.decode("utf-8")}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Chave AES não encontrada. Gere a chave primeiro.")
    except InvalidTag:
        raise HTTPException(
            status_code=400, detail="Falha na decifragem. Verifique o texto cifrado e o nonce."
        )

# _______________Parte 2_____________________________

@router.get("/cofre/status")
def status_cofre():
    with sessao_hsm() as sessao:
        sessao_atual = sessao.token.label
        return {"token": sessao_atual}

@router.get("/cofre/chaves")
def listar_chaves_cofre(): 
    with sessao_hsm() as sessao:
        lista_de_chaves = []
        for chave in sessao.get_objects({Attribute.CLASS: ObjectClass.PRIVATE_KEY}):
            lista_de_chaves.append({"label": chave.label, "tipo": chave.key_type.name})
        return lista_de_chaves
