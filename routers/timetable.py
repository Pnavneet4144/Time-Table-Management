from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import base64
import json
from database import get_db
import models, schemas, auth
from utils.pdf_generator import generate_timetable_pdf
from scheduler import run_scheduler, DEFAULT_TIME_SLOTS, DEFAULT_DAYS

router = APIRouter(prefix="/admin", tags=["timetable"])

# ── Teachers ──────────────────────────────────────────────────────────
@router.post("/teachers", response_model=schemas.TeacherOut, status_code=201)
def create_teacher(teacher: schemas.TeacherCreate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth.require_admin)):
    if teacher.email:
        existing = db.query(models.Teacher).filter(models.Teacher.email == teacher.email).first()
        if existing:
            raise HTTPException(400, "Teacher email already exists")
    obj = models.Teacher(
        name=teacher.name,
        email=teacher.email,
        unavailable_slots=json.dumps([s.dict() for s in (teacher.unavailable_slots or [])])
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return _teacher_to_out(obj)

@router.get("/teachers", response_model=List[schemas.TeacherOut])
def get_teachers(db: Session = Depends(get_db),
                 current_user: models.User = Depends(auth.require_admin)):
    teachers = db.query(models.Teacher).all()
    return [_teacher_to_out(t) for t in teachers]

@router.put("/teachers/{teacher_id}", response_model=schemas.TeacherOut)
def update_teacher(teacher_id: int, teacher: schemas.TeacherUpdate,
                   db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth.require_admin)):
    obj = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if not obj: raise HTTPException(404, "Teacher not found")
    if teacher.name is not None: obj.name = teacher.name
    if teacher.email is not None: obj.email = teacher.email
    if teacher.unavailable_slots is not None:
        obj.unavailable_slots = json.dumps([s.dict() for s in teacher.unavailable_slots])
    db.commit(); db.refresh(obj)
    return _teacher_to_out(obj)

@router.delete("/teachers/{teacher_id}", status_code=204)
def delete_teacher(teacher_id: int, db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth.require_admin)):
    obj = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if not obj: raise HTTPException(404, "Teacher not found")
    # Remove teacher_id from subjects
    db.query(models.Subject).filter(models.Subject.teacher_id == teacher_id).update(
        {models.Subject.teacher_id: None})
    db.delete(obj); db.commit()

def _teacher_to_out(t: models.Teacher) -> schemas.TeacherOut:
    """Convert Teacher model to TeacherOut schema with parsed unavailable_slots."""
    unavail = []
    if t.unavailable_slots:
        try:
            raw = json.loads(t.unavailable_slots)
            unavail = [schemas.UnavailableSlot(**s) for s in raw]
        except (json.JSONDecodeError, TypeError):
            pass
    return schemas.TeacherOut(
        id=t.id,
        name=t.name,
        email=t.email,
        unavailable_slots=unavail
    )


# ── Subjects ──────────────────────────────────────────────────────────
@router.post("/subjects", response_model=schemas.SubjectOut, status_code=201)
def create_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth.require_admin)):
    if db.query(models.Subject).filter(models.Subject.code == subject.code).first():
        raise HTTPException(400, "Subject code already exists")
    if subject.teacher_id:
        if not db.query(models.Teacher).filter(models.Teacher.id == subject.teacher_id).first():
            raise HTTPException(404, "Teacher not found")
    obj = models.Subject(**subject.dict())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.get("/subjects", response_model=List[schemas.SubjectOut])
def get_subjects(db: Session = Depends(get_db),
                 current_user: models.User = Depends(auth.require_admin)):
    return db.query(models.Subject).options(joinedload(models.Subject.teacher)).all()

@router.put("/subjects/{subject_id}", response_model=schemas.SubjectOut)
def update_subject(subject_id: int, subject: schemas.SubjectCreate,
                   db: Session = Depends(get_db),
                   current_user: models.User = Depends(auth.require_admin)):
    obj = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not obj: raise HTTPException(404, "Subject not found")
    if subject.teacher_id:
        if not db.query(models.Teacher).filter(models.Teacher.id == subject.teacher_id).first():
            raise HTTPException(404, "Teacher not found")
    for k, v in subject.dict().items(): setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj

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
def get_timetable(
    semester: Optional[str] = Query(None),
    section: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    query = db.query(models.TimetableEntry).options(
        joinedload(models.TimetableEntry.subject),
        joinedload(models.TimetableEntry.room)
    )
    if semester and semester != "all":
        query = query.filter(models.TimetableEntry.semester == semester)
    if section and section != "all":
        query = query.filter(models.TimetableEntry.section == section)
    return query.all()

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


# ── Auto-generate timetable ──────────────────────────────────────────
@router.post("/timetable/auto-generate", response_model=schemas.AutoGenerateResponse)
def auto_generate_timetable(
    request: schemas.AutoGenerateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    """
    Automatically generate a conflict-free timetable for the given
    semester and section. Replaces any existing entries for that
    semester + section.
    """
    # 1. Fetch subjects
    query = db.query(models.Subject).options(joinedload(models.Subject.teacher))
    if request.subject_ids:
        query = query.filter(models.Subject.id.in_(request.subject_ids))
    subjects = query.all()

    if not subjects:
        raise HTTPException(400, "No subjects found to schedule.")

    # 2. Fetch rooms
    rooms = db.query(models.Room).all()
    if not rooms:
        raise HTTPException(400, "No rooms available. Add rooms first.")

    # 3. Build subject data
    subjects_data = []
    for s in subjects:
        subjects_data.append({
            "id": s.id,
            "code": s.code,
            "name": s.name,
            "teacher_id": s.teacher_id,
            "teacher_name": s.teacher.name if s.teacher else s.coordinator_name,
            "lectures_per_week": s.lectures_per_week or 3,
            "is_lab": s.is_lab or False,
            "lab_duration": s.lab_duration or 2,
        })

    # 4. Build room data
    rooms_data = [{"id": r.id, "room_number": r.room_number, "capacity": r.capacity} for r in rooms]

    # 5. Build teacher unavailability
    teacher_unavailable = {}
    teacher_ids = set(s.teacher_id for s in subjects if s.teacher_id)
    for tid in teacher_ids:
        teacher = db.query(models.Teacher).filter(models.Teacher.id == tid).first()
        if teacher:
            teacher_unavailable[tid] = teacher.get_unavailable()

    # 6. Load existing entries from OTHER sections (for cross-section conflict detection)
    other_entries = db.query(models.TimetableEntry).options(
        joinedload(models.TimetableEntry.subject)
    ).filter(
        models.TimetableEntry.semester == request.semester,
        models.TimetableEntry.section != request.section
    ).all()

    existing_entries_data = []
    for e in other_entries:
        existing_entries_data.append({
            "day_of_week": e.day_of_week,
            "start_time": e.start_time,
            "end_time": e.end_time,
            "room_id": e.room_id,
            "teacher_id": e.subject.teacher_id if e.subject else None,
        })

    # 7. Determine time slots
    time_slots = request.time_slots or DEFAULT_TIME_SLOTS
    days = request.days or DEFAULT_DAYS

    # 8. Run scheduler
    result = run_scheduler(
        subjects_data=subjects_data,
        rooms_data=rooms_data,
        days=days,
        time_slots=time_slots,
        teacher_unavailable=teacher_unavailable,
        existing_entries=existing_entries_data,
    )

    if not result.entries:
        return schemas.AutoGenerateResponse(
            success=False,
            entries=[],
            warnings=result.warnings or ["Could not generate any timetable entries."],
            total_placed=0,
            total_required=result.total_required,
        )

    # 9. Delete existing entries for this semester + section
    db.query(models.TimetableEntry).filter(
        models.TimetableEntry.semester == request.semester,
        models.TimetableEntry.section == request.section
    ).delete(synchronize_session="fetch")

    # 10. Insert new entries
    response_entries = []
    for entry in result.entries:
        new_entry = models.TimetableEntry(
            subject_id=entry.subject.id,
            room_id=entry.room.id,
            day_of_week=entry.day,
            start_time=entry.start_time,
            end_time=entry.end_time,
            semester=request.semester,
            section=request.section,
        )
        db.add(new_entry)
        response_entries.append(schemas.AutoGenerateEntry(
            subject_id=entry.subject.id,
            subject_code=entry.subject.code,
            subject_name=entry.subject.name,
            room_id=entry.room.id,
            room_number=entry.room.room_number,
            teacher_name=entry.subject.teacher_name,
            day_of_week=entry.day,
            start_time=entry.start_time,
            end_time=entry.end_time,
        ))

    db.commit()

    return schemas.AutoGenerateResponse(
        success=result.success,
        entries=response_entries,
        warnings=result.warnings,
        total_placed=len(response_entries),
        total_required=result.total_required,
    )


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