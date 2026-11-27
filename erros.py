"""Padroniza o formato de erro de toda a API: `{"erro": "...", "detalhe": "..."}`.

Sem isso, um 401/404/429 levantado com HTTPException vem em um formato
(`{"detail": "..."}`) e um 422 de validação do Pydantic vem em outro bem
diferente (lista de objetos). Isso obriga qualquer cliente (a interface web,
um script, outro serviço) a tratar cada código de erro de um jeito. Com um
único formato, o cliente trata erro genérico uma vez só.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_NOMES_POR_CODIGO = {
    401: "nao_autorizado",
    403: "proibido",
    404: "nao_encontrado",
    422: "dados_invalidos",
    429: "limite_de_tentativas",
}


def registrar_tratadores_de_erro(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def tratar_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "erro": _NOMES_POR_CODIGO.get(exc.status_code, "erro"),
                "detalhe": exc.detail,
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def tratar_erro_de_validacao(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "erro": "dados_invalidos",
                "detalhe": exc.errors(),
            },
        )
