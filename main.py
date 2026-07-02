from users import members, pros
from courts import courts
import json

bookings_file = bookings.json

member = members[0]
coach = pros[0]
court = courts[0]

open_time = 8 * 60
close_time = 20 * 60
allowed_durations = [30, 60, 90, 120]


#club number upon login determines the user booking the court

def find_user_by_club_number(club_number):
    all_users = pros + members
    for user in all_users:
        if user["club_number"] == club_number:
            return user
    return None
club_number = int(input("Enter club number: "))





current_user = find_user_by_club_number(club_number)
if current_user is None:
    print("User not found.")
else:
    print(f"Logged in as {current_user['first_name']} {current_user['last_name']}")

##

def load_bookings():
    try:
        with open(bookings_file, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_bookings():
    with open(BOOKING_FILE, "w") as file:
        json.dump(bookings, file, indent=4)

### rule check functions ----- #


def is_valid_duration(duration):
    return duration in allowed_durations

def is_within_club_hours (start_time, duration):   #makes sure reservation is within
    end_time = start_time + duration

    if start_time < open_time:
        return False
    
    if end_time > close_time:
        return False
    

    return True

def bookings_overlap(new_booking, existing_booking):   #returns true or false
    new_start = new_booking["start_time"]
    new_end = new_start + new_booking["duration"]

    existing_start = existing_booking["start_time"]
    existing_end = existing_start + existing_booking["duration"]

    return new_start < existing_end and new_end > existing_start

def has_booking_conflict(new_booking, bookings):       #boolean
    for existing_booking in bookings:
        if bookings_overlap(new_booking, existing_booking):
            return True
        
    return False

#--------#

bookings = load_bookings()

club_number = int(input("Enter club number: "))
current_user = find_user_by_club_number(club_number)

start_hour = int(input("Start hour: "))
start_minute = int(input("Start minute: "))
duration = int(input("Duration: "))

start_time = start_hour * 60 + start_minute

new_reservation = {
    "user": current_user,
    "court": court,
    "start_time": start_time,
    "duration": duration,
}

if not is_valid_duration(duration):
    print("Invalid duration.")
elif not is_within_club_hours(start_time, duration):
    print("Reservation must be between 8:00 AM and 8:00 PM.")
elif has_booking_conflict(new_reservation, bookings):
    print("Booking conflict. This court is already reserved at that time.")
else:
    bookings.append(new_reservation)
    print("Reservation created.")
    print(new_reservation)