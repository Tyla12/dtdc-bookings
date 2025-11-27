from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(50), default='official')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='requester', lazy='dynamic')

    # -------------------------------
    # PASSWORD HELPERS
    # -------------------------------
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_manager(self):
        return self.role == 'manager'

    # -------------------------------
    # RESET PASSWORD TOKEN HELPERS
    # -------------------------------
    def get_reset_token(self):
        """Generate a secure reset token valid for 30 minutes."""
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, max_age=1800):
        """Verify the token and return the user if valid."""
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=max_age)
        except:
            return None

        return User.query.get(data['user_id'])


class Room(db.Model):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(255), nullable=False)
    capacity = db.Column(db.Integer, default=0)
    description = db.Column(db.String(500), nullable=True)

    bookings = db.relationship('Booking', backref='room', lazy='dynamic')


class Booking(db.Model):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    requester_name = db.Column(db.String(255), nullable=False)
    requester_email = db.Column(db.String(255), nullable=False)
    requester_phone = db.Column(db.String(50), nullable=True)
    unit = db.Column(db.String(255), nullable=True)

    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    activity = db.Column(db.String(500), nullable=False)
    participants = db.Column(db.Integer, default=0)
    requirements = db.Column(db.String(1000), nullable=True)

    status = db.Column(db.String(50), default='pending')
    reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def overlaps(self, other):
        if self.date != other.date or self.room_id != other.room_id:
            return False
        return not (self.end_time <= other.start_time or self.start_time >= other.end_time)
