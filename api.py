import os
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

import banco
import regras
from relogio import Relogio
from turmas import TURMAS

DEMO = os.environ.get("MODO_DEMO") == "1"
PIN = os.environ.get("PIN_PROFESSOR", "1234")
NOMES_DEMO = ["Ana", "Bruno", "Carla", "Diego", "Elisa"]

banco.iniciar()


def semear_alunos_fixos():
    ids_usados = set()
    with banco.conectar() as conexao:
        for turma, alunos in TURMAS.items():
            for aluno_id, nome in alunos:
                if not isinstance(aluno_id, int) or aluno_id <= 0 or not nome.strip():
                    raise ValueError(f"Aluno inválido configurado na turma {turma!r}.")
                if aluno_id in ids_usados:
                    raise ValueError(f"O ID {aluno_id} foi cadastrado em mais de uma turma.")
                ids_usados.add(aluno_id)
                conexao.execute(
                    """
                    INSERT INTO alunos (id, nome) VALUES (?, ?)
                    ON CONFLICT(id) DO UPDATE SET nome = excluded.nome
                    """,
                    (aluno_id, nome.strip()),
                )


def semear():
    for i, nome in enumerate(NOMES_DEMO, start=1):
        regras.cadastrar_aluno(i, nome)


semear_alunos_fixos()
if DEMO and not regras.listar_alunos():
    semear()

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


@app.post("/api/professor/zerar/{aluno_id}")
def zerar(aluno_id: int, x_pin: str = Header(default="")):
    exigir_pin(x_pin)
    regras.zerar_contador(aluno_id)
    registrar(f"Professor zerou o contador (ID {aluno_id}).", "ok")
    return {"ok": True}


@app.get("/registros")
def pagina_registros():
    return FileResponse(PASTA / "static" / "registros.html")


@app.get("/api/professor/eventos")
def listar_eventos(x_pin: str = Header(default="")):
    exigir_pin(x_pin)
    return {"eventos": list(eventos)}


@app.post("/api/demo/reiniciar")
def reiniciar():
    exigir_demo()
    regras.resetar_banco()
    semear_alunos_fixos()
    if not regras.listar_alunos():
        semear()
    relogio.reiniciar()
    eventos.clear()
    registrar("Simulação reiniciada. Todos os alunos estão na sala.")
    return {"ok": True}