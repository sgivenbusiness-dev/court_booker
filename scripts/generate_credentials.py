import csv
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


def load_initial_credentials():
    if not EXPORT_FILE.exists():
        raise SystemExit(f"The test credential file is missing: {EXPORT_FILE}")

    with EXPORT_FILE.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    credentials = {}
    for row in rows:
        try:
            club_number = int(row["club_number"])
            username = row["username"].strip().lower()
            password = row["password"]
        except (KeyError, TypeError, ValueError) as error:
            raise SystemExit("The test credential file has an invalid row.") from error

        if not username or not password:
            raise SystemExit("Every test credential needs a username and password.")
        if club_number in credentials:
            raise SystemExit(f"Duplicate club number in test credentials: {club_number}")
        credentials[club_number] = (username, password)

    return credentials


def generate():
    credentials = load_initial_credentials()
    seed_users = initial_pros + initial_members
    missing_credentials = [
        user["club_number"]
        for user in seed_users
        if user["club_number"] not in credentials
    ]
    if missing_credentials:
        formatted = ", ".join(str(number) for number in missing_credentials)
        raise SystemExit(f"Missing test credentials for club number(s): {formatted}")

    with app.app_context():
        if db.session.scalar(db.select(db.func.count()).select_from(User)):
            raise SystemExit(
                "The database already contains users; test credentials were not changed."
            )

        for user_data in seed_users:
            username, password = credentials[user_data["club_number"]]
            db.session.add(
                User(
                    **user_data,
                    username=username,
                    password_hash=generate_password_hash(password),
                )
            )
        db.session.commit()

    print(f"Created {len(seed_users)} test accounts.")
    print("Password hashes saved in SQLite.")
    print(f"Test usernames and passwords: {EXPORT_FILE}")


if __name__ == "__main__":
    generate()
