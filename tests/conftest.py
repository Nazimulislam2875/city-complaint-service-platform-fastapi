import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from database import Base
from main import app, get_db
from router.auth import get_db as auth_get_db
from router.admin import get_db as admin_get_db

from models import Users
from router.auth import bcrypt_context, create_access_token
from datetime import timedelta


SQLALCHEMY_DATABASE_URL = 'sqlite://'

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={'check_same_thread': False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(
    autoflush=False,
    autocommit=False,
    bind=engine
)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[auth_get_db] = override_get_db
    app.dependency_overrides[admin_get_db] = override_get_db

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def normal_user(db):
    user = Users(
        email='user@test.com',
        username='testuser',
        firstname='Test',
        lastname='User',
        hash_password=bcrypt_context.hash('test1234'),
        is_active=True,
        role='user'
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@pytest.fixture
def admin_user(db):
    admin = Users(
        email='admin@test.com',
        username='testadmin',
        firstname='Test',
        lastname='Admin',
        hash_password=bcrypt_context.hash('admin1234'),
        is_active=True,
        role='admin'
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)

    return admin


@pytest.fixture
def user_token(normal_user):
    return create_access_token(
        normal_user.username,
        normal_user.id,
        normal_user.role,
        timedelta(minutes=30)
    )


@pytest.fixture
def admin_token(admin_user):
    return create_access_token(
        admin_user.username,
        admin_user.id,
        admin_user.role,
        timedelta(minutes=30)
    )