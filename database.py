import json
from pathlib import Path

from courts import courts as initial_courts
from extensions import db
from models import Court, User
from users import members as initial_members
from users import pros as initial_pros


BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = BASE_DIR / "data" / "credentials.json"


def initialize_database():
    db.create_all()

    for court_id, court_data in enumerate(initial_courts):
        if db.session.get(Court, court_id) is None:
            db.session.add(Court(id=court_id, **court_data))

    if db.session.scalar(db.select(db.func.count()).select_from(User)):
        db.session.commit()
        return

    seed_users = initial_pros + initial_members
    credentials = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
    credentials_by_club_number = {
        int(value["club_number"]): (username, value["password_hash"])
        for username, value in credentials.items()
    }
    for user_data in seed_users:
        club_number = user_data["club_number"]
        username, password_hash = credentials_by_club_number[club_number]
        db.session.add(
            User(
                **user_data,
                username=username,
                password_hash=password_hash,
            )
        )

    db.session.commit()
