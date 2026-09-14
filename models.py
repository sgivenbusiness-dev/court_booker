from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from extensions import db


booking_members = db.Table(
    "booking_members",
    db.Column(
        "booking_id",
        db.String(36),
        db.ForeignKey("booking.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "club_number",
        db.Integer,
        db.ForeignKey("user.club_number"),
        primary_key=True,
    ),
)


class User(db.Model):
    club_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    user_type: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    def to_dict(self):
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "club_number": self.club_number,
            "user_type": self.user_type,
        }


class Court(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    surface: Mapped[str] = mapped_column(String(20), nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "surface": self.surface}


class Booking(db.Model):
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    court_id: Mapped[int] = mapped_column(ForeignKey("court.id"), nullable=False)
    start_datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_club_number: Mapped[int] = mapped_column(
        ForeignKey("user.club_number"), nullable=False
    )
    guest_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("user.club_number"), nullable=False
    )
    created_by_role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overrode_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    court: Mapped[Court] = relationship()
    owner: Mapped[User] = relationship(foreign_keys=[owner_club_number])
    creator: Mapped[User] = relationship(foreign_keys=[created_by])
    additional_members: Mapped[list[User]] = relationship(
        secondary=booking_members,
        order_by=User.club_number,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.owner.to_dict(),
            "court": self.court_id,
            "start_datetime": self.start_datetime.strftime("%Y-%m-%d %H:%M"),
            "duration": self.duration,
            "owner_club_number": self.owner_club_number,
            "additional_members": [user.to_dict() for user in self.additional_members],
            "guest_count": self.guest_count,
            "created_by": self.created_by,
            "created_by_role": self.created_by_role,
            "override": self.is_override,
            "overrode_count": self.overrode_count,
        }
