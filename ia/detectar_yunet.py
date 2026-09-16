import cv2

# =========================
# MODELO YUNET
# =========================

detector = cv2.FaceDetectorYN.create(
    "modelos/yunet.onnx",
    "",
    (640, 480),
    0.8,   # confiança mínima
    0.3,   # NMS
    5000
)

# =========================
# WEBCAM EXTERNA
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
        print("Erro ao capturar imagem.")
        break

    # Descobre o tamanho real da imagem
    altura, largura = frame.shape[:2]

    # Informa ao YuNet o tamanho atual
    detector.setInputSize(
        (largura, altura)
    )

    # Detecta os rostos
    _, rostos = detector.detect(frame)

    if rostos is not None:

        for rosto in rostos:

            # Retângulo do rosto
            x = int(rosto[0])
            y = int(rosto[1])
            largura_rosto = int(rosto[2])
            altura_rosto = int(rosto[3])

            cv2.rectangle(
                frame,
                (x, y),
                (x + largura_rosto, y + altura_rosto),
                (0, 255, 0),
                2
            )

            # Confiança da detecção
            confianca = rosto[-1]

            cv2.putText(
                frame,
                f"Rosto {confianca:.2f}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

    cv2.imshow(
        "Deteccao Facial - YuNet",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()