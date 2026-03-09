from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from database import get_db
import models
import schemas
import auth

router = APIRouter(prefix="/admin/feedback", tags=["feedback"])


@router.post("/form", response_model=schemas.FeedbackFormOut, status_code=status.HTTP_201_CREATED)
def create_feedback_form(
    form_data: schemas.FeedbackFormCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    db_form = models.FeedbackForm(
        title=form_data.title,
        created_by_admin_id=current_user.id
    )
    db.add(db_form)
    db.flush()

    for q in form_data.questions:
        db_question = models.FeedbackQuestion(
            form_id=db_form.id,
            question_text=q.question_text,
            question_type=q.question_type,
            options=json.dumps(q.options) if q.options else None
        )
        db.add(db_question)

    db.commit()
    db.refresh(db_form)
    return _form_to_out(db_form)


@router.post("/form/{form_id}/questions", response_model=schemas.FeedbackQuestionOut, status_code=status.HTTP_201_CREATED)
def add_question_to_form(
    form_id: int,
    question: schemas.FeedbackQuestionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    form = db.query(models.FeedbackForm).filter(models.FeedbackForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    db_question = models.FeedbackQuestion(
        form_id=form_id,
        question_text=question.question_text,
        question_type=question.question_type,
        options=json.dumps(question.options) if question.options else None
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return schemas.FeedbackQuestionOut.from_orm_model(db_question)


@router.get("/forms", response_model=List[schemas.FeedbackFormOut])
def get_feedback_forms(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    forms = db.query(models.FeedbackForm).all()
    return [_form_to_out(f) for f in forms]


@router.post("/form/{form_id}/share", status_code=status.HTTP_200_OK)
def share_form_to_students(
    form_id: int,
    share_request: schemas.ShareFormRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    form = db.query(models.FeedbackForm).filter(models.FeedbackForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    assigned = []
    for student_id in share_request.student_ids:
        student = db.query(models.User).filter(
            models.User.id == student_id,
            models.User.role == "student"
        ).first()
        if not student:
            continue
        existing = db.query(models.FeedbackAssignment).filter(
            models.FeedbackAssignment.form_id == form_id,
            models.FeedbackAssignment.student_id == student_id
        ).first()
        if not existing:
            assignment = models.FeedbackAssignment(form_id=form_id, student_id=student_id)
            db.add(assignment)
            assigned.append(student_id)

    form.is_shared = True
    db.commit()
    return {"message": f"Form shared to {len(assigned)} student(s)", "student_ids": assigned}


@router.get("/responses/{form_id}")
def get_form_responses(
    form_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    form = db.query(models.FeedbackForm).filter(models.FeedbackForm.id == form_id).first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    responses = db.query(models.FeedbackResponse).filter(
        models.FeedbackResponse.form_id == form_id
    ).all()
    return _aggregate_responses(responses, db)


@router.get("/responses/{form_id}/student/{student_id}")
def get_student_response(
    form_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    responses = db.query(models.FeedbackResponse).filter(
        models.FeedbackResponse.form_id == form_id,
        models.FeedbackResponse.student_id == student_id
    ).all()
    if not responses:
        raise HTTPException(status_code=404, detail="No responses found for this student")
    return _aggregate_responses(responses, db)


@router.get("/students")
def get_all_students(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    students = db.query(models.User).filter(models.User.role == "student").all()
    return [{"id": s.id, "username": s.username, "email": s.email} for s in students]


def _form_to_out(form: models.FeedbackForm) -> schemas.FeedbackFormOut:
    questions = [schemas.FeedbackQuestionOut.from_orm_model(q) for q in form.questions]
    return schemas.FeedbackFormOut(
        id=form.id,
        title=form.title,
        created_by_admin_id=form.created_by_admin_id,
        created_at=form.created_at,
        is_shared=form.is_shared,
        questions=questions
    )


def _aggregate_responses(responses, db):
    result = []
    for r in responses:
        student = db.query(models.User).filter(models.User.id == r.student_id).first()
        question = db.query(models.FeedbackQuestion).filter(models.FeedbackQuestion.id == r.question_id).first()
        result.append({
            "response_id": r.id,
            "student_id": r.student_id,
            "student_username": student.username if student else "Unknown",
            "question_id": r.question_id,
            "question_text": question.question_text if question else "Unknown",
            "answer": r.answer,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None
        })
    return result