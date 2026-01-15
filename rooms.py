from models import db, Room

def seed_rooms():
    rooms_to_add = [
        "ROOM 1",
        "ROOM 2",
        "ROOM 3/HALL",
        "ROOM 4",
        "ROOM 5",
        "ROOM 6",
        "BOARDROOM"
    ]

    for room_name in rooms_to_add:
        existing = Room.query.filter_by(room_name=room_name).first()
        if not existing:
            db.session.add(Room(room_name=room_name))

    db.session.commit()
