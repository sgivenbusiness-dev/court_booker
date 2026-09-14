from courts import courts as initial_courts
from extensions import db
from models import Court


def initialize_database():
    db.create_all()

    for court_id, court_data in enumerate(initial_courts):
        if db.session.get(Court, court_id) is None:
            db.session.add(Court(id=court_id, **court_data))

    db.session.commit()
