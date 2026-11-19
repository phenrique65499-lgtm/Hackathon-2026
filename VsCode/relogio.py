import time


class Relogio:
    """Relógio da aplicação, sempre em tempo real."""

    def __init__(self, inicio=None):
        self._sim = time.time() if inicio is None else inicio
        self._real = time.time()

    def agora(self):
        return self._sim + (time.time() - self._real)

    def reiniciar(self):
        self._sim = time.time()
        self._real = time.time()