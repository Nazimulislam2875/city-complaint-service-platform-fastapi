def test_database(client):
    response = client.get('/profile')

    assert response.status_code == 401



def test_refresh_token(client, normal_user, user_token):
    response = client.post('/refresh-token', json={
        'refresh_token': client.post('/login', data={
            'username': 'testuser',
            'password': 'test1234'
        }).json()['refresh_token']
    })

    assert response.status_code == 200
    assert 'access_token' in response.json()
    assert response.json()['token_type'] == 'bearer'


def test_forgot_password(client, normal_user):
    response = client.post('/forgot-password', json={
        'email': 'user@test.com'
    })

    assert response.status_code == 200
    assert 'reset_token' in response.json()


def test_reset_password(client, normal_user):
    forgot_response = client.post('/forgot-password', json={
        'email': 'user@test.com'
    })

    reset_token = forgot_response.json()['reset_token']

    response = client.post('/reset-password', json={
        'email': 'user@test.com',
        'reset_token': reset_token,
        'new_password': 'newpassword123'
    })

    assert response.status_code == 200
    assert response.json()['message'] == 'Password reset successfully'


def test_profile_update(client, normal_user, user_token):
    response = client.put(
        '/profile/update',
        headers={'Authorization': f'Bearer {user_token}'},
        json={
            'firstname': 'Updated'
        }
    )

    assert response.status_code == 200
    assert response.json()['message'] == 'Profile updated successfully'


def test_change_password(client, normal_user, user_token):
    response = client.put(
        '/profile/change-password',
        headers={'Authorization': f'Bearer {user_token}'},
        json={
            'current_password': 'test1234',
            'new_password': 'changed123'
        }
    )

    assert response.status_code == 200
    assert response.json()['message'] == 'Password changed successfully'