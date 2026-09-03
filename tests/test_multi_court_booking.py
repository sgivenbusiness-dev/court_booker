import unittest
from unittest.mock import patch

import main


class MultiCourtBookingTests(unittest.TestCase):
    def setUp(self):
        main.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = main.app.test_client()

    def sign_in_as(self, club_number):
        with self.client.session_transaction() as session:
            session["club_number"] = club_number

    @staticmethod
    def booking_form(**overrides):
        form = {
            "court": "0",
            "court_ids": "0,2",
            "date": "2099-01-05",
            "return_date": "2099-01-05",
            "surface": "hard",
            "start_time": "10:00",
            "duration": "60",
            "guest_count": "0",
            "override_confirmed": "no",
        }
        form.update(overrides)
        return form

    def test_pro_and_front_desk_can_book_multiple_courts(self):
        for club_number in (0, 5):
            with self.subTest(club_number=club_number):
                self.sign_in_as(club_number)
                with patch("main.load_bookings", return_value=[]), patch("main.save_bookings") as save_bookings:
                    response = self.client.post("/bookings", data=self.booking_form())

                self.assertEqual(response.status_code, 302)
                saved = save_bookings.call_args.args[0]
                self.assertEqual([booking["court"] for booking in saved], [0, 2])
                self.assertTrue(all(booking["created_by"] == club_number for booking in saved))

    def test_member_cannot_forge_a_multi_court_request(self):
        self.sign_in_as(1000)
        with patch("main.load_bookings", return_value=[]), patch("main.save_bookings") as save_bookings:
            response = self.client.post("/bookings", data=self.booking_form())

        self.assertEqual(response.status_code, 302)
        save_bookings.assert_not_called()

    def test_member_can_still_book_one_court(self):
        self.sign_in_as(1000)
        form = self.booking_form(court_ids="0")
        with patch("main.load_bookings", return_value=[]), patch("main.save_bookings") as save_bookings:
            response = self.client.post("/bookings", data=form)

        self.assertEqual(response.status_code, 302)
        saved = save_bookings.call_args.args[0]
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["court"], 0)


if __name__ == "__main__":
    unittest.main()
