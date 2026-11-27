"""Testes de regras.py. Rode com: pytest

`config.py` recusa rodar em produção sem PIN/senha fortes, então cada teste
ativa MODO_DEMO=1 e usa um banco SQLite temporário e isolado — nada aqui
toca no banco real do projeto.
"""
import importlib
import sys

import pytest


@pytest.fixture
def regras_isoladas(tmp_path, monkeypatch):
    monkeypatch.setenv("MODO_DEMO", "1")
    monkeypatch.setenv("ESCOLA_DB", str(tmp_path / "teste.db"))

    for nome in ("config", "banco", "regras"):
        sys.modules.pop(nome, None)

    import config  # noqa: F401  (recarregado para ler as env vars novas)
    import banco
    import regras

    banco.iniciar()
    with banco.conectar() as con:
        con.execute("INSERT INTO alunos (id, nome, estouros, liberado) VALUES (1, 'Aluno Teste', 0, 0)")

    return regras


def test_primeira_digital_registra_saida(regras_isoladas):
    status, msg = regras_isoladas.passar_digital(1, agora=1000)
    assert status == "saida"
    assert "saiu" in msg


def test_alunos_fora_retorna_duracao_e_sinaliza_limite(regras_isoladas):
    regras_isoladas.passar_digital(1, agora=1000)
    assert regras_isoladas.alunos_fora(agora=1060) == [("Aluno Teste", 60, False)]
    assert regras_isoladas.alunos_fora(agora=1181) == [("Aluno Teste", 181, True)]


def test_retorno_dentro_do_limite_nao_conta_estouro(regras_isoladas):
    regras_isoladas.passar_digital(1, agora=1000)
    status, msg = regras_isoladas.passar_digital(1, agora=1000 + 60)  # 1 min, limite é 3 min
    assert status == "retorno"
    assert "Dentro do tempo" in msg


def test_retorno_fora_do_limite_conta_estouro(regras_isoladas):
    regras_isoladas.passar_digital(1, agora=1000)
    status, msg = regras_isoladas.passar_digital(1, agora=1000 + 200)  # 200s > 180s
    assert status == "retorno"
    assert "Estouro 1/3" in msg


def test_tres_estouros_bloqueia_proxima_saida(regras_isoladas):
    for volta in range(3):
        base = 1000 + volta * 1000
        regras_isoladas.passar_digital(1, agora=base)
        regras_isoladas.passar_digital(1, agora=base + 200)  # sempre estoura

    status, msg = regras_isoladas.passar_digital(1, agora=9000)
    assert status == "negado"


def test_professor_libera_uma_unica_saida(regras_isoladas):
    for volta in range(3):
        base = 1000 + volta * 1000
        regras_isoladas.passar_digital(1, agora=base)
        regras_isoladas.passar_digital(1, agora=base + 200)

    regras_isoladas.liberar_aluno(1)
    status, _ = regras_isoladas.passar_digital(1, agora=9000)
    assert status == "saida"

    regras_isoladas.passar_digital(1, agora=9100)  # retorno, sem novo estouro
    status, _ = regras_isoladas.passar_digital(1, agora=9200)  # ainda tem 3 estouros, liberação já foi usada
    assert status == "negado"


def test_digital_desconhecida_nao_quebra(regras_isoladas):
    status, msg = regras_isoladas.passar_digital(999, agora=1000)
    assert status == "desconhecido"


def test_secretaria_zera_contador_e_libera_saida(regras_isoladas):
    for volta in range(3):
        base = 1000 + volta * 1000
        regras_isoladas.passar_digital(1, agora=base)
        regras_isoladas.passar_digital(1, agora=base + 200)

    regras_isoladas.zerar_contador(1)
    status, _ = regras_isoladas.passar_digital(1, agora=9000)
    assert status == "saida"


def test_cada_acao_grava_na_auditoria(regras_isoladas):
    """O /registros da interface lê desta mesma tabela — se parar de gravar
    aqui, a tela de eventos para de atualizar."""
    regras_isoladas.passar_digital(1, agora=1000)
    with regras_isoladas.conectar() as con:
        linhas = con.execute("SELECT acao, classe FROM auditoria ORDER BY id").fetchall()
    assert len(linhas) == 1
    assert linhas[0]["acao"] == "saida"
