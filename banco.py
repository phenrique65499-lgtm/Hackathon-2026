"""Camada de persistência SQLite com configuração segura e índices."""
import sqlite3
import time
from pathlib import Path
import config

DB_PATH = Path(config.DB_PATH)


def conectar():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA busy_timeout = 15000")
    return con


def iniciar():
    with conectar() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS alunos (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL CHECK(length(trim(nome)) > 0),
            estouros INTEGER NOT NULL DEFAULT 0 CHECK(estouros >= 0),
            liberado INTEGER NOT NULL DEFAULT 0 CHECK(liberado IN (0,1))
        );
        CREATE TABLE IF NOT EXISTS saidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            aluno_id INTEGER NOT NULL REFERENCES alunos(id),
            saida REAL NOT NULL,
            retorno REAL,
            estourou INTEGER NOT NULL DEFAULT 0 CHECK(estourou IN (0,1)),
            CHECK(retorno IS NULL OR retorno >= saida)
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_saida_aberta_unica
          ON saidas(aluno_id) WHERE retorno IS NULL;
        CREATE INDEX IF NOT EXISTS idx_saidas_aluno_data ON saidas(aluno_id, saida DESC);
        CREATE INDEX IF NOT EXISTS idx_alunos_estouros ON alunos(estouros);
        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instante REAL NOT NULL,
            ator TEXT NOT NULL,
            acao TEXT NOT NULL,
            aluno_id INTEGER,
            detalhe TEXT NOT NULL DEFAULT '',
            classe TEXT NOT NULL DEFAULT ''   -- "", "ok" ou "bad" (estilo exibido em /registros)
        );
        CREATE INDEX IF NOT EXISTS idx_auditoria_instante ON auditoria(instante DESC);
        """)
        # Migração leve: bancos criados antes da coluna `classe` existir.
        colunas = {row["name"] for row in con.execute("PRAGMA table_info(auditoria)")}
        if "classe" not in colunas:
            con.execute("ALTER TABLE auditoria ADD COLUMN classe TEXT NOT NULL DEFAULT ''")


def registrar_auditoria(ator, acao, aluno_id=None, detalhe="", instante=None, classe="", con=None):
    """Grava um evento de auditoria.

    Se `con` for passada (uma conexão já aberta por quem está chamando, no
    meio de uma transação), reusa essa mesma conexão em vez de abrir outra.
    Abrir uma segunda conexão de escrita enquanto a primeira ainda tem uma
    transação em aberto trava o SQLite ("database is locked") até o
    busy_timeout estourar — é o mesmo thread esperando a si mesmo. Quem já
    está dentro de um `with conectar() as con:` deve sempre passar `con=con`.
    """
    instante = instante if instante is not None else time.time()
    sql = "INSERT INTO auditoria(instante, ator, acao, aluno_id, detalhe, classe) VALUES(?,?,?,?,?,?)"
    parametros = (instante, ator, acao, aluno_id, detalhe, classe)
    if con is not None:
        con.execute(sql, parametros)
    else:
        with conectar() as con_propria:
            con_propria.execute(sql, parametros)


def listar_eventos(limite=100):
    """Eventos mais recentes primeiro, já formatados para a tela /registros.

    Lê da mesma tabela `auditoria` usada para a trilha de auditoria — um só
    lugar de verdade, persistente, em vez de duplicar em um deque em memória.
    """
    with conectar() as con:
        linhas = con.execute(
            "SELECT instante, detalhe, classe FROM auditoria ORDER BY instante DESC, id DESC LIMIT ?",
            (limite,),
        ).fetchall()
    return [
        {
            "hora": time.strftime("%H:%M:%S", time.localtime(l["instante"])),
            "texto": l["detalhe"],
            "cls": l["classe"],
        }
        for l in linhas
    ]


def limpar_eventos():
    with conectar() as con:
        con.execute("DELETE FROM auditoria")
