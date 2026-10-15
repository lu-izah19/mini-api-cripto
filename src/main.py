from fastapi import FastAPI, Request
import metricas
from schemas import MonitoramentoResponse, Chave, Operacoes, Disco, Tempo_no_ar

from router import router

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

    return MonitoramentoResponse(
        chave=Chave(total=total, rsa=rsa, aes=aes),
        operacoes=Operacoes(
            total=metricas.total_operacoes,
            rota=metricas.operacoes_por_tipo,
        ),
        disco=Disco(bytes=bytes, legivel=disco_legivel),
        tempo=Tempo_no_ar(segundos=diferenca, legivel=tempo_legivel),
    )
