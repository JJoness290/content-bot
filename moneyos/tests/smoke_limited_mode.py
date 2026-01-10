import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

os.environ["MONEYOS_LIMITED_MODE"] = "1"

from moneyos.app.main import app  # noqa: E402


def main() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Limited Mode" in response.text


if __name__ == "__main__":
    main()
