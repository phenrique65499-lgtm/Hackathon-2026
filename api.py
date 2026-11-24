import os
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import banco
import regras
import secretaria
from relogio import Relogio
from turmas import TURMAS

DEMO = os.environ.get("MODO_DEMO") == "1"
PIN = os.environ.get("PIN_PROFESSOR", "1234")

banco.iniciar()

relogio = Relogio(max(time.time(), regras.ultimo_instante()))
eventos = deque(maxlen=12)


def registrar(texto, cls=""):
    hora = time.strftime("%H:%M:%S", time.localtime(relogio.agora()))
    eventos.appendleft({"hora": hora, "texto": texto, "cls": cls})


def exigir_pin(pin):
    if pin != PIN:
        raise HTTPException(403, "PIN do professor incorreto.")


def exigir_demo():
    if not DEMO:
        raise HTTPException(404, "Disponível apenas no modo simulação.")


app = FastAPI(title="Controle de saída da sala")


PASTA = Path(__file__).parent
app.mount("/static", StaticFiles(directory=PASTA / "static"), name="static")


def achar_pagina():
    for caminho in (PASTA / "static" / "index.html", PASTA / "index.html"):
        if caminho.is_file():
            return caminho
    return None


@app.get("/")
def pagina():
    caminho = achar_pagina()
    if caminho is None:
        return HTMLResponse(
            "<h2>Arquivo da página não encontrado</h2>"
            "<p>Crie a pasta <b>static</b> ao lado de <b>api.py</b> e coloque nela o arquivo "
            f"<b>index.html</b>.</p><p>Procurei em: <code>{PASTA / 'static' / 'index.html'}</code></p>",
            status_code=500,
        )
    return FileResponse(caminho)


@app.get("/api/estado")
def estado():
    alunos = regras.estado_alunos()
    turma_por_id = {
        aluno_id: turma
        for turma, lista in TURMAS.items()
        for aluno_id, _ in lista
    }
    if DEMO and TURMAS:
        turma_demo = next(iter(TURMAS))
        for aluno in alunos:
            turma_por_id.setdefault(aluno["id"], turma_demo)

    return {
        "agora": relogio.agora(),
        "limite": regras.LIMITE_SEGUNDOS,
        "max": regras.LIMITE_ESTOUROS,
        "demo": DEMO,
        "turmas": list(TURMAS),
        "alunos": [
            {"id": r["id"], "nome": r["nome"], "estouros": r["estouros"],
             "liberado": bool(r["liberado"]), "saida": r["saida"],
             "turma": turma_por_id.get(r["id"])}
            for r in alunos
            if r["id"] in turma_por_id
        ],
    }


@app.post("/api/professor/validar")
def validar_pin(x_pin: str = Header(default="")):
    exigir_pin(x_pin)
    return {"ok": True}


@app.post("/api/digital/{aluno_id}")
def digital(aluno_id: int):
    """Equivale a encostar o dedo no sensor da porta."""
    status, msg = regras.passar_digital(aluno_id, relogio.agora())
    ruim = status in ("negado", "desconhecido") or "passou de" in msg
    registrar(msg, "bad" if ruim else ("ok" if status == "retorno" else ""))
    return {"status": status, "mensagem": msg}


@app.post("/api/professor/liberar/{aluno_id}")
def liberar(aluno_id: int, x_pin: str = Header(default="")):
    exigir_pin(x_pin)
    regras.liberar_aluno(aluno_id)
    registrar(f"Professor liberou uma saída (ID {aluno_id}).", "ok")
    return {"ok": True}


@app.post("/api/demo/estouro/{aluno_id}")
def simular_estouros(aluno_id: int, x_pin: str = Header(default="")):
    exigir_demo()
    exigir_pin(x_pin)
    if not regras.marcar_aluno_problema(aluno_id):
        raise HTTPException(404, "Aluno não encontrado.")
    registrar(f"Professor simulou 3/3 atrasos para o aluno (ID {aluno_id}).", "ok")
    return {"ok": True}


@app.get("/registros")
def pagina_registros():
    return FileResponse(PASTA / "static" / "registros.html")


@app.get("/api/professor/eventos")
def listar_eventos(x_pin: str = Header(default="")):
    exigir_pin(x_pin)
    return {"eventos": list(eventos)}


@app.get("/secretaria")
def pagina_secretaria():
    return FileResponse(PASTA / "static" / "secretaria.html")


@app.get("/api/secretaria/problema")
def problema_secretaria():
    """Lista enxuta (nome + turma) dos alunos problema, para exibir na secretaria."""
    return {"alunos": secretaria.alunos_problema()}


@app.post("/api/secretaria/zerar/{aluno_id}")
def zerar_atrasos_secretaria(aluno_id: int):
    if not any(aluno["id"] == aluno_id for aluno in secretaria.alunos_problema()):
        raise HTTPException(404, "Aluno problema não encontrado.")
    regras.zerar_contador(aluno_id)
    registrar(f"Secretaria zerou os atrasos do aluno (ID {aluno_id}).", "ok")
    return {"ok": True}


@app.post("/api/demo/reiniciar")
def reiniciar():
    exigir_demo()
    regras.resetar_banco()
    relogio.reiniciar()
    eventos.clear()
    registrar("Simulação reiniciada. Todos os alunos estão na sala.")
    return {"ok": True}