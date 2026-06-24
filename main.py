court = {
    "name": "Court 1",
    "surface": "hard",
    "indoor": False
}

coach = {
    "name": "Sean Given",
    "user_type": "employee"
}

member = {
    "name": "John Smith",
    "user_type": "member"
}

OPEN_TIME = 8 * 60
CLOSE_TIME = 20 * 60

ALLOWED_DURATIONS = [30, 60, 90, 120]




reservation = {
    "user": member,
    "court": court,
    "start_time": 10 * 60,
    "duration": 60,
}

new_reservation = {
    "user": coach,
    "court": court,
    "start_time": 10 * 60 + 30,
    "duration": 60,
}

bookings = [reservation]

### rule check functions


def is_valid_duration(duration):
    return duration in ALLOWED_DURATIONS



def is_within_club_hours (start_time, duration):   #makes sure reservation is within
    end_time = start_time + duration

    if start_time < OPEN_TIME:
        return False
    
    if end_time > CLOSE_TIME:
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

            
selected_user = member

start_hour = int(input("Start hour: "))
start_minute = int(input("Start minute: "))
duration = int(input("Duration: "))

start_time = start_hour * 60 + start_minute

new_reservation = {
    "user": selected_user,
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

