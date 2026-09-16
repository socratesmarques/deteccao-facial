import cv2

# =========================
# YUNET - DETECÇÃO
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
# SFACE - RECONHECIMENTO
# =========================

reconhecedor = cv2.FaceRecognizerSF.create(
    "modelos/sface.onnx",
    ""
)

# =========================
# WEBCAM
# =========================

camera = cv2.VideoCapture(
    "/dev/video2",
    cv2.CAP_V4L2
)

if not camera.isOpened():
    print("Erro ao abrir a webcam.")
    exit()

while True:

    sucesso, frame = camera.read()

    if not sucesso:
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
            largura_rosto = int(rosto[2])
            altura_rosto = int(rosto[3])

            # =========================
            # ALINHAMENTO
            # =========================

            rosto_alinhado = reconhecedor.alignCrop(
                frame,
                rosto
            )

            # =========================
            # EMBEDDING
            # =========================

            embedding = reconhecedor.feature(
                rosto_alinhado
            )

            print("Embedding:")
            print(embedding)
            print("Formato:", embedding.shape)
            print("----------------------")

            cv2.rectangle(
                frame,
                (x, y),
                (
                    x + largura_rosto,
                    y + altura_rosto
                ),
                (0, 255, 0),
                2
            )

    cv2.imshow(
        "SFace - Embedding",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()