from __future__ import annotations

import threading
import time


class ControleAcesso:
    """Controla diretamente um relé ligado ao GPIO do Orange Pi."""

    def __init__(
        self,
        gpio_chip: str = "/dev/gpiochip0",
        gpio_linha: int = -1,
        ativo_alto: bool = False,
        tempo_acionamento: float = 1.0,
    ):
        self.gpio_chip = gpio_chip
        self.gpio_linha = int(gpio_linha)
        self.ativo_alto = bool(ativo_alto)
        self.tempo_acionamento = float(tempo_acionamento)
        self.gpio = None
        self.ultimo_erro = ""
        self._lock = threading.Lock()

    def configurar(
        self,
        gpio_chip: str,
        gpio_linha: int,
        ativo_alto: bool,
        tempo_acionamento: float,
    ) -> None:
        nova_config = (
            str(gpio_chip), int(gpio_linha), bool(ativo_alto), float(tempo_acionamento)
        )
        atual = (
            self.gpio_chip, self.gpio_linha, self.ativo_alto, self.tempo_acionamento
        )
        if nova_config != atual:
            self.desconectar()
            (
                self.gpio_chip,
                self.gpio_linha,
                self.ativo_alto,
                self.tempo_acionamento,
            ) = nova_config

    def _nivel_ativo(self) -> bool:
        return self.ativo_alto

    def _nivel_inativo(self) -> bool:
        return not self.ativo_alto

    def conectar(self) -> bool:
        with self._lock:
            return self._conectar_sem_lock()

    def _conectar_sem_lock(self) -> bool:
        if self.gpio is not None:
            return True
        if self.gpio_linha < 0:
            self.ultimo_erro = "Linha GPIO do relé não configurada."
            return False
        try:
            from periphery import GPIO

            self.gpio = GPIO(self.gpio_chip, self.gpio_linha, "out")
            self.gpio.write(self._nivel_inativo())
            self.ultimo_erro = ""
            return True
        except (ImportError, OSError, RuntimeError) as erro:
            self.ultimo_erro = f"Não foi possível abrir o GPIO do Orange Pi: {erro}"
            self._desconectar_sem_lock()
            return False

    def abrir(self) -> bool:
        """Aciona o relé e confirma localmente que o pulso GPIO foi concluído."""
        with self._lock:
            if not self._conectar_sem_lock():
                return False
            try:
                self.gpio.write(self._nivel_ativo())
                time.sleep(self.tempo_acionamento)
                self.gpio.write(self._nivel_inativo())
                self.ultimo_erro = ""
                return True
            except (OSError, RuntimeError) as erro:
                self.ultimo_erro = f"Falha ao acionar o relé no Orange Pi: {erro}"
                try:
                    if self.gpio is not None:
                        self.gpio.write(self._nivel_inativo())
                except (OSError, RuntimeError):
                    pass
                self._desconectar_sem_lock()
                return False

    def desconectar(self) -> None:
        with self._lock:
            self._desconectar_sem_lock()

    def _desconectar_sem_lock(self) -> None:
        if self.gpio is None:
            return
        try:
            self.gpio.write(self._nivel_inativo())
        except (OSError, RuntimeError):
            pass
        try:
            self.gpio.close()
        except (OSError, RuntimeError):
            pass
        self.gpio = None
