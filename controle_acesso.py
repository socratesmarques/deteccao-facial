import serial
import time


class ControleAcesso:
    def __init__(
        self,
        porta="/dev/ttyACM0",
        baudrate=115200
    ):
        self.porta = porta
        self.baudrate = baudrate
        self.esp32 = None

    def conectar(self):
        try:
            if (
                self.esp32 is not None
                and self.esp32.is_open
            ):
                return True

            self.esp32 = serial.Serial()

            self.esp32.port = self.porta
            self.esp32.baudrate = self.baudrate
            self.esp32.timeout = 1

            # Importante para o nosso ESP32
            self.esp32.dtr = False
            self.esp32.rts = False

            self.esp32.open()

            time.sleep(2)

            self.esp32.reset_input_buffer()

            # Testa a comunicação
            self.esp32.write(b"PING\n")
            self.esp32.flush()

            fim = time.time() + 2

            while time.time() < fim:
                resposta = (
                    self.esp32
                    .readline()
                    .decode("utf-8", errors="ignore")
                    .strip()
                )

                if resposta == "PONG":
                    print("ESP32 conectado.")
                    return True

            print("ESP32 não respondeu ao PING.")
            self.desconectar()
            return False

        except Exception as erro:
            print(
                "Erro ao conectar ao ESP32:",
                erro
            )
            self.desconectar()
            return False

    def abrir(self):
        if (
            self.esp32 is None
            or not self.esp32.is_open
        ):
            if not self.conectar():
                return False

        try:
            self.esp32.write(b"ABRIR\n")
            self.esp32.flush()

            print("Comando ABRIR enviado.")
            return True

        except Exception as erro:
            print(
                "Erro ao enviar comando:",
                erro
            )
            self.desconectar()
            return False

    def desconectar(self):
        try:
            if (
                self.esp32 is not None
                and self.esp32.is_open
            ):
                self.esp32.close()
        except Exception:
            pass

        self.esp32 = None