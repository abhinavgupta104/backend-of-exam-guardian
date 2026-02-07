"""
ProctorGuard - Online Exam Proctoring System
Flask backend application for exam monitoring and student surveillance
"""

from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask_cors import CORS
from datetime import datetime
import logging
import json
from models import (
    init_database,
    fetch_one,
    fetch_all,
    add_student,
    add_exam,
    add_alert,
    add_submission,
    add_violation_screenshot
)
from detection import analyze_frame


# Initialize Flask application
app = Flask(__name__)
app.config.from_object('config')

# Configure CORS for frontend communication
cors_config = {
    "origins": app.config.get('CORS_ALLOWED_ORIGINS', []),
    "methods": app.config.get('CORS_ALLOW_METHODS', ["GET", "POST", "PUT", "DELETE", "OPTIONS"]),
    "allow_headers": app.config.get('CORS_ALLOW_HEADERS', ["Content-Type", "Authorization"])
}
CORS(app, resources={r"/api/*": cors_config})

print("[APP] Flask application initialized")
print(f"[APP] CORS enabled for: {app.config.get('CORS_ALLOWED_ORIGINS', [])}")


# Configure logging
log_level_name = app.config.get('LOG_LEVEL', 'INFO')
log_level = getattr(logging, log_level_name.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
print(f"[APP] Logging configured at level: {log_level_name}")


# Initialize database on app startup
def init_database_once():
    """Initialize database once when the app starts serving"""
    try:
        init_database()
        print("[APP] Database initialized on startup")
        logger.info("Database initialized on startup")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        logger.exception("Database initialization failed")
        raise


# Register startup hook with Flask-version compatibility
if hasattr(app, 'before_serving'):
    app.before_serving(init_database_once)
else:
    @app.before_request
    def init_database_on_first_request():
        if not getattr(app, '_db_initialized', False):
            init_database_once()
            app._db_initialized = True


def wants_raw_response() -> bool:
    """Return True when the caller asks for raw JSON without wrapper fields."""
    raw_value = request.args.get('raw', '')
    return str(raw_value).strip().lower() in {'1', 'true', 'yes'}


def resolve_student_id(student_id_value):
    """Coerce student_id to int when possible, otherwise raise ValueError."""
    if isinstance(student_id_value, int):
        return student_id_value
    if isinstance(student_id_value, str) and student_id_value.isdigit():
        return int(student_id_value)
    if isinstance(student_id_value, float) and student_id_value.is_integer():
        return int(student_id_value)
    raise ValueError('student_id must be a numeric value')


def resolve_exam_id(exam_id_value):
    """Resolve exam_id from int or exam code string."""
    if isinstance(exam_id_value, int):
        return exam_id_value
    if isinstance(exam_id_value, float) and exam_id_value.is_integer():
        return int(exam_id_value)
    if isinstance(exam_id_value, str):
        exam_id_value = exam_id_value.strip()
        if exam_id_value.isdigit():
            return int(exam_id_value)
        if exam_id_value:
            exam = fetch_one('SELECT id FROM exams WHERE code = ?', (exam_id_value,))
            if exam:
                return int(exam['id'])
            raise ValueError('Exam code not found')
    raise ValueError('exam_id is required')


def normalize_submission_row(row: dict) -> dict:
    """Parse JSON answers from the database for API output."""
    if not row:
        return row
    answers_value = row.get('answers')
    if isinstance(answers_value, str):
        try:
            row['answers'] = json.loads(answers_value)
        except json.JSONDecodeError:
            row['answers'] = {}
    if 'flagged' in row:
        row['flagged'] = bool(row['flagged'])
    return row


# ============================================================================
# API ROUTES
# ============================================================================

@app.route('/', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify server is running
    
    Returns:
        JSON: Server status and timestamp
    """
    print("[ROUTE] GET / - Health check")
    return jsonify({
        'status': 'success',
        'message': 'ProctorGuard Backend is running',
        'timestamp': datetime.now().isoformat(),
        'service': 'ProctorGuard API v1.0'
    }), 200


@app.route('/api/health', methods=['GET'])
def api_health():
    """
    API health check endpoint
    
    Returns:
        JSON: API status
    """
    print("[ROUTE] GET /api/health - API health check")
    return jsonify({
        'status': 'healthy',
        'message': 'ProctorGuard API is operational',
        'timestamp': datetime.now().isoformat()
    }), 200


# ============================================================================
# STUDENT ENDPOINTS
# ============================================================================

@app.route('/api/students', methods=['POST'])
def create_student():
    """
    Create a new student record
    
    Request JSON:
        - name (str): Student name
        - email (str): Student email
        - exam_id (str, optional): Associated exam ID
    
    Returns:
        JSON: Created student details
    """
    try:
        print("[ROUTE] POST /api/students - Create student")
        data = request.get_json()
        
        if not data or not data.get('name') or not data.get('email'):
            print("[ERROR] Invalid student data provided")
            return jsonify({
                'status': 'error',
                'message': 'Name and email are required'
            }), 400
        
        student_id = add_student(
            name=data['name'],
            email=data['email'],
            exam_id=data.get('exam_id')
        )

        student = fetch_one('SELECT * FROM students WHERE id = ?', (student_id,))
        if wants_raw_response():
            return jsonify(student), 201

        return jsonify({
            'status': 'success',
            'message': 'Student created successfully',
            'student_id': student_id,
            'data': student
        }), 201
        
    except Exception as e:
        print(f"[ERROR] Failed to create student: {e}")
        logger.error(f"Failed to create student: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to create student'
        }), 500


@app.route('/api/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """
    Get student details by ID
    
    Args:
        student_id (int): Student ID
    
    Returns:
        JSON: Student details
    """
    try:
        print(f"[ROUTE] GET /api/students/{student_id} - Get student")
        student = fetch_one(
            'SELECT * FROM students WHERE id = ?',
            (student_id,)
        )
        
        if not student:
            print(f"[ERROR] Student {student_id} not found")
            return jsonify({
                'status': 'error',
                'message': 'Student not found'
            }), 404
        
        if wants_raw_response():
            return jsonify(student), 200

        return jsonify({
            'status': 'success',
            'data': student
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to get student: {e}")
        logger.error(f"Failed to get student: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve student'
        }), 500


@app.route('/api/students', methods=['GET'])
def get_all_students():
    """
    Get all students
    
    Returns:
        JSON: List of all students
    """
    try:
        print("[ROUTE] GET /api/students - Get all students")
        students = fetch_all('SELECT * FROM students')
        
        if wants_raw_response():
            return jsonify(students), 200

        return jsonify({
            'status': 'success',
            'count': len(students),
            'data': students
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to get all students: {e}")
        logger.error(f"Failed to get all students: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve students'
        }), 500


# ============================================================================
# EXAM ENDPOINTS
# ============================================================================

@app.route('/api/exams', methods=['POST'])
def create_exam():
    """
    Create a new exam
    
    Request JSON:
        - name (str): Exam name
        - duration (int): Duration in minutes
        - total_questions (int): Total number of questions
    
    Returns:
        JSON: Created exam details
    """
    try:
        print("[ROUTE] POST /api/exams - Create exam")
        data = request.get_json()
        
        if not data or not data.get('name'):
            print("[ERROR] Invalid exam data provided")
            return jsonify({
                'status': 'error',
                'message': 'Exam name is required'
            }), 400
        
        exam_id = add_exam(
            name=data['name'],
            duration=data.get('duration', 0),
            total_questions=data.get('total_questions', 0),
            code=data.get('code') or data.get('exam_code')
        )

        exam = fetch_one('SELECT * FROM exams WHERE id = ?', (exam_id,))
        if wants_raw_response():
            return jsonify(exam), 201

        return jsonify({
            'status': 'success',
            'message': 'Exam created successfully',
            'exam_id': exam_id,
            'data': exam
        }), 201
        
    except Exception as e:
        print(f"[ERROR] Failed to create exam: {e}")
        logger.error(f"Failed to create exam: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to create exam'
        }), 500


@app.route('/api/exams/<int:exam_id>', methods=['GET'])
def get_exam(exam_id):
    """
    Get exam details by ID
    
    Args:
        exam_id (int): Exam ID
    
    Returns:
        JSON: Exam details
    """
    try:
        print(f"[ROUTE] GET /api/exams/{exam_id} - Get exam")
        exam = fetch_one(
            'SELECT * FROM exams WHERE id = ?',
            (exam_id,)
        )
        
        if not exam:
            print(f"[ERROR] Exam {exam_id} not found")
            return jsonify({
                'status': 'error',
                'message': 'Exam not found'
            }), 404
        
        if wants_raw_response():
            return jsonify(exam), 200

        return jsonify({
            'status': 'success',
            'data': exam
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to get exam: {e}")
        logger.error(f"Failed to get exam: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve exam'
        }), 500


@app.route('/api/exams', methods=['GET'])
def get_all_exams():
    """
    Get all exams
    
    Returns:
        JSON: List of all exams
    """
    try:
        print("[ROUTE] GET /api/exams - Get all exams")
        exams = fetch_all('SELECT * FROM exams')
        
        if wants_raw_response():
            return jsonify(exams), 200

        return jsonify({
            'status': 'success',
            'count': len(exams),
            'data': exams
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to get all exams: {e}")
        logger.error(f"Failed to get all exams: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve exams'
        }), 500


# ============================================================================
# ALERTS ENDPOINTS
# ============================================================================

@app.route('/api/alerts', methods=['POST'])
def create_alert():
    """
    Create a new alert for a student
    
    Request JSON:
        - student_id (int): Student ID
        - exam_id (int): Exam ID
        - reason (str): Reason for alert
        - severity (str, optional): 'warning' or 'critical' (default: 'warning')
    
    Returns:
        JSON: Created alert details
    """
    try:
        print("[ROUTE] POST /api/alerts - Create alert")
        data = request.get_json()
        
        if not data or not data.get('student_id') or not data.get('exam_id') or not data.get('reason'):
            print("[ERROR] Invalid alert data provided")
            return jsonify({
                'status': 'error',
                'message': 'student_id, exam_id, and reason are required'
            }), 400
        
        try:
            resolved_student_id = resolve_student_id(data['student_id'])
            resolved_exam_id = resolve_exam_id(data['exam_id'])
        except ValueError as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 400

        alert_id = add_alert(
            student_id=resolved_student_id,
            exam_id=resolved_exam_id,
            reason=data['reason'],
            severity=data.get('severity', 'warning')
        )

        alert = fetch_one('SELECT * FROM alerts WHERE id = ?', (alert_id,))
        if wants_raw_response():
            return jsonify(alert), 201

        return jsonify({
            'status': 'success',
            'message': 'Alert created successfully',
            'alert_id': alert_id,
            'data': alert
        }), 201
        
    except Exception as e:
        print(f"[ERROR] Failed to create alert: {e}")
        logger.error(f"Failed to create alert: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to create alert'
        }), 500


@app.route('/api/alerts/student/<int:student_id>', methods=['GET'])
def get_student_alerts(student_id):
    """
    Get all alerts for a specific student
    
    Args:
        student_id (int): Student ID
    
    Returns:
        JSON: List of alerts for the student
    """
    try:
        print(f"[ROUTE] GET /api/alerts/student/{student_id} - Get student alerts")
        alerts = fetch_all(
            'SELECT * FROM alerts WHERE student_id = ? ORDER BY timestamp DESC',
            (student_id,)
        )
        
        if wants_raw_response():
            return jsonify(alerts), 200

        return jsonify({
            'status': 'success',
            'count': len(alerts),
            'data': alerts
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to get student alerts: {e}")
        logger.error(f"Failed to get student alerts: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve alerts'
        }), 500


@app.route('/api/alerts', methods=['GET'])
def get_all_alerts():
    """
    Get all alerts
    
    Returns:
        JSON: List of all alerts
    """
    try:
        print("[ROUTE] GET /api/alerts - Get all alerts")
        alerts = fetch_all('SELECT * FROM alerts ORDER BY timestamp DESC')
        
        if wants_raw_response():
            return jsonify(alerts), 200

        return jsonify({
            'status': 'success',
            'count': len(alerts),
            'data': alerts
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to get all alerts: {e}")
        logger.error(f"Failed to get all alerts: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve alerts'
        }), 500


@app.route('/api/log-violation', methods=['POST'])
def log_violation():
    """Log a non-frame violation (fullscreen, tab switch, blur, etc)."""
    try:
        data = request.get_json() or {}
        if not data.get('student_id') or not data.get('exam_id') or not data.get('violation_type'):
            return jsonify({'status': 'error', 'message': 'student_id, exam_id, and violation_type are required'}), 400

        try:
            resolved_student_id = resolve_student_id(data['student_id'])
            resolved_exam_id = resolve_exam_id(data['exam_id'])
        except ValueError as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 400

        violation_type = str(data['violation_type']).strip()
        reason_map = {
            'left_fullscreen': 'Left fullscreen mode',
            'switched_tab': 'Switched tab or window',
            'window_blur': 'Window lost focus',
            'no_face': 'No face detected',
            'multiple_faces': 'Multiple faces detected'
        }
        reason = reason_map.get(violation_type, 'Violation detected')

        alert_id = add_alert(
            student_id=resolved_student_id,
            exam_id=resolved_exam_id,
            reason=reason,
            severity='critical'
        )

        response = {'success': True, 'alert_id': alert_id}
        if wants_raw_response():
            return jsonify(response), 201

        return jsonify({'status': 'success', 'data': response}), 201
    except Exception as e:
        print(f"[ERROR] Failed to log violation: {e}")
        logger.error(f"Failed to log violation: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to log violation'}), 500


# ============================================================================
# FRAME ANALYSIS ENDPOINTS
# ============================================================================

@app.route('/api/analyze-frame', methods=['POST'])
def analyze_frame_endpoint():
    """Analyze a webcam frame and optionally record violations with screenshots."""
    try:
        data = request.get_json() or {}
        image_data = data.get('image')
        exam_id_value = data.get('examId') or data.get('exam_id')
        student_id_value = data.get('studentId') or data.get('student_id')

        if not image_data or not exam_id_value or not student_id_value:
            return jsonify({'status': 'error', 'message': 'image, examId, and studentId are required'}), 400

        try:
            resolved_student_id = resolve_student_id(student_id_value)
            resolved_exam_id = resolve_exam_id(exam_id_value)
        except ValueError as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 400

        result = analyze_frame(image_data)
        response = {
            'alert': bool(result.get('alert')),
            'reason': result.get('reason'),
            'severity': result.get('severity'),
            'violation_type': result.get('violation_type'),
            'compressed_image': result.get('compressed_image')
        }

        if response['alert']:
            reason = response['reason'] or 'Suspicious activity detected'
            severity = response['severity'] or 'warning'
            violation_type = response['violation_type'] or 'frame_alert'

            alert_id = add_alert(
                student_id=resolved_student_id,
                exam_id=resolved_exam_id,
                reason=reason,
                severity=severity
            )

            if response['compressed_image']:
                add_violation_screenshot(
                    alert_id=alert_id,
                    student_id=resolved_student_id,
                    exam_id=resolved_exam_id,
                    image_data=response['compressed_image'],
                    violation_type=violation_type
                )

        if wants_raw_response():
            return jsonify(response), 200

        return jsonify({'status': 'success', 'data': response}), 200
    except Exception as e:
        print(f"[ERROR] Frame analysis failed: {e}")
        logger.error(f"Frame analysis failed: {e}")
        return jsonify({'status': 'error', 'message': 'Frame analysis failed'}), 500


# ============================================================================
# UI ROUTES
# ============================================================================

@app.route('/ui', methods=['GET'])
def ui_dashboard():
    """Render admin dashboard UI"""
    try:
        students_count = fetch_one('SELECT COUNT(*) AS count FROM students')
        exams_count = fetch_one('SELECT COUNT(*) AS count FROM exams')
        alerts_count = fetch_one('SELECT COUNT(*) AS count FROM alerts')
        stats = {
            'students': (students_count or {}).get('count', 0),
            'exams': (exams_count or {}).get('count', 0),
            'alerts': (alerts_count or {}).get('count', 0)
        }
        return render_template('dashboard.html', title='Dashboard', stats=stats)
    except Exception as e:
        print(f"[ERROR] UI dashboard failed: {e}")
        logger.error(f"UI dashboard failed: {e}")
        return jsonify({'status': 'error', 'message': 'UI failed to load'}), 500


@app.route('/ui/students', methods=['GET', 'POST'])
def ui_students():
    """Render and manage students UI"""
    try:
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip()
            exam_id = request.form.get('exam_id', '').strip() or None
            if name and email:
                add_student(name=name, email=email, exam_id=exam_id)
            return redirect(url_for('ui_students'))

        students = fetch_all('SELECT * FROM students ORDER BY created_at DESC')
        return render_template('students.html', title='Students', students=students)
    except Exception as e:
        print(f"[ERROR] UI students failed: {e}")
        logger.error(f"UI students failed: {e}")
        return jsonify({'status': 'error', 'message': 'UI failed to load'}), 500


@app.route('/ui/exams', methods=['GET', 'POST'])
def ui_exams():
    """Render and manage exams UI"""
    try:
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            duration = int(request.form.get('duration', '0') or 0)
            total_questions = int(request.form.get('total_questions', '0') or 0)
            if name:
                add_exam(name=name, duration=duration, total_questions=total_questions)
            return redirect(url_for('ui_exams'))

        exams = fetch_all('SELECT * FROM exams ORDER BY created_at DESC')
        return render_template('exams.html', title='Exams', exams=exams)
    except Exception as e:
        print(f"[ERROR] UI exams failed: {e}")
        logger.error(f"UI exams failed: {e}")
        return jsonify({'status': 'error', 'message': 'UI failed to load'}), 500


@app.route('/ui/alerts', methods=['GET'])
def ui_alerts():
    """Render alerts UI"""
    try:
        alerts = fetch_all('SELECT * FROM alerts ORDER BY timestamp DESC')
        return render_template('alerts.html', title='Alerts', alerts=alerts)
    except Exception as e:
        print(f"[ERROR] UI alerts failed: {e}")
        logger.error(f"UI alerts failed: {e}")
        return jsonify({'status': 'error', 'message': 'UI failed to load'}), 500


# ============================================================================
# SUBMISSIONS ENDPOINTS
# ============================================================================

@app.route('/api/submissions', methods=['POST'])
def create_submission():
    """
    Create a new submission
    
    Request JSON:
        - student_id (int): Student ID
        - exam_id (int): Exam ID
        - answers (dict): Student's answers
        - score (int): Score obtained
    
    Returns:
        JSON: Created submission details
    """
    try:
        print("[ROUTE] POST /api/submissions - Create submission")
        data = request.get_json()
        
        if not data or not data.get('student_id') or not data.get('exam_id'):
            print("[ERROR] Invalid submission data provided")
            return jsonify({
                'status': 'error',
                'message': 'student_id and exam_id are required'
            }), 400
        
        try:
            resolved_student_id = resolve_student_id(data['student_id'])
            resolved_exam_id = resolve_exam_id(data['exam_id'])
        except ValueError as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 400

        answers_value = data.get('answers', {})
        if isinstance(answers_value, str):
            try:
                answers_value = json.loads(answers_value)
            except json.JSONDecodeError:
                answers_value = {}

        flagged_value = bool(data.get('flagged', False))

        submission_id = add_submission(
            student_id=resolved_student_id,
            exam_id=resolved_exam_id,
            answers=answers_value,
            score=data.get('score', 0),
            flagged=flagged_value
        )

        submission = fetch_one('SELECT * FROM submissions WHERE id = ?', (submission_id,))
        submission = normalize_submission_row(submission)

        if wants_raw_response():
            return jsonify(submission), 201

        return jsonify({
            'status': 'success',
            'message': 'Submission created successfully',
            'submission_id': submission_id,
            'data': submission
        }), 201
        
    except Exception as e:
        print(f"[ERROR] Failed to create submission: {e}")
        logger.error(f"Failed to create submission: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to create submission'
        }), 500


@app.route('/api/submit-exam', methods=['POST'])
def submit_exam():
    """Submit an exam with optional flagged status."""
    try:
        data = request.get_json() or {}
        if not data.get('studentId') and not data.get('student_id'):
            return jsonify({'status': 'error', 'message': 'studentId is required'}), 400
        if not data.get('examId') and not data.get('exam_id'):
            return jsonify({'status': 'error', 'message': 'examId is required'}), 400

        student_id_value = data.get('studentId') or data.get('student_id')
        exam_id_value = data.get('examId') or data.get('exam_id')

        try:
            resolved_student_id = resolve_student_id(student_id_value)
            resolved_exam_id = resolve_exam_id(exam_id_value)
        except ValueError as exc:
            return jsonify({'status': 'error', 'message': str(exc)}), 400

        answers_value = data.get('answers', {})
        if isinstance(answers_value, str):
            try:
                answers_value = json.loads(answers_value)
            except json.JSONDecodeError:
                answers_value = {}

        submission_id = add_submission(
            student_id=resolved_student_id,
            exam_id=resolved_exam_id,
            answers=answers_value,
            score=data.get('score', 0),
            flagged=bool(data.get('flagged', False))
        )

        submission = fetch_one('SELECT * FROM submissions WHERE id = ?', (submission_id,))
        submission = normalize_submission_row(submission)

        if wants_raw_response():
            return jsonify(submission), 201

        return jsonify({
            'status': 'success',
            'data': submission
        }), 201
    except Exception as e:
        print(f"[ERROR] Failed to submit exam: {e}")
        logger.error(f"Failed to submit exam: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to submit exam'}), 500


@app.route('/api/submissions/student/<int:student_id>', methods=['GET'])
def get_student_submissions(student_id):
    """
    Get all submissions for a specific student
    
    Args:
        student_id (int): Student ID
    
    Returns:
        JSON: List of submissions for the student
    """
    try:
        print(f"[ROUTE] GET /api/submissions/student/{student_id} - Get student submissions")
        submissions = fetch_all(
            'SELECT * FROM submissions WHERE student_id = ? ORDER BY submitted_at DESC',
            (student_id,)
        )
        
        submissions = [normalize_submission_row(row) for row in submissions]

        if wants_raw_response():
            return jsonify(submissions), 200

        return jsonify({
            'status': 'success',
            'count': len(submissions),
            'data': submissions
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to get student submissions: {e}")
        logger.error(f"Failed to get student submissions: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve submissions'
        }), 500


@app.route('/api/submissions', methods=['GET'])
def get_all_submissions():
    """
    Get all submissions
    
    Returns:
        JSON: List of all submissions
    """
    try:
        print("[ROUTE] GET /api/submissions - Get all submissions")
        submissions = fetch_all('SELECT * FROM submissions ORDER BY submitted_at DESC')
        
        submissions = [normalize_submission_row(row) for row in submissions]

        if wants_raw_response():
            return jsonify(submissions), 200

        return jsonify({
            'status': 'success',
            'count': len(submissions),
            'data': submissions
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to get all submissions: {e}")
        logger.error(f"Failed to get all submissions: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve submissions'
        }), 500


@app.route('/api/violations-with-screenshots', methods=['GET'])
def get_violations_with_screenshots():
    """Return violations joined with screenshot evidence."""
    try:
        rows = fetch_all(
            '''
            SELECT 
                alerts.id AS alert_id,
                students.name AS student_name,
                violation_screenshots.violation_type AS violation_type,
                violation_screenshots.timestamp AS timestamp,
                violation_screenshots.image_data AS image_data,
                alerts.severity AS severity
            FROM violation_screenshots
            JOIN alerts ON alerts.id = violation_screenshots.alert_id
            JOIN students ON students.id = violation_screenshots.student_id
            ORDER BY violation_screenshots.timestamp DESC
            '''
        )

        if wants_raw_response():
            return jsonify(rows), 200

        return jsonify({
            'status': 'success',
            'count': len(rows),
            'data': rows
        }), 200
    except Exception as e:
        print(f"[ERROR] Failed to get violations with screenshots: {e}")
        logger.error(f"Failed to get violations with screenshots: {e}")
        return jsonify({'status': 'error', 'message': 'Failed to retrieve violations'}), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found_error(error):
    """
    Handle 404 Not Found errors
    
    Args:
        error: The error object
    
    Returns:
        JSON: Error response
    """
    print(f"[ERROR] 404 Not Found: {request.path}")
    return jsonify({
        'status': 'error',
        'message': 'Resource not found',
        'path': request.path
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """
    Handle 500 Internal Server errors
    
    Args:
        error: The error object
    
    Returns:
        JSON: Error response
    """
    print(f"[ERROR] 500 Internal Server Error: {error}")
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'status': 'error',
        'message': 'Internal server error'
    }), 500


@app.errorhandler(400)
def bad_request_error(error):
    """
    Handle 400 Bad Request errors
    
    Args:
        error: The error object
    
    Returns:
        JSON: Error response
    """
    print(f"[ERROR] 400 Bad Request: {error}")
    return jsonify({
        'status': 'error',
        'message': 'Bad request'
    }), 400


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    try:
        print("\n" + "="*60)
        print("ProctorGuard - Online Exam Proctoring System")
        print("Starting Flask Backend Server")
        print("="*60)
        print(f"[INFO] Server starting on {app.config.get('FLASK_HOST')}:{app.config.get('FLASK_PORT')}")
        print(f"[INFO] Debug mode: {app.config.get('DEBUG')}")
        print("="*60 + "\n")
        
        # Run the Flask application
        app.run(
            host=app.config.get('FLASK_HOST'),
            port=app.config.get('FLASK_PORT'),
            debug=app.config.get('DEBUG')
        )
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Failed to start application: {e}")
        logger.critical(f"Failed to start application: {e}")
        raise
