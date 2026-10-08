from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

# _______________Testes Parte 2_____________________________

def cofre_status_responde_com_label_do_token():
    pass

def gerar_chave_no_cofre_devolve_parte_pública():
    pass

def chave_privada_NÃO_pode_ser_lida_nem_exportada():
    pass

def assinar_verificar_pelo_cofre_funciona():
    pass

def texto_alterado_reprova_verificação():
    pass

def cifrar_decifrar_pelo_cofre_devolve_original():
    pass

def listar_chaves_devolve_as_que_foram_criadas():
    pass