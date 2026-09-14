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
from users import members as initial_members  # noqa: E402
from users import pros as initial_pros  # noqa: E402

DATA_DIR = ROOT / "data"
EXPORT_FILE = DATA_DIR / "initial_credentials.csv"
ALPHABET = string.ascii_letters + string.digits + "!@#$%"


def username_for(user):
    return f"{user.first_name}.{user.last_name}".lower()


def users_for_credentials():
    users_by_club_number = {
        user.club_number: user for user in db.session.scalars(db.select(User))
    }

    for user_data in initial_pros + initial_members:
        club_number = user_data["club_number"]
        if club_number not in users_by_club_number:
            user = User(
                **user_data,
                username=f"{user_data['first_name']}.{user_data['last_name']}".lower(),
                password_hash="pending",
            )
            db.session.add(user)
            users_by_club_number[club_number] = user

    return sorted(users_by_club_number.values(), key=lambda user: user.club_number)


def generate():
    DATA_DIR.mkdir(exist_ok=True)
    if EXPORT_FILE.exists():
        raise SystemExit(
            "The credential export already exists; remove it explicitly before "
            "regenerating all passwords."
        )

    exported = []
    with app.app_context():
        for user in users_for_credentials():
            username = username_for(user)
            password = "".join(secrets.choice(ALPHABET) for _ in range(14))
            user.username = username
            user.password_hash = generate_password_hash(password)
            exported.append(
                {
                    "name": f"{user.first_name} {user.last_name}",
                    "role": user.user_type,
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
