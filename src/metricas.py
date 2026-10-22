from datetime import UTC, datetime

import config

inicio = datetime.now(UTC)

def tempo_execucao():
    agora = datetime.now(UTC)
    diferenca = agora - inicio
    diferenca = int(diferenca.total_seconds())

    horas = diferenca // 3600
    minutos = (diferenca % 3600) // 60
    segs = diferenca % 60

    legivel = f"{horas}h {minutos}min {segs}s"
    return legivel, diferenca

total_operacoes = 0
operacoes_por_tipo = {}

def registrar_operacao(caminho):
    global total_operacoes
    total_operacoes += 1

    operacoes_por_tipo[caminho] = operacoes_por_tipo.get(caminho, 0) + 1

def contar_chaves():
    rsa = len(list(config.PASTA_CHAVES.glob("*_privada.pem")))
    aes = len(list(config.PASTA_CHAVES.glob("*_aes.key")))
    total = rsa + aes
    return total, rsa, aes

def tamanho_em_bytes():
    total_bytes = 0 
    for arquivo in config.PASTA_CHAVES.glob("*"):
        total_bytes += arquivo.stat().st_size 

    if(total_bytes < 1024):
        legivel = f"{total_bytes} B" 
    elif(total_bytes < 1024 * 1024 ):
        legivel = f"{total_bytes / 1024:.2f} KB"
    else:
        legivel = f"{total_bytes / (1024 * 1024):.2f} MB"

    return total_bytes, legivel