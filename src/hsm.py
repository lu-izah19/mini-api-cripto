from contextlib import contextmanager
import os
import pkcs11
from pkcs11 import Attribute, KeyType, ObjectClass
from pkcs11 import Mechanism

CAMINHO_BIBLIOTECA = "/usr/lib/softhsm/libsofthsm2.so"
LABEL_TOKEN = "cofre-treino"
PIN = "5678"


@contextmanager
def sessao_hsm():
    """Abre uma sessão com o cofre e garante que ela será fechada.

    O 'with' garante o fechamento mesmo se der erro no meio.
    """
    lib = pkcs11.lib(CAMINHO_BIBLIOTECA)
    token = lib.get_token(token_label=LABEL_TOKEN)

    sessao = token.open(user_pin=PIN, rw=True)
    try:
        yield sessao
    finally:
        sessao.close()

def gerar_par_no_cofre(label: str) -> bytes:
    """Gera um par RSA DENTRO do cofre. A privada nunca sai."""
    with sessao_hsm() as sessao:
        publica, privada = sessao.generate_keypair(
            KeyType.RSA,
            2048,
            store=True,          # guarda no cofre (não só na sessão)
            label=label,
            private_template={
                Attribute.TOKEN: True,
                Attribute.PRIVATE: True,
                Attribute.SENSITIVE: True,
                Attribute.EXTRACTABLE: False,
                Attribute.SIGN: True,
                Attribute.LABEL: label,
            },
            public_template={
                Attribute.TOKEN: True,
                Attribute.VERIFY: True,
                Attribute.LABEL: label,
            },
        )
        return bytes(publica[Attribute.MODULUS])

def assinar_no_cofre(label: str, texto: str) -> bytes:
    """Manda o trabalho para o cofre. A chave não sai de lá."""
    with sessao_hsm() as sessao:
        privada = sessao.get_key(
            object_class=ObjectClass.PRIVATE_KEY,
            label=label,
        )
        return privada.sign(texto.encode(), mechanism=Mechanism.SHA256_RSA_PKCS)


def verificar_no_cofre(label: str, texto: str, assinatura: bytes) -> bool:
    with sessao_hsm() as sessao:
        publica = sessao.get_key(
            object_class=ObjectClass.PUBLIC_KEY,
            label=label,
        )
        return publica.verify(
            texto.encode(), assinatura, mechanism=Mechanism.SHA256_RSA_PKCS
        )

def gerar_aes_no_cofre(label: str):
    with sessao_hsm() as sessao:
        pchave_aes = sessao.generate_key(
            KeyType.AES,
            256,
            store=True,
            label=label,
            template={
                Attribute.TOKEN: True,
                Attribute.PRIVATE: True,
                Attribute.SENSITIVE: True,
                Attribute.EXTRACTABLE: False,
                Attribute.LABEL: label,
                Attribute.ENCRYPT: True,
                Attribute.DECRYPT: True,
            },
        )

def cifrar_aes_no_cofre(label: str, texto: str):
    with sessao_hsm() as sessao:
        chave_aes = sessao.get_key(
            object_class=ObjectClass.SECRET_KEY,
            label=label,
        )
        nonce = os.urandom(12)
        return chave_aes.encrypt(
            texto.encode(), mechanism=Mechanism.AES_GCM, mechanism_param=(nonce, b"", 128)
        ), nonce

def decifrar_aes_no_cofre(label: str, cifrado: bytes, nonce: bytes):
    with sessao_hsm() as sessao:
        chave_aes = sessao.get_key(
            object_class=ObjectClass.SECRET_KEY,
            label=label,
        )
        return chave_aes.decrypt(
            cifrado, mechanism=Mechanism.AES_GCM, mechanism_param=(nonce, b"", 128)
        ).decode()
    

