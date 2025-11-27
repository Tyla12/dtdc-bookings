import re
from wtforms.validators import ValidationError

from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, SelectField,
    IntegerField, TextAreaField, DateField, TimeField
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange, Optional
)

def gmail_email_check(form, field):
    pattern = r'^[a-zA-Z0-9_.+-]+@gmail\.com$'
    if not re.match(pattern, field.data or ''):
        raise ValidationError('Only Gmail addresses (example@gmail.com) are allowed.')

class RegistrationForm(FlaskForm):
    name = StringField('Full name', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), gmail_email_check])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign in')

class BookingForm(FlaskForm):
    name = StringField('Full Names', validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField('Email', validators=[DataRequired(), Email(), gmail_email_check])
    phone = StringField('Phone', validators=[DataRequired(), Length(max=20)])
    unit = StringField('Unit / Directorate', validators=[DataRequired(), Length(max=120)])
    room_id = SelectField('Room', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    start_time = TimeField('Start time', validators=[DataRequired()])
    end_time = TimeField('End time', validators=[DataRequired()])
    activity = StringField('Event / Activity', validators=[DataRequired(), Length(max=255)])
    participants = IntegerField('Expected participants', validators=[DataRequired(), NumberRange(min=1)])
    requirements = TextAreaField('Special Requirements', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Submit Booking')

class ResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        'Confirm Password',
        validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField('Reset Password')
