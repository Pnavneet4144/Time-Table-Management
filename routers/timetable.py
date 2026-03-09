from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import base64
from database import get_db
import models, schemas, auth
from utils.pdf_generator import generate_timetable_pdf

router = APIRouter(prefix="/admin", tags=["timetable"])

# ── Subjects ──────────────────────────────────────────────────────────
@router.post("/subjects", response_model=schemas.SubjectOut, status_code=201)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth.require_admin)):
    if db.query(models.Subject).filter(models.Subject.code == subject.code).first():
        raise HTTPException(400, "Subject code already exists")
    obj = models.Subject(**subject.dict())
    db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/subjects", response_model=List[schemas.SubjectOut])
def get_subjects(db: Session = Depends(get_db),
                 current_user: models.User = Depends(auth.require_admin)):
    return db.query(models.Subject).all()

@router.put("/subjects/{subject_id}", response_model=schemas.SubjectOut)
def update_subject(subject_id: int, subject: schemas.SubjectCreate,
                   db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth.require_admin)):
    obj = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not obj: raise HTTPException(404, "Subject not found")
    for k, v in subject.dict().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@router.delete("/subjects/{subject_id}", status_code=204)
def delete_subject(subject_id: int, db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth.require_admin)):
    obj = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not obj: raise HTTPException(404, "Subject not found")
    db.delete(obj); db.commit()

# ── Rooms ─────────────────────────────────────────────────────────────
@router.post("/rooms", response_model=schemas.RoomOut, status_code=201)
def create_room(room: schemas.RoomCreate, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth.require_admin)):
    if db.query(models.Room).filter(models.Room.room_number == room.room_number).first():
        raise HTTPException(400, "Room number already exists")
    obj = models.Room(**room.dict())
    db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/rooms", response_model=List[schemas.RoomOut])
def get_rooms(db: Session = Depends(get_db),
              current_user: models.User = Depends(auth.require_admin)):
    return db.query(models.Room).all()

@router.delete("/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth.require_admin)):
    obj = db.query(models.Room).filter(models.Room.id == room_id).first()
    if not obj: raise HTTPException(404, "Room not found")
    db.delete(obj); db.commit()

# ── Timetable entries ─────────────────────────────────────────────────
@router.post("/timetable", response_model=schemas.TimetableEntryOut, status_code=201)
def create_timetable_entry(entry: schemas.TimetableEntryCreate,
                            db: Session = Depends(get_db),
                            current_user: models.User = Depends(auth.require_admin)):
    if not db.query(models.Subject).filter(models.Subject.id == entry.subject_id).first():
        raise HTTPException(404, "Subject not found")
    if not db.query(models.Room).filter(models.Room.id == entry.room_id).first():
        raise HTTPException(404, "Room not found")
    obj = models.TimetableEntry(**entry.dict())
    db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/timetable", response_model=List[schemas.TimetableEntryOut])
def get_timetable(db: Session = Depends(get_db),
                  current_user: models.User = Depends(auth.require_admin)):
    return db.query(models.TimetableEntry).all()

@router.put("/timetable/{entry_id}", response_model=schemas.TimetableEntryOut)
def update_timetable_entry(entry_id: int, entry: schemas.TimetableEntryCreate,
                            db: Session = Depends(get_db),
                            current_user: models.User = Depends(auth.require_admin)):
    obj = db.query(models.TimetableEntry).filter(models.TimetableEntry.id == entry_id).first()
    if not obj: raise HTTPException(404, "Entry not found")
    for k, v in entry.dict().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj); return obj

@router.delete("/timetable/{entry_id}", status_code=204)
def delete_timetable_entry(entry_id: int, db: Session = Depends(get_db),
                            current_user: models.User = Depends(auth.require_admin)):
    obj = db.query(models.TimetableEntry).filter(models.TimetableEntry.id == entry_id).first()
    if not obj: raise HTTPException(404, "Entry not found")
    db.delete(obj); db.commit()

# ── PDF download ──────────────────────────────────────────────────────
@router.post("/timetable/pdf")
async def download_timetable_pdf(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin),
    college_name: str     = Form(default="Indian Institute of Information Technology"),
    college_subtitle: str = Form(default="(An Institute of National Importance by an Act of Parliament)"),
    college_address: str  = Form(default="Gat No - 5 & 6, Vill - Nanoli-Tarf Chakan, PO \u2013 Talegaon, Tah \u2013 Maval, Dist - Pune, Maharashtra \u2013 410507"),
    semester_label: str   = Form(default="Even Semester, AY 2025-26"),
    section_label: str    = Form(default="Section B CSE"),
    location_label: str   = Form(default="LH8"),
    logo: Optional[UploadFile] = File(default=None)
):
    entries = db.query(models.TimetableEntry).all()
    logo_b64 = None
    if logo and logo.filename:
        raw = await logo.read()
        logo_b64 = base64.b64encode(raw).decode()
    pdf = generate_timetable_pdf(
        entries,
        college_name=college_name,
        college_subtitle=college_subtitle,
        college_address=college_address,
        semester_label=semester_label,
        section_label=section_label,
        location_label=location_label,
        logo_base64=logo_b64
    )
    return StreamingResponse(pdf, media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=timetable.pdf"})