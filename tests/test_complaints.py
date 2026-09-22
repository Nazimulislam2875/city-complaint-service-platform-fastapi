
from models import Users
from router.auth import bcrypt_context

def test_create_complaint(client, normal_user, user_token):
    response = client.post(
        '/complaints/create',
        headers={'Authorization': f'Bearer {user_token}'},
        json={
            'title': 'Broken Road',
            'description': 'The main road is badly damaged',
            'category': 'road',
            'location': 'Dhaka',
            'priority': 'high'
        }
    )

    assert response.status_code == 201
    assert response.json()['message'] == 'Complaint submitted successfully'
    assert 'complaint_id' in response.json()


def test_create_complaint_validation(client, normal_user, user_token):
    response = client.post(
        '/complaints/create',
        headers={'Authorization': f'Bearer {user_token}'},
        json={
            'title': 'Hi',
            'description': 'Short',
            'category': 'invalid',
            'location': 'Dhaka'
        }
    )

    assert response.status_code == 422


def test_my_complaints(client, normal_user, user_token, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Water Problem',
        description='There is no water supply',
        category='water',
        location='Dhaka',
        priority='medium',
        status='pending'
    )

    db.add(complaint)
    db.commit()

    response = client.get(
        '/complaints/my',
        headers={'Authorization': f'Bearer {user_token}'}
    )

    assert response.status_code == 200
    assert response.json()['total'] == 1
    assert len(response.json()['complaints']) == 1


def test_my_complaints_search_filter_sort_pagination(client, normal_user, user_token, db):
    from models import Complaints

    complaints = [
        Complaints(
            user_id=normal_user.id,
            title='Broken Road',
            description='Road is damaged badly',
            category='road',
            location='Dhaka',
            priority='high',
            status='pending'
        ),
        Complaints(
            user_id=normal_user.id,
            title='Water Problem',
            description='Water supply is unavailable',
            category='water',
            location='Dhaka',
            priority='medium',
            status='resolved'
        ),
        Complaints(
            user_id=normal_user.id,
            title='Garbage Issue',
            description='Garbage has not been collected',
            category='garbage',
            location='Dhaka',
            priority='low',
            status='pending'
        )
    ]

    db.add_all(complaints)
    db.commit()

    response = client.get(
        '/complaints/my?search=Road&category=road&status=pending&sort=alphabetical&page=1&page_size=1',
        headers={'Authorization': f'Bearer {user_token}'}
    )

    assert response.status_code == 200
    assert response.json()['total'] == 1
    assert response.json()['page'] == 1
    assert response.json()['page_size'] == 1
    assert response.json()['total_pages'] == 1
    assert response.json()['complaints'][0]['title'] == 'Broken Road'


def test_get_specific_complaint(client, normal_user, user_token, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Street Light Problem',
        description='Street light is not working',
        category='street_light',
        location='Dhaka',
        priority='medium',
        status='pending'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.get(
        f'/complaints/{complaint.id}',
        headers={'Authorization': f'Bearer {user_token}'}
    )

    assert response.status_code == 200
    assert response.json()['title'] == 'Street Light Problem'


def test_user_cannot_view_other_user_complaint(client, normal_user, user_token, db):
    from models import Complaints

    other_user = Users(
        email='other@test.com',
        username='otheruser',
        firstname='Other',
        lastname='User',
        hash_password=bcrypt_context.hash('other1234'),
        is_active=True,
        role='user'
    )

    db.add(other_user)
    db.commit()
    db.refresh(other_user)

    complaint = Complaints(
        user_id=other_user.id,
        title='Private Complaint',
        description='This belongs to another user',
        category='other',
        location='Dhaka',
        priority='low',
        status='pending'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.get(
        f'/complaints/{complaint.id}',
        headers={'Authorization': f'Bearer {user_token}'}
    )

    assert response.status_code == 403


def test_update_complaint(client, normal_user, user_token, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Old Title',
        description='This is the old complaint description',
        category='road',
        location='Dhaka',
        priority='low',
        status='pending'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.put(
        f'/complaints/update/{complaint.id}',
        headers={'Authorization': f'Bearer {user_token}'},
        json={
            'title': 'Updated Title',
            'priority': 'high'
        }
    )

    assert response.status_code == 200
    assert response.json()['message'] == 'Complaint updated successfully'


def test_cannot_update_resolved_complaint(client, normal_user, user_token, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Resolved Complaint',
        description='This complaint is already resolved',
        category='road',
        location='Dhaka',
        priority='medium',
        status='resolved'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.put(
        f'/complaints/update/{complaint.id}',
        headers={'Authorization': f'Bearer {user_token}'},
        json={'title': 'Trying to Update'}
    )

    assert response.status_code == 400


def test_delete_complaint(client, normal_user, user_token, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Delete Complaint',
        description='This complaint will be deleted',
        category='garbage',
        location='Dhaka',
        priority='low',
        status='pending'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.delete(
        f'/complaints/delete/{complaint.id}',
        headers={'Authorization': f'Bearer {user_token}'}
    )

    assert response.status_code == 200
    assert response.json()['message'] == 'Complaint deleted successfully'


def test_cannot_delete_resolved_complaint(client, normal_user, user_token, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Resolved Complaint',
        description='This complaint cannot be deleted',
        category='water',
        location='Dhaka',
        priority='medium',
        status='resolved'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.delete(
        f'/complaints/delete/{complaint.id}',
        headers={'Authorization': f'Bearer {user_token}'}
    )

    assert response.status_code == 400


