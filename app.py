from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import init_db, get_db_connection
from auth import register_user, verify_user
import os
from werkzeug.utils import secure_filename
from model_utils import predict_image
from functools import wraps 

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Serve images via /static/uploads/... (matches your templates' View Image link)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# Initialize DB (creates/updates tables + columns)
init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def is_admin():
    return session.get('user_type') == 'admin'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin():
            flash('Admin access required', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        user = verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['user_type'] = user['user_type']
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard' if user['user_type'] == 'admin' else 'upload'))
        else:
            flash('Invalid username or password', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match', 'error')
        else:
            if register_user(username, email, password):
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Username or email already exists', 'error')

    return render_template('register.html')

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'error')
        return redirect(url_for('index'))

    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected", "error")
            cursor.close(); conn.close()
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "error")
            cursor.close(); conn.close()
            return redirect(request.url)

        if file and allowed_file(file.filename):
            # Collect panel details
            panel_id = request.form.get('panel_id', '').strip() or None
            site_name = request.form.get('site_name', '').strip() or None
            location = request.form.get('location', '').strip() or None
            panel_notes = request.form.get('panel_notes', '').strip() or None

            # Save file
            filename = secure_filename(file.filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            try:
                # Predict
                result = predict_image(filepath)

                # Insert (with panel details)
                cursor.execute(
                    """
                    INSERT INTO uploads (user_id, filename, result, panel_id, site_name, location, panel_notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (session['user_id'], filename, result, panel_id, site_name, location, panel_notes)
                )
                conn.commit()
                flash(f"Image analyzed successfully! Result: {result}", "success")
            except Exception as e:
                flash(f"Error processing image: {str(e)}", "error")
                cursor.close(); conn.close()
                return redirect(request.url)
            finally:
                cursor.close()
                conn.close()

            return redirect(url_for("upload"))

    # GET: show recent uploads by this user
    cursor.execute(
        """
        SELECT id, filename, upload_date, result, panel_id, site_name, location, panel_notes
        FROM uploads
        WHERE user_id = %s
        ORDER BY upload_date DESC
        LIMIT 10
        """,
        (session['user_id'],)
    )
    uploads = cursor.fetchall()
    cursor.close(); conn.close()

    return render_template("upload.html", uploads=uploads)

@app.route('/account')
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'error')
        return redirect(url_for('index'))

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, filename, upload_date, result, panel_id, site_name, location
        FROM uploads
        WHERE user_id = %s
        ORDER BY upload_date DESC
        LIMIT 10
        """,
        (session['user_id'],)
    )
    uploads = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('account.html', uploads=uploads)

# Admin Dashboard
@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'error')
        return redirect(url_for('index'))

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS count FROM users")
    users_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM uploads")
    uploads_count = cursor.fetchone()['count']

    cursor.execute("SELECT COUNT(*) AS count FROM uploads WHERE result LIKE '%defect%'")
    defects_count = cursor.fetchone()['count']

    defect_rate = (defects_count / uploads_count * 100) if uploads_count > 0 else 0

    cursor.execute("""
        SELECT u.*, usr.username
        FROM uploads u
        JOIN users usr ON u.user_id = usr.id
        ORDER BY u.upload_date DESC
        LIMIT 5
    """)
    recent_uploads = cursor.fetchall()

    cursor.close(); conn.close()
    return render_template(
        'admin_dashboard.html',
        users_count=users_count,
        uploads_count=uploads_count,
        defect_rate=round(defect_rate, 2),
        recent_uploads=recent_uploads
    )

# Admin - Manage Users
@app.route('/admin/users')
@admin_required
def manage_users():
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'error')
        return redirect(url_for('index'))

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('manage_users.html', users=users)

# Admin - Manage Uploads
@app.route('/admin/uploads')
@admin_required
def manage_uploads():
    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'error')
        return redirect(url_for('index'))

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.*, usr.username
        FROM uploads u
        JOIN users usr ON u.user_id = usr.id
        ORDER BY u.upload_date DESC
    """)
    uploads = cursor.fetchall()
    cursor.close(); conn.close()
    return render_template('manage_uploads.html', uploads=uploads)

# Admin - Take Action
@app.route('/admin/action/<int:upload_id>', methods=['POST'])
@admin_required
def take_action(upload_id):
    action = request.form.get('action')
    notes = request.form.get('notes', '')

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'error')
        return redirect(url_for('manage_uploads'))

    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            UPDATE uploads
            SET action_taken = %s,
                action_notes = %s,
                action_date = NOW()
            WHERE id = %s
            """,
            (action, notes, upload_id)
        )
        conn.commit()
        flash('Action recorded successfully!', 'success')
    except Exception as e:
        flash(f'Error recording action: {str(e)}', 'error')
    finally:
        cursor.close(); conn.close()

    return redirect(url_for('manage_uploads'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

# Admin - Delete User
@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == session['user_id']:
        flash('Cannot delete your own account', 'error')
        return redirect(url_for('manage_users'))

    conn = get_db_connection()
    if conn is None:
        flash('Database connection error', 'error')
        return redirect(url_for('manage_users'))

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT user_type FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if not user:
            flash('User not found', 'error')
        elif user[0] == 'admin':
            flash('Cannot delete admin users', 'error')
        else:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            flash('User deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    finally:
        cursor.close(); conn.close()

    return redirect(url_for('manage_users'))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
