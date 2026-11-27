"""Rotas públicas: páginas estáticas e health check (sem credencial)."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

import config
import schemas

router = APIRouter(tags=["público"])


def _arquivo_estatico(nome: str) -> FileResponse:
    caminho = config.STATIC_DIR / nome
    if not caminho.is_file():
        raise HTTPException(404, f"Página {nome} não encontrada.")
    return FileResponse(caminho)


@router.get("/health", response_model=schemas.SaudeResposta)
def saude():
    return schemas.SaudeResposta(status="ok", modo="simulacao" if config.DEMO else "producao")


@router.get("/")
def pagina_principal():
    for caminho in (config.STATIC_DIR / "index.html", config.BASE_DIR / "index.html"):
        if caminho.is_file():
            return FileResponse(caminho)
    return HTMLResponse(
        "<h2>Interface não instalada</h2><p>Adicione static/index.html.</p>",
        status_code=404,
    )


@router.get("/registros")
def pagina_registros():
    return _arquivo_estatico("registros.html")


@router.get("/secretaria")
def pagina_secretaria():
    return _arquivo_estatico("secretaria.html")
