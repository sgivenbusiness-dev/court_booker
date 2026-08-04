import csv
import json
import secrets
import string
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from users import members, pros  # noqa: E402

DATA_DIR = ROOT / "data"
AUTH_FILE = DATA_DIR / "credentials.json"
EXPORT_FILE = DATA_DIR / "initial_credentials.csv"
ALPHABET = string.ascii_letters + string.digits + "!@#$%"


def username_for(user):
    return f"{user['first_name']}.{user['last_name']}".lower()


def generate():
    DATA_DIR.mkdir(exist_ok=True)
    if AUTH_FILE.exists() or EXPORT_FILE.exists():
        raise SystemExit("Credential files already exist; remove them explicitly before regenerating all passwords.")

    credentials = {}
    exported = []
    for user in pros + members:
        username = username_for(user)
        password = "".join(secrets.choice(ALPHABET) for _ in range(14))
        credentials[username] = {
            "club_number": user["club_number"],
            "password_hash": generate_password_hash(password),
        }
        exported.append(
            {
                "name": f"{user['first_name']} {user['last_name']}",
                "role": "pro" if user["club_number"] < 1000 else "member",
                "club_number": user["club_number"],
                "username": username,
                "temporary_password": password,
            }
        )

    AUTH_FILE.write_text(json.dumps(credentials, indent=2), encoding="utf-8")
    with EXPORT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=exported[0].keys())
        writer.writeheader()
        writer.writerows(exported)
    print(f"Generated {len(exported)} accounts.")
    print(f"Password hashes: {AUTH_FILE}")
    print(f"One-time credentials: {EXPORT_FILE}")


if __name__ == "__main__":
    generate()
