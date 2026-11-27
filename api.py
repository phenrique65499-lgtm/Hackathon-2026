"""Ponto de entrada da API.

A ordem das linhas abaixo importa: `banco.iniciar()` e `sincronizar()`
precisam rodar ANTES de importar os routers, porque `routers/professor.py`
importa `estado.py`, que calcula o relógio simulado consultando a tabela
`saidas` — ela precisa existir e já estar com os alunos de turmas.py.
"""
import banco

banco.iniciar()

from seed_alunos import sincronizar  # noqa: E402 (import tardio, de propósito — ver docstring)

sincronizar(silencioso=True)

from fastapi import FastAPI  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

import config  # noqa: E402
from erros import registrar_tratadores_de_erro  # noqa: E402
from routers import professor, publico, secretaria  # noqa: E402

app = FastAPI(title="Controle de Saída Escolar", version="2.0.0")
registrar_tratadores_de_erro(app)

if config.STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=config.STATIC_DIR), name="static")

app.include_router(publico.router)
app.include_router(professor.router)
app.include_router(secretaria.router)
