import cv2
import json

# =========================
# CARREGA OS NOMES
# =========================

with open("pessoas.json", "r") as arquivo:
    pessoas = json.load(arquivo)

# JSON transforma as chaves em strings.
# Vamos converter novamente para números.
pessoas = {
    int(id_pessoa): nome
    for id_pessoa, nome in pessoas.items()
}

print("Pessoas cadastradas:")
for id_pessoa, nome in pessoas.items():
    print(f"{id_pessoa} -> {nome}")


# =========================
# DETECTOR DE ROSTOS
# =========================

detector = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)


# =========================
# MODELO
# =========================

modelo = cv2.face.LBPHFaceRecognizer_create()
modelo.read("modelo.yml")


# =========================
# CÂMERA
# =========================

camera = cv2.VideoCapture("/dev/video2", cv2.CAP_V4L2)

while True:

    sucesso, frame = camera.read()

    if not sucesso:
        print("Erro ao acessar a câmera.")
        break

    cinza = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    rostos = detector.detectMultiScale(
        cinza,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(100, 100)
    )

    # Pode reconhecer vários rostos
    for x, y, largura, altura in rostos:

        rosto = cinza[
            y:y + altura,
            x:x + largura
        ]

        rosto = cv2.resize(
            rosto,
            (200, 200)
        )

        # Reconhecimento
        id_pessoa, distancia = modelo.predict(rosto)

        if distancia < 70:
            nome = pessoas.get(
                id_pessoa,
                "Desconhecido"
            )
        else:
            nome = "Desconhecido"

        # Desenha o retângulo
        cv2.rectangle(
            frame,
            (x, y),
            (x + largura, y + altura),
            (0, 255, 0),
            2
        )

        # Mostra resultado
        texto = f"{nome} ({distancia:.1f})"

        cv2.putText(
            frame,
            texto,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    cv2.imshow(
        "Reconhecimento Facial",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


camera.release()
cv2.destroyAllWindows()