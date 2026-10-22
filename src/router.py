import base64
import os

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, HTTPException

import config
from hsm import (
    CofreIndisponivel,
    assinar_no_cofre,
    cifrar_aes_no_cofre,
    decifrar_aes_no_cofre,
    gerar_aes_no_cofre,
    gerar_par_no_cofre,
    listar_chaves_no_cofre,
    sessao_hsm,
    verificar_no_cofre,
)
from metricas import contar_chaves
from schemas import (
    AssinarRequest,
    CifrarRequest,
    DecifrarRequest,
    GerarChaveRequest,
    VerificarRequest,
)

router = APIRouter(prefix="/chaves", tags=["chaves"])

def contar_total_geral():
    total, _rsa, _aes = contar_chaves()
    quantiade = len(listar_chaves_no_cofre())
    numero_de_chaves = total + quantiade
    return numero_de_chaves

def verificar_limite():
    try:
        numero_de_chaves = contar_total_geral()
    except CofreIndisponivel:
        raise HTTPException(
            status_code=503,
            detail="Cofre indisponível. " \
            "Não é possível verificar o limite de chaves, por isso a criação foi recusada.",
        )
    if numero_de_chaves >= config.LIMITE_CHAVES:
        raise HTTPException(
            status_code=409,
            detail=f"Limite de {config.LIMITE_CHAVES} chaves atingido. "
            f"Existem {numero_de_chaves} chaves, por isso a criação foi recusada.",
        )

# _______________Parte 1_____________________________

@router.post("/rsa")
def gerar_par_de_chaves(dados: GerarChaveRequest):
    verificar_limite()
    config.PASTA_CHAVES.mkdir(exist_ok=True)
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    publica = privada.public_key()
    privada_pem = privada.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    publica_pem = publica.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    with open(config.PASTA_CHAVES / f"{dados.nome}_privada.pem", "wb") as privada_arquivo:
        privada_arquivo.write(privada_pem)
    with open(config.PASTA_CHAVES / f"{dados.nome}_publica.pem", "wb") as publica_arquivo:
        publica_arquivo.write(publica_pem)
    return {"message": "Par de chaves RSA gerado com sucesso"}

@router.post("/assinar")
def assinar(dados: AssinarRequest):
    try:
        with open(config.PASTA_CHAVES / f"{dados.nome}_privada.pem", "rb") as privada_arquivo: 
            privada_pem = privada_arquivo.read()
        privada = serialization.load_pem_private_key(privada_pem, password=None)
        texto_bytes = dados.texto.encode("utf-8")
        assinatura = privada.sign(texto_bytes, padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        texto_assinado_b64 = base64.b64encode(assinatura).decode("utf-8")
        return {"assinatura": texto_assinado_b64}
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail="Chave privada não encontrada. Gere o par de chaves primeiro."
        )

@router.post("/verificar")
def verificar(dados: VerificarRequest):
    try:
        with open(config.PASTA_CHAVES / f"{dados.nome}_publica.pem", "rb") as publica_arquivo: 
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
    verificar_limite()
    config.PASTA_CHAVES.mkdir(exist_ok=True)
    chave_aes = os.urandom(32) 
    with open(config.PASTA_CHAVES / f"{dados.nome}_aes.key", "wb") as chave_arquivo:
        chave_arquivo.write(chave_aes)
    return {"message": "Chave AES gerada com sucesso"}

@router.post("/cifrar")
def cifrar(dados: CifrarRequest):
    try:
        with open(config.PASTA_CHAVES / f"{dados.nome}_aes.key", "rb") as chave_arquivo:
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
        with open(config.PASTA_CHAVES / f"{dados.nome}_aes.key", "rb") as chave_arquivo:
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
    lista = listar_chaves_no_cofre()
    return lista

@router.post("/cofre/rsa")
def gerar_par_RSA_no_cofre(dados: GerarChaveRequest):
    verificar_limite()
    chave_cofre = gerar_par_no_cofre(dados.nome)
    chave_publica = base64.b64encode(chave_cofre).decode("utf-8")  
    return {"chave_publica": chave_publica}

@router.post("/cofre/assinar")
def assinar_chave_no_cofre(dados: AssinarRequest):
    assinatura = assinar_no_cofre(dados.nome, dados.texto)
    texto_assinado_b64 = base64.b64encode(assinatura).decode("utf-8")
    return {"assinatura": texto_assinado_b64}

@router.post("/cofre/verificar")
def verificar_assinatura_no_cofre(dados: VerificarRequest):
        cofre_verificado = verificar_no_cofre(dados.nome, dados.texto_assinado, base64.b64decode(dados.assinatura_b64))
        return {"valida": cofre_verificado}     

@router.post("/cofre/aes")
def gerar_chave_AES_no_cofre(dados: GerarChaveRequest):
    verificar_limite()
    gerar_aes_no_cofre(dados.nome)
    return {"message": "Chave AES gerada com sucesso"}

@router.post("/cofre/cifrar")
def cifrar_no_cofre(dados: CifrarRequest):
    texto_cifrado_cofre = cifrar_aes_no_cofre(dados.nome, dados.texto)
    cifrado_cofre, nonce_cofre = texto_cifrado_cofre
    cifrado_cofre = base64.b64encode(cifrado_cofre).decode("utf-8")
    nonce_cofre = base64.b64encode(nonce_cofre).decode("utf-8")
    return {"cifrado": cifrado_cofre, "nonce": nonce_cofre}


@router.post("/cofre/decifrar")
def decifrar_no_cofre(dados: DecifrarRequest):
    texto_decifrado_cofre = decifrar_aes_no_cofre(
        dados.nome, base64.b64decode(dados.texto_cifrado), base64.b64decode(dados.nonce)
    )
    return {"texto": texto_decifrado_cofre}
