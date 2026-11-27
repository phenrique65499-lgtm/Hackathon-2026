"""Regras de negócio do controle de saídas. Não depende da interface HTTP."""
import sqlite3
import time
from banco import conectar, registrar_auditoria

LIMITE_SEGUNDOS = 180
LIMITE_ESTOUROS = 3


def fmt(segundos):
    segundos = int(abs(segundos))
    return f"{segundos // 60:02d}:{segundos % 60:02d}"


def passar_digital(aluno_id, agora=None):
    agora = agora if agora is not None else time.time()
    with conectar() as con:
        aluno = con.execute("SELECT * FROM alunos WHERE id=?", (aluno_id,)).fetchone()
        if aluno is None:
            return "desconhecido", "Digital não reconhecida."
        aberta = con.execute("SELECT * FROM saidas WHERE aluno_id=? AND retorno IS NULL", (aluno_id,)).fetchone()
        if aberta:
            duracao = max(0, agora - aberta["saida"])
            estourou = duracao > LIMITE_SEGUNDOS
            con.execute("UPDATE saidas SET retorno=?, estourou=? WHERE id=?", (agora, int(estourou), aberta["id"]))
            if estourou:
                con.execute("UPDATE alunos SET estouros=estouros+1 WHERE id=?", (aluno_id,))
                total = aluno["estouros"] + 1
                msg = f"{aluno['nome']} voltou após {fmt(duracao)} (limite 03:00). Estouro {total}/{LIMITE_ESTOUROS}."
                if total >= LIMITE_ESTOUROS:
                    msg += " ALUNO PROBLEMA."
                classe = "bad"
            else:
                msg = f"{aluno['nome']} voltou em {fmt(duracao)}. Dentro do tempo."
                classe = "ok"
            registrar_auditoria("sensor", "retorno", aluno_id, msg, agora, classe=classe, con=con)
            return "retorno", msg

        if aluno["estouros"] >= LIMITE_ESTOUROS and not aluno["liberado"]:
            msg = f"SAÍDA NEGADA: {aluno['nome']} é Aluno problema. Somente professor pode liberar."
            registrar_auditoria("sensor", "saida_negada", aluno_id, msg, agora, classe="bad", con=con)
            return "negado", msg

        if aluno["liberado"]:
            con.execute("UPDATE alunos SET liberado=0 WHERE id=?", (aluno_id,))

        try:
            con.execute("INSERT INTO saidas(aluno_id, saida) VALUES(?,?)", (aluno_id, agora))
        except sqlite3.IntegrityError:
            # Duas digitais quase simultâneas para o mesmo aluno: o índice único
            # idx_saida_aberta_unica barrou a segunda. Melhor pedir pra repetir
            # do que devolver um 500 cru pro sensor.
            msg = f"{aluno['nome']}: já havia uma saída em aberto registrada no mesmo instante. Encoste o dedo de novo."
            registrar_auditoria("sensor", "saida_concorrente", aluno_id, msg, agora, classe="bad", con=con)
            return "negado", msg

        msg = f"{aluno['nome']} saiu. Cronômetro de {fmt(LIMITE_SEGUNDOS)} iniciado."
        registrar_auditoria("sensor", "saida", aluno_id, msg, agora, classe="", con=con)
        return "saida", msg


def estado_alunos():
    with conectar() as con:
        return con.execute("""SELECT a.id,a.nome,a.estouros,a.liberado,s.saida
          FROM alunos a LEFT JOIN saidas s ON s.aluno_id=a.id AND s.retorno IS NULL ORDER BY a.id""").fetchall()


def alunos_fora(agora=None):
    agora = agora if agora is not None else time.time()
    fora = []
    for aluno in estado_alunos():
        if aluno["saida"] is None:
            continue
        duracao = max(0, agora - aluno["saida"])
        fora.append((aluno["nome"], duracao, duracao > LIMITE_SEGUNDOS))
    return fora


def alunos_problema():
    with conectar() as con:
        return con.execute("SELECT * FROM alunos WHERE estouros>=? ORDER BY nome", (LIMITE_ESTOUROS,)).fetchall()


def liberar_aluno(aluno_id):
    with conectar() as con:
        cur = con.execute("UPDATE alunos SET liberado=1 WHERE id=?", (aluno_id,))
        if cur.rowcount:
            registrar_auditoria(
                "professor", "liberacao", aluno_id,
                f"Professor liberou uma saída (ID {aluno_id}).", classe="ok", con=con,
            )
        return cur.rowcount > 0


def zerar_contador(aluno_id):
    with conectar() as con:
        cur = con.execute("UPDATE alunos SET estouros=0, liberado=0 WHERE id=?", (aluno_id,))
        if cur.rowcount:
            registrar_auditoria(
                "secretaria", "contador_zerado", aluno_id,
                f"Secretaria zerou os atrasos do aluno (ID {aluno_id}).", classe="ok", con=con,
            )
        return cur.rowcount > 0


def marcar_aluno_problema(aluno_id):
    """Define o limite de atrasos para demonstrações."""
    with conectar() as con:
        cur = con.execute("UPDATE alunos SET estouros=?,liberado=0 WHERE id=?", (LIMITE_ESTOUROS, aluno_id))
        if cur.rowcount:
            registrar_auditoria(
                "professor", "simulacao_estouro", aluno_id,
                f"Professor simulou 3/3 atrasos para o aluno (ID {aluno_id}).", classe="ok", con=con,
            )
        return cur.rowcount > 0


def historico(aluno_id):
    with conectar() as con:
        return con.execute("SELECT * FROM saidas WHERE aluno_id=? ORDER BY saida DESC", (aluno_id,)).fetchall()


def relatorio_saidas():
    """Todas as saídas já registradas, da mais recente para a mais antiga (para exportação)."""
    with conectar() as con:
        return con.execute(
            """SELECT a.id AS aluno_id, a.nome, s.saida, s.retorno, s.estourou
               FROM saidas s JOIN alunos a ON a.id = s.aluno_id
               ORDER BY s.saida DESC"""
        ).fetchall()


def ultimo_instante():
    with conectar() as con:
        row = con.execute("SELECT MAX(saida) a, MAX(retorno) b FROM saidas").fetchone()
    return max(row["a"] or 0, row["b"] or 0)


def resetar_banco():
    """Só reseta os dados. Quem chama (api.py) decide quando limpar/registrar
    os eventos, pra não apagar o próprio aviso de "simulação reiniciada"."""
    with conectar() as con:
        con.execute("DELETE FROM saidas")
        con.execute("UPDATE alunos SET estouros=0,liberado=0")
