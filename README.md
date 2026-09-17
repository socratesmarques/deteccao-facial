# FaceAI — controle de acesso facial

Aplicação local de reconhecimento facial com interface PySide6, detecção YuNet,
reconhecimento SFace e acionamento de relé diretamente pelo GPIO do Orange Pi.

## O que foi melhorado

- Compatibilidade com notebook Ubuntu e Orange Pi 3 LTS.
- O cadastro não salva fotografias: somente o perfil numérico local.
- Dados biométricos ficam em `dados_privados/`, fora do Git.
- Comparação vetorizada dos perfis com NumPy.
- Escrita atômica de perfis e configurações.
- Controle de acesso feito diretamente pelo Orange Pi, sem ESP32.
- Logs de acesso em `dados_privados/acessos.csv`.
- Câmera com buffer reduzido e resolução/FPS configuráveis.
- Configuração de autorizados, câmera, GPIO e segurança pela interface.
- A tela de reconhecimento mostra o nome e o estado `LIBERADO` ou `BLOQUEADO`.

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

No Orange Pi, prefira o OpenCV fornecido pelo Ubuntu:

```bash
sudo apt update
sudo apt install python3-opencv python3-venv libgl1 gpiod
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements-orange-pi.txt
cp config.example.json config.json
python main.py
```

Em **Configurações**, selecione `orange_pi`, use `640x480` e comece com 15 FPS
caso a placa apresente uso alto de CPU.

## GPIO e relé

O ESP32 não é mais usado. O próprio programa Python abre a linha GPIO do Orange Pi e
aciona o relé após a confirmação facial.

Antes de configurar o sistema, descubra qual `gpiochip` e qual número de linha correspondem
ao pino físico onde o relé foi conectado:

```bash
gpiodetect
gpioinfo
```

Depois configure na interface:

- **GPIO chip**: por exemplo `/dev/gpiochip0`.
- **Linha GPIO do relé**: número da linha reportada pelo `gpioinfo`.
- **Relé ativo em nível alto**: marque somente se o seu módulo ligar com nível HIGH.
- **Tempo do relé**: duração do pulso de abertura.

O valor padrão da linha é `-1` de propósito: o programa não tenta adivinhar um pino e
não aciona hardware até você informar a linha correta.

## Logs

As decisões de acesso são registradas localmente em:

```text
dados_privados/acessos.csv
```

Cada registro contém data/hora, pessoa, decisão e detalhe. Exemplos de decisões:
`LIBERADO`, `BLOQUEADO` e `ERRO`.

## Cadastro e autorização

1. Abra **Cadastrar pessoa** e capture o perfil.
2. Entre em **Configurações**.
3. Informe os nomes autorizados, separados por vírgula.
4. Configure o GPIO do relé.
5. Volte para **Câmera**.

O cadastro gera embeddings em memória e descarta os frames. O arquivo local
`dados_privados/perfis.npz` contém dados biométricos e não deve ser compartilhado.

## Testes

```bash
pip install pytest
pytest -q
```

Para testar somente o relé, edite a linha GPIO em `teste_controle.py` e execute:

```bash
python teste_controle.py
```

## Desempenho e seleção de um rosto

O reconhecimento roda em uma thread própria; a interface recebe somente o último
quadro processado, sem acumular eventos/imagens em uma fila. O FPS exibido conta
novos quadros processados e exibidos, não repetições artificiais da imagem.

- YuNet detecta por padrão em **320 pixels de largura**, mantendo a proporção.
- O maior rosto inicia a seleção e somente o alvo selecionado recebe reconhecimento.
- Há no máximo uma extração SFace por ciclo de reconhecimento.
- Somente novas inferências contam para confirmar acesso.
- Perda, mudança de identidade, erro e quadros atrasados reiniciam a confirmação.
- O texto da câmera mostra `NOME - LIBERADO` ou `NOME - BLOQUEADO`.
- Após atingir os frames de confirmação, o Orange Pi aciona diretamente o relé.

Em **Configurações**, ajuste **Largura da detecção** e **Intervalo do reconhecimento**.
Configurações antigas recebem automaticamente os novos padrões.

### Limites

A associação é espacial, não uma prova de identidade contínua. O sistema não possui
prova de vivacidade completa e deve ser validado no ambiente real de uso.

Teste na Orange Pi com a mesma iluminação, câmera e resolução: pessoa autorizada,
pessoa bloqueada, pessoa desconhecida, múltiplas pessoas, câmera desconectada e relé.
