import cv2
import os
import numpy as np

PASTA_DADOS = "dados"
ARQUIVO_SAIDA = "embeddings.npz"

# =========================
# YUNET
# =========================

detector = cv2.FaceDetectorYN.create(
    "modelos/yunet.onnx",
    "",
    (320, 320),
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

embeddings = []
nomes = []

# =========================
# PERCORRE AS PESSOAS
# =========================

for nome in sorted(os.listdir(PASTA_DADOS)):

    pasta_pessoa = os.path.join(
        PASTA_DADOS,
        nome
    )

    if not os.path.isdir(pasta_pessoa):
        continue

    print(f"\nProcessando: {nome}")

    quantidade = 0

    for arquivo in os.listdir(pasta_pessoa):

        caminho = os.path.join(
            pasta_pessoa,
            arquivo
        )

        imagem = cv2.imread(caminho)

        if imagem is None:
            continue

        altura, largura = imagem.shape[:2]

        detector.setInputSize(
            (largura, altura)
        )

        # Detecta rosto
        _, rostos = detector.detect(imagem)

        if rostos is None:
            print(f"  Rosto não encontrado: {arquivo}")
            continue

        # Usa o rosto com maior confiança
        rosto = max(
            rostos,
            key=lambda r: r[-1]
        )

        # Alinha
        rosto_alinhado = reconhecedor.alignCrop(
            imagem,
            rosto
        )

        # Gera embedding
        embedding = reconhecedor.feature(
            rosto_alinhado
        )

        # Transforma (1, 128) em (128,)
        embedding = embedding.flatten()

        embeddings.append(embedding)
        nomes.append(nome)

        quantidade += 1

    print(
        f"Embeddings criados para {nome}: "
        f"{quantidade}"
    )


# =========================
# SALVA
# =========================

if len(embeddings) == 0:
    print("\nNenhum embedding foi criado!")
    exit()

np.savez(
    ARQUIVO_SAIDA,
    embeddings=np.array(embeddings),
    nomes=np.array(nomes)
)

print("\n==========================")
print("Banco facial criado!")
print(f"Total: {len(embeddings)} embeddings")
print(f"Arquivo: {ARQUIVO_SAIDA}")