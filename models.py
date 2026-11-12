from datetime import datetime
from typing import Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from werkzeug.security import generate_password_hash, check_password_hash


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.current_timestamp())

    rsvps: Mapped[list["RSVP"]] = relationship(back_populates="user")
    events: Mapped[list["Event"]] = relationship(back_populates="creator")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Event(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    date: Mapped[datetime]
    location: Mapped[Optional[str]] = mapped_column(String(200))
    capacity: Mapped[Optional[int]]  # None means unlimited
    is_public: Mapped[bool] = mapped_column(default=True)
    requires_admin: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey('user.id'))
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.current_timestamp())

    creator: Mapped[Optional["User"]] = relationship(back_populates="events")
    rsvps: Mapped[list["RSVP"]] = relationship(back_populates="event", cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'date': self.date.isoformat() if self.date else None,
            'location': self.location,
            'capacity': self.capacity,
            'is_public': self.is_public,
            'requires_admin': self.requires_admin,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'rsvp_count': len(self.rsvps),
            'attendees': [rsvp.user_id for rsvp in self.rsvps if rsvp.attending and rsvp.user_id is not None]
        }


class RSVP(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey('event.id'))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('user.id'))
    attending: Mapped[bool] = mapped_column(default=True)  # True = going, False = not going
    created_at: Mapped[Optional[datetime]] = mapped_column(default=func.current_timestamp())

    event: Mapped["Event"] = relationship(back_populates="rsvps")
    user: Mapped[Optional["User"]] = relationship(back_populates="rsvps")

    def to_dict(self):
        return {
            'id': self.id,
            'event_id': self.event_id,
            'user_id': self.user_id,
            'attending': self.attending,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
