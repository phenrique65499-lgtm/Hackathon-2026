"""Pacote de routers HTTP: cada módulo agrupa rotas por perfil de uso
(público, professor, secretaria). A lógica de negócio não mora aqui — fica
em regras.py/secretaria.py — os routers só traduzem HTTP <-> funções Python.
"""
