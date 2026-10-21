
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_monitoramento_responde():
    resposta = client.get("/monitoramento")
    assert resposta.status_code == 200

    dados = resposta.json()
    assert "disco" in dados
    assert "chave" in dados
    assert "operacoes" in dados
    assert "tempo" in dados

def test_gerar_chave_aumenta_total():
    antes = client.get("/monitoramento").json()["chave"]["total"]

    client.post("chaves/rsa", json={"nome": "testeMonitoramento"})

    depois = client.get("/monitoramento").json()["chave"]["total"]
    assert depois == antes + 1

def test_3_chamadas_aumenta_total():
    antes = client.get("/monitoramento").json()["operacoes"]["total"]

    client.post("chaves/rsa", json={"nome": "testeChamada1"})
    client.post("chaves/rsa", json={"nome": "testeChamada2"})
    client.post("chaves/rsa", json={"nome": "testeChamada3"})

    depois = client.get("/monitoramento").json()["operacoes"]["total"]
    assert depois == antes + 4

def test_tempo_no_ar_maior_que_zero():
    segundos = client.get("/monitoramento").json()["tempo"]["segundos"]
    assert segundos > 0

def test_gerar_chave_aumenta_espaco_disco():
    antes = client.get("/monitoramento").json()["disco"]["bytes"]

    client.post("chaves/rsa", json={"nome": "testeEspacoDisco"})

    depois = client.get("/monitoramento").json()["disco"]["bytes"]
    assert depois > antes 
