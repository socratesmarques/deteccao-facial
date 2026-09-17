# FaceAI — controle de acesso facial

Aplicação local de reconhecimento facial com interface PySide6, detecção YuNet,
reconhecimento SFace e abertura de acesso por ESP32.

## O que foi melhorado

- Compatibilidade com notebook Ubuntu e Orange Pi 3 LTS.
- O cadastro não salva fotografias: somente o perfil numérico local.
- Dados biométricos ficam em `dados_privados/`, fora do Git.
- Comparação vetorizada dos perfis com NumPy.
- Escrita atômica de perfis e configurações.
- Comunicação com o ESP32 fora da thread da interface.
- Câmera com buffer reduzido e resolução/FPS configuráveis.
- Configuração de autorizados, câmera, serial e segurança pela interface.

## Notebook Ubuntu

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
python baixar_modelo_piscadas.py
cp config.example.json config.json
python main.py
```

## Orange Pi 3 LTS

No Orange Pi, prefira o OpenCV otimizado fornecido pelo Ubuntu:

```bash
sudo apt update
sudo apt install python3-opencv python3-venv libgl1
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements-orange-pi.txt
python baixar_modelo_piscadas.py
cp config.example.json config.json
python main.py
```

Em **Configurações**, selecione `orange_pi`, use `640x480` e comece com 15 FPS
caso a placa apresente uso alto de CPU.

## Cadastro e autorização

1. Abra **Cadastrar pessoa** e capture o perfil.
2. Entre em **Configurações**.
3. Informe os nomes autorizados, separados por vírgula.
4. Volte para **Câmera**.

Antes de liberar o acesso, siga na tela o desafio aleatório de piscadas descrito abaixo.

O cadastro gera embeddings em memória e descarta os frames. O arquivo local
`dados_privados/perfis.npz` contém dados biométricos e não deve ser compartilhado.

## ESP32

O computador envia `PING` e espera `PONG`. Após a confirmação facial, envia
`ABRIR`. O firmware deve aceitar comandos terminados por quebra de linha.

Permita a porta serial sem executar como root:

```bash
sudo usermod -aG dialout "$USER"
```

Depois, encerre a sessão e entre novamente.

## Testes

```bash
pip install pytest
pytest -q
```

## Desempenho e seleção de um rosto

O reconhecimento roda em uma thread própria; a interface recebe somente o último
quadro processado, sem acumular eventos/imagens em uma fila. O FPS exibido conta
novos quadros processados e exibidos, não repetições artificiais da imagem.

- YuNet detecta por padrão em **320 pixels de largura**, mantendo a proporção.
  As coordenadas e os cinco pontos faciais são convertidos para a imagem original:
  SFace continua extraindo características da captura original, sem reduzir o crop.
- O maior rosto inicia a seleção. Novos rostos não roubam o foco enquanto o alvo
  continuar sendo associado à sua posição anterior. Somente ele recebe caixa/nome.
- Há no máximo uma extração SFace por ciclo de reconhecimento, a cada **0,35 s**,
  independentemente do número de pessoas. Sem perfis cadastrados, não há extração.
- Ao perder o alvo, sua caixa/nome somem imediatamente no próximo quadro processado.
  Após **0,7 s** sem associação, outro alvo pode ser selecionado no quadro seguinte.
  Esse intervalo evita trocas rápidas por uma falha pontual do detector.
- Rostos sobrepostos com associação ambígua suspendem o reconhecimento e a liberação;
  a seleção fica reservada enquanto houver detecção na área ambígua.
- Somente novas inferências contam para confirmar acesso. Resultados em cache não
  contam; perda, mudança de identidade, erro e quadros com mais de 1 s reiniciam a
  confirmação. Cinco confirmações de identidade levam pelo menos cerca de 1,4 s
  com o padrão; agora ainda é necessário concluir o desafio de piscadas.
- `processar_a_cada_frames` agora controla quais quadros podem fazer uma nova extração
  (além do intervalo temporal). A detecção continua verificando presença em cada quadro.

Em **Configurações**, ajuste **Largura da detecção** e **Intervalo do reconhecimento**.
Configurações antigas recebem automaticamente os novos padrões. Se rostos distantes
não forem detectados, experimente largura 480 ou 640; isso aumenta o custo da detecção.

### Limites e validação na placa

A associação é espacial, não uma prova de identidade contínua. Cruzamentos, oclusões,
movimentos rápidos ou alguém ocupando exatamente a mesma posição podem causar perda
ou troca do alvo. A confirmação sempre exige inferências novas, mas o desafio de piscadas abaixo não constitui proteção robusta contra ataques de apresentação.
O tempo para perceber uma saída depende da câmera e do processamento de um quadro.
A interface não exibe vídeo de captura independente: seu FPS ainda depende da inferência.

Teste na Orange Pi com a mesma iluminação, câmera e resolução antes/depois: uma pessoa,
três pessoas, saída do alvo, cruzamentos, pessoa desconhecida e câmera desconectada.
Verifique tanto FPS quanto reconhecimento correto e tempo de liberação. O cadastro
continua exigindo uma única pessoa e usa a resolução original para manter qualidade.

Medição de desenvolvimento em CPU do ambiente de testes, imagem sintética vazia
640×480, YuNet real, 2 threads OpenCV, 3 aquecimentos + 20 detecções por tamanho:
640 px = 13,39 ms/detecção; 320 px = 3,50 ms/detecção. **Não é benchmark na Orange Pi,
nem mede SFace, captura, GUI ou FPS com pessoas.** Não há promessa de FPS específico.

Se o driver bloquear a leitura durante o encerramento, a aplicação aguarda até 2 s e
impede a troca para outra página/fechamento enquanto a câmera não for liberada. Tente
novamente após a liberação do driver; não se chama `release()` concorrente com `read()`.


## Desafio aleatório de piscadas (experimental)

**Reconhecer o rosto sozinho não libera o acesso.** Após confirmar uma identidade
autorizada, há uma calibração guiada, seguida de **1 a 5 piscadas**. O número é sorteado
com `secrets`, sem repetir o anterior na mesma sessão da câmera.

### Como usar a contagem corrigida

1. Siga a mensagem **mantenha os olhos abertos normalmente, sem arregalar**.
2. Quando solicitado, **feche os dois olhos por cerca de 1 segundo e reabra**.
   Este fechamento serve para calibrar e **não entra no contador**.
3. Aguarde aparecer **Pisque N vezes: 0/N**. Só então execute as piscadas pedidas.
4. Após a última, mantenha os olhos abertos. Um novo reconhecimento do mesmo nome
   precisa confirmar a identidade antes de liberar uma autorização de uso único.

A calibração mede separadamente a abertura de cada olho com os landmarks LBF e
calcula limites individuais de aberto/fechado. Não usa mais EAR universal 0,20/0,25.
Ela exige referência aberta estável e queda bilateral de pelo menos 20% e 0,025 EAR
no fechamento; sem contraste mensurável, não inicia o desafio. Prazo de calibração:
20 s. O limite para fechado fica em 35% do intervalo medido fechado→aberto, e o limite
para aberto em 70%, evitando alternância por pequenas oscilações.

### Correções da contagem

- A exigência antiga de dois quadros fechados perdia piscadas em FPS baixo. Com
  intervalo mediano entre amostras ≥0,12 s, um quadro **bilateralmente fechado**
  pode contar, desde que precedido por olhos abertos e seguido de duas leituras
  abertas. Com amostragem mais rápida, continuam necessárias duas leituras fechadas.
  Essa tolerância aumenta a sensibilidade a ruído em FPS baixo; não torna o desafio
  uma prova de vivacidade.
- Nenhuma piscada é inventada se todo o fechamento ocorrer entre os quadros.
- A extração SFace é adiada enquanto os olhos estão fechados ou a calibração pede
  fechamento. Isso evita reiniciar o desafio por uma comparação facial ruim causada
  pelo próprio gesto. A detecção do alvo permanece ativa e a identidade é comparada
  novamente com olhos abertos. Nenhum resultado em cache libera acesso.
- A região usada pelo LBF tem agora até 384 px para preservar mais detalhes dos olhos.
- Abaixo da imagem aparece **diagnóstico dos olhos**: estado, EAR esquerdo/direito,
  limites calculados, taxa de amostras e último motivo de reinício/rejeição. Não grava
  fotos, vídeo nem dados biométricos novos em disco.

Se continuar sem contar, envie uma foto/captura dessa área de diagnóstico durante a
calibração e durante uma piscada. Se o EAR quase não mudar ao fechar os olhos, o modelo
não está medindo as pálpebras de forma utilizável naquela condição; alterar apenas o
contador não resolve. Aproximar o rosto, olhar de frente e melhorar iluminação pode
ajudar. Não arregale os olhos para calibrar: a referência deve ser sua abertura normal.

### Instalação do modelo (uma vez por máquina)

No ambiente virtual, com as dependências do projeto instaladas:

```bash
python baixar_modelo_piscadas.py
python main.py
```

Se já instalou o modelo no PR anterior, **não precisa baixá-lo novamente**. O instalador
também detecta o arquivo correto e não refaz o download.

O modelo LBF (~54 MB) vem do [repositório do autor](https://github.com/kurnianggoro/GSOC2017),
com commit fixo e SHA-256 verificado antes da substituição atômica. Fica fora do Git.
Consulte os termos de origem dos dados/modelo antes de usos além da demonstração
acadêmica. Requer `cv2.face.createFacemarkLBF` no OpenCV contrib
([documentação](https://docs.opencv.org/4.x/dc/d63/classcv_1_1face_1_1FacemarkLBF.html)).
Na Orange Pi, confira o OpenCV da distribuição:

```bash
python -c "import cv2; print(cv2.__version__); print(hasattr(cv2, 'face') and hasattr(cv2.face, 'createFacemarkLBF'))"
```

O último resultado deve ser `True`. Ausência do modelo/módulo ou erro de processamento
bloqueiam a liberação, sem fallback para acesso só pelo rosto. Não há MediaPipe/dlib.

### Limites e validação física pendente

- Perda/troca do alvo ou da identidade, olhos sem medição válida, lacuna >0,6 s entre
  amostras e quadros antigos invalidam o desafio. A tela informa o motivo.
- Desafio: 25 s. Fechamento durante o desafio: máximo de 1,5 s. Resultado concluído:
  validade de 3 s e uso único, mesmo se o controlador falhar ao abrir.
- Reiniciar a câmera cria nova sessão: o sorteio pode coincidir com o da sessão anterior.
- Óculos, inclinação, iluminação, rosto pequeno e variações de anatomia prejudicam LBF.
  Rostos menores que 80 px ou cortados pela imagem são rejeitados. Piscadas muito rápidas
  podem não ser capturadas pela câmera; observe o contador e a taxa de amostras.
- Este é um desafio heurístico experimental, **não anti-spoofing robusto**. Movimentar
  fotos, usar vídeos/animações ou manipular a câmera ainda pode enganá-lo. Há somente
  cinco números possíveis; não é proteção suficiente para uma porta real contra fraude.
- Testes automatizados simulam medições e cadência, incluindo 5 e 60 FPS, EAR fora dos
  limites antigos, entrada estática, ausência de contraste, ruído, perda de alvo,
  autorização de uso único e confirmação após a piscada. **Não substituem teste na
  Orange Pi com pessoas reais.** Não tenho câmera/placa/relé nesse ambiente.
