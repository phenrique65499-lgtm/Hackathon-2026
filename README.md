# Controle de Saída Escolar — versão aprimorada

## Estrutura do projeto

```
config.py          configuração central (lida uma vez, validada no import)
banco.py           conexão SQLite, schema, auditoria
regras.py          regras de negócio (cronômetro, estouros, bloqueio) — "serviço" de domínio
secretaria.py       visão enxuta pra secretaria (serviço)
autenticacao.py     PIN/senha + rate-limit, como dependências do FastAPI
schemas.py          formato de cada resposta da API (Pydantic)
erros.py            formato padronizado de erro para toda a API
estado.py           relógio simulado compartilhado entre routers
seed_alunos.py       sincroniza turmas.py -> tabela alunos
relogio.py          relógio da aplicação
turmas.py           lista fixa de turmas/alunos
routers/
  publico.py         páginas estáticas e /health (sem credencial)
  professor.py        /api/estado, /api/digital, /api/professor/*, /api/demo/*
  secretaria.py        /api/secretaria/*
api.py              monta o FastAPI e inclui os routers acima
servidor.py          CLI que sobe o uvicorn
tests/               testes de regras.py e da API de ponta a ponta
```

Os **caminhos HTTP não mudaram** (ex.: `/api/estado` continua `/api/estado`)
— só a organização interna do código. Se você tem uma interface estática
própria, ela continua funcionando sem alteração.

## O que mudou nesta revisão

- **Bug crítico corrigido:** `turmas.py` nunca era sincronizado com a tabela
  `alunos` — o banco ficava vazio e nenhuma digital era reconhecida. Agora
  `api.py` chama `seed_alunos.sincronizar()` no startup. Rode
  `python seed_alunos.py` manualmente depois de editar `turmas.py`.
- **Deadlock de conexão corrigido:** `registrar_auditoria()` abria uma
  segunda conexão SQLite enquanto a primeira ainda tinha uma transação em
  aberto (ex.: dentro de `passar_digital`), travando com "database is
  locked" até o `busy_timeout` estourar. Agora reusa a conexão já aberta via
  `con=con`.
- **Eventos agora persistem:** `/api/professor/eventos` lê da tabela
  `auditoria` (que já existia) em vez de um `deque` em memória — sobrevive a
  reinícios do servidor.
- **Rate-limit da secretaria:** a senha da secretaria agora tem a mesma
  proteção contra força bruta que já existia para o PIN do professor.
- **Corrida de concorrência tratada:** se duas digitais quase simultâneas
  tentarem abrir saída para o mesmo aluno, o índice único do banco impede a
  segunda — e agora isso vira uma mensagem amigável em vez de erro 500.
- **Testes adicionados:** `tests/test_regras.py` (lógica) e
  `tests/test_api.py` (API de ponta a ponta, incluindo a sincronização e o
  rate-limit). Rode com `pytest`.
- **API separada em routers + serviços + schemas**, em vez de tudo num
  `api.py` só: ver "Estrutura do projeto" acima.
- **Respostas validadas por Pydantic** (`schemas.py`) — qualquer campo
  faltando ou com tipo errado numa resposta é pego antes de sair da API, e
  `/docs` passa a documentar o formato de cada uma automaticamente.
- **Erros padronizados:** toda resposta de erro (401, 404, 422, 429...) sai
  no mesmo formato `{"erro": "...", "detalhe": "..."}`, em vez de um formato
  para `HTTPException` e outro, bem diferente, para erro de validação.
- **Autenticação como dependência do FastAPI** (`Depends(exigir_pin)` etc.)
  em vez de uma chamada manual repetida em cada rota — uma rota nova já
  nasce protegida se for registrada no router certo.
- **Dois endpoints que tinham ficado de fora** nesta reescrita voltaram:
  `GET /api/professor/historico/{aluno_id}` e `GET /api/professor/exportar`
  (baixa CSV com todas as saídas).
- **`.gitignore` e `.env.example`** adicionados — o zip enviado tinha
  `__pycache__` versionado junto com o código.

## Instalação
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

## Rodar demonstração
```bash
python servidor.py --demo
```
Ao iniciar, `api.py` já sincroniza `turmas.py` com o banco automaticamente —
não precisa rodar `seed_alunos.py` à parte, a não ser que queira fazer isso
sem subir o servidor.
Credenciais de demonstração: PIN do professor `1234` e senha da secretaria `1234`. **Nunca use credenciais de demonstração em produção.**

## Produção (configuração obrigatória)
Defina no ambiente credenciais diferentes:
- `PIN_PROFESSOR`: pelo menos 8 caracteres
- `SENHA_SECRETARIA`: pelo menos 12 caracteres
- `ESCOLA_DB`: caminho para o banco de dados persistente (opcional)
- `HOST=127.0.0.1` e `PORT=8000` por padrão

O aplicativo recusa iniciar em produção se as credenciais estiverem ausentes,
forem curtas ou forem iguais. Use valores aleatórios e não reutilize senhas.

Windows PowerShell:
```powershell
$env:PIN_PROFESSOR='defina-um-pin-forte-com-8-caracteres-ou-mais'
$env:SENHA_SECRETARIA='defina-uma-senha-forte-com-12-caracteres-ou-mais'
python servidor.py
```

Linux/macOS:
```bash
export PIN_PROFESSOR='defina-um-pin-forte-com-8-caracteres-ou-mais'
export SENHA_SECRETARIA='defina-uma-senha-forte-com-12-caracteres-ou-mais'
python servidor.py
```

Documentação interativa da API: `/docs`. Health check: `/health`.

## Observações para produção real
- Os headers `X-PIN` e `X-SENHA` foram mantidos para compatibilidade com a interface existente; para produção com múltiplos usuários, substitua por login com sessão/token, hash de credenciais, HTTPS e permissões por papel.
- Rate limit da autenticação é em memória e funciona como proteção básica em uma instância única; em múltiplos workers, usar Redis ou proxy com rate limit.
- O projeto é um starter: não coloque dados reais de alunos em demonstração, faça backup periódico, controle acesso à rede e revise privacidade/LGPD.
- Copie sua pasta `static/` original para este projeto para reutilizar a interface. Este pacote contém apenas backend e configuração.
