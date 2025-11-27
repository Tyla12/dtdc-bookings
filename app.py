from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from sqlalchemy.exc import IntegrityError
import os
import re
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from datetime import datetime

from models import db, User, Room, Booking
from forms import RegistrationForm, LoginForm, BookingForm, ResetRequestForm, ResetPasswordForm
from services import send_email, send_sms


def create_app():
    app = Flask(__name__)

    app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("ERROR: DATABASE_URL is missing!")

    # Fix Render DB URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Create tables
    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Ensure manager exists
    with app.app_context():
        create_demo_manager()

    # --------------------- ROUTES ----------------------

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/contact')
    def contact():
        return render_template('contact.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegistrationForm()
        if form.validate_on_submit():

            # Only allow Gmail
            if not re.match(r'^[a-zA-Z0-9_.+-]+@gmail\.com$', form.email.data or ''):
                flash('Only Gmail addresses are allowed.', 'danger')
                return render_template('register.html', form=form)

            user = User(
                name=form.name.data,
                email=form.email.data,
                phone=form.phone.data
            )
            user.set_password(form.password.data)

            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('This email already exists.', 'danger')
                return render_template('register.html', form=form)

            flash('Account created. Please log in.', 'success')
            return redirect(url_for('login'))

        return render_template('register.html', form=form)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash("Incorrect email or password.", "danger")
        return render_template('login.html', form=form)

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('login'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        if current_user.is_manager():
            pending = Booking.query.filter_by(status="pending").all()
            return render_template('manager_dashboard.html', pending=pending)

        bookings = Booking.query.filter_by(user_id=current_user.id).all()
        return render_template('official_dashboard.html', bookings=bookings)

    @app.route('/book', methods=['GET', 'POST'])
    @login_required
    def book():
        form = BookingForm()
        form.room_id.choices = [(r.id, r.room_name) for r in Room.query.all()]

        if request.method == 'GET':
            form.name.data = current_user.name
            form.email.data = current_user.email
            form.phone.data = current_user.phone

        if form.validate_on_submit():

            if form.end_time.data <= form.start_time.data:
                flash('End time must be after start time', 'danger')
                return render_template('booking_form.html', form=form)

            approved = Booking.query.filter_by(
                room_id=form.room_id.data,
                date=form.date.data,
                status="approved"
            ).all()

            new_booking = Booking(
                user_id=current_user.id,
                requester_name=form.name.data,
                requester_email=form.email.data,
                requester_phone=form.phone.data,
                unit=form.unit.data,
                room_id=form.room_id.data,
                date=form.date.data,
                start_time=form.start_time.data,
                end_time=form.end_time.data,
                activity=form.activity.data,
                participants=form.participants.data,
                requirements=form.requirements.data,
                status='pending'
            )

            for e in approved:
                if new_booking.overlaps(e):
                    flash("This time slot is already booked!", "danger")
                    return render_template('booking_form.html', form=form)

            db.session.add(new_booking)
            db.session.commit()

            # Notify manager
            manager = User.query.filter_by(role="manager").first()
            if manager:
                msg = (
                    f"New Booking Request:\n"
                    f"Requester: {new_booking.requester_name}\n"
                    f"Date: {new_booking.date}\n"
                    f"Time: {new_booking.start_time} - {new_booking.end_time}\n"
                    f"Room: {new_booking.room.room_name}\n"
                    f"Activity: {new_booking.activity}"
                )
                send_email(app, "New Booking Request", manager.email, msg)

            flash("Booking submitted!", "success")
            return redirect(url_for('dashboard'))

        return render_template('booking_form.html', form=form)

    # -------------------- FIXED ROUTES ----------------------

    @app.route('/approve/<int:booking_id>', methods=['POST'])
    @login_required
    def approve_booking(booking_id):
        if not current_user.is_manager():
            flash("Unauthorized.", "danger")
            return redirect(url_for('dashboard'))

        booking = Booking.query.get_or_404(booking_id)
        booking.status = "approved"
        db.session.commit()

        flash("Booking approved.", "success")
        return redirect(url_for('dashboard'))

    @app.route('/reject/<int:booking_id>', methods=['POST'])
    @login_required
    def reject_booking(booking_id):
        if not current_user.is_manager():
            flash("Unauthorized.", "danger")
            return redirect(url_for('dashboard'))

        booking = Booking.query.get_or_404(booking_id)
        booking.status = "rejected"
        db.session.commit()

        flash("Booking rejected.", "info")
        return redirect(url_for('dashboard'))

    # -------------------- PASSWORD RESET ----------------------

    @app.route('/reset_request', methods=['GET', 'POST'])
    def reset_request():
        form = ResetRequestForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user:
                token = user.get_reset_token()
                reset_url = url_for('reset_token', token=token, _external=True)

                send_email(app,
                           "Password Reset",
                           user.email,
                           f"Click the link to reset your password:\n{reset_url}")

            flash("If your email exists, a reset link has been sent.", "info")
            return redirect(url_for('login'))

        return render_template('reset_request.html', form=form)

    @app.route('/reset/<token>', methods=['GET', 'POST'])
    def reset_token(token):
        user = User.verify_reset_token(token)
        if not user:
            flash("Invalid or expired token.", "danger")
            return redirect(url_for('reset_request'))

        form = ResetPasswordForm()
        if form.validate_on_submit():
            user.set_password(form.password.data)
            db.session.commit()
            flash("Password updated! You can now log in.", "success")
            return redirect(url_for('login'))

        return render_template('reset_token.html', form=form)

    return app


def create_demo_manager():
    if not User.query.filter_by(role="manager").first():
        m = User(
            name="Teacher Centre Manager",
            email="Stephen.Mnyaks@gmail.com",
            phone="+27 68 086 5988",
            role="manager"
        )
        m.set_password("Mnyakeni123")
        db.session.add(m)
        db.session.commit()


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
