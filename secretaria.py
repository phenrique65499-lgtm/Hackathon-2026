"""Lista de alunos problema para a secretaria.

A secretaria não precisa (e não deve) ver estouros, horários ou liberações —
só o nome do aluno, a turma e o aviso de que ele é um aluno problema.
"""

from turmas import TURMAS
import regras


def _turma_por_id():
    return {
        aluno_id: turma
        for turma, alunos in TURMAS.items()
        for aluno_id, _ in alunos
    }


def alunos_problema():
    """[{"nome": ..., "turma": ...}] dos alunos problema no momento."""
    turma_por_id = _turma_por_id()
    return [
        {"nome": aluno["nome"], "turma": turma_por_id.get(aluno["id"], "—")}
        for aluno in regras.alunos_problema()
    ]