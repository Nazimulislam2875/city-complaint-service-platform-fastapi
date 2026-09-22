def test_admin_complaints_empty(client, admin_user, admin_token):
    response = client.get(
        '/admin/complaints',
        headers={'Authorization': f'Bearer {admin_token}'}
    )

    assert response.status_code == 200
    assert response.json()['total'] == 0


def test_user_cannot_access_admin_complaints(client, normal_user, user_token):
    response = client.get(
        '/admin/complaints',
        headers={'Authorization': f'Bearer {user_token}'}
    )

    assert response.status_code == 403


def test_admin_complaint_details(client, admin_user, admin_token, normal_user, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Broken Road',
        description='The road is damaged',
        category='road',
        location='Dhaka',
        priority='high',
        status='pending'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.get(
        f'/admin/complaints/{complaint.id}',
        headers={'Authorization': f'Bearer {admin_token}'}
    )

    assert response.status_code == 200
    assert response.json()['title'] == 'Broken Road'
    assert response.json()['username'] == 'testuser'


def test_admin_resolve_complaint(client, admin_user, admin_token, normal_user, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Water Problem',
        description='No water supply',
        category='water',
        location='Dhaka',
        priority='medium',
        status='pending'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.patch(
        f'/admin/complaints/{complaint.id}/status',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'status': 'resolved'}
    )

    assert response.status_code == 200
    assert response.json()['message'] == 'Complaint resolved successfully'


def test_admin_reject_complaint(client, admin_user, admin_token, normal_user, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Fake Complaint',
        description='This complaint should be rejected',
        category='other',
        location='Dhaka',
        priority='low',
        status='pending'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.patch(
        f'/admin/complaints/{complaint.id}/status',
        headers={'Authorization': f'Bearer {admin_token}'},
        json={'status': 'rejected'}
    )

    assert response.status_code == 200
    assert response.json()['message'] == 'Complaint rejected successfully'


def test_user_cannot_change_complaint_status(client, normal_user, user_token, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Test Complaint',
        description='Testing user permission',
        category='road',
        location='Dhaka',
        priority='medium',
        status='pending'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.patch(
        f'/admin/complaints/{complaint.id}/status',
        headers={'Authorization': f'Bearer {user_token}'},
        json={'status': 'resolved'}
    )

    assert response.status_code == 403


def test_admin_delete_complaint(client, admin_user, admin_token, normal_user, db):
    from models import Complaints

    complaint = Complaints(
        user_id=normal_user.id,
        title='Delete Test',
        description='Testing admin delete',
        category='garbage',
        location='Dhaka',
        priority='low',
        status='pending'
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    response = client.delete(
        f'/admin/complaints/{complaint.id}',
        headers={'Authorization': f'Bearer {admin_token}'}
    )

    assert response.status_code == 200
    assert response.json()['message'] == 'Complaint deleted successfully'