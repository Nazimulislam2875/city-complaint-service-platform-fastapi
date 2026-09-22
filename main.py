from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Annotated, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
import models
from models import Users, Complaints
from database import engine, SessionLocal
from router import auth, admin
from router.auth import get_current_user

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title='City Complaint & Service Request Management Platform',
    version='1.0.0'
)

origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

models.Base.metadata.create_all(bind=engine)
app.include_router(auth.router)
app.include_router(admin.router)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]


class ComplaintCreate(BaseModel):
    title: str = Field(min_length=3, max_length=100)
    description: str = Field(min_length=10, max_length=1000)
    category: Literal['road', 'water', 'electricity', 'garbage', 'drainage', 'street_light', 'traffic', 'internet', 'other']
    location: str = Field(min_length=3, max_length=200)
    priority: Literal['low', 'medium', 'high', 'urgent'] = 'medium'


class ComplaintUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=100)
    description: Optional[str] = Field(default=None, min_length=10, max_length=1000)
    category: Optional[Literal['road', 'water', 'electricity', 'garbage', 'drainage', 'street_light', 'traffic', 'internet', 'other']] = None
    location: Optional[str] = Field(default=None, min_length=3, max_length=200)
    priority: Optional[Literal['low', 'medium', 'high', 'urgent']] = None


@app.post('/complaints/create')
def create_complaint(user: user_dependency, db: db_dependency, complaint: ComplaintCreate):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    complaint_model = Complaints(
        user_id=user.get('id'),
        title=complaint.title,
        description=complaint.description,
        category=complaint.category,
        location=complaint.location,
        priority=complaint.priority,
        status='pending'
    )

    db.add(complaint_model)
    db.commit()
    db.refresh(complaint_model)

    return JSONResponse(
        status_code=201,
        content={'message': 'Complaint submitted successfully', 'complaint_id': complaint_model.id}
    )


@app.get('/complaints/my')
def get_my_complaints(user: user_dependency, db: db_dependency, search: Optional[str] = Query(default=None), category: Optional[str] = Query(default=None), status: Optional[Literal['pending', 'resolved', 'rejected']] = Query(default=None), sort: str = Query(default='newest'), page: int = Query(default=1, ge=1), page_size: int = Query(default=10, ge=1, le=100)):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    query = db.query(Complaints).filter(Complaints.user_id == user.get('id'))

    if search:
        query = query.filter(Complaints.title.ilike(f'%{search}%'))

    if category:
        query = query.filter(Complaints.category == category)

    if status:
        query = query.filter(Complaints.status == status)

    if sort == 'newest':
        query = query.order_by(Complaints.created_at.desc())
    elif sort == 'oldest':
        query = query.order_by(Complaints.created_at.asc())
    elif sort == 'alphabetical':
        query = query.order_by(Complaints.title.asc())
    else:
        raise HTTPException(status_code=400, detail='Invalid sort option')

    total = query.count()
    complaints = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = (total + page_size - 1) // page_size

    return {
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'complaints': complaints
    }


@app.get('/complaints/{complaint_id}')
def get_specific_complaint(user: user_dependency, db: db_dependency, complaint_id: int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    complaint = db.query(Complaints).filter(Complaints.id == complaint_id).first()
    if complaint is None:
        raise HTTPException(status_code=404, detail='Complaint not found')

    if complaint.user_id != user.get('id') and user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail='Access denied')

    return complaint


@app.put('/complaints/update/{complaint_id}')
def update_complaint(user: user_dependency, db: db_dependency, complaint_id: int, update_data: ComplaintUpdate):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    complaint = db.query(Complaints).filter(Complaints.id == complaint_id).first()
    if complaint is None:
        raise HTTPException(status_code=404, detail='Complaint not found')

    if complaint.user_id != user.get('id'):
        raise HTTPException(status_code=403, detail='Access denied')

    if complaint.status != 'pending':
        raise HTTPException(status_code=400, detail='Only pending complaints can be updated')

    data = update_data.model_dump(exclude_unset=True)

    for key, value in data.items():
        setattr(complaint, key, value)

    complaint.updated_at = datetime.now()
    db.commit()

    return {'message': 'Complaint updated successfully'}


@app.delete('/complaints/delete/{complaint_id}')
def delete_complaint(user: user_dependency, db: db_dependency, complaint_id: int):

    if user is None:
        raise HTTPException(status_code=401, detail='Failed Authentication')

    complaint = db.query(Complaints).filter(Complaints.id == complaint_id).first()
    if complaint is None:
        raise HTTPException(status_code=404, detail='Complaint not found')

    if complaint.user_id != user.get('id'):
        raise HTTPException(status_code=403, detail='Access denied')

    if complaint.status != 'pending':
        raise HTTPException(status_code=400, detail='Only pending complaints can be deleted')

    db.delete(complaint)
    db.commit()

    return {'message': 'Complaint deleted successfully'}