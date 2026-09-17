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

**Reconhecer o rosto sozinho não libera mais o acesso.** Após confirmar um nome
cadastrado e autorizado, a tela pede **1 a 5 piscadas**. A quantidade é sorteada com
`secrets` e difere do desafio anterior na mesma sessão da câmera. Reiniciar a câmera
cria outra sessão, então a quantidade pode coincidir com a da sessão anterior.

1. Olhe de frente e mantenha os dois olhos abertos até aparecer o pedido.
2. Pisque **devagar**, fechando e reabrindo os dois olhos. A tela mostra `0/N`, `1/N` etc.
3. Depois da última piscada, mantenha os olhos abertos até concluir a nova confirmação
   facial. Só então é emitida uma autorização de uso único para o controlador existente.

O sistema mede a proporção de abertura dos olhos (EAR) com **68 pontos faciais LBF**
no rosto selecionado. YuNet sozinho só fornece centros dos olhos, não pálpebras.
Cada piscada exige olhos abertos em dois quadros, fechados em pelo menos dois quadros,
e reabertos em dois quadros. Um único quadro de ruído, um olho fechado ou olhos
permanentemente fechados não devem completar o ciclo. EAR fechado ≤0,20; aberto ≥0,25.
Esses limiares são heurísticos e precisam de validação com pessoas reais.

- Prazo: 25 s por desafio; resultado concluído expira em 3 s.
- Perda/troca do rosto, nome desconhecido, olhos sem medição válida, pausa entre
  amostras acima de 0,6 s ou quadro processado antigo descartam todo o progresso.
- Fechar os olhos por mais de 1,5 s invalida a tentativa. Ao repetir, há novo sorteio.
- O desafio deve terminar antes de um **novo** reconhecimento do mesmo nome: um
  resultado facial em cache não libera a porta. A autorização só pode ser usada uma vez,
  inclusive se a comunicação com o controlador falhar.
- Não há opção de ignorar o desafio nem fallback para acesso só pelo rosto. Modelo
  ausente, OpenCV incompatível ou falha de processamento bloqueiam a liberação.

### Instalar o modelo (uma vez por máquina)

Com o ambiente virtual ativado e as dependências instaladas:

```bash
python baixar_modelo_piscadas.py
python main.py
```

O instalador baixa cerca de 54 MB do [repositório do autor do Facemark/LBF](https://github.com/kurnianggoro/GSOC2017)
num commit fixo, valida SHA-256 e só então substitui o arquivo local. Não baixa nada
durante o reconhecimento. O modelo é mantido fora do Git; consulte a origem e os termos
dos dados/modelo antes de usos além da demonstração acadêmica.

Requer OpenCV com `cv2.face.createFacemarkLBF` ([documentação](https://docs.opencv.org/4.x/dc/d63/classcv_1_1face_1_1FacemarkLBF.html)).
O `opencv-contrib-python` das dependências do notebook fornece esse módulo. Na Orange Pi,
confira o pacote instalado no seu sistema:

```bash
python -c "import cv2; print(cv2.__version__); print(hasattr(cv2, 'face') and hasattr(cv2.face, 'createFacemarkLBF'))"
```

O último resultado precisa ser `True`. Se for `False`, a aplicação mostra erro e mantém
o acesso bloqueado; é necessário instalar um OpenCV contrib compatível com a distribuição.
Não instala MediaPipe nem dlib.

### Limitações e teste na Orange Pi

**Isto dificulta uma foto estática, mas NÃO é anti-spoofing robusto.** O movimento da foto,
falhas dos landmarks, vídeos, animações ou manipulação da câmera podem enganar uma
heurística de piscadas. Há apenas cinco quantidades possíveis. Não usar este desafio
como única proteção de uma porta real que exija segurança contra fraude.

Óculos, pouca luz, rosto pequeno/inclinado e características dos olhos podem impedir
contagem correta. Rostos menores que 80 px ou cortados pela borda são recusados para
a medição ocular. Na Orange Pi com FPS baixo, piscadas naturais rápidas podem não ser
capturadas: use piscadas lentas seguindo o contador; não reduza confirmações para
compensar quadros perdidos. Abaixo de aproximadamente 2 FPS, as lacunas podem reiniciar
o desafio por segurança. Pessoas que não conseguem executar o gesto precisarão de
outro método de acesso, ainda não implementado.

Validação automatizada cobre a máquina de estados e o bloqueio/liberação, não comprova
resistência a ataques físicos. Um smoke test com OpenCV 4.14, YuNet/LBF reais e a imagem
pública `lena.jpg` do OpenCV confirmou carregamento e medição; 30 medições levaram em
média 2,24 ms por rosto na CPU de desenvolvimento (2 threads). Não é medição da Orange Pi,
nem valida piscadas reais. Teste na placa: pessoa cadastrada, cada quantidade de 1 a 5,
foto estática, vídeo, saída/troca de pessoa, timeout, câmera desligada e tentativa de
reutilizar a liberação. O relé/controlador não foi testado fisicamente aqui.
