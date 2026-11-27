"""Rotas da secretaria: visão enxuta (nome + turma) e zerar atrasos."""
from fastapi import APIRouter, Depends, HTTPException

import regras
import schemas
import secretaria as secretaria_servico
from autenticacao import exigir_senha_secretaria

router = APIRouter(prefix="/api/secretaria", tags=["secretaria"])


@router.get(
    "/problema",
    response_model=schemas.ProblemaResposta,
    dependencies=[Depends(exigir_senha_secretaria)],
)
def problema():
    alunos = [
        schemas.AlunoProblema.model_validate(aluno)
        for aluno in secretaria_servico.alunos_problema()
    ]
    return schemas.ProblemaResposta(alunos=alunos)


@router.post(
    "/zerar/{aluno_id}",
    response_model=schemas.OkResposta,
    dependencies=[Depends(exigir_senha_secretaria)],
)
def zerar_atrasos(aluno_id: int):
    if not regras.zerar_contador(aluno_id):
        raise HTTPException(404, "Aluno não encontrado.")
    return schemas.OkResposta()
