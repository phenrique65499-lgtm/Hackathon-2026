import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def carregar_config(variaveis):
    ambiente = os.environ.copy()
    for nome in ("MODO_DEMO", "PIN_PROFESSOR", "SENHA_SECRETARIA"):
        ambiente.pop(nome, None)
    ambiente.update(variaveis)
    return subprocess.run(
        [sys.executable, "-c", "import config; print(config.PIN_PROFESSOR, config.SENHA_SECRETARIA)"],
        cwd=ROOT,
        env=ambiente,
        capture_output=True,
        text=True,
        check=False,
    )


def test_producao_aceita_credenciais_fortes_distintas():
    resultado = carregar_config(
        {
            "PIN_PROFESSOR": "pin-professor-seguro",
            "SENHA_SECRETARIA": "senha-secretaria-segura",
        }
    )
    assert resultado.returncode == 0


@pytest.mark.parametrize(
    "credenciais",
    [
        {"PIN_PROFESSOR": "curto", "SENHA_SECRETARIA": "senha-secretaria-segura"},
        {"PIN_PROFESSOR": "pin-professor-seguro", "SENHA_SECRETARIA": "curta"},
        {"PIN_PROFESSOR": "senha-igual-longa", "SENHA_SECRETARIA": "senha-igual-longa"},
        {},
    ],
)
def test_producao_recusa_credenciais_fracas_ou_iguais(credenciais):
    resultado = carregar_config(credenciais)
    assert resultado.returncode != 0
    assert "Em produção" in resultado.stderr


def test_demo_usa_1234_para_as_duas_credenciais_mesmo_com_env():
    resultado = carregar_config(
        {
            "MODO_DEMO": "1",
            "PIN_PROFESSOR": "qualquer-pin",
            "SENHA_SECRETARIA": "qualquer-senha",
        }
    )
    assert resultado.returncode == 0
    assert resultado.stdout.strip() == "1234 1234"
