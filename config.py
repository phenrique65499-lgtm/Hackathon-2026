"""Configuração centralizada por variáveis de ambiente."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
DEMO = os.getenv("MODO_DEMO", "0") == "1"
DB_PATH = Path(os.getenv("ESCOLA_DB", BASE_DIR / "data" / ("escola_demo.db" if DEMO else "escola.db")))
PIN_PROFESSOR = os.getenv("PIN_PROFESSOR", "")
SENHA_SECRETARIA = os.getenv("SENHA_SECRETARIA", "")
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

if DEMO:
    PIN_PROFESSOR = "1234"
    SENHA_SECRETARIA = "1234"
elif (
    len(PIN_PROFESSOR) < 8
    or not PIN_PROFESSOR.strip()
    or len(SENHA_SECRETARIA) < 12
    or not SENHA_SECRETARIA.strip()
    or PIN_PROFESSOR == SENHA_SECRETARIA
):
    raise RuntimeError(
        "Em produção, configure PIN_PROFESSOR com pelo menos 8 caracteres e "
        "SENHA_SECRETARIA com pelo menos 12 caracteres; use valores diferentes."
    )
