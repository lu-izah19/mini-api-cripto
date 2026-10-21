from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

import metricas
from config import LIMITE_CHAVES
from hsm import CofreIndisponivel
from router import contar_total_geral, router
from schemas import Chave, Disco, Limite, MonitoramentoResponse, Operacoes, Tempo_no_ar

app = FastAPI(title="Mini API de criptografia")
app.include_router(router)


@app.get("/saude")
def saude():
    return {"status": "ok"}

@app.middleware("http")
async def contar_operacoes(request: Request, call_next):
    metricas.registrar_operacao(request.url.path)
    resposta = await call_next(request)
    return resposta

@app.get("/monitoramento", response_model=MonitoramentoResponse)
def monitoramento():
    total, rsa, aes = metricas.contar_chaves()
    bytes, disco_legivel = metricas.tamanho_em_bytes()
    tempo_legivel, diferenca = metricas.tempo_execucao()
    maximo = LIMITE_CHAVES
    try:
        usado = contar_total_geral()
        cofre_disponivel = True
    except CofreIndisponivel:
        usado = None
        cofre_disponivel = False

    return MonitoramentoResponse(
        cofre_disponivel=cofre_disponivel,
        chave=Chave(total=total, rsa=rsa, aes=aes),
        operacoes=Operacoes(
            total=metricas.total_operacoes,
            rota=metricas.operacoes_por_tipo,
        ),
        disco=Disco(bytes=bytes, legivel=disco_legivel),
        tempo=Tempo_no_ar(segundos=diferenca, legivel=tempo_legivel),
        limite=Limite(maximo= maximo, usado= usado),
    )

app.mount("/", StaticFiles(directory="screen", html=True), name="painel")
