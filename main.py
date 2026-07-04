from users import members, pros
from courts import courts
import json
from datetime import datetime, timedelta


BOOKINGS_FILE = "bookings.json"

open_time = 8 * 60
close_time = 20 * 60
allowed_durations = [30, 60, 90, 120]


def find_user_by_club_number(club_number):
    all_users = pros + members

    for user in all_users:
        if user["club_number"] == club_number:
            return user

    return None


def load_bookings():
    try:
        with open(BOOKINGS_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_bookings(bookings):
    with open(BOOKINGS_FILE, "w") as file:
        json.dump(bookings, file, indent=4)


def remove_conflicting_bookings(new_booking, bookings):
    updated_bookings = []
    removed_bookings = []

    for existing_booking in bookings:
        same_court = existing_booking["court"] == new_booking["court"]
        overlapping = bookings_overlap(new_booking, existing_booking)

        if same_court and overlapping:
            removed_bookings.append(existing_booking)
        else:
            updated_bookings.append(existing_booking)

    return updated_bookings, removed_bookings


def is_valid_duration(duration):
    return duration in allowed_durations


def is_within_club_hours(start_datetime, duration):
    end_datetime = start_datetime + timedelta(minutes=duration)

    opening_datetime = start_datetime.replace(hour=8, minute=0, second=0, microsecond=0)
    closing_datetime = start_datetime.replace(hour=20, minute=0, second=0, microsecond=0)

    
    if start_datetime < opening_datetime:
        return False

    if end_datetime > closing_datetime:
        return False

    return True


def bookings_overlap(new_booking, existing_booking):
    new_start = datetime.strptime(new_booking["start_datetime"], "%Y-%m-%d %H:%M")
    new_end = new_start + timedelta(minutes=new_booking["duration"])

    existing_start = datetime.strptime(existing_booking["start_datetime"], "%Y-%m-%d %H:%M")
    existing_end = existing_start + timedelta(minutes=existing_booking["duration"])

    return new_start < existing_end and new_end > existing_start


def has_booking_conflict(new_booking, bookings):
    for existing_booking in bookings:

        # Only check conflicts for the same court
        if existing_booking["court"] == new_booking["court"]:
            if bookings_overlap(new_booking, existing_booking):
                return True

    return False


bookings = load_bookings()

club_number = int(input("Enter club number: "))
current_user = find_user_by_club_number(club_number)

def is_pro(user):
    return user["club_number"] < 1000

if current_user is None:
    print("User not found.")
else:
    print(f"Logged in as {current_user['first_name']} {current_user['last_name']}")


    court = int(input("Court number: "))

    date_input = input("Reservation date (YYYY-MM-DD): ")
    time_input = input("Start time (HH:MM): ")

    start_datetime = datetime.strptime(
        date_input + " " + time_input,
        "%Y-%m-%d %H:%M"
)
    duration = int(input("Duration: "))
    end_datetime = start_datetime + timedelta(minutes=duration)

    new_reservation = {
    "user": current_user,
    "court": court,
    "start_datetime": start_datetime.strftime("%Y-%m-%d %H:%M"),
    "duration": duration,
}

if not is_valid_duration(duration):
    print("Invalid duration.")

elif not is_within_club_hours(start_datetime, duration):
    print("Reservation must be between 8:00 AM and 8:00 PM.")

elif has_booking_conflict(new_reservation, bookings) and not is_pro(current_user):
    print("Booking conflict. This court is already reserved at that time.")

else:
    if has_booking_conflict(new_reservation, bookings) and is_pro(current_user):
        bookings, removed_bookings = remove_conflicting_bookings(new_reservation, bookings)
        print(f"Removed {len(removed_bookings)} conflicting booking(s).")

    bookings.append(new_reservation)
    save_bookings(bookings)
    print("Reservation created.")