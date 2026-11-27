"""Estado compartilhado do processo.

Separado num módulo próprio (em vez de ficar dentro de api.py) para que os
routers possam importar `relogio` sem criar um import circular com api.py
(api.py é quem monta os routers).

Importante: isso só funciona com `banco.iniciar()` já executado, porque
`regras.ultimo_instante()` consulta a tabela `saidas`. Por isso `api.py`
chama `banco.iniciar()` antes de importar qualquer router.
"""
import time

import regras
from relogio import Relogio

relogio = Relogio(max(time.time(), regras.ultimo_instante()))
