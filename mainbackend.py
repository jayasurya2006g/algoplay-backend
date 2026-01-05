from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import uuid

app = Flask(__name__)


CORS(app, resources={
    r"/*": {
        "origins": [
            "http://127.0.0.1:5500",
            "http://localhost:5500"
        ]
    }
})
@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
    return response


# ================= CONFIG =================
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:spacegp_infinite1@localhost/mydatabase'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# ================= MODELS =================
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    schoolname = db.Column(db.String(50), nullable=False)
    classofstudy = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)
    xp = db.Column(db.Integer, default=0)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "schoolname": self.schoolname,
            "classofstudy": self.classofstudy,
            "score": self.score,
            "xp": self.xp
        }

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    schoolname = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "schoolname": self.schoolname
        }

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    teacher_name = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "subject": self.subject,
            "teacher_name": self.teacher_name,
            "date": self.timestamp.strftime("%Y-%m-%d %H:%M"),
            "url": f"http://localhost:5000/uploads/{self.filename}"
        }
# ================= EXAM MODELS =================

class Exam(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(50), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exam.id'))
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200))
    option_b = db.Column(db.String(200))
    option_c = db.Column(db.String(200))
    option_d = db.Column(db.String(200))
    correct_option = db.Column(db.String(1))  # A/B/C/D

class ExamAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer)
    student_id = db.Column(db.Integer)
    score = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime)

with app.app_context():
    db.create_all()

@app.route("/exam/create", methods=["POST"])
def create_exam():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "No JSON received"}), 400

    required = ["title", "subject", "duration", "teacher_id"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    exam = Exam(
        title=data["title"],
        subject=data["subject"],
        duration_minutes=int(data["duration"]),
        teacher_id=int(data["teacher_id"])
    )

    db.session.add(exam)
    db.session.commit()

    return jsonify({"exam_id": exam.id}), 201


@app.route("/exam/<int:exam_id>/add-question", methods=["POST"])
def add_question(exam_id):
    data = request.get_json()

    q = Question(
        exam_id=exam_id,
        question_text=data["question"],
        option_a=data["A"],
        option_b=data["B"],
        option_c=data["C"],
        option_d=data["D"],
        correct_option=data["correct"]
    )

    db.session.add(q)
    db.session.commit()

    return jsonify({"message": "Question added"}), 201
@app.route("/exam/<int:exam_id>/start", methods=["POST"])
def start_exam(exam_id):
    exam = Exam.query.get(exam_id)
    exam.is_active = True
    db.session.commit()
    return jsonify({"message": "Exam started"})

@app.route("/exam/<int:exam_id>/stop", methods=["POST"])
def stop_exam(exam_id):
    exam = Exam.query.get(exam_id)
    exam.is_active = False
    db.session.commit()
    return jsonify({"message": "Exam stopped"})
@app.route("/exams/active", methods=["GET"])
def active_exams():
    exams = Exam.query.filter_by(is_active=True).all()
    return jsonify([
        {
            "id": e.id,
            "title": e.title,
            "subject": e.subject,
            "duration": e.duration_minutes
        } for e in exams
    ])
@app.route("/exam/<int:exam_id>/questions", methods=["GET"])
def get_questions(exam_id):
    questions = Question.query.filter_by(exam_id=exam_id).all()
    return jsonify([
        {
            "id": q.id,
            "question": q.question_text,
            "A": q.option_a,
            "B": q.option_b,
            "C": q.option_c,
            "D": q.option_d
        } for q in questions
    ])
@app.route("/exam/<int:exam_id>/submit", methods=["POST"])
def submit_exam(exam_id):
    data = request.get_json()
    student_id = data["student_id"]
    answers = data["answers"]  # {question_id: "A"}

    score = 0
    for qid, selected in answers.items():
        q = Question.query.get(int(qid))
        if q and q.correct_option == selected:
            score += 1

    attempt = ExamAttempt(
        exam_id=exam_id,
        student_id=student_id,
        score=score,
        submitted_at=datetime.utcnow()
    )

    # update student total score
    # student = Student.query.get(student_id)
    # student.score += score
    # student.xp += score * 10
    student = Student.query.get(student_id)

    if not student:
     return jsonify({"error": "Invalid student ID"}), 400

    student.score += score
    student.xp += score * 10
    db.session.add(attempt)
    db.session.commit()

    return jsonify({"message": "Exam submitted", "score": score})


# ================= STUDENT SIGNUP =================
@app.route("/exam/<int:exam_id>", methods=["GET"])
def exam_info(exam_id):
    exam = Exam.query.get(exam_id)
    if not exam:
        return jsonify({"error": "Exam not found"}), 404

    return jsonify({
        "title": exam.title,
        "subject": exam.subject,
        "duration": exam.duration_minutes
    })

@app.route("/TeacherSignup", methods=["POST"])
def teacher_signup():
    data = request.get_json()

    required = ["name", "email", "schoolname", "password"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    if Teacher.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    teacher = Teacher(
        name=data["name"],
        email=data["email"],
        schoolname=data["schoolname"],
        password=data["password"]
    )

    db.session.add(teacher)
    db.session.commit()

    return jsonify({"message": "Signup successful"}), 201
@app.route("/teacher/dashboard", methods=["GET"])
def teacher_dashboard():
    teacher_email = request.args.get("email")

    if not teacher_email:
        return jsonify({"error": "Teacher email required"}), 400

    teacher = Teacher.query.filter_by(email=teacher_email).first()
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404

    # Students of same school
    students = Student.query.filter_by(
        schoolname=teacher.schoolname
    ).all()

    total_students = len(students)
    active_students = len([s for s in students if s.score > 0])

    # ---------- Progress Buckets ----------
    excellent = len([s for s in students if s.score >= 80])
    average = len([s for s in students if 40 <= s.score < 80])
    needs_help = len([s for s in students if s.score < 40])

    # ---------- Class-wise distribution ----------
    class_distribution = {}
    for s in students:
        class_distribution[s.classofstudy] = class_distribution.get(s.classofstudy, 0) + 1

    return jsonify({
        "teacher": teacher.to_dict(),
        "stats": {
            "total_students": total_students,
            "active_students": active_students
        },
        "progress_chart": {
            "excellent": excellent,
            "average": average,
            "needs_help": needs_help
        },
        "class_chart": class_distribution,
        "students": [s.to_dict() for s in students]
    }), 200


@app.route("/Signup", methods=["POST"])
def signup_student():
    data = request.get_json()
    required = ["name", "age", "schoolname", "classofstudy", "password"]

    if not data or not all(k in data for k in required):
        return jsonify({"error": "Missing fields"}), 400

    if Student.query.filter_by(name=data["name"]).first():
        return jsonify({"error": "Username already exists"}), 400

    student = Student(
        name=data["name"],
        age=int(data["age"]),
        schoolname=data["schoolname"],
        classofstudy=data["classofstudy"],
        password=data["password"],
        xp=0
    )

    db.session.add(student)
    db.session.commit()

    return jsonify({"message": "Signup successful", "student": student.to_dict()}), 201

# ================= STUDENT LOGIN =================
@app.route("/Login", methods=["POST"])
def login_student():
    data = request.get_json()

    student = Student.query.filter_by(name=data.get("identifier")).first()
    if not student or student.password != data.get("password"):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "student": student.to_dict()}), 200

# ================= TEACHER LOGIN =================
@app.route("/TeacherLogin", methods=["POST"])
def login_teacher():
    data = request.get_json()

    teacher = Teacher.query.filter_by(email=data.get("email")).first()
    if not teacher or teacher.password != data.get("password"):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "teacher": teacher.to_dict()}), 200

# ================= ASSIGN WORK =================
from datetime import datetime
import  uuid

import re
from werkzeug.utils import secure_filename
@app.route("/assign_work", methods=["POST"])
def assign_work():
    try:
        subject = request.form.get("subject", "").strip()
        teacher_name = request.form.get("teacher_name", "Unknown Teacher").strip()

        if not subject:
            return jsonify({"error": "Subject missing"}), 400

        if "assignment_file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["assignment_file"]
        if not file or file.filename == "":
            return jsonify({"error": "Empty file"}), 400

        filename = secure_filename(file.filename)

        allowed_extensions = ['.pdf', '.doc', '.docx', '.png', '.jpg']
        ext = os.path.splitext(filename.lower())[1]
        if ext not in allowed_extensions:
            return jsonify({"error": "Invalid file type"}), 400

        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > 10 * 1024 * 1024:
            return jsonify({"error": "File too large"}), 400

        unique_filename = f"{uuid.uuid4().hex[:8]}_{filename}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
        file.save(filepath)

        assignment = Assignment(
            subject=subject,
            filename=unique_filename,
            teacher_name=teacher_name
        )

        db.session.add(assignment)
        db.session.commit()

        # ✅ THIS WAS MISSING
        return jsonify({
            "success": True,
            "message": "Assignment uploaded successfully",
            "assignment": assignment.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ================= GET ASSIGNMENTS (STUDENTS) =================
@app.route("/assignments", methods=["GET"])
def get_assignments():
    works = Assignment.query.order_by(Assignment.timestamp.desc()).all()
    return jsonify([w.to_dict() for w in works]), 200

# ================= FILE SERVE =================
@app.route("/uploads/<filename>")
def serve_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# ================= SCORE UPDATE =================
@app.route("/scoreupdate", methods=["POST"])
def update_score():
    data = request.get_json()
    student = Student.query.filter_by(name=data.get("name")).first()

    if not student:
        return jsonify({"error": "User not found"}), 404

    student.score += int(data.get("score", 0))
    db.session.commit()

    return jsonify({"message": "Score updated", "student": student.to_dict()}), 200

# ================= LEADERBOARD =================
@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    students = Student.query.order_by(Student.score.desc()).all()
    return jsonify([s.to_dict() for s in students]), 200

# ================= PROFILE UPDATE =================
@app.route("/profilesupdate", methods=["POST"])
def update_profile():
    data = request.get_json()
    student = Student.query.filter_by(name=data.get("name")).first()

    if not student:
        return jsonify({"error": "User not found"}), 404

    for field in ["age", "schoolname", "classofstudy", "password"]:
        if field in data:
            setattr(student, field, data[field])

    db.session.commit()
    return jsonify({"message": "Profile updated", "student": student.to_dict()}), 200

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
