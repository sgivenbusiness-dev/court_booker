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

def is_valid_duration(duration):
    return duration in ALLOWED_DURATIONS

def is_within_club_hours (start_time, duration):
    end_time = start_time + duration

    if start_time < OPEN_TIME:
        return False
    
    if end_time > CLOSE_TIME:
        return False
    

    return True

print(is_within_club_hours(10 * 60, 60))          # True
print(is_within_club_hours(7 * 60 + 30, 60))     # False
print(is_within_club_hours(19 * 60 + 30, 60))    # False
print(is_within_club_hours(18 * 60, 120))        # True