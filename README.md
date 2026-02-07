# ProctorGuard Backend (Flask)

A Flask backend for an online exam proctoring system. It provides REST APIs for students, exams, alerts, and submissions, plus a minimal admin UI rendered with Jinja templates. Data is stored in a local SQLite database.

## What this backend can do

- Create and list students, exams, alerts, and submissions.
- Persist all data in SQLite with basic relational links.
- Serve a small admin UI at /ui to view and manage records.
- Allow a separate frontend to connect via CORS to /api endpoints.
- Provide /api/analyze-frame with basic webcam frame checks.

## Project structure

```
backend/
  app.py                # Flask app, routes, and server entry point
  config.py             # Configuration values and env overrides
  models.py             # SQLite helpers and data access methods
  requirements.txt      # Python dependencies
  run.bat               # Windows CMD startup helper
  run.ps1               # Windows PowerShell startup helper
  database.db           # SQLite database file (created on first run)
  static/
    styles.css          # UI styles for templates
  templates/
    base.html           # Base layout for UI pages
    dashboard.html      # Admin dashboard UI
    students.html       # Students UI
    exams.html          # Exams UI
    alerts.html         # Alerts UI
  __pycache__/          # Python bytecode cache
```

## How it works (high level)

- On startup the app initializes the SQLite database if it does not exist.
- The REST API lives under /api and returns JSON.
- A simple admin UI lives under /ui and uses server-side rendering.
- CORS is enabled for allowed frontend origins so a separate frontend can call /api.

## Requirements

- Python 3.9+ recommended
- Windows, macOS, or Linux

## Setup and run

### 1) Create a virtual environment

```bash
python -m venv .venv
```

### 2) Activate the environment

PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

CMD:
```bat
.venv\Scripts\activate.bat
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Start the server

```bash
python app.py
```

Or use the helper scripts:

```bat
run.bat
```

```powershell
.\run.ps1
```

The server listens on the host and port defined in config.py (default 0.0.0.0:5000).

## Configuration

All config values live in config.py and can be overridden by environment variables.

Key settings:

- FLASK_DEBUG: enable debug mode (true/false).
- FLASK_TESTING: enable testing mode (true/false).
- SECRET_KEY: Flask secret key.
- LOG_LEVEL: logging level (INFO, DEBUG, etc).
- CORS_ALLOWED_ORIGINS: list of allowed frontend origins.
- FLASK_HOST / FLASK_PORT: server bind host and port.

Defaults are set for local dev and can be changed for production.

## Database

SQLite database file: database.db (created on first run).

Tables:

- students: id, name, email, exam_id, created_at
- exams: id, name, code, duration, total_questions, created_at
- alerts: id, student_id, exam_id, reason, severity, timestamp
- submissions: id, student_id, exam_id, answers (JSON), score, flagged, submitted_at
- violation_screenshots: id, alert_id, student_id, exam_id, image_data (base64), violation_type, timestamp

Foreign keys link alerts and submissions to students and exams.

## API reference

Base URL: http://localhost:5000

### Health

- GET /
- GET /api/health

### Students

- POST /api/students
  - Body: { "name": "...", "email": "...", "exam_id": "..." }
- GET /api/students
- GET /api/students/<student_id>

### Exams

- POST /api/exams
  - Body: { "name": "...", "code": "EXAM-001", "duration": 60, "total_questions": 40 }
- GET /api/exams
- GET /api/exams/<exam_id>

### Alerts

- POST /api/alerts
  - Body: { "student_id": 1, "exam_id": 1, "reason": "...", "severity": "warning" }
- GET /api/alerts
- GET /api/alerts/student/<student_id>

### Submissions

- POST /api/submissions
  - Body: { "student_id": 1, "exam_id": 1, "answers": {"q1":"A"}, "score": 10, "flagged": false }
- POST /api/submit-exam
  - Body: { "studentId": 1, "examId": "EXAM-001", "answers": {"q1":"A"}, "score": 10, "flagged": true }
- GET /api/submissions
- GET /api/submissions/student/<student_id>

### Frame analysis

- POST /api/analyze-frame
  - Body: { "image": "...", "examId": "EXAM-001", "studentId": 1 }

### Violations

- POST /api/log-violation
  - Body: { "student_id": 1, "exam_id": "EXAM-001", "violation_type": "left_fullscreen" }
- GET /api/violations-with-screenshots

All responses use a consistent JSON shape with status and data fields. Errors return status: "error" and an HTTP error code.

## Admin UI

These routes return HTML using templates and styles in static/.

- GET /ui (dashboard)
- GET/POST /ui/students
- GET/POST /ui/exams
- GET /ui/alerts

The UI is useful for quick manual testing without a separate frontend.

## Connecting a frontend

1) Update CORS_ALLOWED_ORIGINS in config.py to include your frontend URL.
  - Example: http://localhost:3000 or http://localhost:5173

2) Use the API base URL in your frontend:
   - http://localhost:5000/api

3) Make requests from the frontend using fetch or axios.

Optional: append ?raw=1 to API requests to receive raw arrays/objects without the {status,count,data} wrapper.

## Deploy to Render (free)

1) Push this backend to GitHub.
2) In Render, create a new Web Service and connect the repo.
3) Set:
  - Build command: pip install -r requirements.txt
  - Start command: python app.py
4) Environment variables:
  - FLASK_HOST=0.0.0.0
  - FLASK_PORT=10000 (or set PORT and FLASK_PORT will use it)
  - CORS_ALLOWED_ORIGINS=["https://your-frontend.vercel.app"]
5) Deploy and note the backend URL (for example https://your-app.onrender.com).

Then set your frontend Vercel env var:

VITE_API_BASE_URL=https://your-app.onrender.com/api

Example fetch (create student):

```javascript
fetch("http://localhost:5000/api/students", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    name: "Jane Doe",
    email: "jane@example.com",
    exam_id: "EXAM-001"
  })
})
  .then((res) => res.json())
  .then((data) => console.log(data));
```

If your frontend runs on another port or domain, add it to CORS_ALLOWED_ORIGINS.

## Typical usage flow

1) Create an exam.
2) Create a student and link to the exam if needed.
3) Record alerts during monitoring.
4) Submit answers and score when the exam ends.
5) Use /api lists or /ui dashboard to review data.

## Notes and limitations

- SQLite is suitable for local development and small deployments.
- Authentication is not implemented; secure the API before production use.
- File uploads and video streams are not implemented in this backend.

## Troubleshooting

- If you see CORS errors, verify the frontend origin is in CORS_ALLOWED_ORIGINS.
- If database tables are missing, restart the server to re-run initialization.
- If the server will not start, check that the venv is active and dependencies are installed.
