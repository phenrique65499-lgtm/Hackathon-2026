"""Schemas Pydantic: validam e documentam o formato de cada resposta da API.

Sem isso, um erro de digitação num nome de campo em algum endpoint só seria
percebido quando o frontend quebrasse. Com `response_model`, o FastAPI valida
a resposta antes de devolver e também gera a documentação em /docs sozinho.
"""
from typing import Optional

from pydantic import BaseModel


class AlunoEstado(BaseModel):
    id: int
    nome: str
    estouros: int
    liberado: bool
    saida: Optional[float] = None
    turma: Optional[str] = None


class EstadoResposta(BaseModel):
    agora: float
    limite: int
    max: int
    demo: bool
    turmas: list[str]
    alunos: list[AlunoEstado]


class OkResposta(BaseModel):
    ok: bool = True


class DigitalResposta(BaseModel):
    status: str
    mensagem: str


class EventoItem(BaseModel):
    hora: str
    texto: str
    cls: str = ""


class EventosResposta(BaseModel):
    eventos: list[EventoItem]


class HistoricoItem(BaseModel):
    saida: float
    retorno: Optional[float] = None
    duracao: Optional[float] = None
    estourou: bool


class HistoricoResposta(BaseModel):
    historico: list[HistoricoItem]


class AlunoProblema(BaseModel):
    id: int
    nome: str
    turma: str


class ProblemaResposta(BaseModel):
    alunos: list[AlunoProblema]


class SaudeResposta(BaseModel):
    status: str
    modo: str


class ErroResposta(BaseModel):
    """Formato padronizado de todo erro da API — ver erros.py."""
    erro: str
    detalhe: str | list
