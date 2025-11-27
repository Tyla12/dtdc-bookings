from app import create_app
from models import db, Room

app = create_app()

rooms_to_add = [
    "ROOM 1",
    "ROOM 2",
    "ROOM 3/HALL",
    "ROOM 4",
    "ROOM 5",
    "ROOM 6",
    "BOARDROOM"
    
]

with app.app_context():
    print("📌 adding rooms...")

    for room_name in rooms_to_add:
        
        existing = Room.query.filter_by(room_name=room_name).first()
        if not existing:
            new_room = Room(room_name=room_name)
            db.session.add(new_room)
            print(f"✔ Added: {room_name}")
        else:
            print(f"⚠ Skipped (already exists): {room_name}")

    db.session.commit()
    print("✅ Adding rooms complete!")
    print("Current rooms in database:")
    for r in Room.query.all():
        print("-", r.room_name)
