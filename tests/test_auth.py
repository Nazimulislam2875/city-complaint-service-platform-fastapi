def test_signup(client):
    response = client.post('/signup', json={
        'email': 'newuser@test.com',
        'username': 'newuser',
        'firstname': 'New',
        'lastname': 'User',
        'password': 'newuser123'
    })

    assert response.status_code == 201
    assert response.json()['message'] == 'User created successfully'


def test_signup_duplicate_username(client, normal_user):
    response = client.post('/signup', json={
        'email': 'another@test.com',
        'username': 'testuser',
        'firstname': 'Another',
        'lastname': 'User',
        'password': 'test1234'
    })

    assert response.status_code == 400
    assert response.json()['detail'] == 'Username already exists'


def test_login(client, normal_user):
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'test1234'
    })

    assert response.status_code == 200
    assert 'access_token' in response.json()
    assert 'refresh_token' in response.json()
    assert response.json()['token_type'] == 'bearer'


def test_login_wrong_password(client, normal_user):
    response = client.post('/login', data={
        'username': 'testuser',
        'password': 'wrongpassword'
    })

    assert response.status_code == 401


def test_profile(client, normal_user, user_token):
    response = client.get(
        '/profile',
        headers={'Authorization': f'Bearer {user_token}'}
    )

    assert response.status_code == 200
    assert response.json()['username'] == 'testuser'


def test_profile_without_token(client):
    response = client.get('/profile')

    assert response.status_code == 401