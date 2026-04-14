from flask import Flask, render_template, request, redirect, url_for, session, abort, send_from_directory, make_response, jsonify
from functools import wraps
import hashlib
import os
from datetime import datetime, timedelta
import uuid
from collections import Counter
import re

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

# Technician list with specialties
technicians = [
    {
        "id": 1,
        "name": "John Santos",
        "specialty": "Aircon Repair",
        "keywords": ["aircon", "air conditioner", "ac", "cooling", "refrigerant", "compressor"],
        "status": "available",
        "rating": 4.8,
        "contact": "09123456789",
        "email": "john@servicehub.com",
        "assigned_requests": []
    },
    {
        "id": 2,
        "name": "Maria Reyes",
        "specialty": "Plumbing",
        "keywords": ["plumbing", "pipe", "leak", "faucet", "toilet", "drain", "water"],
        "status": "available",
        "rating": 4.9,
        "contact": "09123456780",
        "email": "maria@servicehub.com",
        "assigned_requests": []
    },
    {
        "id": 3,
        "name": "Robert Gomez",
        "specialty": "Electrical",
        "keywords": ["electrical", "wiring", "circuit", "breaker", "light", "outlet", "switch", "power"],
        "status": "available",
        "rating": 4.7,
        "contact": "09123456781",
        "email": "robert@servicehub.com",
        "assigned_requests": []
    },
    {
        "id": 4,
        "name": "Cristina Lopez",
        "specialty": "Appliance Repair",
        "keywords": ["appliance", "refrigerator", "washing machine", "dryer", "oven", "stove", "microwave"],
        "status": "available",
        "rating": 4.6,
        "contact": "09123456782",
        "email": "cristina@servicehub.com",
        "assigned_requests": []
    },
    {
        "id": 5,
        "name": "Michael Cruz",
        "specialty": "Aircon & Refrigeration",
        "keywords": ["aircon", "air conditioner", "ac", "cooling", "refrigerator", "freezer", "refrigeration"],
        "status": "available",
        "rating": 4.9,
        "contact": "09123456783",
        "email": "michael@servicehub.com",
        "assigned_requests": []
    },
    {
        "id": 6,
        "name": "Anna Dela Cruz",
        "specialty": "General Repair",
        "keywords": ["repair", "fix", "maintenance", "general"],
        "status": "available",
        "rating": 4.5,
        "contact": "09123456784",
        "email": "anna@servicehub.com",
        "assigned_requests": []
    }
]

login_count = 0
service_requests = []
activities = []
request_id_counter = 1000

# ===== PAYMENT MANAGEMENT SYSTEM =====
payments = []
payment_id_counter = 1

# Company payment accounts (SAME FOR ALL USERS)
COMPANY_PAYMENT_ACCOUNTS = {
    'gcash': {
        'name': 'GCash',
        'account_number': '0999-888-7777',
        'account_name': 'ServiceHub PH'
    },
    'paymaya': {
        'name': 'PayMaya',
        'account_number': '0988-777-6666',
        'account_name': 'ServiceHub'
    },
    'paypal': {
        'name': 'PayPal',
        'account_number': 'payments@servicehub.com',
        'account_name': 'ServiceHub Solutions'
    },
    'bank_transfer': {
        'name': 'Bank Transfer',
        'account_number': '0045-1234-5678',
        'account_name': 'ServiceHub Solutions Inc.',
        'bank': 'BDO'
    }
}

# Service prices
SERVICE_PRICES = {
    'Aircon Repair': 800,
    'Plumbing': 600,
    'Electrical': 700,
    'Appliance Repair': 500,
    'General Repair': 400,
    'HVAC': 900
}

def calculate_service_amount(category):
    """Calculate the service amount based on category"""
    return SERVICE_PRICES.get(category, 500)

def get_payment_summary():
    """Get payment summary for admin dashboard"""
    total_revenue = sum(p['amount'] for p in payments if p['status'] == 'paid')
    online_revenue = sum(p['amount'] for p in payments if p['status'] == 'paid' and p['payment_method'] == 'online')
    cash_revenue = sum(p['amount'] for p in payments if p['status'] == 'paid' and p['payment_method'] == 'cash')
    pending_verification = sum(p['amount'] for p in payments if p['status'] == 'for_verification')
    pending_cash_total = sum(p['amount'] for p in payments if p['status'] == 'pending_cash')
    
    return {
        'total_revenue': total_revenue,
        'online_revenue': online_revenue,
        'cash_revenue': cash_revenue,
        'pending_verification': pending_verification,
        'pending_cash_total': pending_cash_total,
        'total_transactions': len(payments)
    }

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

def detect_service_category(service_text):
    """Detect what category the service request belongs to"""
    service_text_lower = service_text.lower()
    
    for tech in technicians:
        for keyword in tech.get('keywords', []):
            if keyword in service_text_lower:
                return tech['specialty']
    
    return "General Repair"

def get_available_technicians_for_service(service_text):
    """Get only technicians who can fix the specific service"""
    service_text_lower = service_text.lower()
    available_techs = []
    
    for tech in technicians:
        if tech['status'] != 'available':
            continue
            
        for keyword in tech.get('keywords', []):
            if keyword in service_text_lower:
                available_techs.append(tech)
                break
    
    if not available_techs:
        for tech in technicians:
            if tech['status'] == 'available' and tech['specialty'] == 'General Repair':
                available_techs.append(tech)
    
    return available_techs

def update_technician_status(technician_id):
    """Update technician status based on assigned requests count"""
    for tech in technicians:
        if tech['id'] == technician_id:
            if len(tech['assigned_requests']) >= 1:
                tech['status'] = 'busy'
            else:
                tech['status'] = 'available'
            log_activity(session.get('username'), "Technician Status Updated", f"{tech['name']} -> {tech['status']}")
            break

def assign_technician_to_request(request_id, technician_id):
    """Assign a technician to a service request"""
    for req in service_requests:
        if req['id'] == request_id:
            for tech in technicians:
                if tech['id'] == int(technician_id):
                    req['technician_id'] = tech['id']
                    req['technician_name'] = tech['name']
                    req['technician_specialty'] = tech['specialty']
                    req['technician_assigned_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    req['status'] = 'ongoing'
                    
                    tech['assigned_requests'].append(request_id)
                    
                    # Update technician status to busy
                    update_technician_status(tech['id'])
                    
                    log_activity(session.get('username'), "Assigned Technician", f"Request {request_id} -> {tech['name']} ({tech['specialty']})")
                    return True
    return False

def unassign_technician_from_request(request_id):
    """Remove technician assignment from a request"""
    for req in service_requests:
        if req['id'] == request_id and req.get('technician_id'):
            for tech in technicians:
                if tech['id'] == req['technician_id']:
                    if request_id in tech['assigned_requests']:
                        tech['assigned_requests'].remove(request_id)
                    
                    # Update technician status (will become available if no more requests)
                    update_technician_status(tech['id'])
                    break
            req['technician_id'] = None
            req['technician_name'] = None
            req['technician_specialty'] = None
            req['technician_assigned_date'] = None
            log_activity(session.get('username'), "Unassigned Technician", f"Request {request_id}")
            return True
    return False

def add_new_technician(name, specialty, contact, email, keywords=""):
    """Add a new technician"""
    new_id = max([t['id'] for t in technicians]) + 1 if technicians else 1
    
    default_keywords = {
        "Aircon Repair": ["aircon", "air conditioner", "ac", "cooling", "refrigerant", "compressor"],
        "Plumbing": ["plumbing", "pipe", "leak", "faucet", "toilet", "drain", "water"],
        "Electrical": ["electrical", "wiring", "circuit", "breaker", "light", "outlet", "switch", "power"],
        "Appliance Repair": ["appliance", "refrigerator", "washing machine", "dryer", "oven", "stove", "microwave"],
        "General Repair": ["repair", "fix", "maintenance", "general"]
    }
    
    tech_keywords = default_keywords.get(specialty, ["repair", "fix"])
    if keywords:
        tech_keywords.extend([k.strip() for k in keywords.split(',')])
    
    new_tech = {
        "id": new_id,
        "name": name,
        "specialty": specialty,
        "keywords": tech_keywords,
        "status": "available",
        "rating": 5.0,
        "contact": contact,
        "email": email,
        "assigned_requests": []
    }
    technicians.append(new_tech)
    log_activity(session.get('username'), "Added Technician", f"Added {name} ({specialty})")
    return new_tech

def delete_technician(technician_id):
    """Delete a technician"""
    global technicians
    for tech in technicians:
        if tech['id'] == technician_id:
            for req_id in tech['assigned_requests']:
                for req in service_requests:
                    if req['id'] == req_id:
                        req['technician_id'] = None
                        req['technician_name'] = None
                        req['technician_specialty'] = None
                        req['technician_assigned_date'] = None
                        req['status'] = 'pending'
                        break
            technicians = [t for t in technicians if t['id'] != technician_id]
            log_activity(session.get('username'), "Deleted Technician", f"Deleted ID: {technician_id}")
            return True
    return False

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
            
            detected_category = detect_service_category(service)
            
            service_requests.append({
                "id": generate_request_id(),
                "username": session['username'],
                "service": service,
                "category": detected_category,
                "status": "pending",
                "date_requested": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "service_photo": service_photo,
                "has_photo": service_photo is not None,
                "admin_notes": "",
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "technician_id": None,
                "technician_name": None,
                "technician_specialty": None,
                "technician_assigned_date": None,
                "payment_status": "unpaid",
                "payment_method": None,
                "payment_amount": None
            })
            users[session['username']]['total_requests'] = users[session['username']].get('total_requests', 0) + 1
            service_message = "Service request submitted!"
            log_activity(session['username'], "Service Request", f"{detected_category}: {service[:50]}")

    user_requests = [req for req in service_requests if req['username'] == session['username']]
    
    # Check for payment success message
    payment_success = request.args.get('payment_success')
    payment_amount = request.args.get('amount')
    payment_method = request.args.get('method')
    pay_request = request.args.get('pay_request')
    
    return render_template('userdashboard.html', 
                         profile_message=profile_message,
                         service_message=service_message,
                         user_requests=user_requests,
                         user=users.get(session['username'], {}),
                         calculate_service_amount=calculate_service_amount,
                         payment_success=payment_success,
                         payment_amount=payment_amount,
                         payment_method=payment_method,
                         pay_request=pay_request)

# ===== PAYMENT ROUTES (FIXED) =====

@app.route('/create_payment/<request_id>', methods=['GET'])
@login_required
def create_payment(request_id):
    username = session['username']
    service_req = None
    for req in service_requests:
        if req['id'] == request_id and req['username'] == username:
            service_req = req
            break
    if not service_req:
        return "Request not found", 404
    
    amount = calculate_service_amount(service_req.get('category', 'General Repair'))
    return render_template('payment.html', request_id=request_id, amount=amount)


@app.route('/process_payment_direct', methods=['POST'])
@login_required
def process_payment_direct():
    global payment_id_counter
    
    request_id = request.form.get('request_id')
    payment_method = request.form.get('payment_method')
    online_app = request.form.get('online_app')
    reference_number = request.form.get('reference_number', '')
    amount = request.form.get('amount')
    username = session['username']
    
    # Find request
    service_req = None
    for req in service_requests:
        if req['id'] == request_id and req['username'] == username:
            service_req = req
            break
    
    if not service_req:
        return "Request not found", 404
    
    amount_int = int(amount)
    transaction_id = f"TXN-{username[:3].upper()}{payment_id_counter}{datetime.now().strftime('%m%d%H%M')}"
    
    # Create payment record - USING 'for_verification' to match admin dashboard
    payment = {
        'payment_id': f"PAY-{payment_id_counter}",
        'request_id': request_id,
        'username': username,
        'amount': amount_int,
        'payment_method': payment_method,
        'online_app': online_app if payment_method == 'online' else None,
        'reference_number': reference_number if payment_method == 'online' else None,
        'status': 'for_verification' if payment_method == 'online' else 'pending_cash',
        'payment_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'transaction_id': transaction_id,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    payments.append(payment)
    payment_id_counter += 1
    
    # Update request
    service_req['payment_status'] = 'for_verification' if payment_method == 'online' else 'pending_cash'
    service_req['payment_method'] = payment_method
    service_req['payment_amount'] = amount_int
    service_req['payment_id'] = payment['payment_id']
    service_req['reference_number'] = reference_number if payment_method == 'online' else None
    
    log_activity(username, "Payment Submitted", f"Request {request_id} - {payment_method}")
    
    # Show success page
    if payment_method == 'online':
        return render_template('success.html', 
            icon='✅', 
            title='Payment Submitted!', 
            amount=amount, 
            method=online_app, 
            reference=reference_number, 
            transaction=transaction_id,
            message='⏳ Pending verification by admin. You will receive confirmation within 24 hours.')
    else:
        return render_template('success.html',
            icon='💵', 
            title='Cash Payment Selected!', 
            amount=amount,
            method='Cash', 
            reference='', 
            transaction='',
            message='Please prepare exact amount for the technician upon arrival.')


# ADMIN VERIFY ONLINE PAYMENT (FIXED - matches 'for_verification' status)
@app.route('/verify_payment/<payment_id>', methods=['POST'])
@admin_required
def verify_payment(payment_id):
    action = request.form.get('action', 'approve')
    
    for payment in payments:
        if payment['payment_id'] == payment_id:
            if action == 'approve':
                payment['status'] = 'paid'
                payment['verified_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payment['verified_by'] = session['username']
                
                # Update service request
                for req in service_requests:
                    if req['id'] == payment['request_id']:
                        req['payment_status'] = 'paid'
                        break
                
                log_activity(session['username'], "Payment Verified", f"Payment {payment_id} approved")
            else:
                payment['status'] = 'rejected'
                payment['rejected_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                payment['rejected_by'] = session['username']
                log_activity(session['username'], "Payment Rejected", f"Payment {payment_id} rejected")
            
            return redirect(url_for('admin_dashboard', section='payments'))
    
    return redirect(url_for('admin_dashboard', section='payments', error='not_found'))


# ADMIN CONFIRM CASH PAYMENT
@app.route('/admin/confirm_cash_payment/<request_id>', methods=['POST'])
@admin_required
def confirm_cash_payment(request_id):
    for req in service_requests:
        if req['id'] == request_id:
            if req.get('payment_status') == 'pending_cash':
                req['payment_status'] = 'paid'
                # Update payment record
                for payment in payments:
                    if payment['request_id'] == request_id:
                        payment['status'] = 'paid'
                        payment['cash_confirmed_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        payment['confirmed_by'] = session['username']
                        break
                log_activity(session['username'], "Cash Payment Confirmed", f"Request {request_id}")
                return redirect(url_for('admin_dashboard', section='payments'))
    
    return redirect(url_for('admin_dashboard', section='payments'))

# PROCESS PAYMENT (Original - keep for compatibility)
@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    global payment_id_counter
    
    request_id = request.form.get('request_id')
    payment_method = request.form.get('payment_method')
    online_app = request.form.get('online_app', None)
    reference_number = request.form.get('reference_number', '')
    username = session['username']
    
    # Find the service request
    service_req = None
    for req in service_requests:
        if req['id'] == request_id and req['username'] == username:
            service_req = req
            break
    
    if not service_req:
        return "Request not found", 404
    
    if service_req.get('payment_status') == 'paid':
        return "Already paid", 400
    
    # Calculate amount
    amount = calculate_service_amount(service_req.get('category', 'General Repair'))
    
    # Create unique transaction ID
    transaction_id = f"TXN-{username[:3].upper()}{payment_id_counter}{datetime.now().strftime('%m%d%H%M')}"
    
    # Create payment record
    payment = {
        'payment_id': f"PAY-{payment_id_counter}",
        'request_id': request_id,
        'username': username,
        'amount': amount,
        'payment_method': payment_method,
        'online_app': online_app if payment_method == 'online' else None,
        'reference_number': reference_number if payment_method == 'online' else None,
        'status': 'for_verification' if payment_method == 'online' else 'pending_cash',
        'payment_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'transaction_id': transaction_id
    }
    
    payments.append(payment)
    payment_id_counter += 1
    
    # Update service request with payment info
    service_req['payment_status'] = 'for_verification' if payment_method == 'online' else 'pending_cash'
    service_req['payment_method'] = payment_method
    service_req['payment_amount'] = amount
    service_req['payment_id'] = payment['payment_id']
    service_req['transaction_id'] = transaction_id
    if payment_method == 'online':
        service_req['reference_number'] = reference_number
    
    log_activity(username, "Payment Submitted", f"Request {request_id} - {payment_method} - TXN: {transaction_id}")
    
    # Redirect back to user dashboard with success message
    return redirect(url_for('user_dashboard', payment_success='true', amount=amount, method=payment_method))

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
    
    week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    week_data = [0] * 7
    
    for req in service_requests:
        if req.get('date_requested'):
            try:
                req_date = datetime.strptime(req['date_requested'], "%Y-%m-%d %H:%M:%S")
                day_index = req_date.weekday()
                week_data[day_index] += 1
            except:
                pass
    max_week = max(week_data) if week_data and max(week_data) > 0 else 1
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    revenue_data = [0] * 12
    
    price_per_service = 500
    
    for req in service_requests:
        if req.get('status') == 'completed' and req.get('date_requested'):
            try:
                req_date = datetime.strptime(req['date_requested'], "%Y-%m-%d %H:%M:%S")
                month_index = req_date.month - 1
                revenue_data[month_index] += price_per_service
            except:
                pass
    
    if sum(revenue_data) == 0:
        revenue_data = [0, 0, 0, 0, 12500, 14200, 15800, 16500, 17200, 18800, 19500, 21000]
    
    max_revenue = max(revenue_data) if revenue_data and max(revenue_data) > 0 else 1
    
    hours = ['12 AM', '1 AM', '2 AM', '3 AM', '4 AM', '5 AM', '6 AM', '7 AM', '8 AM', '9 AM', '10 AM', '11 AM', 
             '12 PM', '1 PM', '2 PM', '3 PM', '4 PM', '5 PM', '6 PM', '7 PM', '8 PM', '9 PM', '10 PM', '11 PM']
    hourly_users = [0] * 24
    
    for activity in activities:
        if activity.get('action') == 'Login' and activity.get('timestamp'):
            try:
                activity_time = datetime.strptime(activity['timestamp'], "%Y-%m-%d %H:%M:%S")
                hour_index = activity_time.hour
                hourly_users[hour_index] += 1
            except:
                pass
    
    peak_hours = hours[6:24]
    peak_hourly_data = hourly_users[6:24]
    max_hourly = max(peak_hourly_data) if peak_hourly_data and max(peak_hourly_data) > 0 else 1
    
    theme = request.cookies.get('theme', 'light')
    language = request.cookies.get('language', 'english')
    total_revenue = sum(revenue_data)
    
    # Get payment summary
    payment_summary = get_payment_summary()
    
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
        technicians=technicians,
        week_days=week_days,
        week_data=week_data,
        max_week=max_week,
        months=months,
        revenue_data=revenue_data,
        max_revenue=max_revenue,
        hours=peak_hours,
        hourly_users=peak_hourly_data,
        max_hourly=max_hourly,
        total_revenue=total_revenue,
        theme=theme,
        language=language,
        login_count=login_count,
        activities=activities[-10:],
        payment_summary=payment_summary,
        payments=payments,
        calculate_service_amount=calculate_service_amount
    )

# UPDATE REQUEST STATUS
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
            
            if status == 'completed' and req.get('technician_id'):
                # Unassign technician and update status
                for tech in technicians:
                    if tech['id'] == req['technician_id']:
                        if request_id in tech['assigned_requests']:
                            tech['assigned_requests'].remove(request_id)
                            # Update technician status (will become available if no more requests)
                            update_technician_status(tech['id'])
                        break
                req['technician_id'] = None
                req['technician_name'] = None
                req['technician_specialty'] = None
                req['technician_assigned_date'] = None
            
            log_activity(session['username'], "Updated Request", f"{request_id} -> {status}")
            break
    return redirect(url_for('admin_dashboard', section='requests'))

# GET AVAILABLE TECHNICIANS FOR A SERVICE
@app.route('/get_available_technicians/<request_id>')
@admin_required
def get_available_technicians(request_id):
    for req in service_requests:
        if req['id'] == request_id:
            service_text = req.get('service', '')
            available_techs = get_available_technicians_for_service(service_text)
            return jsonify([{
                'id': tech['id'],
                'name': tech['name'],
                'specialty': tech['specialty'],
                'rating': tech['rating']
            } for tech in available_techs])
    return jsonify([])

# ASSIGN TECHNICIAN TO REQUEST
@app.route('/assign_technician/<request_id>', methods=['POST'])
@admin_required
def assign_technician(request_id):
    technician_id = request.form.get('technician_id')
    if assign_technician_to_request(request_id, technician_id):
        return redirect(url_for('admin_dashboard', section='requests'))
    return "Failed to assign technician", 400

# ASSIGN TECHNICIAN TO REQUEST FROM TECHNICIAN SECTION
@app.route('/assign_technician_to_request', methods=['POST'])
@admin_required
def assign_technician_to_request_route():
    technician_id = request.form.get('technician_id')
    request_id = request.form.get('request_id')
    if technician_id and request_id:
        if assign_technician_to_request(request_id, technician_id):
            return redirect(url_for('admin_dashboard', section='technicians'))
    return "Failed to assign technician", 400

# UNASSIGN TECHNICIAN FROM REQUEST
@app.route('/unassign_technician/<request_id>', methods=['POST'])
@admin_required
def unassign_technician(request_id):
    if unassign_technician_from_request(request_id):
        return redirect(url_for('admin_dashboard', section='requests'))
    return "Failed to unassign technician", 400

# UPDATE TECHNICIAN STATUS (Manual override - optional)
@app.route('/update_technician_status/<int:technician_id>', methods=['POST'])
@admin_required
def update_technician_status_manual(technician_id):
    status = request.form.get('status')
    for tech in technicians:
        if tech['id'] == technician_id:
            tech['status'] = status
            log_activity(session.get('username'), "Updated Technician Status", f"{tech['name']} -> {status}")
            break
    return redirect(url_for('admin_dashboard', section='technicians'))

# ADD NEW TECHNICIAN
@app.route('/add_technician', methods=['POST'])
@admin_required
def add_technician():
    name = request.form.get('name')
    specialty = request.form.get('specialty')
    contact = request.form.get('contact')
    email = request.form.get('email')
    keywords = request.form.get('keywords', '')
    if name and specialty:
        add_new_technician(name, specialty, contact, email, keywords)
    return redirect(url_for('admin_dashboard', section='technicians'))

# DELETE TECHNICIAN
@app.route('/delete_technician/<int:technician_id>')
@admin_required
def delete_technician_route(technician_id):
    delete_technician(technician_id)
    return redirect(url_for('admin_dashboard', section='technicians'))

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