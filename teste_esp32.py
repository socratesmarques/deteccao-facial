import serial
import time

PORTA = "/dev/ttyACM0"
BAUDRATE = 115200

print("Abrindo porta...")

esp32 = serial.Serial()
esp32.port = PORTA
esp32.baudrate = BAUDRATE
esp32.timeout = 1

# Evita manter o ESP32 em reset
esp32.dtr = False
esp32.rts = False

esp32.open()

print("Porta aberta.")
print("Aguardando ESP32...")

time.sleep(3)

# Limpa somente o que chegou durante a inicialização
esp32.reset_input_buffer()

print("Enviando PING...")

for tentativa in range(1, 6):

    print(f"Tentativa {tentativa}")

    esp32.write(b"PING\n")
    esp32.flush()

    fim = time.time() + 2

    while time.time() < fim:

        resposta = esp32.readline().decode(
            "utf-8",
            errors="ignore"
        ).strip()

        if resposta:
            print("ESP32:", repr(resposta))

            if resposta == "PONG":
                print("COMUNICAÇÃO OK!")

                print("Enviando ABRIR...")
                esp32.write(b"ABRIR\n")
                esp32.flush()

                # Aguarda todas as respostas
                fim_abertura = time.time() + 5

                while time.time() < fim_abertura:
                    resposta = esp32.readline().decode(
                        "utf-8",
                        errors="ignore"
                    ).strip()

                    if resposta:
                        print("ESP32:", resposta)

                esp32.close()
                exit()

    time.sleep(1)

print("ESP32 não respondeu.")

esp32.close()