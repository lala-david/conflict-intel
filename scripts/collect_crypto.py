"""
Manual runner for the crypto threat-finance medallion (bronze → silver → gold).

  python scripts/collect_crypto.py

The real logic lives in scripts/pipeline/crypto.py; the daily pipeline
(scripts/pipeline/run.py) invokes it automatically.
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import crypto  # noqa: E402


def main():
    crypto.run(datetime.now().strftime("manual-%Y%m%d-%H%M%S"))


if __name__ == "__main__":
    main()
