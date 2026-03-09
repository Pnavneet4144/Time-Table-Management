from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
import auth
from utils.pdf_generator import generate_timetable_pdf

router = APIRouter(prefix="/student", tags=["student"])


@router.get("/timetable/pdf")
def download_timetable_pdf(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_student)
):
    entries = db.query(models.TimetableEntry).all()
    pdf_buffer = generate_timetable_pdf(entries)
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=my_timetable.pdf"}
    )


@router.get("/timetable")
def get_timetable(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_student)
):
    entries = db.query(models.TimetableEntry).all()
    result = []
    for e in entries:
        subject = db.query(models.Subject).filter(models.Subject.id == e.subject_id).first()
        room = db.query(models.Room).filter(models.Room.id == e.room_id).first()
        result.append({
            "id": e.id,
            "day_of_week": e.day_of_week,
            "start_time": e.start_time,
            "end_time": e.end_time,
            "semester": e.semester,
            "section": e.section,
            "subject_name": subject.name if subject else "",
            "subject_code": subject.code if subject else "",
            "coordinator_name": subject.coordinator_name if subject else "",
            "room_number": room.room_number if room else ""
        })
    return result


@router.get("/feedback/forms")
def get_assigned_forms(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_student)
):
    assignments = db.query(models.FeedbackAssignment).filter(
        models.FeedbackAssignment.student_id == current_user.id
    ).all()
    result = []
    for assignment in assignments:
        form = db.query(models.FeedbackForm).filter(
            models.FeedbackForm.id == assignment.form_id
        ).first()
        if not form:
            continue
        questions = []
        for q in form.questions:
            questions.append({
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": q.get_options() if q.options else []
            })
        result.append({
            "assignment_id": assignment.id,
            "form_id": form.id,
            "form_title": form.title,
            "assigned_at": assignment.assigned_at.isoformat() if assignment.assigned_at else None,
            "is_completed": assignment.is_completed,
            "questions": questions
        })
    return result


@router.post("/feedback/submit/{form_id}", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    form_id: int,
    submission: schemas.FeedbackSubmission,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_student)
):
    assignment = db.query(models.FeedbackAssignment).filter(
        models.FeedbackAssignment.form_id == form_id,
        models.FeedbackAssignment.student_id == current_user.id
    ).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned to this form")
    if assignment.is_completed:
        raise HTTPException(status_code=400, detail="You have already submitted this form")

    form = db.query(models.FeedbackForm).filter(models.FeedbackForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    valid_question_ids = {q.id for q in form.questions}
    for answer in submission.answers:
        if answer.question_id not in valid_question_ids:
            raise HTTPException(status_code=400, detail=f"Question {answer.question_id} not in this form")
        response = models.FeedbackResponse(
            form_id=form_id,
            student_id=current_user.id,
            question_id=answer.question_id,
            answer=answer.answer
        )
        db.add(response)

    assignment.is_completed = True
    db.commit()
    return {"message": "Feedback submitted successfully"}