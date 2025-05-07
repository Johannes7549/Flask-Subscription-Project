import os
from app import create_app, db
from app.models.user import User

app = create_app('development')

with app.app_context():
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_email and admin_password:
        user = User.query.filter_by(email=admin_email).first()
        if not user:
            user = User(email=admin_email)
            user.password = admin_password
            user.is_admin = True
            db.session.add(user)
            db.session.commit()
            print(f"Admin user {admin_email} created.")
        elif not user.is_admin:
            user.is_admin = True
            db.session.commit()
            print(f"User {admin_email} promoted to admin.")
        else:
            print(f"Admin user {admin_email} already exists.")
    else:
        print("ADMIN_EMAIL or ADMIN_PASSWORD not set in environment.")