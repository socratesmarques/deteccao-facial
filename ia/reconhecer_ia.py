import cv2
import numpy as np

# =========================
# CONFIGURAÇÕES
# =========================

CAMERA = "/dev/video2"

# Vamos começar com esse valor e ajustar depois
LIMIAR = 0.45


# =========================
# CARREGA BANCO FACIAL
# =========================

dados = np.load("perfis.npz")

embeddings_cadastrados = dados["perfis"]
nomes_cadastrados = dados["nomes"]

print(f"Embeddings carregados: {len(embeddings_cadastrados)}")

print("Pessoas cadastradas:")

for nome in sorted(set(nomes_cadastrados)):
    print(f"- {nome}")


# =========================
# YUNET
# =========================

detector = cv2.FaceDetectorYN.create(
    "modelos/yunet.onnx",
    "",
    (640, 480),
    0.8,
    0.3,
    5000
)


# =========================
# SFACE
# =========================

reconhecedor = cv2.FaceRecognizerSF.create(
    "modelos/sface.onnx",
    ""
)


# =========================
# CÂMERA
# =========================

camera = cv2.VideoCapture(
    CAMERA,
    cv2.CAP_V4L2
)

if not camera.isOpened():
    print("Erro ao abrir a câmera.")
    exit()


while True:

    sucesso, frame = camera.read()

    if not sucesso:
        print("Erro ao capturar imagem.")
        break

    altura, largura = frame.shape[:2]

    detector.setInputSize(
        (largura, altura)
    )

    # Detecta rostos
    _, rostos = detector.detect(frame)

    if rostos is not None:

        for rosto in rostos:

            x = int(rosto[0])
            y = int(rosto[1])
            w = int(rosto[2])
            h = int(rosto[3])

            # =========================
            # ALINHA O ROSTO
            # =========================

            rosto_alinhado = reconhecedor.alignCrop(
                frame,
                rosto
            )

            # =========================
            # GERA EMBEDDING
            # =========================

            embedding_atual = reconhecedor.feature(
                rosto_alinhado
            )

            embedding_atual = embedding_atual.flatten()


            # =========================
            # COMPARAÇÃO
            # =========================

            melhor_nome = "Desconhecido"
            melhor_score = -1

            for embedding_salvo, nome in zip(
                embeddings_cadastrados,
                nomes_cadastrados
            ):

                score = reconhecedor.match(
                    embedding_atual,
                    embedding_salvo,
                    cv2.FaceRecognizerSF_FR_COSINE
                )

                if score > melhor_score:
                    melhor_score = score
                    melhor_nome = nome


            # =========================
            # DECISÃO
            # =========================

            if melhor_score < LIMIAR:
                melhor_nome = "Desconhecido"


            # =========================
            # INTERFACE
            # =========================

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

            texto = (
                f"{melhor_nome} "
                f"{melhor_score:.2f}"
            )

            cv2.putText(
                frame,
                texto,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )


    cv2.imshow(
        "Reconhecimento Facial - IA",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


camera.release()
cv2.destroyAllWindows()