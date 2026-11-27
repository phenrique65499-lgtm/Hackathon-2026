"""Autenticação por PIN (professor) e senha (secretaria), com rate-limit.

Cada verificação é uma dependência do FastAPI (`Depends(...)`), então uma
rota só precisa declarar `dependencies=[Depends(exigir_pin)]` em vez de
chamar a verificação manualmente em cada handler — menos chance de alguém
esquecer de proteger uma rota nova.

O rate-limit é em memória: funciona como proteção básica numa instância
única. Em produção com múltiplos workers/processos, use Redis ou o rate
limit do proxy/gateway na frente da API.
"""
import secrets
import time
from collections import deque

from fastapi import Header, HTTPException

import config

JANELA_SEGUNDOS = 60
MAX_TENTATIVAS = 10

_tentativas_pin: deque = deque()
_tentativas_secretaria: deque = deque()


def _limitar(tentativas: deque, limite: int = MAX_TENTATIVAS, janela: int = JANELA_SEGUNDOS) -> None:
    agora = time.time()
    while tentativas and agora - tentativas[0] > janela:
        tentativas.popleft()
    if len(tentativas) >= limite:
        raise HTTPException(429, "Muitas tentativas. Aguarde um minuto.")


def exigir_pin(x_pin: str = Header(default="")) -> None:
    """Dependência do FastAPI: valida o PIN do professor (cabeçalho X-Pin)."""
    _limitar(_tentativas_pin)
    if not x_pin or not secrets.compare_digest(x_pin, config.PIN_PROFESSOR):
        _tentativas_pin.append(time.time())
        raise HTTPException(401, "Credencial do professor inválida.")
    _tentativas_pin.clear()


def exigir_senha_secretaria(x_senha: str = Header(default="")) -> None:
    """Dependência do FastAPI: valida a senha da secretaria (cabeçalho X-Senha)."""
    _limitar(_tentativas_secretaria)
    if not x_senha or not secrets.compare_digest(x_senha, config.SENHA_SECRETARIA):
        _tentativas_secretaria.append(time.time())
        raise HTTPException(401, "Credencial da secretaria inválida.")
    _tentativas_secretaria.clear()


def exigir_demo() -> None:
    """Dependência do FastAPI: bloqueia rotas disponíveis só no modo simulação."""
    if not config.DEMO:
        raise HTTPException(404, "Disponível apenas no modo simulação.")
