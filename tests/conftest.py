import pytest

import config
from hsm import sessao_hsm


@pytest.fixture(autouse=True)
def pasta_chaves_temporaria(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PASTA_CHAVES", tmp_path)


def faxina():
    with sessao_hsm() as sessao:
        objetos = list(sessao.get_objects())
        for obj in objetos:
            obj.destroy()

@pytest.fixture(autouse=True)
def limpar():
    faxina()
    yield
    faxina()