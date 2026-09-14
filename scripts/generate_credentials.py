import csv
import hashlib
import secrets
import string
import sys
from pathlib import Path

try:
    from werkzeug.security import generate_password_hash
except ModuleNotFoundError:
    def generate_password_hash(password):
        """Generate the same default scrypt format used by Werkzeug."""
        salt = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        digest = hashlib.scrypt(
            password.encode(), salt=salt.encode(), n=32768, r=8, p=1, maxmem=64 * 1024 * 1024
        )
        return f"scrypt:32768:8:1${salt}${digest.hex()}"


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from extensions import db  # noqa: E402
from main import app  # noqa: E402
from models import User  # noqa: E402

DATA_DIR = ROOT / "data"
EXPORT_FILE = DATA_DIR / "initial_credentials.csv"
ALPHABET = string.ascii_letters + string.digits + "!@#$%"


def username_for(user):
    return f"{user.first_name}.{user.last_name}".lower()


def generate():
    DATA_DIR.mkdir(exist_ok=True)
    if EXPORT_FILE.exists():
        raise SystemExit(
            "The credential export already exists; remove it explicitly before "
            "regenerating all passwords."
        )

    exported = []
    with app.app_context():
        users = db.session.scalars(db.select(User).order_by(User.club_number))
        for user in users:
            username = username_for(user)
            password = "".join(secrets.choice(ALPHABET) for _ in range(14))
            user.username = username
            user.password_hash = generate_password_hash(password)
            exported.append(
                {
                    "name": f"{user.first_name} {user.last_name}",
                    "role": "pro" if user.club_number < 1000 else "member",
                    "club_number": user.club_number,
                    "username": username,
                    "temporary_password": password,
                }
            )
        db.session.commit()

    with EXPORT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=exported[0].keys())
        writer.writeheader()
        writer.writerows(exported)
    print(f"Generated {len(exported)} accounts.")
    print("Password hashes saved in SQLite.")
    print(f"One-time credentials: {EXPORT_FILE}")


if __name__ == "__main__":
    generate()
