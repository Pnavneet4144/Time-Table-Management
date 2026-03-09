from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
import os

from database import engine
import models
from routers import auth_router, timetable, feedback, student, admin_users

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="College Timetable Management System",
    description="API for managing college timetables and student feedback",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(timetable.router)
app.include_router(feedback.router)
app.include_router(student.router)
app.include_router(admin_users.router)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "College Timetable Management System API", "docs": "/docs"}


@app.get("/login")
def serve_login():
    return FileResponse(os.path.join(static_dir, "login.html"))


@app.get("/admin-dashboard")
def serve_admin():
    return FileResponse(os.path.join(static_dir, "admin-dashboard.html"))


@app.get("/student-dashboard")
def serve_student():
    return FileResponse(os.path.join(static_dir, "student-dashboard.html"))


@app.get("/health")
def health_check():
    return {"status": "ok"}