import os
from functools import wraps
from datetime import date, datetime, timedelta
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database import initialize_database
from extensions import db, migrate
from models import Booking, Court, User

###############################################
'''these here are the "time rules" variables'''
OPEN_MINUTES = 8 * 60
CLOSE_MINUTES = 20 * 60
ALLOWED_DURATIONS = (30, 60, 90, 120)
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
###############################################


app = Flask(__name__)
# Use the environment value if it exists, otherwise use the development value.
app.secret_key = os.environ.get("COURT_BOOKER_SECRET", "court-booker-development-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "sqlite:///court_booker.db",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate.init_app(app, db)

with app.app_context():
    initialize_database()


# we find the user by checking if the users club number matches to a registered club number
def find_user_by_club_number(club_number):
    user = db.session.get(User, club_number)
    return user.to_dict() if user else None


def users_by_type(user_type):
    statement = (
        db.select(User).where(User.user_type == user_type).order_by(User.club_number)
    )
    return [user.to_dict() for user in db.session.scalars(statement)]


#check if a user is a pro by comparing the int value of club number to 1000
def is_pro(user):
    # dict.get() reads a key and uses 1000 if that key is missing.
    return bool(user and user.get("club_number", 1000) < 1000)


def load_bookings():
    statement = db.select(Booking).order_by(Booking.start_datetime, Booking.court_id)
    return [booking.to_dict() for booking in db.session.scalars(statement)]


def save_bookings(bookings):
    desired_ids = {booking["id"] for booking in bookings}
    for existing in db.session.scalars(db.select(Booking)):
        if existing.id not in desired_ids:
            db.session.delete(existing)

    for booking_data in bookings:
        booking = db.session.get(Booking, booking_data["id"])
        if booking is None:
            booking = Booking(id=booking_data["id"])
            db.session.add(booking)

        booking.court_id = int(booking_data["court"])
        booking.start_datetime = booking_start(booking_data)
        booking.duration = int(booking_data["duration"])
        booking.owner_club_number = int(booking_data["owner_club_number"])
        booking.guest_count = int(booking_data.get("guest_count", 0))
        booking.created_by = int(booking_data["created_by"])
        booking.created_by_role = booking_data["created_by_role"]
        booking.is_override = bool(booking_data.get("override"))
        booking.overrode_count = int(booking_data.get("overrode_count", 0))

        member_numbers = [
            int(member["club_number"])
            for member in booking_data.get("additional_members", [])
        ]
        if member_numbers:
            statement = db.select(User).where(User.club_number.in_(member_numbers))
            booking.additional_members = list(db.session.scalars(statement))
        else:
            booking.additional_members = []

    db.session.commit()

#takes a bookings saved date and time text and converts it into a datetime object
def booking_start(booking):
    return datetime.strptime(booking["start_datetime"], DATETIME_FORMAT)

#bookings_overlap() checks whether two bookings use any of the same time.
'''It works by:
1. Finding when each booking starts.
2. Adding its duration to calculate when it ends.
3. Checking whether the two time periods cross.'''
def bookings_overlap(new_booking, existing_booking):
    new_start = booking_start(new_booking)
    new_end = new_start + timedelta(minutes=int(new_booking["duration"]))  # time delta represents and amount of time
    existing_start = booking_start(existing_booking)
    existing_end = existing_start + timedelta(minutes=int(existing_booking["duration"]))
    return new_start < existing_end and new_end > existing_start

#conflicting_bookings() finds every existing booking that conflicts with a new booking.
def conflicting_bookings(new_booking, bookings):
    # This list comprehension keeps only bookings that meet both conditions.
    return [
        booking
        for booking in bookings
        if int(booking["court"]) == int(new_booking["court"])
        and bookings_overlap(new_booking, booking)
    ]


def is_within_club_hours(start_datetime, duration):
    start_minutes = start_datetime.hour * 60 + start_datetime.minute
    return (
        start_datetime.minute in (0, 30)
        and start_minutes >= OPEN_MINUTES
        and start_minutes + duration <= CLOSE_MINUTES
    )


def requested_court_ids():
    raw_court_ids = request.form.get("court_ids", "").strip()
    if not raw_court_ids:
        raw_court_ids = request.form.get("court", "").strip()

    try:
        court_ids = [
            int(value.strip())
            for value in raw_court_ids.split(",")
            if value.strip()
        ]
    except ValueError:
        return None

    # dict.fromkeys() removes duplicate IDs while preserving their order.
    # "or None" changes an empty result into None.
    return list(dict.fromkeys(court_ids)) or None


def parse_booking_roster(member_number_values, guest_count_text, owner):
    try:
        guest_count = int(guest_count_text or 0)
    except ValueError:
        return None, None, "Guest count must be a whole number."
    if guest_count < 0 or guest_count > 20:
        return None, None, "Guest count must be between 0 and 20."

    raw_numbers = [value.strip() for value in member_number_values if value.strip()]
    if len(raw_numbers) > 3:
        return None, None, "A booking can include no more than three additional members."
    try:
        club_numbers = [int(value) for value in raw_numbers]
    except ValueError:
        return None, None, "Additional member numbers must contain only numbers separated by commas."
    if len(club_numbers) != len(set(club_numbers)):
        return None, None, "Enter each additional member only once."
    if owner["club_number"] in club_numbers:
        return None, None, "The booking owner's club number is already included automatically."

    # This dictionary comprehension makes club numbers quick to look up.
    member_lookup = {
        member["club_number"]: member for member in users_by_type("member")
    }
    unknown_numbers = [number for number in club_numbers if number not in member_lookup]
    if unknown_numbers:
        formatted = ", ".join(str(number) for number in unknown_numbers)
        return None, None, f"Unknown member club number(s): {formatted}."
    return [member_lookup[number] for number in club_numbers], guest_count, None


def booking_owner_for_request(staff_user):
    if not is_pro(staff_user):
        return staff_user, None
    owner_number_text = request.form.get("owner_club_number", "").strip()
    if not owner_number_text:
        return staff_user, None
    try:
        owner_number = int(owner_number_text)
    except ValueError:
        return None, "Select a valid booking owner."
    if owner_number == staff_user["club_number"]:
        return staff_user, None
    owner_record = db.session.get(User, owner_number)
    owner = (
        owner_record.to_dict()
        if owner_record and owner_record.user_type == "member"
        else None
    )
    if owner is None:
        return None, "Select a valid member as the booking owner."
    return owner, None


def current_user():
    club_number = session.get("club_number")
    if club_number is None:
        return None
    return find_user_by_club_number(int(club_number))


def load_credentials():
    return {
        user.username: {
            "club_number": user.club_number,
            "password_hash": user.password_hash,
        }
        for user in db.session.scalars(db.select(User))
    }


def login_required(view):
    # This decorator builds a login check that can wrap any page function.
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if current_user() is None:
            flash("Please sign in to view the court schedule.", "error")
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        # *args and **kwargs pass through all positional and named arguments.
        return view(*args, **kwargs)

    return wrapped_view


def surface_courts(surface):
    statement = db.select(Court).where(Court.surface == surface).order_by(Court.id)
    return [court.to_dict() for court in db.session.scalars(statement)]


def calendar_url(surface, selected_date):
    return url_for("calendar", surface=surface, date=selected_date.isoformat())


# This decorator makes the returned values available in every HTML template.
@app.context_processor
def inject_globals():
    user = current_user()
    return {
        "current_user": user,
        "current_user_is_pro": is_pro(user),
        # This is a one-line if/else expression.
        "current_user_role_label": (
            "Front Desk" if user and user.get("club_number") == 5 else "Pro"
        ),
    }


# Flask decorators connect the URL above a function to that function.
@app.get("/")
def index():
    if current_user() is None:
        return redirect(url_for("login"))
    return redirect(url_for("calendar", surface="hard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if current_user() is not None:
            return redirect(url_for("index"))
        return render_template("login.html")

    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    credential = load_credentials().get(username)
    if not credential or not check_password_hash(credential["password_hash"], password):
        flash("Incorrect username or password.", "error")
        return render_template("login.html", username=username), 401

    user = find_user_by_club_number(int(credential["club_number"]))
    if user is None:
        flash("This account is no longer active.", "error")
        return render_template("login.html", username=username), 401

    session.clear()
    session["club_number"] = user["club_number"]
    next_url = request.args.get("next", "")
    flash(f"Welcome, {user['first_name']}.", "success")
    return redirect(next_url if next_url.startswith("/") and not next_url.startswith("//") else url_for("index"))


@app.post("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("login"))


@app.get("/calendar/<surface>")
@login_required
def calendar(surface):
    if surface not in {"hard", "clay"}:
        return redirect(url_for("calendar", surface="hard"))

    try:
        selected_date = date.fromisoformat(request.args.get("date", date.today().isoformat()))
    except ValueError:
        flash("That date is invalid; showing today instead.", "error")
        selected_date = date.today()

    visible_courts = surface_courts(surface)
    court_ids = {court["id"] for court in visible_courts}
    day_bookings = []
    for booking in load_bookings():
        start = booking_start(booking)
        if start.date() != selected_date or int(booking["court"]) not in court_ids:
            continue
        user = booking.get("user", {})
        duration = int(booking["duration"])
        additional_members = booking.get("additional_members", [])
        guest_count = int(booking.get("guest_count", 0))
        owner_is_employee = user.get("user_type") == "employee"
        # join() combines the generated member labels with commas between them.
        member_roster = ", ".join(
            f'{member.get("first_name", "Member")} {member.get("last_name", "")} (#{member.get("club_number", "?")})'
            for member in additional_members
        ) or "None"
        day_bookings.append(
            {
                **booking,
                "court": int(booking["court"]),
                "start": start,
                "start_label": start.strftime("%-I:%M %p") if os.name != "nt" else start.strftime("%I:%M %p").lstrip("0"),
                "end_label": (start + timedelta(minutes=duration)).strftime("%I:%M %p").lstrip("0"),
                # // divides and discards any remainder, giving a whole row count.
                "rowspan": duration // 30,
                "name": f'{user.get("first_name", "Unknown")} {user.get("last_name", "member")}',
                "owner_club_number": booking.get("owner_club_number", user.get("club_number", "?")),
                "additional_member_count": len(additional_members),
                "member_roster": member_roster,
                "guest_count": guest_count,
                "billable_people": 1 + len(additional_members) + (0 if owner_is_employee else guest_count),
                "guests_are_free": owner_is_employee,
                "is_own": user.get("club_number") == current_user()["club_number"],
                "is_pro_booking": booking.get("created_by_role") == "employee"
                or user.get("user_type") == "employee",
                "is_override": bool(booking.get("override")),
            }
        )

    # Tuple keys let one dictionary use both court and time as its lookup key.
    bookings_by_start = {
        (booking["court"], booking["start"].strftime("%H:%M")): booking
        for booking in day_bookings
    }
    covered = set()
    for booking in day_bookings:
        for offset in range(1, booking["rowspan"]):
            covered_time = booking["start"] + timedelta(minutes=30 * offset)
            covered.add((booking["court"], covered_time.strftime("%H:%M")))

    slots = []
    for minutes in range(OPEN_MINUTES, CLOSE_MINUTES, 30):
        slot_time = datetime.combine(selected_date, datetime.min.time()) + timedelta(minutes=minutes)
        slots.append(
            {
                "value": slot_time.strftime("%H:%M"),
                "label": slot_time.strftime("%I:%M %p").lstrip("0"),
                "is_past": slot_time < datetime.now(),
            }
        )

    return render_template(
        "calendar.html",
        surface=surface,
        surface_title=surface.title(),
        courts=visible_courts,
        slots=slots,
        selected_date=selected_date,
        selected_date_label=selected_date.strftime("%A, %B %d, %Y").replace(" 0", " "),
        previous_date=selected_date - timedelta(days=1),
        next_date=selected_date + timedelta(days=1),
        bookings_by_start=bookings_by_start,
        covered=covered,
        return_url=request.full_path.rstrip("?"),
        members=users_by_type("member"),
        staff_durations=range(30, CLOSE_MINUTES - OPEN_MINUTES + 1, 30),
    )


@app.post("/bookings")
@login_required
def create_booking():
    return_surface = request.form.get("surface", "hard")
    return_date_text = request.form.get("return_date", date.today().isoformat())
    try:
        court_ids = requested_court_ids()
        duration = int(request.form["duration"])
        start = datetime.strptime(
            f'{request.form["date"]} {request.form["start_time"]}', DATETIME_FORMAT
        )
    except (KeyError, TypeError, ValueError):
        flash("The selected court time is invalid.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))

    selected_courts = (
        list(
            db.session.scalars(
                db.select(Court).where(Court.id.in_(court_ids or []))
            )
        )
        if court_ids
        else []
    )
    if len(selected_courts) != len(court_ids or []):
        flash("That court does not exist.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))
    staff_user = current_user()
    if len(court_ids) > 1 and not is_pro(staff_user):
        flash("Only pros and Front Desk staff can book multiple courts at once.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))
    if len({court.surface for court in selected_courts}) > 1:
        flash("Selected courts must have the same surface.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))
    if (not is_pro(staff_user) and duration not in ALLOWED_DURATIONS) or (
        is_pro(staff_user) and (duration < 30 or duration % 30 != 0)
    ):
        flash("Select a valid booking duration.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))
    if not is_within_club_hours(start, duration):
        flash("Bookings must fit between 8:00 AM and 8:00 PM.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))

    user, owner_error = booking_owner_for_request(staff_user)
    if owner_error:
        flash(owner_error, "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))
    additional_members, guest_count, roster_error = parse_booking_roster(
        request.form.getlist("additional_member_numbers"),
        request.form.get("guest_count", "0"),
        user,
    )
    if roster_error:
        flash(roster_error, "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))
    # This creates one booking dictionary for each selected court.
    new_bookings = [
        {
            "id": str(uuid4()),
            "user": user,
            "court": court_id,
            "start_datetime": start.strftime(DATETIME_FORMAT),
            "duration": duration,
            "owner_club_number": user["club_number"],
            "additional_members": additional_members,
            "guest_count": guest_count,
            "created_by": staff_user["club_number"],
            "created_by_role": staff_user["user_type"],
        }
        for court_id in court_ids
    ]
    bookings = load_bookings()
    # This dictionary maps each court ID to its list of conflicting bookings.
    conflicts_by_court = {
        new_booking["court"]: conflicting_bookings(new_booking, bookings)
        for new_booking in new_bookings
    }
    # The two for clauses flatten those smaller lists into one list.
    conflicts = [
        conflict
        for court_conflicts in conflicts_by_court.values()
        for conflict in court_conflicts
    ]
    if conflicts and not is_pro(staff_user):
        flash("That selection conflicts with an existing booking.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))
    if conflicts and request.form.get("override_confirmed") != "yes":
        flash("Confirm the override before replacing another booking.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))

    if conflicts:
        conflict_ids = {booking["id"] for booking in conflicts}
        bookings = [booking for booking in bookings if booking["id"] not in conflict_ids]
        for new_booking in new_bookings:
            court_conflicts = conflicts_by_court[new_booking["court"]]
            if court_conflicts:
                new_booking["override"] = True
                new_booking["overrode_count"] = len(court_conflicts)
    bookings.extend(new_bookings)
    save_bookings(bookings)
    if len(new_bookings) == 1:
        flash("Booking created successfully.", "success")
    else:
        flash(f"{len(new_bookings)} courts booked successfully.", "success")
    return redirect(url_for("calendar", surface=return_surface, date=return_date_text))


@app.post("/bookings/<booking_id>/cancel")
@login_required
def cancel_booking(booking_id):
    return_surface = request.form.get("surface", "hard")
    return_date_text = request.form.get("return_date", date.today().isoformat())
    bookings = load_bookings()
    target = next((booking for booking in bookings if booking["id"] == booking_id), None)
    if not target:
        flash("That booking could not be found.", "error")
    elif target.get("user", {}).get("club_number") != current_user()["club_number"] and not is_pro(current_user()):
        flash("You can only cancel your own bookings.", "error")
    else:
        bookings.remove(target)
        save_bookings(bookings)
        flash("Booking canceled.", "success")
    return redirect(url_for("calendar", surface=return_surface, date=return_date_text))


# This is true only when main.py is run directly, not when another file imports it.
if __name__ == "__main__":
    app.run(debug=True)
