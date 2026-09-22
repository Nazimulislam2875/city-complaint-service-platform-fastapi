from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import timedelta, datetime, timezone
from typing import Annotated, Optional
from database import SessionLocal
from models import Users
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
import os
from dotenv import load_dotenv


router = APIRouter()

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
OAuth2_bearer = OAuth2PasswordBearer(tokenUrl='login')

load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = 'HS256'



class CreateUser(BaseModel):
    email: str = Field(min_length=5, max_length=100)
    username: str = Field(min_length=3, max_length=50)
    firstname: str = Field(min_length=2, max_length=50)
    lastname: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class UpdateUser(BaseModel):
    email: Optional[str] = Field(default=None, min_length=5, max_length=100)
    username: Optional[str] = Field(default=None, min_length=3, max_length=50)
    firstname: Optional[str] = Field(default=None, min_length=2, max_length=50)
    lastname: Optional[str] = Field(default=None, min_length=2, max_length=50)


class UpdatePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=6, max_length=100)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    reset_token: str
    new_password: str = Field(min_length=6, max_length=100)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]


def authenticate_user(username, password, db):
    user = db.query(Users).filter(Users.username == username).first()

    if user is None:
        return False

    if not user.is_active:
        return False

    if bcrypt_context.verify(password, user.hash_password):
        return user

    return False


def create_access_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {
        'sub': username,
        'id': user_id,
        'role': role,
        'type': 'access'
    }

    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})

    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(username: str, user_id: int, role: str, expires_delta: timedelta):
    encode = {
        'sub': username,
        'id': user_id,
        'role': role,
        'type': 'refresh'
    }

    expires = datetime.now(timezone.utc) + expires_delta
    encode.update({'exp': expires})

    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def create_reset_token(email: str):
    encode = {
        'sub': email,
        'type': 'reset'
    }

    expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    encode.update({'exp': expires})

    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: Annotated[str, Depends(OAuth2_bearer)]):

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username = payload.get('sub')
        user_id = payload.get('id')
        role = payload.get('role')
        token_type = payload.get('type')

        if username is None or user_id is None or token_type != 'access':
            raise HTTPException(status_code=401, detail='Invalid access token')

        return {
            'username': username,
            'id': user_id,
            'role': role
        }

    except JWTError:
        raise HTTPException(status_code=401, detail='Invalid or expired token')


user_dependency = Annotated[dict, Depends(get_current_user)]


@router.post('/signup')
def create_user(db: db_dependency, new_user: CreateUser):

    existing_username = db.query(Users).filter(Users.username == new_user.username).first()

    if existing_username:
        raise HTTPException(status_code=400, detail='Username already exists')

    existing_email = db.query(Users).filter(Users.email == new_user.email).first()

    if existing_email:
        raise HTTPException(status_code=400, detail='Email already exists')

    user_model = Users(
        email=new_user.email,
        username=new_user.username,
        firstname=new_user.firstname,
        lastname=new_user.lastname,
        hash_password=bcrypt_context.hash(new_user.password),
        is_active=True,
        role='user'
    )

    db.add(user_model)
    db.commit()

    return JSONResponse(status_code=201, content={'message': 'User created successfully'})


@router.post('/login')
def login_user(db: db_dependency, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):

    user = authenticate_user(form_data.username, form_data.password, db)

    if not user:
        raise HTTPException(status_code=401, detail='Invalid username or password')

    access_token = create_access_token(
        user.username,
        user.id,
        user.role,
        timedelta(minutes=30)
    )

    refresh_token = create_refresh_token(
        user.username,
        user.id,
        user.role,
        timedelta(days=7)
    )
 
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'bearer'
    }


@router.post('/refresh-token')
def refresh_access_token(data: RefreshTokenRequest):

    try:
        payload = jwt.decode(data.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        username = payload.get('sub')
        user_id = payload.get('id')
        role = payload.get('role')
        token_type = payload.get('type')

        if username is None or user_id is None or token_type != 'refresh':
            raise HTTPException(status_code=401, detail='Invalid refresh token')

        access_token = create_access_token(
            username,
            user_id,
            role,
            timedelta(minutes=30)
        )

        return {
            'access_token': access_token,
            'token_type': 'bearer'
        }

    except JWTError:
        raise HTTPException(status_code=401, detail='Invalid or expired refresh token')


@router.post('/forgot-password')
def forgot_password(db: db_dependency, data: ForgotPasswordRequest):

    user = db.query(Users).filter(Users.email == data.email).first()

    if user is None:
        raise HTTPException(status_code=404, detail='User not found')

    reset_token = create_reset_token(user.email)

    return {
        'message': 'Password reset token generated',
        'reset_token': reset_token
    }


@router.post('/reset-password')
def reset_password(db: db_dependency, data: ResetPasswordRequest):

    try:
        payload = jwt.decode(data.reset_token, SECRET_KEY, algorithms=[ALGORITHM])

        email = payload.get('sub')
        token_type = payload.get('type')

        if email != data.email or token_type != 'reset':
            raise HTTPException(status_code=401, detail='Invalid reset token')

    except JWTError:
        raise HTTPException(status_code=401, detail='Invalid or expired reset token')

    user = db.query(Users).filter(Users.email == data.email).first()

    if user is None:
        raise HTTPException(status_code=404, detail='User not found')

    user.hash_password = bcrypt_context.hash(data.new_password)

    db.commit()

    return {
        'message': 'Password reset successfully'
    }


@router.put('/profile/update')
def update_user(user: user_dependency, db: db_dependency, update_data: UpdateUser):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    current_user = db.query(Users).filter(Users.id == user.get('id')).first()

    if current_user is None:
        raise HTTPException(status_code=404, detail='User not found')

    data = update_data.model_dump(exclude_unset=True)

    for key, value in data.items():

        if key == 'username':
            existing = db.query(Users).filter(Users.username == value, Users.id != current_user.id).first()

            if existing:
                raise HTTPException(status_code=400, detail='Username already exists')

        if key == 'email':
            existing = db.query(Users).filter(Users.email == value, Users.id != current_user.id).first()

            if existing:
                raise HTTPException(status_code=400, detail='Email already exists')

        setattr(current_user, key, value)

    db.commit()

    return JSONResponse(status_code=200, content={'message': 'Profile updated successfully'})


@router.put('/profile/change-password')
def update_password(user: user_dependency, db: db_dependency, password_data: UpdatePassword):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    current_user = db.query(Users).filter(Users.id == user.get('id')).first()

    if current_user is None:
        raise HTTPException(status_code=404, detail='User not found')

    if not bcrypt_context.verify(password_data.current_password, current_user.hash_password):
        raise HTTPException(status_code=401, detail='Wrong password')

    current_user.hash_password = bcrypt_context.hash(password_data.new_password)

    db.commit()

    return JSONResponse(status_code=200, content={'message': 'Password changed successfully'})


@router.get('/profile')
def get_user_details(user: user_dependency, db: db_dependency):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    current_user = db.query(Users).filter(Users.id == user.get('id')).first()

    if current_user is None:
        raise HTTPException(status_code=404, detail='User not found')

    return {
        'id': current_user.id,
        'email': current_user.email,
        'username': current_user.username,
        'firstname': current_user.firstname,
        'lastname': current_user.lastname,
        'role': current_user.role,
        'is_active': current_user.is_active,
        'created_at': current_user.created_at
    }