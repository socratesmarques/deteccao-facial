from __future__ import annotations

import threading
import time
import serial


class ControleAcesso:
    """Cliente serial thread-safe para o protocolo do ESP32."""

    def __init__(self, porta="/dev/ttyACM0", baudrate=115200):
        self.porta, self.baudrate = porta, int(baudrate)
        self.esp32 = None
        self._lock = threading.Lock()

    def configurar(self, porta: str, baudrate: int) -> None:
        if porta != self.porta or int(baudrate) != self.baudrate:
            self.desconectar()
            self.porta, self.baudrate = porta, int(baudrate)

    def conectar(self) -> bool:
        with self._lock:
            return self._conectar_sem_lock()

    def _conectar_sem_lock(self) -> bool:
        if self.esp32 is not None and self.esp32.is_open:
            return True
        try:
            self.esp32 = serial.Serial(
                port=self.porta, baudrate=self.baudrate, timeout=0.25,
                write_timeout=1, dsrdtr=False, rtscts=False,
            )
            self.esp32.dtr = False
            self.esp32.rts = False
            time.sleep(1.8)
            self.esp32.reset_input_buffer()
            self.esp32.write(b"PING\n")
            self.esp32.flush()
            limite = time.monotonic() + 2.0
            while time.monotonic() < limite:
                resposta = self.esp32.readline().decode("utf-8", errors="ignore").strip()
                if resposta == "PONG":
                    return True
            self._desconectar_sem_lock()
        except (OSError, serial.SerialException) as erro:
            print("Erro ao conectar ao ESP32:", erro)
            self._desconectar_sem_lock()
        return False

    def abrir(self) -> bool:
        with self._lock:
            if not self._conectar_sem_lock():
                return False
            try:
                self.esp32.write(b"ABRIR\n")
                self.esp32.flush()
                return True
            except (OSError, serial.SerialException) as erro:
                print("Erro ao enviar comando ao ESP32:", erro)
                self._desconectar_sem_lock()
                return False

    def desconectar(self) -> None:
        with self._lock:
            self._desconectar_sem_lock()

    def _desconectar_sem_lock(self) -> None:
        try:
            if self.esp32 is not None and self.esp32.is_open:
                self.esp32.close()
        except (OSError, serial.SerialException):
            pass
        self.esp32 = None
