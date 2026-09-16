from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
MODELS_DIR = ROOT_DIR / "modelos"
PRIVATE_DATA_DIR = ROOT_DIR / "dados_privados"
PROFILES_FILE = PRIVATE_DATA_DIR / "perfis.npz"
CONFIG_FILE = ROOT_DIR / "config.json"
YUNET_MODEL = MODELS_DIR / "yunet.onnx"
SFACE_MODEL = MODELS_DIR / "sface.onnx"


def ensure_private_data_dir() -> Path:
    """Cria a pasta local de dados biométricos quando necessário."""
    PRIVATE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return PRIVATE_DATA_DIR
