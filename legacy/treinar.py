import cv2
import os
import json
import numpy as np

PASTA_DADOS = "dados"

rostos = []
labels = []
pessoas = {}

id_atual = 0

# Percorre todas as pastas dentro de dados/
for nome in sorted(os.listdir(PASTA_DADOS)):

    pasta_pessoa = os.path.join(PASTA_DADOS, nome)

    # Ignora arquivos que não sejam pastas
    if not os.path.isdir(pasta_pessoa):
        continue

    print(f"Carregando: {nome}")

    # Associa um ID à pessoa
    pessoas[id_atual] = nome

    for arquivo in os.listdir(pasta_pessoa):

        caminho = os.path.join(pasta_pessoa, arquivo)

        imagem = cv2.imread(
            caminho,
            cv2.IMREAD_GRAYSCALE
        )

        if imagem is None:
            continue

        imagem = cv2.resize(imagem, (200, 200))

        rostos.append(imagem)
        labels.append(id_atual)

    id_atual += 1


if len(rostos) == 0:
    print("Nenhum rosto encontrado!")
    exit()


print("\nPessoas cadastradas:")

for id_pessoa, nome in pessoas.items():
    print(f"{id_pessoa} -> {nome}")

print(f"\nTotal de imagens: {len(rostos)}")


# Cria e treina o modelo
modelo = cv2.face.LBPHFaceRecognizer_create()

modelo.train(
    rostos,
    np.array(labels)
)

modelo.write("modelo.yml")


# Salva os IDs e nomes
with open("pessoas.json", "w") as arquivo:
    json.dump(pessoas, arquivo, indent=4)


print("\nTreinamento concluído!")
print("modelo.yml criado.")
print("pessoas.json criado.")