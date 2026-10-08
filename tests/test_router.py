from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

# _______________Testes parte 1_____________________________

def test_gerar_par_de_chaves_cria_os_dois_arquivos():
    client.post("chaves/rsa", json={"nome": "teste01"})
    assert os.path.exists("chaves/teste01_privada.pem")
    assert os.path.exists("chaves/teste01_publica.pem")

def test_assinar_verificar_mesmo_texto_devolve_verdadeiro():
    teste_texto_assinado = client.post("chaves/assinar", json={"nome": "teste01", "texto": "teste_texto"})
    assinatura = teste_texto_assinado.json()["assinatura"]
    texto_verificado = client.post(
        "chaves/verificar", 
        json={"nome": "teste01","assinatura_b64": assinatura, "texto_assinado": "teste_texto"}
    )
    verificado = texto_verificado.json()["valida"]
    assert verificado == True

def test_texto_alterado_em_uma_letra_reprova_verificacao():
    client.post("chaves/rsa", json={"nome": "teste02"})
    teste_texto_assinado = client.post("chaves/assinar", json={"nome": "teste02", "texto": "test_texto"})
    assinatura = teste_texto_assinado.json()["assinatura"]
    texto_verificado = client.post(
        "chaves/verificar", 
        json={"nome": "teste02","assinatura_b64": assinatura, "texto_assinado": "teste_texto"}
    )
    verificado = texto_verificado.json()["valida"]
    assert verificado == False

def test_cifrar_decifrar_devolve_texto_original():
    client.post("chaves/aes", json={"nome": "teste03"})
    cifrado = client.post("chaves/cifrar", json={"nome": "teste03", "texto": "teste_texto"})
    teste_texto_cifrado = cifrado.json()["cifrado"]
    teste_nonce = cifrado.json()["nonce"] 
    decifrado = client.post("chaves/decifrar", json={
        "nome": "teste03",
        "texto_cifrado": teste_texto_cifrado,
        "nonce": teste_nonce,
    })
    resposta = decifrado.json()["texto"]
    assert resposta == "teste_texto"

def test_cifrar_mesmo_texto_duas_vezes_da_resultados_DIFERENTES():
    client.post("chaves/aes", json={"nome": "teste04"})
    cifrado1 = client.post("chaves/cifrar", json={"nome": "teste04", "texto": "teste_texto"})
    teste_texto_cifrado1 = cifrado1.json()["cifrado"]

    cifrado2 = client.post("chaves/cifrar", json={"nome": "teste04", "texto": "teste_texto"})
    teste_texto_cifrado2 = cifrado2.json()["cifrado"]

    assert teste_texto_cifrado1 != teste_texto_cifrado2

def test_decifrar_com_iv_errado_falha():
    client.post("chaves/aes", json={"nome": "teste05"})
    cifrado1 = client.post("chaves/cifrar", json={"nome": "teste05", "texto": "teste_texto"})
    teste_texto_cifrado1 = cifrado1.json()["cifrado"]
    teste_nonce1 = cifrado1.json()["nonce"] 

    cifrado2 = client.post("chaves/cifrar", json={"nome": "teste05", "texto": "teste_texto"})
    teste_texto_cifrado2 = cifrado2.json()["cifrado"]
    teste_nonce2 = cifrado2.json()["nonce"] 

    decifrado = client.post("chaves/decifrar", json={
        "nome": "teste05",
        "texto_cifrado": teste_texto_cifrado1,
        "nonce": teste_nonce2,
    })

    assert decifrado.status_code == 400
