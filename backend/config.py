from pathlib import Path
import os, secrets
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('SYLRAK_RUNTIME', ROOT / 'runtime'))
RUNTIME.mkdir(parents=True, exist_ok=True)
ENV = ROOT / '.env'
if not ENV.exists():
    ENV.write_text('SYLRAK_ADMIN_PASSWORD=' + secrets.token_urlsafe(12) + '\nSYLRAK_OPERATOR_PASSWORD=' + secrets.token_urlsafe(12) + '\n', encoding='utf-8')
load_dotenv(ENV)
ASSETS = ROOT / 'assets'
EVIDENCE = RUNTIME / 'evidence'
EVIDENCE.mkdir(exist_ok=True)
DB_URL = os.environ.get('SYLRAK_DB_URL', f'sqlite:///{(RUNTIME / "sylrak.db").as_posix()}')
RETENTION_DAYS = int(os.environ.get('SYLRAK_RETENTION_DAYS', '7'))
EXACT_THRESHOLD = float(os.environ.get('SYLRAK_EXACT_THRESHOLD', '.90'))
POSSIBLE_THRESHOLD = float(os.environ.get('SYLRAK_POSSIBLE_THRESHOLD', '.60'))
# 12 Sep 2026 10:00 IST. This is a simulated event clock, never a capture date claim.
SCENARIO_START = 1789187400.0
