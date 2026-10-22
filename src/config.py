import os
from pathlib import Path

LIMITE_CHAVES = int(os.getenv("LIMITE_CHAVES", "10"))
PIN = os.getenv("PIN", "5678")
PASTA_CHAVES = Path(os.getenv("PASTA_CHAVES", "chaves"))
