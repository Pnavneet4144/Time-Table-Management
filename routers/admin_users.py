from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
import models
import auth

router = APIRouter(prefix="/admin", tags=["admin-users"])


class ResetPasswordRequest(BaseModel):
    student_id: int
    new_password: str


class ChangeMyPasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/reset-student-password")
def reset_student_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_admin)
):
    student = db.query(models.User).filter(
        models.User.id == request.student_id,
        models.User.role == "student"
    ).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    student.password_hash = auth.get_password_hash(request.new_password)
    db.commit()
    return {"message": f"Password reset successfully for student '{student.username}'"}


@router.post("/change-my-password")
def change_my_password(
    request: ChangeMyPasswordRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    if not auth.verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    if request.old_password == request.new_password:
        raise HTTPException(status_code=400, detail="New password must be different from old password")
    current_user.password_hash = auth.get_password_hash(request.new_password)
    db.commit()
    return {"message": "Password changed successfully. Please login again."}