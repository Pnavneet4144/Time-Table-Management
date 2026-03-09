import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, engine
import models
from auth import get_password_hash

models.Base.metadata.create_all(bind=engine)

def create_admin():
    db = SessionLocal()

    existing = db.query(models.User).filter(models.User.role == "admin").first()
    if existing:
        print(f"Admin already exists: username='{existing.username}'")
        print("If you forgot the password, delete college_timetable.db and run this script again.")
        db.close()
        return

    print("=== Create Admin Account ===")
    username = input("Enter admin username: ").strip()
    email = input("Enter admin email: ").strip()
    password = input("Enter admin password: ").strip()

    if not username or not email or not password:
        print("Error: All fields are required.")
        db.close()
        return

    if len(password) < 6:
        print("Error: Password must be at least 6 characters.")
        db.close()
        return

    admin = models.User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        role="admin"
    )
    db.add(admin)
    db.commit()
    print(f"\nAdmin account created successfully!")
    print(f"Username : {username}")
    print(f"Email    : {email}")
    print(f"Role     : admin")
    print(f"\nYou can now login at http://localhost:8000/static/login.html")
    db.close()

if __name__ == "__main__":
    create_admin()
