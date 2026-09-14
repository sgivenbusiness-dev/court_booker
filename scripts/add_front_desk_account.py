import csv
import secrets
import string
import sys
from pathlib import Path

from werkzeug.security import generate_password_hash


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from extensions import db  # noqa: E402
from main import app  # noqa: E402
from models import User  # noqa: E402


EXPORT_FILE = ROOT / "data" / "initial_credentials.csv"
USERNAME = "front.desk"
CLUB_NUMBER = 5
ALPHABET = string.ascii_letters + string.digits + "!@#$%"


def add_account():
    password = "".join(secrets.choice(ALPHABET) for _ in range(14))
    with app.app_context():
        if db.session.get(User, CLUB_NUMBER) is not None:
            raise SystemExit("The Front Desk account already exists.")
        db.session.add(
            User(
                club_number=CLUB_NUMBER,
                username=USERNAME,
                first_name="Front",
                last_name="Desk",
                user_type="employee",
                password_hash=generate_password_hash(password),
            )
        )
        db.session.commit()

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
