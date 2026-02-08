# ProctorGuard — AI-Powered Online Exam Proctoring System

> **Developed by Abhinav Gupta**

ProctorGuard is a full-stack online exam proctoring application that uses **computer vision (OpenCV)** to monitor students in real time during online examinations. It detects cheating behaviors such as face absence, multiple faces in frame, tab switching, and fullscreen exits — then logs every violation with a timestamped screenshot as evidence. An admin dashboard gives examiners complete visibility into student activity, alerts, and submissions.

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [How ProctorGuard Solves It](#how-proctorguard-solves-it)
3. [Features](#features)
4. [Architecture Overview](#architecture-overview)
5. [Project Structure](#project-structure)
6. [How the Frontend Works](#how-the-frontend-works)
7. [How the Backend Works](#how-the-backend-works)
8. [How Frontend and Backend Are Connected](#how-frontend-and-backend-are-connected)
9. [How the Database Works](#how-the-database-works)
10. [How Violation Detection Works](#how-violation-detection-works)
11. [API Reference](#api-reference)
12. [Tech Stack](#tech-stack)
13. [Requirements](#requirements)
14. [Setup & Run](#setup--run)

---

## Problem Statement

Online examinations face a critical trust problem. Without physical supervision, students can:
- Look away from the screen to consult notes or another person.
- Have someone else sit in their place or assist them on-camera.
- Switch browser tabs to search for answers.
- Exit fullscreen mode to access other applications.
- Use a second device while the exam is running.

Traditional video-call proctoring requires **one human proctor per student**, which is expensive and unscalable. Institutions need an **automated, AI-driven** solution that can monitor hundreds of students simultaneously and flag suspicious activity in real time.

---

## How ProctorGuard Solves It

ProctorGuard eliminates the need for manual proctoring by running **continuous, automated checks** on every student's webcam feed during an exam:

| Problem | ProctorGuard Solution |
|---|---|
| Student looks away / leaves seat | **No-face detection** — flags a warning alert when no face is found in the webcam frame |
| Someone else joins / assists | **Multiple-face detection** — flags a critical alert when more than one face appears |
| Tab switching to search for answers | **Tab-switch & window-blur detection** — logs a critical violation the moment the student leaves the exam window |
| Exiting fullscreen | **Fullscreen-exit detection** — logs a critical violation when the student leaves fullscreen mode |
| Lack of evidence | **Screenshot capture** — every violation is saved with a compressed JPEG screenshot for review |
| No central monitoring | **Admin dashboard** — a real-time web UI shows all students, exams, alerts, and submissions in one place |

---

## Features

### Core Proctoring
- **Real-time face detection** using OpenCV Haar Cascade classifiers
- **No-face alert** (severity: warning) — triggered when the webcam cannot find a face
- **Multiple-face alert** (severity: critical) — triggered when two or more faces appear
- **Tab-switch detection** — logs when a student switches to another browser tab
- **Window-blur detection** — logs when the exam window loses focus
- **Fullscreen-exit detection** — logs when a student leaves fullscreen mode
- **Violation screenshots** — every violation is paired with a compressed Base64 JPEG image stored in the database

### Admin Dashboard (Server-Side UI)
- **Dashboard page** — at-a-glance counts of students, exams, and alerts
- **Students page** — add new students via a form, view all registered students in a table
- **Exams page** — create exams with name, code, duration, and question count; view all exams
- **Alerts page** — review all proctoring alerts with severity color-coding (amber for warning, red for critical)

### REST API
- Full CRUD endpoints for **Students**, **Exams**, **Alerts**, and **Submissions**
- **Frame analysis endpoint** (`POST /api/analyze-frame`) — accepts a Base64 webcam image and returns face-detection results
- **Violation logging endpoint** (`POST /api/log-violation`) — records non-frame violations (tab switch, fullscreen exit, etc.)
- **Violations with screenshots** (`GET /api/violations-with-screenshots`) — returns all violations joined with their screenshot evidence
- **Exam submission** (`POST /api/submit-exam`) — records student answers with an optional `flagged` status
- **Raw response mode** — append `?raw=1` to any endpoint to get unwrapped JSON without status/message wrappers
- CORS configured for multiple frontend origins

### Data & Storage
- **SQLite** database — zero-configuration, file-based, created automatically on first run
- **5 relational tables** with foreign key constraints enforced via `PRAGMA foreign_keys = ON`
- Automatic schema migration for backward compatibility (adds missing columns to existing databases)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT / BROWSER                         │
│                                                              │
│  ┌──────────────────┐     ┌──────────────────────────────┐  │
│  │  Admin UI (/ui)  │     │  Separate Frontend (React/   │  │
│  │  Server-rendered │     │  Next.js on localhost:3000   │  │
│  │  Jinja2 pages    │     │  or Vercel deployment)       │  │
│  └────────┬─────────┘     └──────────────┬───────────────┘  │
│           │ HTML forms                    │ JSON via CORS    │
└───────────┼──────────────────────────────┼──────────────────┘
            │                              │
            ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FLASK BACKEND (app.py)                     │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐  │
│  │  UI Routes     │  │  API Routes    │  │  Detection    │  │
│  │  /ui/*         │  │  /api/*        │  │  Module       │  │
│  │  render_template│  │  jsonify()     │  │  (OpenCV)     │  │
│  └────────┬───────┘  └────────┬───────┘  └───────┬───────┘  │
│           │                   │                   │          │
│           ▼                   ▼                   ▼          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              models.py (Data Access Layer)            │   │
│  │  init_database · add_student · add_exam · add_alert  │   │
│  │  add_submission · add_violation_screenshot · fetch_*  │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             │                                │
│                             ▼                                │
│                    ┌─────────────────┐                       │
│                    │   SQLite DB     │                       │
│                    │  database.db    │                       │
│                    └─────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
backend/
├── app.py                  # Flask application — all routes (API + UI), CORS, error handlers
├── config.py               # Configuration — DB path, CORS origins, server host/port, env overrides
├── detection.py            # Computer vision module — Haar Cascade face detection, image compression
├── models.py               # Data access layer — SQLite connection, schema init, CRUD functions
├── requirements.txt        # Python dependencies (Flask, flask-cors, opencv-python, etc.)
├── run.bat                 # One-click startup for Windows CMD
├── run.ps1                 # One-click startup for Windows PowerShell
├── database.db             # SQLite database file (auto-created on first run)
├── static/
│   └── styles.css          # Dark-themed CSS for the admin UI (glass-morphism, responsive grid)
├── templates/
│   ├── base.html           # Jinja2 base layout — top nav bar, page structure
│   ├── dashboard.html      # Dashboard — stat cards for students/exams/alerts
│   ├── students.html       # Students — add form + data table
│   ├── exams.html          # Exams — create form + data table
│   └── alerts.html         # Alerts — violation log table with severity coloring
└── __pycache__/            # Python bytecode cache (auto-generated)
```

---

## How the Frontend Works

The frontend is a **server-side rendered (SSR)** admin panel built with **Jinja2 templates** and plain CSS — no JavaScript frameworks required.

### Page Flow

1. **`base.html`** — The master layout. Every page extends this template. It defines:
   - A sticky top navigation bar with links to Dashboard, Students, Exams, and Alerts.
   - A `{% block content %}` placeholder that child templates fill in.
   - A link to `styles.css` for all styling.

2. **`dashboard.html`** — Extends `base.html`. Displays three stat cards showing the total count of students, exams, and alerts. Each card links to its respective management page.

3. **`students.html`** — Extends `base.html`. Contains:
   - A **form** (HTML `<form method="post">`) with fields for student name, email, and optional exam ID.
   - A **table** listing all students (ID, name, email, exam ID, created date).
   - On form submit, the browser sends a standard POST request to `/ui/students`. Flask processes it, inserts the record, and redirects back — no JavaScript needed.

4. **`exams.html`** — Same pattern. Form fields: exam name, exam code, duration (minutes), total questions. Table shows all exams.

5. **`alerts.html`** — Read-only table displaying every proctoring alert with columns for student ID, exam ID, reason, severity, and timestamp. Severity cells are color-coded via CSS classes (`warning` = amber, `critical` = red).

### Styling

- **Dark theme** with CSS custom properties (`--bg: #0b1220`, `--accent: #33d6a6`, etc.)
- **Glass-morphism** top bar using `backdrop-filter: blur(10px)`
- **Responsive CSS grid** for cards and forms — collapses on screens below 720px
- No external CSS libraries — everything is in one `styles.css` file

---

## How the Backend Works

The backend is a **Flask** application split across four Python modules:

### `app.py` — Application Core (1050 lines)
- Creates the Flask app and configures CORS for allowed frontend origins.
- Registers all **API routes** under `/api/*` (return JSON) and **UI routes** under `/ui/*` (return HTML).
- Initializes the SQLite database on the first request.
- Contains helper functions:
  - `resolve_student_id()` — coerces student ID from string/float → int
  - `resolve_exam_id()` — resolves an exam by numeric ID or by exam code string
  - `normalize_submission_row()` — parses JSON answers from DB text column
  - `wants_raw_response()` — checks `?raw=1` query param
- Defines error handlers for 400, 404, and 500.
- Entry point: `python app.py` starts Flask on the configured host and port.

### `models.py` — Data Access Layer (395 lines)
- `get_db_connection()` — opens a SQLite connection with `row_factory = sqlite3.Row` for dict-like access and enables foreign keys.
- `init_database()` — creates all 5 tables if they don't exist; also runs `ALTER TABLE` for backward-compatible schema migrations.
- `add_student()`, `add_exam()`, `add_alert()`, `add_submission()`, `add_violation_screenshot()` — insert functions that return the new row's ID.
- `fetch_one()`, `fetch_all()` — generic query helpers that return dicts.

### `detection.py` — Computer Vision Engine (90 lines)
- `_decode_base64_image()` — converts a Base64/data-URI string into an OpenCV BGR image matrix.
- `compress_image()` — resizes to 640×480 and re-encodes as JPEG (quality 75) for storage-efficient screenshots.
- `analyze_frame()` — the core detection function:
  1. Decodes the Base64 image.
  2. Converts to grayscale.
  3. Loads OpenCV's `haarcascade_frontalface_default.xml` Haar Cascade classifier.
  4. Runs `detectMultiScale()` with `scaleFactor=1.1`, `minNeighbors=5`, `minSize=(60,60)`.
  5. Returns a result dict with `alert`, `reason`, `severity`, `violation_type`, and `compressed_image`.

### `config.py` — Configuration (62 lines)
- Database path (`database.db` in project root).
- Flask settings: `DEBUG`, `TESTING`, `SECRET_KEY` — all overridable via environment variables.
- CORS origins: defaults to `localhost:3000`, `localhost:5173`, `localhost:8080`, and a Vercel deployment URL.
- Server: `FLASK_HOST` (default `0.0.0.0`), `FLASK_PORT` (default `5000`).
- Upload limits: 50 MB max, allowed image extensions.

---

## How Frontend and Backend Are Connected

ProctorGuard supports **two types of frontend connection**:

### 1. Built-in Admin UI (Server-Side Rendering)

```
Browser ──GET /ui/students──▶ Flask (app.py)
                                │
                                ├─ Queries SQLite via models.py
                                ├─ Passes data to Jinja2 template
                                │
Flask ◀── Rendered HTML ────── render_template('students.html', students=...)
                                │
Browser ◀── Full HTML page ────┘
```

- The browser requests a `/ui/*` route.
- Flask queries the database, passes the results to a Jinja2 template, and returns fully rendered HTML.
- Forms use `method="post"` — the browser submits data as `application/x-www-form-urlencoded`.
- After a POST, Flask inserts the record and responds with a `302 redirect` back to the same page, following the **Post/Redirect/Get (PRG)** pattern to avoid duplicate submissions.

### 2. External Frontend via REST API (e.g., React / Next.js)

```
React App (localhost:3000)                Flask API (localhost:5000)
         │                                          │
         ├── POST /api/analyze-frame ──────────────▶│
         │   { image: "base64...",                  │
         │     studentId: 1, examId: 1 }            │
         │                                          ├─ detection.py analyzes frame
         │                                          ├─ Saves alert + screenshot to DB
         │◀── JSON { alert: true,                   │
         │          reason: "No face detected",     │
         │          severity: "warning" }     ──────┘
         │
         ├── POST /api/log-violation ──────────────▶│
         │   { student_id: 1, exam_id: 1,           │
         │     violation_type: "switched_tab",      │
         │     image: "base64..." }                 │
         │◀── JSON { success: true, alert_id: 42 } ┘
```

- CORS is configured in `app.py` to accept requests from the allowed origins listed in `config.py`.
- The external frontend sends JSON payloads to `/api/*` endpoints.
- Flask processes them and returns JSON responses.
- The webcam feed is captured in the browser, converted to Base64, and sent frame-by-frame to `/api/analyze-frame`.

---

## How the Database Works

ProctorGuard uses **SQLite** — a zero-configuration, file-based relational database stored in `database.db`. The schema contains **5 tables** linked by foreign keys:

```
┌──────────────┐       ┌──────────────┐
│   students   │       │    exams     │
├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │
│ name         │       │ name         │
│ email        │       │ code         │
│ exam_id      │       │ duration     │
│ created_at   │       │ total_ques.  │
└──────┬───────┘       │ created_at   │
       │               └──────┬───────┘
       │                      │
       ▼                      ▼
┌──────────────────────────────────┐
│            alerts                │
├──────────────────────────────────┤
│ id (PK)                         │
│ student_id (FK → students.id)   │
│ exam_id    (FK → exams.id)      │
│ reason                          │
│ severity   (warning / critical) │
│ timestamp                       │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│     violation_screenshots        │
├──────────────────────────────────┤
│ id (PK)                         │
│ alert_id   (FK → alerts.id)     │
│ student_id (FK → students.id)   │
│ exam_id    (FK → exams.id)      │
│ image_data (Base64 JPEG)        │
│ violation_type                  │
│ timestamp                       │
└──────────────────────────────────┘

┌──────────────────────────────────┐
│         submissions              │
├──────────────────────────────────┤
│ id (PK)                         │
│ student_id (FK → students.id)   │
│ exam_id    (FK → exams.id)      │
│ answers    (JSON text)          │
│ score                           │
│ flagged    (0 or 1)             │
│ submitted_at                    │
└──────────────────────────────────┘
```

### Data Flow Example

1. Admin creates an **Exam** (name: "Math Final", code: "MATH-101", duration: 60 min).
2. Admin registers a **Student** (name: "John Doe", email: john@example.com, exam_id: "MATH-101").
3. During the exam, the frontend sends webcam frames to `/api/analyze-frame`.
4. If the detection module finds zero faces → an **Alert** is created (severity: warning) and a **Violation Screenshot** is saved.
5. If the student switches tabs → the frontend calls `/api/log-violation` → another **Alert** + **Screenshot**.
6. When the student finishes, the frontend calls `/api/submit-exam` → a **Submission** is created, optionally marked as `flagged` if violations were detected.

---

## How Violation Detection Works

ProctorGuard uses a **multi-layered** violation detection system:

### Layer 1 — Face Detection (Server-Side, OpenCV)

The detection engine in `detection.py` processes each webcam frame:

```
Webcam Frame (Base64) ──▶ Decode to NumPy array
                              │
                              ▼
                     Convert to Grayscale
                              │
                              ▼
                  Haar Cascade Face Detection
                 (haarcascade_frontalface_default.xml)
                              │
               ┌──────────────┼──────────────┐
               │              │              │
          0 faces         1 face        2+ faces
               │              │              │
               ▼              ▼              ▼
         ⚠️ WARNING      ✅ OK        🚨 CRITICAL
        "No face         No alert     "Multiple faces
         detected"                     detected"
```

**Parameters used:**
- `scaleFactor = 1.1` — how much the image size is reduced at each scale
- `minNeighbors = 5` — how many neighbors each candidate rectangle needs to retain it
- `minSize = (60, 60)` — minimum face size in pixels to avoid noise

When a violation is detected:
1. The frame is **compressed** to 640×480 JPEG (quality 75) to save storage.
2. An **alert** record is inserted into the `alerts` table.
3. The compressed image is stored in the `violation_screenshots` table linked to that alert.

### Layer 2 — Browser-Side Events (Client-Side)

The external frontend (React/Next.js) monitors browser events and reports them:

| Event | Detection Method | Violation Type | Severity |
|---|---|---|---|
| Student exits fullscreen | `document.fullscreenchange` event | `left_fullscreen` | Critical |
| Student switches tab | `document.visibilitychange` event | `switched_tab` | Critical |
| Exam window loses focus | `window.blur` event | `window_blur` | Critical |

These are sent to `POST /api/log-violation` with an optional screenshot captured at the moment of violation.

### Evidence Trail

Every violation produces:
1. **An alert row** — with student ID, exam ID, reason, severity, and timestamp.
2. **A screenshot row** — with the Base64 JPEG of the exact moment the violation occurred.
3. Both are queryable via `GET /api/violations-with-screenshots` which JOINs alerts, screenshots, and student names.

---

## API Reference

### Health

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Server health check |
| GET | `/api/health` | API health check |

### Students

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/students` | Create a student (`name`, `email`, `exam_id`) |
| GET | `/api/students` | List all students |
| GET | `/api/students/:id` | Get a student by ID |

### Exams

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/exams` | Create an exam (`name`, `code`, `duration`, `total_questions`) |
| GET | `/api/exams` | List all exams |
| GET | `/api/exams/:id` | Get an exam by ID |

### Alerts

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/alerts` | Create an alert (`student_id`, `exam_id`, `reason`, `severity`) |
| GET | `/api/alerts` | List all alerts |
| GET | `/api/alerts/student/:id` | Get alerts for a specific student |

### Proctoring

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyze-frame` | Analyze a webcam frame (`image`, `studentId`, `examId`) |
| POST | `/api/log-violation` | Log a browser violation (`student_id`, `exam_id`, `violation_type`, `image`) |
| GET | `/api/violations-with-screenshots` | Get all violations with screenshot evidence |

### Submissions

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/submissions` | Create a submission (`student_id`, `exam_id`, `answers`, `score`, `flagged`) |
| POST | `/api/submit-exam` | Submit an exam (alias with `studentId`/`examId` keys) |
| GET | `/api/submissions` | List all submissions |
| GET | `/api/submissions/student/:id` | Get submissions for a specific student |

> **Tip:** Append `?raw=1` to any GET/POST endpoint to receive the raw data without the `{ status, message, data }` wrapper.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Flask 3.0+ (Python) |
| **Database** | SQLite 3 (file-based, zero-config) |
| **Computer Vision** | OpenCV 4.8+ (Haar Cascade face detection) |
| **Template Engine** | Jinja2 (server-side HTML rendering) |
| **Cross-Origin** | Flask-CORS |
| **Environment Config** | python-dotenv |
| **Production Server** | Gunicorn (optional) |
| **Frontend Styling** | Plain CSS with custom properties (dark theme) |

---

## Requirements

- **Python 3.9+** recommended
- **Windows**, macOS, or Linux
- **pip** for dependency installation
- A webcam-equipped browser for the student-facing frontend

---

## Setup & Run

### 1) Create a virtual environment

```bash
python -m venv .venv
```

### 2) Activate it

**Windows CMD:**
```cmd
.venv\Scripts\activate.bat
```

**Windows PowerShell:**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
source .venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Run the server

```bash
python app.py
```

Or use the one-click scripts:
- **CMD:** double-click `run.bat`
- **PowerShell:** run `.\run.ps1`

The server starts at **http://localhost:5000**. Open **http://localhost:5000/ui** for the admin dashboard.

### 5) Connect an external frontend (optional)

1. Add your frontend URL to `CORS_ALLOWED_ORIGINS` in `config.py`.
2. Point your frontend's API base URL to `http://localhost:5000/api`.
3. Example fetch from JavaScript:

```javascript
const res = await fetch("http://localhost:5000/api/students", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    name: "Jane Doe",
    email: "jane@example.com",
    exam_id: "EXAM-001"
  })
});
const data = await res.json();
console.log(data);
```

---

## Deployment (Render + Vercel)

### Backend → Render (free tier)

1. Push this repo to GitHub.
2. Create a new **Web Service** on Render and connect it.
3. Set:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
4. Environment variables:
   - `FLASK_HOST=0.0.0.0`
   - `CORS_ALLOWED_ORIGINS=["https://your-frontend.vercel.app"]`
5. Note your backend URL (e.g., `https://your-app.onrender.com`).

### Frontend → Vercel

Set the environment variable in your Vercel project:

```
VITE_API_BASE_URL=https://your-app.onrender.com/api
```

---

## Notes & Limitations

- **SQLite** is ideal for local development and small deployments. For production scale, migrate to PostgreSQL.
- **Authentication** is not implemented — secure the API with JWT or session auth before production use.
- **Video stream recording** is not built-in; the system analyzes individual frames sent by the client.
- **Haar Cascades** provide lightweight face detection. For higher accuracy (e.g., head-pose, gaze tracking), integrate a deep learning model like MediaPipe or dlib.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| CORS errors in browser console | Add your frontend origin to `CORS_ALLOWED_ORIGINS` in `config.py` |
| Database tables missing | Restart the server — `init_database()` runs on the first request |
| Server won't start | Ensure the venv is activated and `pip install -r requirements.txt` ran successfully |
| OpenCV import error | Run `pip install opencv-python` — some systems need `opencv-python-headless` instead |

---

**Developed by Abhinav Gupta**
