"""Visão minimizada para secretaria: somente alunos e turma."""
from turmas import TURMAS
import regras


def alunos_problema():
    turma_por_id = {sid: turma for turma, alunos in TURMAS.items() for sid, _ in alunos}
    return [{"id": row["id"], "nome": row["nome"], "turma": turma_por_id.get(row["id"], "—")}
            for row in regras.alunos_problema()]
