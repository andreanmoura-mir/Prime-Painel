
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SIANNET_USER = os.getenv("SIANNET_USER")
SIANNET_PASSWORD = os.getenv("SIANNET_PASSWORD")

# Período dos relatórios
DATA_INICIO = os.getenv("DATA_INICIO")
DATA_FIM = os.getenv("DATA_FIM")

# Diretórios de armazenamento
DADOS_DIR = BASE_DIR / "dados"

PASTA_ESCALADOS = DADOS_DIR / "escalados"
PASTA_PERFORMANCE = DADOS_DIR / "performance"
PASTA_TELEMETRIA = DADOS_DIR / "telemetria"
PASTA_EVENTOS_VIAGENS = DADOS_DIR / "eventos_viagens"

# Perfil exclusivo do Chrome
PERFIL_CHROME = BASE_DIR / "chrome_profile"

# Cria as pastas caso ainda não existam
for pasta in [
    PASTA_ESCALADOS,
    PASTA_PERFORMANCE,
    PASTA_TELEMETRIA,
    PASTA_EVENTOS_VIAGENS,
]:
    pasta.mkdir(parents=True, exist_ok=True)
