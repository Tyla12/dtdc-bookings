from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import re
import os
from itsdangerous import URLSafeTimedSerializer

from models import db, User, Room, Booking
from forms import RegistrationForm, LoginForm, BookingForm
from services import send_email, send_sms


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL","sqlite:///dtdc.db")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    def notify_officials(subject, message):
        officials = User.query.filter_by(role='official').all()
        for o in officials:
            try:
                send_email(app, subject, o.email, message)
            except Exception as e:
                print('Email notify failed for', o.email, e)

            if o.phone:
                try:
                    send_sms(app, o.phone, message)
                except Exception as e:
                    print('SMS notify failed for', o.phone, e)

    with app.app_context():
        db.create_all()
        create_demo_manager()

    # STATIC PAGES
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/contact')
    def contact():
        return render_template('contact.html')

    # AUTH ROUTES
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        form = RegistrationForm()
        if form.validate_on_submit():

            # UPDATED: Gmail-only validation
            if not re.match(r'^[a-zA-Z0-9_.+-]+@gmail\.com$', form.email.data or ''):
                flash('Only Gmail addresses (example@gmail.com) can register.', 'danger')
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
                flash('This email is already registered.', 'danger')
                return render_template('register.html', form=form)

            flash('Your account was created successfully. Please log in.', 'success')
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
            flash("Incorrect email or password", "danger")
        return render_template('login.html', form=form)

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('login'))

    # DASHBOARD
    @app.route('/dashboard')
    @login_required
    def dashboard():
        if current_user.is_manager():
            pending = Booking.query.filter_by(status='pending').order_by(Booking.date.desc()).all()
            return render_template('manager_dashboard.html', pending=pending)
        else:
            bookings = Booking.query.filter_by(user_id=current_user.id).all()
            return render_template('official_dashboard.html', bookings=bookings)

    # BOOKING ROUTES
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

            start = form.start_time.data
            end = form.end_time.data
            if end <= start:
                flash('End time must be after start time', 'danger')
                return render_template('booking_form.html', form=form)

            existing = Booking.query.filter_by(
                room_id=form.room_id.data,
                date=form.date.data,
                status='approved'
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

            for e in existing:
                if new_booking.overlaps(e):
                    flash("This time slot is already booked!", "danger")
                    return render_template('booking_form.html', form=form)

            db.session.add(new_booking)
            db.session.commit()

            manager = User.query.filter_by(role="manager").first()
            if manager:
                body = (
                    f"New booking request submitted:\n"
                    f"Requester: {new_booking.requester_name}\n"
                    f"Date: {new_booking.date}\n"
                    f"Time: {new_booking.start_time} - {new_booking.end_time}\n"
                    f"Room: {new_booking.room.room_name}\n"
                    f"Activity: {new_booking.activity}\n"
                )
                send_email(app, "New Booking Request - DTDC", manager.email, body)

            flash("Your Booking was submitted successfully!", "success")
            return redirect(url_for('dashboard'))

        return render_template('booking_form.html', form=form)

    # APPROVAL ROUTES
    @app.route('/approve/<int:id>')
    @login_required
    def approve(id):
        if not current_user.is_manager():
            return "Unauthorized", 403

        booking = Booking.query.get_or_404(id)
        booking.status = 'approved'
        db.session.commit()

        send_email(
            app,
            "Booking Approved",
            booking.requester_email,
            f"Your booking has been approved.\nDate: {booking.date}\nRoom: {booking.room.room_name}"
        )

        notify_officials(
            "Booking Approved",
            f"Booking by {booking.requester_name} on {booking.date} in {booking.room.room_name} was approved."
        )

        flash("Booking approved", "success")
        return redirect(url_for('dashboard'))

    @app.route('/decline/<int:id>', methods=['POST'])
    @login_required
    def decline(id):
        if not current_user.is_manager():
            return "Unauthorized", 403

        reason = request.form.get('reason', 'Not specified')
        booking = Booking.query.get_or_404(id)
        booking.status = 'declined'
        booking.reason = reason
        db.session.commit()

        send_email(
            app,
            "Booking Declined",
            booking.requester_email,
            f"Your booking was declined.\nReason: {reason}"
        )

        notify_officials(
            "Booking Declined",
            f"Booking by {booking.requester_name} on {booking.date} in {booking.room.room_name} was declined. Reason: {reason}"
        )

        flash("Booking declined", "info")
        return redirect(url_for('dashboard'))

    @app.route('/approve_booking/<int:booking_id>', methods=['POST'])
    @login_required
    def approve_booking(booking_id):
        return approve(booking_id)

    @app.route('/decline_booking/<int:booking_id>', methods=['POST'])
    @login_required
    def decline_booking(booking_id):
        return decline(booking_id)

    # PASSWORD RESET SYSTEM

    @app.route('/reset_password', methods=['GET', 'POST'])
    def reset_request():
        if request.method == "POST":
            email = request.form.get("email")
            user = User.query.filter_by(email=email).first()

            if user:
                s = URLSafeTimedSerializer(app.config["SECRET_KEY"])
                token = s.dumps(email)

                reset_link = url_for("reset_token", token=token, _external=True)
                print("RESET LINK:", reset_link)

            flash("If that email exists, a reset link has been sent.", "info")
            return redirect(url_for("login"))

        return render_template("reset_request.html")

    @app.route('/reset_password/<token>', methods=['GET', 'POST'])
    def reset_token(token):
        s = URLSafeTimedSerializer(app.config["SECRET_KEY"])

        try:
            email = s.loads(token, max_age=3600)
        except:
            flash("Invalid or expired token", "danger")
            return redirect(url_for("reset_request"))

        user = User.query.filter_by(email=email).first()

        if request.method == "POST":
            new_pass = request.form.get("password")
            user.set_password(new_pass)
            db.session.commit()
            flash("Password successfully reset!", "success")
            return redirect(url_for('login'))

        return render_template("reset_token.html")

    return app


def create_demo_manager():
    """Create default manager if none exists."""
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
