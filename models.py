from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default='official')  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='requester', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_manager(self):
        return self.role == 'manager'

class Room(db.Model):
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, default=0)
    description = db.Column(db.String(255), nullable=True)

    bookings = db.relationship('Booking', backref='room', lazy='dynamic')

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
 
    requester_name = db.Column(db.String(120), nullable=False)
    requester_email = db.Column(db.String(150), nullable=False)
    requester_phone = db.Column(db.String(20), nullable=True)
    unit = db.Column(db.String(120), nullable=True)

    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    activity = db.Column(db.String(255), nullable=False)
    participants = db.Column(db.Integer, default=0)
    requirements = db.Column(db.String(500), nullable=True)

    status = db.Column(db.String(20), default='pending')
    reason = db.Column(db.String(255), nullable=True)  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def overlaps(self, other):
        """Return True if booking overlaps with other booking on same date and room."""
        if self.date != other.date or self.room_id != other.room_id:
            return False
        return not (self.end_time <= other.start_time or self.start_time >= other.end_time)


from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def get_reset_token(self):
    s = URLSafeTimedSerializer(current_app.config.get('SECRET_KEY'))
    return s.dumps(self.email)

@staticmethod
def verify_reset_token(token, expires_sec=3600):
    s = URLSafeTimedSerializer(current_app.config.get('SECRET_KEY'))
    try:
        email = s.loads(token, max_age=expires_sec)
    except Exception:
        return None
    return User.query.filter_by(email=email).first()

try:
    User.get_reset_token = get_reset_token
    User.verify_reset_token = staticmethod(verify_reset_token)
except Exception:
    pass
