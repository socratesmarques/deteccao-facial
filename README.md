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
  confirmação. Cinco confirmações levam pelo menos cerca de 1,4 s com o padrão.
- `processar_a_cada_frames` agora controla quais quadros podem fazer uma nova extração
  (além do intervalo temporal). A detecção continua verificando presença em cada quadro.

Em **Configurações**, ajuste **Largura da detecção** e **Intervalo do reconhecimento**.
Configurações antigas recebem automaticamente os novos padrões. Se rostos distantes
não forem detectados, experimente largura 480 ou 640; isso aumenta o custo da detecção.

### Limites e validação na placa

A associação é espacial, não uma prova de identidade contínua. Cruzamentos, oclusões,
movimentos rápidos ou alguém ocupando exatamente a mesma posição podem causar perda
ou troca do alvo. A confirmação sempre exige inferências novas, mas o sistema não
possui detecção de vivacidade e não deve ser tratado como proteção contra fotos/vídeos.
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
