import cv2

detector = cv2.FaceDetectorYN.create(
    "modelos/yunet.onnx",
    "",
    (640, 480),
    0.9,
    0.3,
    5000
)

print("YuNet carregado!")

reconhecedor = cv2.FaceRecognizerSF.create(
    "modelos/sface.onnx",
    ""
)

print("SFace carregado!")