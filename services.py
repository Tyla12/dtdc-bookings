from flask_mail import Message, Mail
from twilio.rest import Client

mail = Mail()

def init_mail(app):
    mail.init_app(app)

def send_email(app, subject, recipients, body):
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        print(f"[MAIL DEMO] To: {recipients} Subject: {subject}\n{body}")
        return True

    msg = Message(
        subject=subject,
        recipients=[recipients],
        body=body,
        sender=app.config.get('MAIL_USERNAME')  
    )

    try:
        with app.app_context():
            mail.send(msg)
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False

def send_sms(app, to_number, message):
    sid = app.config.get('TWILIO_ACCOUNT_SID')
    token = app.config.get('TWILIO_AUTH_TOKEN')
    from_number = app.config.get('TWILIO_PHONE_NUMBER')

    if not sid or not token or not from_number:
        print(f"[SMS DEMO] To: {to_number}\nMessage: {message}")
        return False

    try:
        client = Client(sid, token)
        client.messages.create(body=message, from_=from_number, to=to_number)
        return True
    except Exception as e:
        print("Twilio error:", e)
        return False
