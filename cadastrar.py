import cv2
import os
import time
import numpy as np


# =========================
# CONFIGURAÇÕES
# =========================

CAMERA = "/dev/video2"

PASTA_DADOS = "dados"
ARQUIVO_PERFIS = "perfis.npz"

QUANTIDADE_RECOMENDADA = 20

# Tempo entre cada captura automática
INTERVALO_CAPTURA = 0.7


# =========================
# NOME DA PESSOA
# =========================

nome = input("Nome da pessoa: ").strip().lower()

if not nome:
    print("Nome inválido.")
    exit()

pasta = os.path.join(
    PASTA_DADOS,
    nome
)

os.makedirs(
    pasta,
    exist_ok=True
)


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


# =========================
# CONTADOR
# =========================

contador = len([
    arquivo
    for arquivo in os.listdir(pasta)
    if arquivo.lower().endswith(
        (".jpg", ".jpeg", ".png")
    )
])

ultima_captura = 0


print()
print("==========================")
print("CADASTRO FACIAL")
print("==========================")
print(f"Pessoa: {nome}")
print()
print("Mova levemente o rosto.")
print("A captura será automática.")
print("Q = finalizar")
print()


# =========================
# CAPTURA
# =========================

while True:

    sucesso, frame = camera.read()

    if not sucesso:
        print("Erro ao capturar imagem.")
        break


    # =========================
    # TAMANHO DA IMAGEM
    # =========================

    altura, largura = frame.shape[:2]

    detector.setInputSize(
        (largura, altura)
    )


    # =========================
    # DETECÇÃO
    # =========================

    _, rostos = detector.detect(frame)

    rosto_selecionado = None


    # =========================
    # UM ÚNICO ROSTO
    # =========================

    if rostos is not None:

        if len(rostos) == 1:

            rosto_selecionado = rostos[0]

            x = int(
                rosto_selecionado[0]
            )

            y = int(
                rosto_selecionado[1]
            )

            w = int(
                rosto_selecionado[2]
            )

            h = int(
                rosto_selecionado[3]
            )

            confianca = rosto_selecionado[-1]


            # =========================
            # RETÂNGULO
            # =========================

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )


            # =========================
            # CONFIANÇA
            # =========================

            cv2.putText(
                frame,
                f"Rosto: {confianca:.2f}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )


        elif len(rostos) > 1:

            cv2.putText(
                frame,
                "Deixe apenas uma pessoa na camera",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )


    # =========================
    # CAPTURA AUTOMÁTICA
    # =========================

    agora = time.time()

    if (
        rosto_selecionado is not None
        and contador < QUANTIDADE_RECOMENDADA
        and agora - ultima_captura >= INTERVALO_CAPTURA
    ):

        confianca = rosto_selecionado[-1]

        # Só salva detecções boas
        if confianca >= 0.90:

            rosto_alinhado = reconhecedor.alignCrop(
                frame,
                rosto_selecionado
            )

            contador += 1

            caminho = os.path.join(
                pasta,
                f"rosto_{contador}.jpg"
            )

            cv2.imwrite(
                caminho,
                rosto_alinhado
            )

            ultima_captura = agora

            print(
                f"Foto {contador}/"
                f"{QUANTIDADE_RECOMENDADA} salva."
            )


    # =========================
    # PROGRESSO
    # =========================

    cv2.putText(
        frame,
        f"Fotos: {contador}/{QUANTIDADE_RECOMENDADA}",
        (20, frame.shape[0] - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )


    # =========================
    # CADASTRO COMPLETO
    # =========================

    if contador >= QUANTIDADE_RECOMENDADA:

        cv2.putText(
            frame,
            "Cadastro concluido! Pressione Q",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )


    # =========================
    # MOSTRA A CÂMERA
    # =========================

    cv2.imshow(
        "Cadastro Facial - IA",
        frame
    )


    tecla = cv2.waitKey(1) & 0xFF

    if tecla == ord("q"):
        break


camera.release()
cv2.destroyAllWindows()


# =========================
# VERIFICA FOTOS
# =========================

if contador == 0:

    print(
        "\nNenhuma foto foi capturada."
    )

    exit()


# =========================
# GERA EMBEDDINGS
# =========================

print()
print("Gerando perfil facial...")

embeddings = []


for arquivo in os.listdir(pasta):

    if not arquivo.lower().endswith(
        (".jpg", ".jpeg", ".png")
    ):
        continue


    caminho = os.path.join(
        pasta,
        arquivo
    )


    imagem = cv2.imread(
        caminho
    )


    if imagem is None:
        continue


    # =========================
    # SFACE
    # =========================

    embedding = reconhecedor.feature(
        imagem
    ).flatten()


    # =========================
    # NORMALIZAÇÃO
    # =========================

    norma = np.linalg.norm(
        embedding
    )

    if norma == 0:
        continue

    embedding = (
        embedding / norma
    )

    embeddings.append(
        embedding
    )


# =========================
# VERIFICA EMBEDDINGS
# =========================

if len(embeddings) == 0:

    print(
        "Não foi possível gerar o perfil."
    )

    exit()


# =========================
# PERFIL MÉDIO
# =========================

perfil = np.mean(
    embeddings,
    axis=0
)


# Normaliza novamente
norma = np.linalg.norm(
    perfil
)

if norma > 0:
    perfil /= norma


# =========================
# CARREGA BANCO ATUAL
# =========================

if os.path.exists(
    ARQUIVO_PERFIS
):

    dados = np.load(
        ARQUIVO_PERFIS
    )

    perfis = list(
        dados["perfis"]
    )

    nomes = list(
        dados["nomes"]
    )

else:

    perfis = []
    nomes = []


# =========================
# ATUALIZA PERFIL
# =========================

if nome in nomes:

    indice = nomes.index(
        nome
    )

    perfis[indice] = perfil

    print(
        f"Perfil de {nome} atualizado."
    )

else:

    nomes.append(
        nome
    )

    perfis.append(
        perfil
    )

    print(
        f"Novo perfil de {nome} criado."
    )


# =========================
# SALVA BANCO
# =========================

np.savez(
    ARQUIVO_PERFIS,

    perfis=np.array(
        perfis,
        dtype=np.float32
    ),

    nomes=np.array(
        nomes
    )
)


# =========================
# FINAL
# =========================

print()
print("==========================")
print("CADASTRO CONCLUÍDO")
print("==========================")
print(f"Nome: {nome}")
print(f"Fotos utilizadas: {len(embeddings)}")
print("Perfil facial salvo.")
print("Pessoa pronta para reconhecimento!")