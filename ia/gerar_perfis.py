import cv2
import os
import numpy as np

PASTA_DADOS = "dados"
ARQUIVO_SAIDA = "perfis.npz"

# =========================
# SFACE
# =========================

reconhecedor = cv2.FaceRecognizerSF.create(
    "modelos/sface.onnx",
    ""
)

perfis = []
nomes = []


# =========================
# PERCORRE AS PESSOAS
# =========================

for nome in sorted(os.listdir(PASTA_DADOS)):

    pasta = os.path.join(
        PASTA_DADOS,
        nome
    )

    if not os.path.isdir(pasta):
        continue

    print(f"\nProcessando {nome}...")

    embeddings_pessoa = []

    for arquivo in os.listdir(pasta):

        # Ignora arquivos que não sejam imagens
        if not arquivo.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):
            continue

        caminho = os.path.join(
            pasta,
            arquivo
        )

        imagem = cv2.imread(caminho)

        if imagem is None:
            print(f"Erro ao abrir: {arquivo}")
            continue

        # =========================
        # EMBEDDING
        # =========================

        embedding = reconhecedor.feature(
            imagem
        ).flatten()

        # Normaliza cada embedding
        norma = np.linalg.norm(embedding)

        if norma == 0:
            continue

        embedding = embedding / norma

        embeddings_pessoa.append(
            embedding
        )


    # =========================
    # CRIA PERFIL
    # =========================

    if len(embeddings_pessoa) == 0:

        print(
            f"Nenhuma imagem válida para {nome}"
        )

        continue

    embedding_medio = np.mean(
        embeddings_pessoa,
        axis=0
    )

    # Normaliza novamente depois da média
    norma = np.linalg.norm(
        embedding_medio
    )

    if norma > 0:
        embedding_medio /= norma

    perfis.append(
        embedding_medio
    )

    nomes.append(nome)

    print(
        f"{len(embeddings_pessoa)} imagens utilizadas."
    )


# =========================
# VERIFICAÇÃO
# =========================

if len(perfis) == 0:
    print("\nNenhum perfil criado!")
    exit()


# =========================
# SALVA BANCO
# =========================

np.savez(
    ARQUIVO_SAIDA,
    perfis=np.array(
        perfis,
        dtype=np.float32
    ),
    nomes=np.array(nomes)
)


# =========================
# RESULTADO
# =========================

print("\n========================")
print("Perfis criados!")

for nome in nomes:
    print(f"- {nome}")

print(f"\nTotal de pessoas: {len(nomes)}")
print(f"Arquivo: {ARQUIVO_SAIDA}")