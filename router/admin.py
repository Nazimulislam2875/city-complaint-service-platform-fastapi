from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, cast, String, desc, asc, case
from datetime import date, datetime, timedelta
from typing import Annotated, Optional, Literal
from database import SessionLocal
from models import Users, Complaints
from router.auth import get_current_user


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class ComplaintStatusUpdate(BaseModel):
    status: Literal['resolved', 'rejected']


def check_admin(user):

    if user is None or user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Admin access required')


@router.get('/admin/complaints')
def get_all_complaints(
    user: user_dependency,
    db: db_dependency,
    search: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    status: Optional[Literal['pending', 'resolved', 'rejected']] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    sort: str = Query(default='newest'),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100)
):
    check_admin(user)

    query = db.query(Complaints, Users).join(
        Users,
        Complaints.user_id == Users.id
    )

    if search:
        search_term = f'%{search}%'

        query = query.filter(
            or_(
                Complaints.title.ilike(search_term),
                Users.firstname.ilike(search_term),
                Users.lastname.ilike(search_term),
                Users.username.ilike(search_term),
                cast(Complaints.id, String).ilike(search_term)
            )
        )

    if category:
        query = query.filter(Complaints.category == category)

    if status:
        query = query.filter(Complaints.status == status)

    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query = query.filter(Complaints.created_at >= start_datetime)

    if end_date:
        end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time())
        query = query.filter(Complaints.created_at < end_datetime)

    if sort == 'newest':
        query = query.order_by(desc(Complaints.created_at))

    elif sort == 'oldest':
        query = query.order_by(asc(Complaints.created_at))

    elif sort == 'alphabetical':
        query = query.order_by(asc(Complaints.title))

    elif sort == 'priority':
        priority_order = case(
            (Complaints.priority == 'urgent', 1),
            (Complaints.priority == 'high', 2),
            (Complaints.priority == 'medium', 3),
            (Complaints.priority == 'low', 4),
            else_=5
        )

        query = query.order_by(priority_order)

    else:
        raise HTTPException(status_code=400, detail='Invalid sort option')

    total = query.count()

    complaints = query.offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    result = []

    for complaint, user_data in complaints:
        result.append({
            'id': complaint.id,
            'user_id': complaint.user_id,
            'username': user_data.username,
            'user_name': f'{user_data.firstname} {user_data.lastname}',
            'title': complaint.title,
            'description': complaint.description,
            'category': complaint.category,
            'location': complaint.location,
            'priority': complaint.priority,
            'status': complaint.status,
            'created_at': complaint.created_at,
            'updated_at': complaint.updated_at
        })

    total_pages = (total + page_size - 1) // page_size

    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'complaints': result
    }


@router.get('/admin/complaints/{complaint_id}')
def get_complaint_details(user: user_dependency, db: db_dependency, complaint_id: int):

    check_admin(user)

    result = db.query(Complaints, Users).join(
        Users,
        Complaints.user_id == Users.id
    ).filter(
        Complaints.id == complaint_id
    ).first()

    if result is None:
        raise HTTPException(status_code=404, detail='Complaint not found')

    complaint, user_data = result

    return {
        'id': complaint.id,
        'user_id': complaint.user_id,
        'username': user_data.username,
        'user_name': f'{user_data.firstname} {user_data.lastname}',
        'email': user_data.email,
        'title': complaint.title,
        'description': complaint.description,
        'category': complaint.category,
        'location': complaint.location,
        'priority': complaint.priority,
        'status': complaint.status,
        'created_at': complaint.created_at,
        'updated_at': complaint.updated_at
    }


@router.patch('/admin/complaints/{complaint_id}/status')
def update_complaint_status(user: user_dependency, db: db_dependency, complaint_id: int, status_data: ComplaintStatusUpdate):

    check_admin(user)

    complaint = db.query(Complaints).filter(
        Complaints.id == complaint_id
    ).first()

    if complaint is None:
        raise HTTPException(status_code=404, detail='Complaint not found')

    if complaint.status != 'pending':
        raise HTTPException(
            status_code=400,
            detail='Only pending complaints can be reviewed'
        )

    complaint.status = status_data.status
    complaint.updated_at = datetime.now()

    db.commit()

    return {
        'message': f'Complaint {status_data.status} successfully'
    }


@router.delete('/admin/complaints/{complaint_id}')
def delete_complaint(user: user_dependency, db: db_dependency, complaint_id: int):

    check_admin(user)

    complaint = db.query(Complaints).filter(
        Complaints.id == complaint_id
    ).first()

    if complaint is None:
        raise HTTPException(status_code=404, detail='Complaint not found')

    db.delete(complaint)
    db.commit()

    return {
        'message': 'Complaint deleted successfully'
    }