court = {
    "name": "court1",
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

print(is_valid_duration(45)) # False
print(is_valid_duration(60)) # True