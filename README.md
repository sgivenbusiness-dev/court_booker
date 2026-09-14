# Tennis Court Booking System

A Flask-based web application for managing tennis court reservations. The application allows club members and teaching professionals to reserve courts while enforcing booking-duration, operating-hour, and scheduling-conflict rules.

## Features

* Member and professional user roles
* Indoor and outdoor court reservations
* Booking conflict detection
* Court operating-hour validation
* Different booking privileges based on user type
* Persistent reservation storage
* Flask web interface using Jinja2 templates

## Technologies

* Python
* Flask
* Flask-SQLAlchemy
* SQLite
* Jinja2
* HTML/CSS

## How It Works

Users log in using their username and password, then select a court, date, start time, and reservation duration. The application validates the request before creating the reservation.

Members are limited to standard booking rules, while teaching professionals have additional privileges for managing court reservations.

The booking logic checks for:

* Existing reservations that overlap the requested time
* Valid court operating hours
* Valid reservation durations
* User permissions

## Running the Project

1. Clone the repository.
2. Install the required Python packages with `python -m pip install -r requirements.txt`.
3. For a new database, create the initial accounts with `python scripts/generate_credentials.py`.
4. Save the generated one-time credentials from `data/initial_credentials.csv` somewhere secure.
5. Run the Flask application with `python main.py`.
6. Open the local Flask server in a web browser.

The credential-generation command creates `instance/court_booker.db`, seeds its users
and courts, and stores password hashes in SQLite. The one-time credential CSV is
ignored by Git. After setup, users, courts, bookings, and login credentials are read
from the SQLite database without any additional data files.

## Purpose

This project was created to practice building a complete web application around a real-world scheduling problem. It demonstrates Python application logic, Flask routing, server-side validation, templating, persistent data storage, and role-based business rules.
