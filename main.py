import json
import os
from functools import wraps
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from courts import courts
from users import members, pros


BASE_DIR = Path(__file__).resolve().parent
BOOKINGS_FILE = BASE_DIR / "bookings.json"
CREDENTIALS_FILE = BASE_DIR / "data" / "credentials.json"
OPEN_MINUTES = 8 * 60
CLOSE_MINUTES = 20 * 60
ALLOWED_DURATIONS = (30, 60, 90, 120)
DATETIME_FORMAT = "%Y-%m-%d %H:%M"

app = Flask(__name__)
app.secret_key = os.environ.get("COURT_BOOKER_SECRET", "court-booker-development-key")


def find_user_by_club_number(club_number):
    return next(
        (user for user in pros + members if user["club_number"] == club_number),
        None,
    )


def is_pro(user):
    return bool(user and user.get("club_number", 1000) < 1000)


def load_bookings():
    try:
        with BOOKINGS_FILE.open("r", encoding="utf-8") as file:
            bookings = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    for index, booking in enumerate(bookings):
        booking.setdefault("id", f"legacy-{index}")
    return bookings


def save_bookings(bookings):
    with BOOKINGS_FILE.open("w", encoding="utf-8") as file:
        json.dump(bookings, file, indent=4)


def booking_start(booking):
    return datetime.strptime(booking["start_datetime"], DATETIME_FORMAT)


def bookings_overlap(new_booking, existing_booking):
    new_start = booking_start(new_booking)
    new_end = new_start + timedelta(minutes=int(new_booking["duration"]))
    existing_start = booking_start(existing_booking)
    existing_end = existing_start + timedelta(minutes=int(existing_booking["duration"]))
    return new_start < existing_end and new_end > existing_start


def conflicting_bookings(new_booking, bookings):
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

    member_lookup = {member["club_number"]: member for member in members}
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
    owner = next((member for member in members if member["club_number"] == owner_number), None)
    if owner is None:
        return None, "Select a valid member as the booking owner."
    return owner, None


def current_user():
    club_number = session.get("club_number")
    if club_number is None:
        return None
    return find_user_by_club_number(int(club_number))


def load_credentials():
    try:
        with CREDENTIALS_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError as error:
        raise RuntimeError(
            "Credentials are missing. Run: python scripts/generate_credentials.py"
        ) from error


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if current_user() is None:
            flash("Please sign in to view the court schedule.", "error")
            return redirect(url_for("login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped_view


def surface_courts(surface):
    return [
        {**court, "id": index}
        for index, court in enumerate(courts)
        if court["surface"] == surface
    ]


def calendar_url(surface, selected_date):
    return url_for("calendar", surface=surface, date=selected_date.isoformat())


@app.context_processor
def inject_globals():
    user = current_user()
    return {
        "current_user": user,
        "current_user_is_pro": is_pro(user),
        "current_user_role_label": (
            "Front Desk" if user and user.get("club_number") == 5 else "Pro"
        ),
    }


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
        members=members,
        staff_durations=range(30, CLOSE_MINUTES - OPEN_MINUTES + 1, 30),
    )


@app.post("/bookings")
@login_required
def create_booking():
    return_surface = request.form.get("surface", "hard")
    return_date_text = request.form.get("return_date", date.today().isoformat())
    try:
        court_id = int(request.form["court"])
        duration = int(request.form["duration"])
        start = datetime.strptime(
            f'{request.form["date"]} {request.form["start_time"]}', DATETIME_FORMAT
        )
    except (KeyError, TypeError, ValueError):
        flash("The selected court time is invalid.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))

    if court_id not in range(len(courts)):
        flash("That court does not exist.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))
    staff_user = current_user()
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
    new_booking = {
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
    bookings = load_bookings()
    conflicts = conflicting_bookings(new_booking, bookings)
    if conflicts and not is_pro(staff_user):
        flash("That selection conflicts with an existing booking.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))
    if conflicts and request.form.get("override_confirmed") != "yes":
        flash("Confirm the override before replacing another booking.", "error")
        return redirect(url_for("calendar", surface=return_surface, date=return_date_text))

    if conflicts:
        conflict_ids = {booking["id"] for booking in conflicts}
        bookings = [booking for booking in bookings if booking["id"] not in conflict_ids]
        new_booking["override"] = True
        new_booking["overrode_count"] = len(conflicts)
    bookings.append(new_booking)
    save_bookings(bookings)
    flash("Booking created successfully.", "success")
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


if __name__ == "__main__":
    app.run(debug=True)
