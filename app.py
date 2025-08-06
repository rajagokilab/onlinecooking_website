from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3
from flask_migrate import Migrate
import re # Import re for regex operations
import os # Import os for path manipulation and file handling
from werkzeug.utils import secure_filename # For securing filenames



# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'a_very_secret_key'

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads' # Directory to save uploaded files
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}
MAX_FILE_SIZE_MB = 5
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE_MB * 1024 * 1024 # Max file size in bytes

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ------------------ MODELS ------------------

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Ticket('{self.requester}', '{self.subject}')"

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(20), nullable=False)
    use_gstin = db.Column(db.Boolean, default=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Enrollment('{self.name}', '{self.email}')"

# ------------------ DATABASE CONNECTION FOR USERS ------------------

def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn
# Helper function for allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ------------------ ROUTES ------------------

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/courses')
def courses():
    return render_template('courses.html')

from flask import Flask, render_template, request, flash, redirect, url_for

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        requester = request.form.get('requester', '').strip()
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        captcha = request.form.get('captcha') # This will be 'on' if checked, None otherwise
        attachment = request.files.get('attachment') # Get the uploaded file

        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'

        errors = []

        # Validate Requester (Email)
        if not requester:
            errors.append('Email is required.')
        elif not re.match(email_regex, requester):
            errors.append('Please provide a valid email address.')

        # Validate Subject
        if not subject:
            errors.append('Subject is required.')

        # Validate Description
        if not description:
            errors.append('Description is required.')

        # Validate Captcha
        if not captcha: # If checkbox is not checked, it won't be in request.form
            errors.append('Please confirm you are not a robot.')

        # Validate Attachment
        if attachment and attachment.filename != '':
            if not allowed_file(attachment.filename):
                errors.append(f'Invalid file type. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}.')
            # Check file size. Flask's MAX_CONTENT_LENGTH handles overall request size,
            # but you can add a more specific check here if needed per file.
            # For this, we'd need to read the file size or rely on Flask's config.
            # The client-side JS handles this more gracefully before upload.
            # If you need precise server-side file size validation for a single file,
            # you'd typically read its stream, but app.config['MAX_CONTENT_LENGTH']
            # is a good first line of defense for the entire request.
            if attachment.content_length > app.config['MAX_CONTENT_LENGTH']:
                 errors.append(f'File size exceeds {MAX_FILE_SIZE_MB}MB.')

        elif attachment and attachment.filename == '':
            # This case might happen if the file input was touched but no file was selected
            # or if the file was removed after selection.
            pass # No error for no file selected, as it's not required.


        if errors:
            for err in errors:
                flash(err, 'error')
            return redirect(url_for('contact'))

        try:
            # If there's an attachment and it's valid, save it
            uploaded_filename = None
            if attachment and attachment.filename != '' and allowed_file(attachment.filename):
                filename = secure_filename(attachment.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                attachment.save(file_path)
                uploaded_filename = filename # Store filename if needed for DB
                flash(f'File "{filename}" uploaded successfully.', 'success')


            # Insert ticket into database
            # Note: The Ticket model doesn't currently store attachment info.
            # If you want to store file paths, you'd need to add columns to the Ticket model
            # and update the INSERT statement.
            new_ticket = Ticket(requester=requester, subject=subject, description=description)
            db.session.add(new_ticket)
            db.session.commit()

            flash('Your ticket was submitted successfully!', 'success')
        except Exception as e:
            flash('An error occurred while submitting your ticket.', 'error')
            print(f"Error submitting ticket: {e}")

        return redirect(url_for('contact'))

    return render_template('contact.html')

@app.route('/enrollment')
def enrollment():
    return render_template('enrolldetails.html')

@app.route('/submit-enrollment', methods=['POST'])
def submit_enrollment():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        use_gstin = 'gst' in request.form

        if not name or not email or not mobile:
            flash('All fields are required!', 'error')
            return redirect(url_for('enroll_confirm'))  # redirects back to the form if error

        new_enrollment = Enrollment(name=name, email=email, mobile=mobile, use_gstin=use_gstin)
        db.session.add(new_enrollment)
        db.session.commit()

        # ✅ Redirect to the success page after form submission
        return redirect(url_for('enrollment_success'))

    except Exception as e:
        print(f"Error during enrollment: {e}")
        flash(f'An error occurred during enrollment: {e}', 'error')
        return redirect(url_for('enroll_confirm'))


@app.route('/enrollment-success')
def enrollment_success():
    return render_template('enrollment-success-page.html')




@app.route('/home-enrollment', methods=['POST'])
def home_enrollment():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')

        if not name or not email or not mobile:
            flash('All fields are required!', 'error')
            return redirect(url_for('home_cooking'))

        new_enrollment = Enrollment(name=name, email=email, mobile=mobile, use_gstin=False)
        db.session.add(new_enrollment)
        db.session.commit()
        return redirect(url_for('enrollment_success'))

    except Exception as e:
        print(f"Error during home cooking enrollment: {e}")
        flash(f'An error occurred during enrollment: {e}', 'error')
        return redirect(url_for('home_cooking'))

@app.route('/enrollconfirm')
def enroll_confirm():
    return render_template('enrollconfirm.html')

# ------------------ AUTH ROUTES ------------------

import re
from flask import Flask, request, jsonify, render_template
from werkzeug.security import generate_password_hash
# assuming get_db_connection() is defined elsewhere

def is_valid_email(email):
    # Basic regex pattern for validating email
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def is_valid_mobile(mobile):
    # Simple validation for 10-digit numbers
    return re.fullmatch(r"\d{10}", mobile) is not None

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        mobile = request.form.get('mobile')

        # Check for missing fields
        if not username or not email or not password or not mobile:
            return jsonify(success=False, message="Please fill all required fields"), 400

        # Validate email format
        if not is_valid_email(email):
            return jsonify(success=False, message="Invalid email format"), 400

        # Validate mobile number format
        if not is_valid_mobile(mobile):
            return jsonify(success=False, message="Invalid mobile number. Must be 10 digits."), 400

        # Hash the password
        hashed_password = generate_password_hash(password)

        # Connect to DB
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check for existing user
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return jsonify(success=False, message="Email already registered"), 409

        # Insert user
        cursor.execute(
            "INSERT INTO users (username, email, password, mobile) VALUES (?, ?, ?, ?)",
            (username, email, hashed_password, mobile)
        )
        conn.commit()
        conn.close()

        return jsonify(success=True, message="User created successfully"), 201

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()

            if not user:
                return jsonify({"status": "error", "message": "User not found"}), 200

            if not check_password_hash(user['password'], password):
                return jsonify({"status": "error", "message": "Invalid credentials"}), 200

            return jsonify({"status": "success", "message": "Login successful"}), 200

        return render_template('login.html')

    except Exception as e:
        print("Login route error:", e)
        return jsonify({"status": "error", "message": "Server error"}), 500
    
    
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            return jsonify(success=False, message="Email is required"), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify(success=False, message="No account found with this email"), 404

        # TODO: Send reset email with token (real implementation)
        return jsonify(success=True, message="Password reset instructions sent to your email")

    return render_template('forgot_password.html')

# ------------------ EXTRA PAGES ------------------

@app.route('/bakery')
def bakery():
    return render_template('bakery.html')

@app.route('/cloud')
def cloud():
    return render_template('cloud.html')

from flask import Flask, render_template

# ... other imports and app setup

@app.route('/programs')
def programs():
    return render_template('programs.html')
# ------------------ MAIN ENTRY ------------------

if __name__ == '__main__':
    app.run(debug=True)
