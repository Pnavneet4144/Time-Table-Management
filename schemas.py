from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any, Dict
from datetime import datetime


class UserCreate(BaseModel):
    username: str
    password: str
    email: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    email: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


# ── Teacher ───────────────────────────────────────────────────────────
class UnavailableSlot(BaseModel):
    day: str
    slot: str  # e.g. "09:30|10:30"


class TeacherCreate(BaseModel):
    name: str
    email: Optional[str] = None
    unavailable_slots: Optional[List[UnavailableSlot]] = []


class TeacherUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    unavailable_slots: Optional[List[UnavailableSlot]] = None


class TeacherOut(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    unavailable_slots: Optional[List[UnavailableSlot]] = []

    class Config:
        from_attributes = True


# ── Subject ───────────────────────────────────────────────────────────
class SubjectCreate(BaseModel):
    name: str
    code: str
    coordinator_name: str
    teacher_id: Optional[int] = None
    lectures_per_week: Optional[int] = 3
    is_lab: Optional[bool] = False
    lab_duration: Optional[int] = 2


class SubjectOut(BaseModel):
    id: int
    name: str
    code: str
    coordinator_name: str
    teacher_id: Optional[int] = None
    lectures_per_week: int = 3
    is_lab: bool = False
    lab_duration: int = 2
    teacher: Optional[TeacherOut] = None

    class Config:
        from_attributes = True


# ── Room ──────────────────────────────────────────────────────────────
class RoomCreate(BaseModel):
    room_number: str
    capacity: int


class RoomOut(BaseModel):
    id: int
    room_number: str
    capacity: int

    class Config:
        from_attributes = True


# ── Timetable ─────────────────────────────────────────────────────────
class TimetableEntryCreate(BaseModel):
    subject_id: int
    room_id: int
    day_of_week: str
    start_time: str
    end_time: str
    semester: str
    section: str


class TimetableEntryOut(BaseModel):
    id: int
    subject_id: int
    room_id: int
    day_of_week: str
    start_time: str
    end_time: str
    semester: str
    section: str
    subject: Optional[SubjectOut] = None
    room: Optional[RoomOut] = None

    class Config:
        from_attributes = True


# ── Auto-Generate ─────────────────────────────────────────────────────
class AutoGenerateRequest(BaseModel):
    semester: str
    section: str
    days: List[str] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    time_slots: Optional[List[str]] = None  # e.g. ["09:30|10:30", ...]; None = use defaults
    subject_ids: Optional[List[int]] = None  # None = use all subjects


class AutoGenerateEntry(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    room_id: int
    room_number: str
    teacher_name: str
    day_of_week: str
    start_time: str
    end_time: str


class AutoGenerateResponse(BaseModel):
    success: bool
    entries: List[AutoGenerateEntry] = []
    warnings: List[str] = []
    total_placed: int = 0
    total_required: int = 0


class FeedbackQuestionCreate(BaseModel):
    question_text: str
    question_type: str
    options: Optional[List[str]] = None


class FeedbackQuestionOut(BaseModel):
    id: int
    form_id: int
    question_text: str
    question_type: str
    options: Optional[List[str]] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_model(cls, q):
        return cls(
            id=q.id,
            form_id=q.form_id,
            question_text=q.question_text,
            question_type=q.question_type,
            options=q.get_options() if q.options else None
        )


class FeedbackFormCreate(BaseModel):
    title: str
    questions: Optional[List[FeedbackQuestionCreate]] = []


class FeedbackFormOut(BaseModel):
    id: int
    title: str
    created_by_admin_id: int
    created_at: Optional[datetime] = None
    is_shared: bool
    questions: Optional[List[FeedbackQuestionOut]] = []

    class Config:
        from_attributes = True


class ShareFormRequest(BaseModel):
    student_ids: List[int]


class FeedbackAnswerCreate(BaseModel):
    question_id: int
    answer: str


class FeedbackSubmission(BaseModel):
    answers: List[FeedbackAnswerCreate]


class FeedbackResponseOut(BaseModel):
    id: int
    form_id: int
    student_id: int
    question_id: int
    answer: str
    submitted_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FeedbackAssignmentOut(BaseModel):
    id: int
    form_id: int
    student_id: int
    assigned_at: Optional[datetime] = None
    is_completed: bool
    form: Optional[FeedbackFormOut] = None

    class Config:
        from_attributes = True