# College Timetable Management System — Setup Guide

## Prerequisites
- Python 3.10+
- pip

## Installation

```bash
# Clone / navigate to project directory
cd project

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

## Run the Application

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Access

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Landing page |
| http://localhost:8000/static/login.html | Login / Register |
| http://localhost:8000/static/admin-dashboard.html | Admin dashboard |
| http://localhost:8000/static/student-dashboard.html | Student dashboard |
| http://localhost:8000/docs | Interactive API docs (Swagger UI) |

## Quick Start Workflow

1. **Register an Admin account** via the Register tab on the login page (role: Admin)
2. **Login as Admin** → redirected to Admin Dashboard
3. **Add Subjects** under "Manage Subjects"
4. **Add Rooms** under "Manage Rooms"
5. **Build Timetable** under "Build Timetable"
6. **View Timetable** and download PDF
7. **Create a Feedback Form** with dynamic question builder
8. **Register a Student account** (new browser / incognito tab)
9. **Share Feedback** — select the form and student(s)
10. **Student Login** → fill feedback form → submit
11. **Admin → View Responses** — see all submitted feedback

## Project Structure

```
project/
├── main.py                  # FastAPI app entrypoint
├── database.py              # SQLAlchemy engine + session
├── models.py                # ORM table models
├── schemas.py               # Pydantic request/response schemas
├── auth.py                  # JWT authentication helpers
├── routers/
│   ├── auth_router.py       # /auth/register, /auth/login
│   ├── timetable.py         # /admin/subjects, /admin/rooms, /admin/timetable
│   ├── feedback.py          # /admin/feedback/*
│   └── student.py           # /student/*
├── utils/
│   └── pdf_generator.py     # ReportLab PDF timetable generator
├── static/
│   ├── index.html           # 5-section landing page
│   ├── login.html           # Login + Register
│   ├── admin-dashboard.html # Full admin UI
│   ├── student-dashboard.html # Student portal UI
│   ├── css/
│   │   ├── main.css         # Landing page + shared styles
│   │   ├── forms.css        # Auth forms styling
│   │   └── dashboard.css    # Dashboard UI
│   └── js/
│       ├── auth.js          # JWT helpers, API wrapper, toast notifications
│       ├── admin.js         # All admin dashboard logic
│       └── student.js       # All student dashboard logic
└── requirements.txt
```

## Notes

- SQLite database (`college_timetable.db`) is auto-created on first run
- JWT tokens expire after 24 hours
- Secret key in `auth.py` should be changed to a secure random value in production
- PDF generation uses ReportLab with landscape A4 layout
- All API endpoints protected with JWT; role-based access enforced per route
