from pathlib import Path

import pytest

from hsm import sessao_hsm

PASTA_CHAVES = Path("chaves")


def faxina():
    with sessao_hsm() as sessao:
        objetos = list(sessao.get_objects())
        for obj in objetos:
            obj.destroy()
    if PASTA_CHAVES.exists():
        for arquivo in PASTA_CHAVES.glob("*"):
            arquivo.unlink()

@pytest.fixture(autouse=True)
def limpar():
    faxina()
    yield
    faxina()