import os
from dotenv import load_dotenv
from database import SessionLocal, engine
import models
from models import Users
from router.auth import bcrypt_context


load_dotenv()

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

admin_email = os.getenv('ADMIN_EMAIL')
admin_username = os.getenv('ADMIN_USERNAME')
admin_password = os.getenv('ADMIN_PASSWORD')
admin_firstname = os.getenv('ADMIN_FIRSTNAME')
admin_lastname = os.getenv('ADMIN_LASTNAME')


if not admin_email or not admin_username or not admin_password:
    raise ValueError('Admin environment variables are not set')


existing_admin = db.query(Users).filter(Users.username == admin_username).first()

if existing_admin:
    print('Admin account already exists')
else:
    admin_user = Users(
        email=admin_email,
        username=admin_username,
        firstname=admin_firstname,
        lastname=admin_lastname,
        hash_password=bcrypt_context.hash(admin_password),
        is_active=True,
        role='admin'
    )

    db.add(admin_user)
    db.commit()

    print('Admin account created successfully')

db.close()