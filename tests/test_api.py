"""Testes de api.py de ponta a ponta (HTTP), incluindo a sincronização de
turmas.py no startup e o rate-limit de PIN/senha. Rode com: pytest
"""
import sys

import pytest
from fastapi.testclient import TestClient


_MODULOS_DO_PROJETO = (
    "config", "banco", "regras", "secretaria", "seed_alunos",
    "autenticacao", "schemas", "erros", "estado", "api",
)


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("MODO_DEMO", "1")
    monkeypatch.setenv("ESCOLA_DB", str(tmp_path / "teste_api.db"))

    for nome in list(sys.modules):
        if nome in _MODULOS_DO_PROJETO or nome.startswith("routers"):
            sys.modules.pop(nome)

    import api  # dispara banco.iniciar() + sincronizar() com o banco temporário
    return TestClient(api.app), api


def test_startup_sincroniza_alunos_de_turmas(cliente):
    """Reproduz o bug original: sem a sincronização automática, esta lista viria vazia."""
    client, api_mod = cliente
    r = client.get("/api/estado", headers={"x-pin": api_mod.config.PIN_PROFESSOR})
    assert r.status_code == 200
    assert len(r.json()["alunos"]) > 0


def test_pin_invalido_eh_rejeitado(cliente):
    client, _ = cliente
    r = client.post("/api/professor/validar", headers={"x-pin": "errado"})
    assert r.status_code == 401


def test_pin_demo_correto_funciona(cliente):
    client, api_mod = cliente
    r = client.post("/api/professor/validar", headers={"x-pin": api_mod.config.PIN_PROFESSOR})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_fluxo_completo_saida_e_retorno(cliente):
    client, api_mod = cliente
    headers = {"x-pin": api_mod.config.PIN_PROFESSOR}

    aluno_id = client.get("/api/estado", headers=headers).json()["alunos"][0]["id"]

    r = client.post(f"/api/digital/{aluno_id}", headers=headers)
    assert r.json()["status"] == "saida"

    r = client.post(f"/api/digital/{aluno_id}", headers=headers)
    assert r.json()["status"] == "retorno"

    # o evento fica persistido (lido da auditoria), não some com o fim do request
    r = client.get("/api/professor/eventos", headers=headers)
    assert len(r.json()["eventos"]) == 2


def test_bloqueio_apos_varias_tentativas_erradas_de_pin(cliente):
    client, _ = cliente
    for _ in range(10):
        client.post("/api/professor/validar", headers={"x-pin": "0000"})
    r = client.post("/api/professor/validar", headers={"x-pin": "0000"})
    assert r.status_code == 429


def test_erro_tem_formato_padronizado(cliente):
    """Todo erro da API — seja HTTPException ou validação do Pydantic — sai
    no mesmo formato {"erro": ..., "detalhe": ...}, não {"detail": ...}."""
    client, _ = cliente
    r = client.post("/api/professor/validar", headers={"x-pin": "errado"})
    assert r.status_code == 401
    corpo = r.json()
    assert set(corpo) == {"erro", "detalhe"}
    assert corpo["erro"] == "nao_autorizado"


def test_historico_por_aluno(cliente):
    client, api_mod = cliente
    headers = {"x-pin": api_mod.config.PIN_PROFESSOR}
    aluno_id = client.get("/api/estado", headers=headers).json()["alunos"][0]["id"]

    client.post(f"/api/digital/{aluno_id}", headers=headers)
    client.post(f"/api/digital/{aluno_id}", headers=headers)

    r = client.get(f"/api/professor/historico/{aluno_id}", headers=headers)
    assert r.status_code == 200
    historico = r.json()["historico"]
    assert len(historico) == 1
    assert historico[0]["retorno"] is not None


def test_exportar_csv(cliente):
    client, api_mod = cliente
    headers = {"x-pin": api_mod.config.PIN_PROFESSOR}
    aluno_id = client.get("/api/estado", headers=headers).json()["alunos"][0]["id"]
    client.post(f"/api/digital/{aluno_id}", headers=headers)
    client.post(f"/api/digital/{aluno_id}", headers=headers)

    r = client.get("/api/professor/exportar", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    linhas = r.text.strip().splitlines()
    assert linhas[0] == "aluno_id,nome,turma,saida,retorno,duracao_segundos,estourou"
    assert len(linhas) == 2


def test_bloqueio_tambem_vale_para_senha_da_secretaria(cliente):
    """Antes só o PIN do professor tinha rate-limit; a senha da secretaria ficava de fora."""
    client, _ = cliente
    for _ in range(10):
        client.post("/api/secretaria/zerar/1", headers={"x-senha": "errada"})
    r = client.post("/api/secretaria/zerar/1", headers={"x-senha": "errada"})
    assert r.status_code == 429


def test_lista_de_alunos_problema_exige_senha_da_secretaria(cliente):
    client, api_mod = cliente
    headers = {"x-senha": api_mod.config.SENHA_SECRETARIA}
    client.post(
        "/api/demo/estouro/1",
        headers={"x-pin": api_mod.config.PIN_PROFESSOR},
    )

    sem_senha = client.get("/api/secretaria/problema")
    assert sem_senha.status_code == 401

    autenticada = client.get("/api/secretaria/problema", headers=headers)
    assert autenticada.status_code == 200
    assert autenticada.json()["alunos"][0]["id"] == 1


def test_reiniciar_demo_limpa_e_relança_um_unico_evento(cliente):
    client, api_mod = cliente
    headers = {"x-pin": api_mod.config.PIN_PROFESSOR}
    aluno_id = client.get("/api/estado", headers=headers).json()["alunos"][0]["id"]
    client.post(f"/api/digital/{aluno_id}", headers=headers)

    r = client.post("/api/demo/reiniciar", headers=headers)
    assert r.status_code == 200

    eventos = client.get("/api/professor/eventos", headers=headers).json()["eventos"]
    assert len(eventos) == 1
    assert "reiniciada" in eventos[0]["texto"]
