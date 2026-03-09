from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import json


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    feedback_forms_created = relationship("FeedbackForm", back_populates="creator")
    feedback_assignments = relationship("FeedbackAssignment", back_populates="student")
    feedback_responses = relationship("FeedbackResponse", back_populates="student")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, nullable=False)
    coordinator_name = Column(String, nullable=False)

    timetable_entries = relationship("TimetableEntry", back_populates="subject")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String, unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)

    timetable_entries = relationship("TimetableEntry", back_populates="room")


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    day_of_week = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    semester = Column(String, nullable=False)
    section = Column(String, nullable=False)

    subject = relationship("Subject", back_populates="timetable_entries")
    room = relationship("Room", back_populates="timetable_entries")


class FeedbackForm(Base):
    __tablename__ = "feedback_forms"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    created_by_admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    is_shared = Column(Boolean, default=False)

    creator = relationship("User", back_populates="feedback_forms_created")
    questions = relationship("FeedbackQuestion", back_populates="form", cascade="all, delete-orphan")
    assignments = relationship("FeedbackAssignment", back_populates="form", cascade="all, delete-orphan")
    responses = relationship("FeedbackResponse", back_populates="form", cascade="all, delete-orphan")


class FeedbackQuestion(Base):
    __tablename__ = "feedback_questions"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("feedback_forms.id"), nullable=False)
    question_text = Column(String, nullable=False)
    question_type = Column(String, nullable=False)
    options = Column(Text, nullable=True)

    form = relationship("FeedbackForm", back_populates="questions")
    responses = relationship("FeedbackResponse", back_populates="question")

    def get_options(self):
        if self.options:
            return json.loads(self.options)
        return []

    def set_options(self, options_list):
        self.options = json.dumps(options_list)


class FeedbackAssignment(Base):
    __tablename__ = "feedback_assignments"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("feedback_forms.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_at = Column(DateTime, server_default=func.now())
    is_completed = Column(Boolean, default=False)

    form = relationship("FeedbackForm", back_populates="assignments")
    student = relationship("User", back_populates="feedback_assignments")


class FeedbackResponse(Base):
    __tablename__ = "feedback_responses"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("feedback_forms.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("feedback_questions.id"), nullable=False)
    answer = Column(Text, nullable=False)
    submitted_at = Column(DateTime, server_default=func.now())

    form = relationship("FeedbackForm", back_populates="responses")
    student = relationship("User", back_populates="feedback_responses")
    question = relationship("FeedbackQuestion", back_populates="responses")
