import csv
import json
import secrets
import string
from pathlib import Path

from werkzeug.security import generate_password_hash


ROOT = Path(__file__).resolve().parents[1]
AUTH_FILE = ROOT / "data" / "credentials.json"
EXPORT_FILE = ROOT / "data" / "initial_credentials.csv"
USERNAME = "front.desk"
CLUB_NUMBER = 5
ALPHABET = string.ascii_letters + string.digits + "!@#$%"


def add_account():
    credentials = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    if USERNAME in credentials:
        raise SystemExit("The Front Desk account already exists.")

    password = "".join(secrets.choice(ALPHABET) for _ in range(14))
    credentials[USERNAME] = {
        "club_number": CLUB_NUMBER,
        "password_hash": generate_password_hash(password),
    }
    AUTH_FILE.write_text(json.dumps(credentials, indent=2), encoding="utf-8")

    with EXPORT_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=("name", "role", "club_number", "username", "temporary_password"),
        )
        writer.writerow(
            {
                "name": "Front Desk",
                "role": "front desk",
                "club_number": CLUB_NUMBER,
                "username": USERNAME,
                "temporary_password": password,
            }
        )
    print(f"Front Desk username: {USERNAME}")
    print(f"Front Desk temporary password: {password}")


if __name__ == "__main__":
    add_account()
