from fastapi import FastAPI

from router import router

app = FastAPI(title="Mini API de criptografia")
app.include_router(router)


@app.get("/saude")
def saude():
    return {"status": "ok"}