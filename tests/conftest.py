import pytest
from fastapi.testclient import TestClient

PAROLE = "droša-parole-123"
HTML = {"accept": "text/html"}


@pytest.fixture
def lietotne(tmp_path, monkeypatch):
    monkeypatch.setenv("CRM_DB_PATH", str(tmp_path / "crm.db"))
    from crm.app import izveidot_lietotni

    return izveidot_lietotni()


@pytest.fixture
def jauns_klients(lietotne):
    """Rūpnīca neatkarīgiem klientiem: katram sava sesija."""
    klienti = []

    def izveidot() -> TestClient:
        klients = TestClient(lietotne)
        klients.__enter__()
        klienti.append(klients)
        return klients

    yield izveidot
    for klients in klienti:
        klients.__exit__(None, None, None)


@pytest.fixture
def klients(jauns_klients) -> TestClient:
    return jauns_klients()


def registret(klients: TestClient, epasts: str, vards: str = "Testa Lietotājs") -> dict:
    atbilde = klients.post("/auth/register", json={"vards": vards, "epasts": epasts, "parole": PAROLE})
    assert atbilde.status_code == 201, atbilde.text
    return atbilde.json()


def pieslegt(klients: TestClient, epasts: str, vards: str = "Testa Lietotājs") -> dict:
    """Reģistrē (ja vajag) un pieslēdz lietotāju šim klientam."""
    klients.post("/auth/register", json={"vards": vards, "epasts": epasts, "parole": PAROLE})
    atbilde = klients.post("/auth/login", json={"epasts": epasts, "parole": PAROLE})
    assert atbilde.status_code == 200, atbilde.text
    return atbilde.json()["lietotajs"]
