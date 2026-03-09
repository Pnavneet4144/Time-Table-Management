import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, engine
import models
from auth import get_password_hash

models.Base.metadata.create_all(bind=engine)


def show_menu():
    print("\n=============================")
    print("   NIT TMS — Admin Manager   ")
    print("=============================")
    print("1. View current admin details")
    print("2. Change admin password")
    print("3. Change admin email")
    print("4. Change admin username")
    print("5. Delete admin and create new one")
    print("6. Exit")
    print("=============================")
    return input("Choose option (1-6): ").strip()


def get_admin(db):
    admin = db.query(models.User).filter(models.User.role == "admin").first()
    if not admin:
        print("\nNo admin account found. Run 'python create_admin.py' first.")
        return None
    return admin


def view_admin(db):
    admin = get_admin(db)
    if not admin:
        return
    print("\n--- Current Admin Details ---")
    print(f"  Username : {admin.username}")
    print(f"  Email    : {admin.email}")
    print(f"  Role     : {admin.role}")
    print(f"  User ID  : {admin.id}")
    print("-----------------------------")


def change_password(db):
    admin = get_admin(db)
    if not admin:
        return
    print(f"\nChanging password for admin: '{admin.username}'")
    new_password = input("Enter new password (min 6 chars): ").strip()
    if len(new_password) < 6:
        print("Error: Password must be at least 6 characters.")
        return
    confirm = input("Confirm new password: ").strip()
    if new_password != confirm:
        print("Error: Passwords do not match.")
        return
    admin.password_hash = get_password_hash(new_password)
    db.commit()
    print(f"Password updated successfully for '{admin.username}'.")


def change_email(db):
    admin = get_admin(db)
    if not admin:
        return
    print(f"\nCurrent email: {admin.email}")
    new_email = input("Enter new email: ").strip()
    if not new_email or "@" not in new_email:
        print("Error: Invalid email address.")
        return
    existing = db.query(models.User).filter(
        models.User.email == new_email,
        models.User.id != admin.id
    ).first()
    if existing:
        print("Error: That email is already used by another account.")
        return
    admin.email = new_email
    db.commit()
    print(f"Email updated to '{new_email}' successfully.")


def change_username(db):
    admin = get_admin(db)
    if not admin:
        return
    print(f"\nCurrent username: {admin.username}")
    new_username = input("Enter new username: ").strip()
    if not new_username:
        print("Error: Username cannot be empty.")
        return
    existing = db.query(models.User).filter(
        models.User.username == new_username,
        models.User.id != admin.id
    ).first()
    if existing:
        print("Error: That username is already taken.")
        return
    admin.username = new_username
    db.commit()
    print(f"Username updated to '{new_username}' successfully.")


def delete_and_recreate(db):
    admin = get_admin(db)
    if admin:
        print(f"\nThis will DELETE the existing admin '{admin.username}' and create a new one.")
        confirm = input("Are you sure? Type YES to continue: ").strip()
        if confirm != "YES":
            print("Cancelled.")
            return
        db.delete(admin)
        db.commit()
        print("Old admin deleted.")

    print("\n--- Create New Admin ---")
    username = input("Enter new admin username: ").strip()
    email = input("Enter new admin email: ").strip()
    password = input("Enter new admin password: ").strip()

    if not username or not email or not password:
        print("Error: All fields are required.")
        return
    if len(password) < 6:
        print("Error: Password must be at least 6 characters.")
        return

    new_admin = models.User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        role="admin"
    )
    db.add(new_admin)
    db.commit()
    print(f"\nNew admin created successfully!")
    print(f"  Username : {username}")
    print(f"  Email    : {email}")


def main():
    db = SessionLocal()
    try:
        while True:
            choice = show_menu()
            if choice == "1":
                view_admin(db)
            elif choice == "2":
                change_password(db)
            elif choice == "3":
                change_email(db)
            elif choice == "4":
                change_username(db)
            elif choice == "5":
                delete_and_recreate(db)
            elif choice == "6":
                print("Bye!")
                break
            else:
                print("Invalid option. Choose 1-6.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
