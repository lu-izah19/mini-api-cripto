import uuid

import pytest
from fastapi.testclient import TestClient
from pkcs11 import Attribute, ObjectClass
from pkcs11.exceptions import AttributeSensitive

from hsm import sessao_hsm
from main import app

client = TestClient(app)

# _______________Testes Parte 2_____________________________

def test_cofre_status_responde_com_label_do_token():
    resposta = client.get("chaves/cofre/status")
    assert resposta.status_code == 200
    assert resposta.json()["token"] == "cofre-treino"


def test_gerar_chave_no_cofre_devolve_parte_pública():
    nome = f"teste_cofre_{uuid.uuid4().hex}"
    resposta = client.post("chaves/cofre/rsa", json={"nome": nome}) 
    assert resposta.status_code == 200
    assert "chave_publica" in resposta.json()
    assert len(resposta.json()["chave_publica"]) > 0

def test_chave_privada_NÃO_pode_ser_lida_nem_exportada():
    nome = f"teste_cofre_{uuid.uuid4().hex}"
    client.post("chaves/cofre/rsa", json={"nome": nome}) 
    with sessao_hsm() as sessao:
        privada = sessao.get_key(
            object_class=ObjectClass.PRIVATE_KEY,
            label=nome,
        )
        assert privada[Attribute.EXTRACTABLE] is False
        assert privada[Attribute.SENSITIVE] is True
        with pytest.raises(AttributeSensitive):
            privada[Attribute.PRIVATE_EXPONENT]

def test_assinar_verificar_pelo_cofre_funciona():
    texto = "teste_txt_cofre"
    nome = f"teste_cofre_{uuid.uuid4().hex}"
    client.post("chaves/cofre/rsa", json={"nome": nome})
    assinatura_cofre = client.post("chaves/cofre/assinar", json={"nome": nome, "texto": texto})
    verificacao_cofre = client.post("chaves/cofre/verificar", json={
        "nome": nome, "texto_assinado": texto, "assinatura_b64": assinatura_cofre.json()["assinatura"]
    })
    assert verificacao_cofre.status_code == 200
    assert verificacao_cofre.json()["valida"] is True

def test_texto_alterado_reprova_verificação():
    nome = f"teste_cofre_{uuid.uuid4().hex}"
    client.post("chaves/cofre/rsa", json={"nome": nome}) 
    assinatura_cofre = client.post("chaves/cofre/assinar", json={"nome": nome, "texto": "texto_original"})
    verificacao_cofre = client.post("chaves/cofre/verificar", json={
        "nome": nome, "texto_assinado": "texto_alterado", "assinatura_b64": assinatura_cofre.json()["assinatura"]
    })
    assert verificacao_cofre.status_code == 200
    assert verificacao_cofre.json()["valida"] is False

def test_cifrar_decifrar_pelo_cofre_devolve_original():
    texto = "teste_txt_cofre"
    nome = f"teste_cofre_{uuid.uuid4().hex}"
    client.post("chaves/cofre/aes", json={"nome": nome}) 
    cifrado_cofre = client.post("chaves/cofre/cifrar", json={"nome": nome, "texto": texto})
    decifrado_cofre = client.post("chaves/cofre/decifrar", json={
        "nome": nome, "texto_cifrado": cifrado_cofre.json()["cifrado"], "nonce": cifrado_cofre.json()["nonce"]
    })
    assert decifrado_cofre.status_code == 200
    assert decifrado_cofre.json()["texto"] == texto

def test_listar_chaves_devolve_as_que_foram_criadas():
    nome = f"teste_cofre_{uuid.uuid4().hex}"
    client.post("chaves/cofre/rsa", json={"nome": nome}) 
    chaves_cofre = client.get("chaves/cofre/chaves")
    assert chaves_cofre.status_code == 200
    lista_chaves_cofre = []   
    for chave in chaves_cofre.json():
        lista_chaves_cofre.append(chave["label"])
    assert nome in lista_chaves_cofre

def test_verificar_no_cofre_com_chave_inexistente_devolve_404():
    resposta = client.post(
        "/chaves/cofre/verificar",
        json={
            "nome": "nao-existe",
            "texto_assinado": "oi",
            "assinatura_b64": "YWJj",
        },
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Chave não encontrada no cofre. Gere a chave primeiro."

def test_cifrar_no_cofre_com_chave_inexistente_devolve_404():
    resposta = client.post(
        "/chaves/cofre/cifrar",
        json={
            "nome": "nao-existe",
            "texto": "oi",
        },
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Chave não encontrada no cofre. Gere a chave primeiro."

def test_decifrar_no_cofre_com_chave_inexistente_devolve_404():
    resposta = client.post(
        "/chaves/cofre/decifrar",
        json={
            "nome": "nao-existe",
            "texto_cifrado": "YWJj",
            "nonce": "YWJj",
        },
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Chave não encontrada no cofre. Gere a chave primeiro."

def test_assinar_no_cofre_com_chave_inexistente_devolve_404():
    resposta = client.post(
        "/chaves/cofre/assinar",
        json={
            "nome": "nao-existe",
            "texto": "oi",
        },
    )

    assert resposta.status_code == 404
    assert resposta.json()["detail"] == "Chave não encontrada no cofre. Gere a chave primeiro."
 