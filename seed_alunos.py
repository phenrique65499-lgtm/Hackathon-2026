"""Sincroniza a tabela `alunos` do banco com a lista fixa em turmas.py.

PROBLEMA QUE ISSO RESOLVE:
    `banco.iniciar()` só cria as tabelas (inclusive com os CHECKs e índices),
    mas nunca insere os alunos. Sem rodar esta sincronização, a tabela
    `alunos` fica vazia e toda digital cai em "Digital não reconhecida",
    porque `regras.passar_digital` busca o aluno na tabela e não encontra
    ninguém — mesmo com o esquema do banco impecável.

O QUE A SINCRONIZAÇÃO FAZ:
    - Insere quem está em turmas.py e ainda não existe no banco.
    - Atualiza o nome de quem já existe, se o nome mudou em turmas.py.
    - NUNCA mexe em `estouros` ou `liberado` de quem já existe.
    - NUNCA remove do banco quem saiu de turmas.py (preserva histórico).
    - Recusa sincronizar se houver ID duplicado entre turmas (erro claro
      em vez de um aluno sobrescrever o outro silenciosamente).

USO:
    python seed_alunos.py            # chamada direta, fora da API
    from seed_alunos import sincronizar; sincronizar()   # como em api.py
"""
import banco
from turmas import TURMAS


def _verificar_duplicatas():
    vista_em = {}
    duplicados = []
    for turma, alunos in TURMAS.items():
        for aluno_id, nome in alunos:
            if aluno_id in vista_em:
                duplicados.append((aluno_id, nome, vista_em[aluno_id], turma))
            else:
                vista_em[aluno_id] = turma

    if duplicados:
        linhas = "\n".join(
            f"  - ID {aluno_id} ({nome}) aparece em '{turma_a}' e de novo em '{turma_b}'"
            for aluno_id, nome, turma_a, turma_b in duplicados
        )
        raise ValueError(
            "turmas.py tem ID(s) duplicado(s). Corrija antes de sincronizar:\n" + linhas
        )


def sincronizar(silencioso=False):
    """Garante que todo aluno de TURMAS existe no banco. Retorna (inseridos, atualizados)."""
    _verificar_duplicatas()
    banco.iniciar()

    inseridos = 0
    atualizados = 0
    with banco.conectar() as con:
        existentes = {r["id"]: r["nome"] for r in con.execute("SELECT id, nome FROM alunos")}
        for turma, alunos in TURMAS.items():
            for aluno_id, nome in alunos:
                if aluno_id not in existentes:
                    con.execute(
                        "INSERT INTO alunos (id, nome, estouros, liberado) VALUES (?, ?, 0, 0)",
                        (aluno_id, nome),
                    )
                    inseridos += 1
                elif existentes[aluno_id] != nome:
                    con.execute("UPDATE alunos SET nome = ? WHERE id = ?", (nome, aluno_id))
                    atualizados += 1

    if not silencioso:
        print(f"Sincronização concluída: {inseridos} aluno(s) novo(s), {atualizados} nome(s) atualizado(s).")
    return inseridos, atualizados


if __name__ == "__main__":
    sincronizar()
