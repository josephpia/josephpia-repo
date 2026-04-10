from flask import Flask, render_template, request, redirect, url_for, session, abort, send_from_directory, make_response
from functools import wraps
import hashlib
import os
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
app.secret_key = "secretkey123"

# Configuration for file uploads
PROFILE_UPLOAD_FOLDER = 'static/uploads/profiles'
SERVICE_UPLOAD_FOLDER = 'static/uploads/service_requests'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024

app.config['PROFILE_UPLOAD_FOLDER'] = PROFILE_UPLOAD_FOLDER
app.config['SERVICE_UPLOAD_FOLDER'] = SERVICE_UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create upload folders
os.makedirs(PROFILE_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SERVICE_UPLOAD_FOLDER, exist_ok=True)

# Default admin account
users = {
    "admin": {
        "password": hashlib.sha256("1234".encode()).hexdigest(),
        "role": "admin",
        "firstname": "System",
        "lastname": "Administrator",
        "email": "admin@system.com",
        "profile_pic": None,
        "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
}

login_count = 0
service_requests = []
activities = []
request_id_counter = 1000

# ===== HELPER FUNCTIONS =====
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file, folder):
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    filepath = os.path.join(folder, filename)
    file.save(filepath)
    return filename

def generate_request_id():
    global request_id_counter
    request_id_counter += 1
    return f"SRQ-{request_id_counter}"

def log_activity(username, action, details=""):
    activities.append({
        "id": len(activities) + 1,
        "username": username,
        "action": action,
        "details": details,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

# ===== AUTHENTICATION DECORATORS =====
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('username'):
            abort(403)
        if session.get('role') != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('username'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def block_direct_admin():
    if request.path == '/admin':
        abort(404)

@app.route('/')
def home():
    if 'username' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    global login_count
    message = ""

    if session.get('username'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            message = "Please enter both username and password"
        elif username not in users:
            message = "User does not have an account"
        elif users[username]["password"] == hash_password(password):
            session['username'] = username
            session['role'] = users[username]["role"]
            login_count += 1
            log_activity(username, "Login", "User logged in successfully")

            if users[username]["role"] == "admin":
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            message = "Wrong password"

    return render_template('login.html', message=message)

# SIGNUP
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if session.get('username'):
        return redirect(url_for('home'))
        
    message = ""

    if request.method == 'POST':
        firstname = request.form.get('firstname', '').strip()
        middlename = request.form.get('middlename', '').strip()
        lastname = request.form.get('lastname', '').strip()
        age = request.form.get('age', '').strip()
        address = request.form.get('address', '').strip()
        birthdate = request.form.get('birthdate', '').strip()
        email = request.form.get('email', '').strip()
        cellphone = request.form.get('cellphone', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        if username in users:
            message = "Username already exists"
        elif len(username) < 3:
            message = "Username must be at least 3 characters"
        elif len(password) < 4:
            message = "Password must be at least 4 characters"
        elif password != confirm_password:
            message = "Passwords do not match"
        elif not all([firstname, lastname, age, address, birthdate, email, cellphone]):
            message = "All fields are required"
        else:
            users[username] = {
                "firstname": firstname,
                "middlename": middlename,
                "lastname": lastname,
                "age": age,
                "address": address,
                "birthdate": birthdate,
                "email": email,
                "cellphone": cellphone,
                "password": hash_password(password),
                "role": "user",
                "profile_pic": None,
                "join_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_requests": 0
            }
            log_activity(username, "Account Created", "New user registered")
            return redirect(url_for('login'))

    return render_template('signup.html', message=message)

# USER DASHBOARD
@app.route('/userdashboard', methods=['GET', 'POST'])
@login_required
def user_dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    profile_message = ""
    service_message = ""
    service_photo = None
    
    # Handle Profile Photo Upload
    if request.method == 'POST' and 'profile_photo' in request.files:
        photo = request.files['profile_photo']
        if photo.filename == '':
            profile_message = "No file selected"
        elif not allowed_file(photo.filename):
            profile_message = "Invalid file type"
        else:
            if users[session['username']].get('profile_pic'):
                old_photo_path = os.path.join(app.config['PROFILE_UPLOAD_FOLDER'], users[session['username']]['profile_pic'])
                if os.path.exists(old_photo_path):
                    os.remove(old_photo_path)
            filename = save_file(photo, app.config['PROFILE_UPLOAD_FOLDER'])
            users[session['username']]['profile_pic'] = filename
            profile_message = "Profile photo uploaded!"
            log_activity(session['username'], "Profile Photo Upload", filename)
    
    # Handle Service Request
    elif request.method == 'POST' and 'service' in request.form:
        service = request.form.get('service', '').strip()
        
        if not service:
            service_message = "Please enter your service request"
        else:
            if 'service_photo' in request.files:
                photo = request.files['service_photo']
                if photo.filename != '' and allowed_file(photo.filename):
                    service_photo = save_file(photo, app.config['SERVICE_UPLOAD_FOLDER'])
            
            service_requests.append({
                "id": generate_request_id(),
                "username": session['username'],
                "service": service,
                "status": "pending",
                "date_requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "service_photo": service_photo,
                "has_photo": service_photo is not None,
                "admin_notes": "",
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            users[session['username']]['total_requests'] = users[session['username']].get('total_requests', 0) + 1
            service_message = "Service request submitted!"
            log_activity(session['username'], "Service Request", service[:50])

    user_requests = [req for req in service_requests if req['username'] == session['username']]
    
    return render_template('userdashboard.html', 
                         profile_message=profile_message,
                         service_message=service_message,
                         user_requests=user_requests,
                         user=users.get(session['username'], {}))

# EDIT REQUEST
@app.route('/edit_request/<request_id>', methods=['GET', 'POST'])
@login_required
def edit_request(request_id):
    request_to_edit = None
    for req in service_requests:
        if req['id'] == request_id and req['username'] == session['username']:
            request_to_edit = req
            break
    
    if not request_to_edit:
        return "Request not found", 404
    
    if request_to_edit['status'] in ['ongoing', 'completed']:
        return "Cannot edit request that is ongoing or completed", 403
    
    if request.method == 'POST':
        new_service = request.form.get('service', '').strip()
        if new_service:
            request_to_edit['service'] = new_service
            request_to_edit['last_edited'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_activity(session['username'], "Edited Request", request_id)
            return redirect(url_for('user_dashboard'))
    
    return render_template('edit_request.html', request=request_to_edit)

# DELETE MY REQUEST
@app.route('/delete_my_request/<request_id>')
@login_required
def delete_my_request(request_id):
    global service_requests
    for req in service_requests:
        if req['id'] == request_id and req['username'] == session['username']:
            if req['status'] != 'pending':
                return "Cannot delete request that is ongoing or completed", 403
            if req.get('service_photo'):
                photo_path = os.path.join(app.config['SERVICE_UPLOAD_FOLDER'], req['service_photo'])
                if os.path.exists(photo_path):
                    os.remove(photo_path)
            service_requests = [r for r in service_requests if r['id'] != request_id]
            log_activity(session['username'], "Deleted Own Request", request_id)
            break
    return redirect(url_for('user_dashboard'))

# VIEW PHOTOS
@app.route('/view_profile_photo/<username>')
@login_required
def view_profile_photo(username):
    if username not in users:
        return "User not found", 404
    if users[username].get('profile_pic'):
        return send_from_directory(app.config['PROFILE_UPLOAD_FOLDER'], users[username]['profile_pic'])
    return "No photo", 404

@app.route('/view_service_photo/<request_id>')
@admin_required
def view_service_photo(request_id):
    for req in service_requests:
        if req['id'] == request_id and req.get('service_photo'):
            return send_from_directory(app.config['SERVICE_UPLOAD_FOLDER'], req['service_photo'])
    return "No photo", 404

# ADMIN DASHBOARD
@app.route('/admindashboard')
@admin_required
def admin_dashboard():
    section = request.args.get('section', 'dashboard')
    
    total_users = len([u for u in users if u != 'admin'])
    total_requests = len(service_requests)
    pending_requests = len([r for r in service_requests if r.get('status') == 'pending'])
    ongoing_requests = len([r for r in service_requests if r.get('status') == 'ongoing'])
    completed_requests = len([r for r in service_requests if r.get('status') == 'completed'])
    users_with_photos = len([u for u in users.values() if u.get('profile_pic')])
    requests_with_photos = len([r for r in service_requests if r.get('has_photo')])
    
    week_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    week_data = [12, 15, 18, 14, 22, 8, 5]
    max_week = max(week_data) if week_data else 1
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    revenue_data = [8500, 9200, 10500, 11800, 12500, 14200, 15800, 16500, 17200, 18800, 19500, 21000]
    max_revenue = max(revenue_data) if revenue_data else 1
    
    hours = ['6 AM', '9 AM', '12 PM', '3 PM', '6 PM', '9 PM', '12 AM']
    hourly_users = [3, 8, 15, 22, 18, 12, 5]
    max_hourly = max(hourly_users) if hourly_users else 1
    
    theme = request.cookies.get('theme', 'light')
    language = request.cookies.get('language', 'english')
    
    return render_template(
        'admindashboard.html',
        section=section,
        total_users=total_users,
        total_requests=total_requests,
        pending_requests=pending_requests,
        ongoing_requests=ongoing_requests,
        completed_requests=completed_requests,
        users_with_photos=users_with_photos,
        requests_with_photos=requests_with_photos,
        users=users,
        service_requests=service_requests,
        week_days=week_days,
        week_data=week_data,
        max_week=max_week,
        months=months,
        revenue_data=revenue_data,
        max_revenue=max_revenue,
        hours=hours,
        hourly_users=hourly_users,
        max_hourly=max_hourly,
        theme=theme,
        language=language,
        login_count=login_count,
        activities=activities[-10:]
    )

# UPDATE REQUEST STATUS - WITH ON-GOING AND NOTES
@app.route('/update_request/<request_id>', methods=['POST'])
@admin_required
def update_request(request_id):
    status = request.form.get('status')
    notes = request.form.get('notes', '')
    for req in service_requests:
        if req['id'] == request_id:
            req['status'] = status
            if notes:
                req['admin_notes'] = notes
            req['last_update'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_activity(session['username'], "Updated Request", f"{request_id} -> {status}")
            break
    return redirect(url_for('admin_dashboard', section='requests'))

# DELETE USER
@app.route('/delete_user/<username>')
@admin_required
def delete_user(username):
    if username == 'admin':
        return "Cannot delete admin", 403
    elif username in users:
        if users[username].get('profile_pic'):
            photo_path = os.path.join(app.config['PROFILE_UPLOAD_FOLDER'], users[username]['profile_pic'])
            if os.path.exists(photo_path):
                os.remove(photo_path)
        del users[username]
        log_activity(session['username'], "Deleted User", username)
    return redirect(url_for('admin_dashboard', section='dashboard'))

# DELETE REQUEST
@app.route('/delete_request/<request_id>')
@admin_required
def delete_request(request_id):
    global service_requests
    for req in service_requests:
        if req['id'] == request_id and req.get('service_photo'):
            photo_path = os.path.join(app.config['SERVICE_UPLOAD_FOLDER'], req['service_photo'])
            if os.path.exists(photo_path):
                os.remove(photo_path)
    service_requests = [req for req in service_requests if req['id'] != request_id]
    log_activity(session['username'], "Deleted Request", request_id)
    return redirect(url_for('admin_dashboard', section='requests'))

# SAVE SETTINGS
@app.route('/save_settings', methods=['POST'])
@admin_required
def save_settings():
    theme = request.form.get('theme', 'light')
    language = request.form.get('language', 'english')
    response = make_response(redirect(url_for('admin_dashboard', section='settings')))
    response.set_cookie('theme', theme, max_age=31536000)
    response.set_cookie('language', language, max_age=31536000)
    return response

# PROFILE PAGE
@app.route('/profile')
@login_required
def profile():
    user = users.get(session['username'])
    if not user:
        return "User not found", 404
    user_requests = [req for req in service_requests if req['username'] == session['username']]
    return render_template('profile.html', user=user, user_requests=user_requests)

# LOGOUT
@app.route('/logout')
def logout():
    username = session.get('username')
    session.clear()
    if username:
        log_activity(username, "Logout", "User logged out")
    return redirect(url_for('login'))

# ERROR HANDLERS
@app.errorhandler(403)
def forbidden(e):
    return "<h1>403 Access Denied</h1><a href='/login'>Back to Login</a>", 403

@app.errorhandler(404)
def not_found(e):
    return "<h1>404 Page Not Found</h1><a href='/login'>Back to Login</a>", 404

if __name__ == '__main__':
    app.run(debug=True)