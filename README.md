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
