from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os
import uuid

# ================= APP SETUP =================
app = Flask(__name__)
CORS(app)

# ================= DATABASE CONFIG =================
db_url = os.environ.get("DATABASE_URL")

if db_url and db_url.startswith("postgresql://"):
    db_url = db_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = db_url

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ================= UPLOAD CONFIG =================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

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
            "url": f"/uploads/{self.filename}"
        }

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
    correct_option = db.Column(db.String(1))

class ExamAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer)
    student_id = db.Column(db.Integer)
    score = db.Column(db.Integer, default=0)
    submitted_at = db.Column(db.DateTime)

# ================= CREATE TABLES =================
with app.app_context():
    db.create_all()

# ================= ROUTES =================

@app.route("/")
def home():
    return "AlgoPlay Backend Running"

# ---------- STUDENT SIGNUP ----------
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
        password=data["password"]
    )

    db.session.add(student)
    db.session.commit()

    return jsonify({"message": "Signup successful", "student": student.to_dict()}), 201

@app.route("/teacher/dashboard", methods=["GET"])
def teacher_dashboard():
    teacher_email = request.args.get("email")

    if not teacher_email:
        return jsonify({"error": "Teacher email required"}), 400

    teacher = Teacher.query.filter_by(email=teacher_email).first()
    if not teacher:
        return jsonify({"error": "Teacher not found"}), 404

    # Students belonging to same school
    students = Student.query.filter_by(
        schoolname=teacher.schoolname
    ).all()

    total_students = len(students)

    return jsonify({
        "teacher": teacher.to_dict(),
        "total_students": total_students,
        "students": [s.to_dict() for s in students]
    }), 200


# ---------- STUDENT LOGIN ----------
@app.route("/Login", methods=["POST"])
def login_student():
    data = request.get_json()
    student = Student.query.filter_by(name=data.get("identifier")).first()

    if not student or student.password != data.get("password"):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "student": student.to_dict()}), 200

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

@app.route("/TeacherLogin", methods=["POST"])
def login_teacher():
    data = request.get_json()

    teacher = Teacher.query.filter_by(email=data.get("email")).first()
    if not teacher or teacher.password != data.get("password"):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful", "teacher": teacher.to_dict()}), 200


# ---------- FILE UPLOAD ----------
@app.route("/assign_work", methods=["POST"])
def assign_work():
    subject = request.form.get("subject")
    teacher_name = request.form.get("teacher_name", "Unknown")

    if "assignment_file" not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files["assignment_file"]
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4().hex}_{filename}"

    file.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_filename))

    assignment = Assignment(
        subject=subject,
        filename=unique_filename,
        teacher_name=teacher_name
    )

    db.session.add(assignment)
    db.session.commit()

    return jsonify({"message": "Uploaded", "assignment": assignment.to_dict()}), 201
@app.route("/assignments", methods=["GET"])
def get_assignments():
    works = Assignment.query.order_by(Assignment.timestamp.desc()).all()
    return jsonify([w.to_dict() for w in works]), 200    
@app.route("/leaderboard", methods=["GET"])
def leaderboard():
    students = Student.query.order_by(Student.score.desc()).all()
    return jsonify([s.to_dict() for s in students]), 200


@app.route("/scoreupdate", methods=["POST"])
def update_score():
    data = request.get_json()
    student = Student.query.filter_by(name=data.get("name")).first()

    if not student:
        return jsonify({"error": "User not found"}), 404

    student.score += int(data.get("score", 0))
    db.session.commit()

    return jsonify({"message": "Score updated", "student": student.to_dict()}), 200


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

# ---------- SERVE FILE ----------
@app.route("/uploads/<filename>")
def serve_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)





