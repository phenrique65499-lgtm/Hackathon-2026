"""Rotas do professor. Protegidas em bloco pelo PIN (`dependencies=` do router),
então uma rota nova aqui já nasce protegida sem precisar lembrar de declarar isso."""
import csv
import io
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

import banco
import config
import regras
import schemas
from autenticacao import exigir_demo, exigir_pin
from estado import relogio
from turmas import TURMAS

router = APIRouter(prefix="/api", tags=["professor"], dependencies=[Depends(exigir_pin)])


@router.get("/estado", response_model=schemas.EstadoResposta)
def estado():
    linhas = regras.estado_alunos()
    turma_por_id = {sid: turma for turma, alunos in TURMAS.items() for sid, _ in alunos}
    if config.DEMO and TURMAS:
        turma_demo = next(iter(TURMAS))
        for linha in linhas:
            turma_por_id.setdefault(linha["id"], turma_demo)

    return schemas.EstadoResposta(
        agora=relogio.agora(),
        limite=regras.LIMITE_SEGUNDOS,
        max=regras.LIMITE_ESTOUROS,
        demo=config.DEMO,
        turmas=list(TURMAS),
        alunos=[
            schemas.AlunoEstado(
                id=linha["id"],
                nome=linha["nome"],
                estouros=linha["estouros"],
                liberado=bool(linha["liberado"]),
                saida=linha["saida"],
                turma=turma_por_id.get(linha["id"]),
            )
            for linha in linhas
            if linha["id"] in turma_por_id
        ],
    )


@router.post("/professor/validar", response_model=schemas.OkResposta)
def validar_pin():
    return schemas.OkResposta()


@router.post("/digital/{aluno_id}", response_model=schemas.DigitalResposta)
def digital(aluno_id: int):
    """Equivale a encostar o dedo no sensor da porta."""
    status, msg = regras.passar_digital(aluno_id, relogio.agora())
    return schemas.DigitalResposta(status=status, mensagem=msg)


@router.post("/professor/liberar/{aluno_id}", response_model=schemas.OkResposta)
def liberar(aluno_id: int):
    if not regras.liberar_aluno(aluno_id):
        raise HTTPException(404, "Aluno não encontrado.")
    return schemas.OkResposta()


@router.get("/professor/eventos", response_model=schemas.EventosResposta)
def listar_eventos():
    eventos = [
        schemas.EventoItem.model_validate(evento)
        for evento in banco.listar_eventos()
    ]
    return schemas.EventosResposta(eventos=eventos)


@router.get("/professor/historico/{aluno_id}", response_model=schemas.HistoricoResposta)
def historico_aluno(aluno_id: int):
    """Histórico de saídas de um aluno específico."""
    linhas = regras.historico(aluno_id)
    return schemas.HistoricoResposta(
        historico=[
            schemas.HistoricoItem(
                saida=l["saida"],
                retorno=l["retorno"],
                duracao=(l["retorno"] - l["saida"]) if l["retorno"] is not None else None,
                estourou=bool(l["estourou"]),
            )
            for l in linhas
        ]
    )


@router.get("/professor/exportar")
def exportar_relatorio():
    """Baixa um CSV com todas as saídas já registradas (para arquivar/imprimir)."""
    turma_por_id = {sid: turma for turma, alunos in TURMAS.items() for sid, _ in alunos}

    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(["aluno_id", "nome", "turma", "saida", "retorno", "duracao_segundos", "estourou"])
    for linha in regras.relatorio_saidas():
        saida_fmt = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(linha["saida"]))
        if linha["retorno"] is not None:
            retorno_fmt = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(linha["retorno"]))
            duracao = int(linha["retorno"] - linha["saida"])
        else:
            retorno_fmt, duracao = "", ""
        escritor.writerow([
            linha["aluno_id"], linha["nome"], turma_por_id.get(linha["aluno_id"], "—"),
            saida_fmt, retorno_fmt, duracao, bool(linha["estourou"]),
        ])
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=relatorio_saidas.csv"},
    )


@router.post("/demo/estouro/{aluno_id}", response_model=schemas.OkResposta, dependencies=[Depends(exigir_demo)])
def simular_estouros(aluno_id: int):
    if not regras.marcar_aluno_problema(aluno_id):
        raise HTTPException(404, "Aluno não encontrado.")
    return schemas.OkResposta()


@router.post("/demo/reiniciar", response_model=schemas.OkResposta, dependencies=[Depends(exigir_demo)])
def reiniciar():
    regras.resetar_banco()
    relogio.reiniciar()
    banco.limpar_eventos()
    banco.registrar_auditoria(
        "sistema", "reset_simulacao", None,
        "Simulação reiniciada. Todos os alunos estão na sala.", relogio.agora(),
    )
    return schemas.OkResposta()
