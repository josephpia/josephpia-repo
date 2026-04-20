from flask import Flask, render_template, request, redirect, url_for, session, abort, send_from_directory, make_response, jsonify
from functools import wraps
import hashlib
import os
from datetime import datetime, timedelta
import uuid
from collections import Counter
import re
import qrcode
from io import BytesIO
import base64
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from enum import Enum
import tempfile
import cloudinary
import cloudinary.uploader
import cloudinary.utils
import statistics

# ===== CLOUDINARY CONFIGURATION (REQUIRED FOR VERCEL) =====
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', ''),
    api_key=os.environ.get('CLOUDINARY_API_KEY', ''),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET', ''),
    secure=True
)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'secretkey123')

# ===== ENUMS AND CONSTANTS =====
class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"

class RequestStatus(Enum):
    PENDING = "pending"
    ONGOING = "ongoing"
    COMPLETED = "completed"

class TechnicianStatus(Enum):
    AVAILABLE = "available"
    BUSY = "busy"

class PaymentStatus(Enum):
    UNPAID = "unpaid"
    FOR_VERIFICATION = "for_verification"
    PENDING_CASH = "pending_cash"
    PAID = "paid"
    REJECTED = "rejected"

class PaymentMethod(Enum):
    ONLINE = "online"
    CASH = "cash"

class OnlinePaymentApp(Enum):
    GCASH = "GCash"
    PAYMAYA = "PayMaya"
    PAYPAL = "PayPal"
    BANK_TRANSFER = "Bank Transfer"


# ===== CONFIGURATION CLASS =====
class Config:
    """Configuration management using encapsulation"""
    def __init__(self):
        self._secret_key = os.environ.get('FLASK_SECRET_KEY', "secretkey123")
        self._profile_upload_folder = tempfile.gettempdir() + '/uploads/profiles'
        self._service_upload_folder = tempfile.gettempdir() + '/uploads/service_requests'
        self._allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        self._max_file_size = 5 * 1024 * 1024
        
        os.makedirs(self._profile_upload_folder, exist_ok=True)
        os.makedirs(self._service_upload_folder, exist_ok=True)
        
        self._service_prices = {
            'Appliances Repair': 800,
            'Plumbing Repair': 600,
            'Electrical Repair': 700,
            'Electronics Repair': 400,
            'General Repair': 500,
        }
        
        self._company_payment_accounts = {
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
    
    @property
    def secret_key(self):
        return self._secret_key
    
    @property
    def profile_upload_folder(self):
        return self._profile_upload_folder
    
    @property
    def service_upload_folder(self):
        return self._service_upload_folder
    
    @property
    def allowed_extensions(self):
        return self._allowed_extensions
    
    @property
    def max_file_size(self):
        return self._max_file_size
    
    @property
    def service_prices(self):
        return self._service_prices
    
    @property
    def company_payment_accounts(self):
        return self._company_payment_accounts
    
    def get_service_price(self, category: str) -> int:
        return self._service_prices.get(category, 500)


# ===== TRANSACTION CLASS =====
@dataclass
class Transaction:
    """Transaction class for completed services"""
    transaction_id: int
    request_id: str
    amount: float
    transaction_date: datetime
    payment_method: str
    username: str
    category: str


# ===== USER CLASS =====
class User:
    """User class with encapsulation"""
    def __init__(self, username: str, password: str, firstname: str, lastname: str, 
                 email: str, role: str = "user", middlename: str = "", age: str = "",
                 address: str = "", birthdate: str = "", cellphone: str = ""):
        self._username = username
        self._password = self._hash_password(password)
        self._firstname = firstname
        self._lastname = lastname
        self._middlename = middlename
        self._age = age
        self._address = address
        self._birthdate = birthdate
        self._email = email
        self._cellphone = cellphone
        self._role = role
        self._profile_pic = None
        self._profile_pic_url = None
        self._join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._total_requests = 0
    
    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password: str) -> bool:
        return self._password == hashlib.sha256(password.encode()).hexdigest()
    
    @property
    def username(self):
        return self._username
    
    @property
    def firstname(self):
        return self._firstname
    
    @property
    def lastname(self):
        return self._lastname
    
    @property
    def middlename(self):
        return self._middlename
    
    @property
    def age(self):
        return self._age
    
    @property
    def address(self):
        return self._address
    
    @property
    def birthdate(self):
        return self._birthdate
    
    @property
    def email(self):
        return self._email
    
    @property
    def cellphone(self):
        return self._cellphone
    
    @property
    def role(self):
        return self._role
    
    @property
    def profile_pic(self):
        return self._profile_pic
    
    @property
    def profile_pic_url(self):
        return self._profile_pic_url
    
    @property
    def join_date(self):
        return self._join_date
    
    @property
    def total_requests(self):
        return self._total_requests
    
    @profile_pic.setter
    def profile_pic(self, value):
        self._profile_pic = value
    
    @profile_pic_url.setter
    def profile_pic_url(self, value):
        self._profile_pic_url = value
    
    def increment_requests(self):
        self._total_requests += 1
    
    def to_dict(self) -> Dict:
        return {
            "username": self._username,
            "firstname": self._firstname,
            "middlename": self._middlename,
            "lastname": self._lastname,
            "age": self._age,
            "address": self._address,
            "birthdate": self._birthdate,
            "email": self._email,
            "cellphone": self._cellphone,
            "password": self._password,
            "role": self._role,
            "profile_pic": self._profile_pic,
            "profile_pic_url": self._profile_pic_url,
            "join_date": self._join_date,
            "total_requests": self._total_requests
        }


# ===== TECHNICIAN CLASS =====
class Technician:
    """Technician class with encapsulation"""
    def __init__(self, id: int, name: str, specialty: str, contact: str, email: str, 
                 keywords: List[str] = None, rating: float = 5.0):
        self._id = id
        self._name = name
        self._specialty = specialty
        self._contact = contact
        self._email = email
        self._keywords = keywords or []
        self._status = TechnicianStatus.AVAILABLE
        self._rating = rating
        self._assigned_requests = []
    
    @property
    def id(self):
        return self._id
    
    @property
    def name(self):
        return self._name
    
    @property
    def specialty(self):
        return self._specialty
    
    @property
    def contact(self):
        return self._contact
    
    @property
    def email(self):
        return self._email
    
    @property
    def keywords(self):
        return self._keywords
    
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value):
        self._status = value
    
    @property
    def rating(self):
        return self._rating
    
    @property
    def assigned_requests(self):
        return self._assigned_requests
    
    def can_handle_service(self, service_text: str) -> bool:
        service_text_lower = service_text.lower()
        for keyword in self._keywords:
            if keyword in service_text_lower:
                return True
        return False
    
    def assign_request(self, request_id: str):
        self._assigned_requests.append(request_id)
        if len(self._assigned_requests) >= 1:
            self._status = TechnicianStatus.BUSY
    
    def unassign_request(self, request_id: str):
        if request_id in self._assigned_requests:
            self._assigned_requests.remove(request_id)
        if len(self._assigned_requests) == 0:
            self._status = TechnicianStatus.AVAILABLE
    
    def to_dict(self) -> Dict:
        return {
            "id": self._id,
            "name": self._name,
            "specialty": self._specialty,
            "keywords": self._keywords,
            "status": self._status.value,
            "rating": self._rating,
            "contact": self._contact,
            "email": self._email,
            "assigned_requests": self._assigned_requests
        }


# ===== SERVICE REQUEST CLASS =====
class ServiceRequest:
    """Service Request class with encapsulation"""
    def __init__(self, request_id: str, username: str, service: str, category: str, 
                 service_photo: str = None, service_photo_url: str = None):
        self._id = request_id
        self._username = username
        self._service = service
        self._category = category
        self._status = RequestStatus.PENDING
        self._date_requested = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._service_photo = service_photo
        self._service_photo_url = service_photo_url
        self._has_photo = bool(service_photo_url)
        self._admin_notes = ""
        self._last_update = self._date_requested
        self._technician_id = None
        self._technician_name = None
        self._technician_specialty = None
        self._technician_contact = None
        self._technician_assigned_date = None
        self._payment_status = PaymentStatus.UNPAID
        self._payment_method = None
        self._payment_amount = None
        self._payment_id = None
        self._reference_number = None
        self._transaction_id = None
        self._completion_date = None
    
    @property
    def id(self):
        return self._id
    
    @property
    def username(self):
        return self._username
    
    @property
    def service(self):
        return self._service
    
    @service.setter
    def service(self, value):
        self._service = value
        self._last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @property
    def category(self):
        return self._category
    
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value):
        self._status = value
        self._last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if value == RequestStatus.COMPLETED:
            self._completion_date = datetime.now()
    
    @property
    def date_requested(self):
        return self._date_requested
    
    @property
    def service_photo(self):
        return self._service_photo
    
    @property
    def service_photo_url(self):
        return self._service_photo_url
    
    @property
    def has_photo(self):
        return self._has_photo
    
    @property
    def admin_notes(self):
        return self._admin_notes
    
    @admin_notes.setter
    def admin_notes(self, value):
        self._admin_notes = value
    
    @property
    def last_update(self):
        return self._last_update
    
    @property
    def technician_id(self):
        return self._technician_id
    
    @technician_id.setter
    def technician_id(self, value):
        self._technician_id = value
    
    @property
    def technician_name(self):
        return self._technician_name
    
    @technician_name.setter
    def technician_name(self, value):
        self._technician_name = value
    
    @property
    def technician_specialty(self):
        return self._technician_specialty
    
    @technician_specialty.setter
    def technician_specialty(self, value):
        self._technician_specialty = value
    
    @property
    def technician_contact(self):
        return self._technician_contact
    
    @technician_contact.setter
    def technician_contact(self, value):
        self._technician_contact = value
    
    @property
    def technician_assigned_date(self):
        return self._technician_assigned_date
    
    @technician_assigned_date.setter
    def technician_assigned_date(self, value):
        self._technician_assigned_date = value
    
    @property
    def payment_status(self):
        return self._payment_status
    
    @payment_status.setter
    def payment_status(self, value):
        self._payment_status = value
    
    @property
    def payment_method(self):
        return self._payment_method
    
    @payment_method.setter
    def payment_method(self, value):
        self._payment_method = value
    
    @property
    def payment_amount(self):
        return self._payment_amount
    
    @payment_amount.setter
    def payment_amount(self, value):
        self._payment_amount = value
    
    @property
    def payment_id(self):
        return self._payment_id
    
    @payment_id.setter
    def payment_id(self, value):
        self._payment_id = value
    
    @property
    def reference_number(self):
        return self._reference_number
    
    @reference_number.setter
    def reference_number(self, value):
        self._reference_number = value
    
    @property
    def transaction_id(self):
        return self._transaction_id
    
    @transaction_id.setter
    def transaction_id(self, value):
        self._transaction_id = value
    
    @property
    def completion_date(self):
        return self._completion_date
    
    def assign_technician(self, technician: Technician):
        self._technician_id = technician.id
        self._technician_name = technician.name
        self._technician_specialty = technician.specialty
        self._technician_contact = technician.contact
        self._technician_assigned_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._status = RequestStatus.ONGOING
    
    def unassign_technician(self):
        self._technician_id = None
        self._technician_name = None
        self._technician_specialty = None
        self._technician_contact = None
        self._technician_assigned_date = None
    
    def set_payment_info(self, payment_method: str, amount: int, payment_id: str, 
                        reference_number: str = None, transaction_id: str = None):
        self._payment_method = payment_method
        self._payment_amount = amount
        self._payment_id = payment_id
        self._reference_number = reference_number
        self._transaction_id = transaction_id
        
        if payment_method == 'online':
            self._payment_status = PaymentStatus.FOR_VERIFICATION
        else:
            self._payment_status = PaymentStatus.PENDING_CASH
    
    def to_dict(self) -> Dict:
        return {
            "id": self._id,
            "username": self._username,
            "service": self._service,
            "category": self._category,
            "status": self._status.value,
            "date_requested": self._date_requested,
            "service_photo": self._service_photo,
            "service_photo_url": self._service_photo_url,
            "has_photo": self._has_photo,
            "admin_notes": self._admin_notes,
            "last_update": self._last_update,
            "technician_id": self._technician_id,
            "technician_name": self._technician_name,
            "technician_specialty": self._technician_specialty,
            "technician_contact": self._technician_contact,
            "technician_assigned_date": self._technician_assigned_date,
            "payment_status": self._payment_status.value if self._payment_status else "unpaid",
            "payment_method": self._payment_method,
            "payment_amount": self._payment_amount,
            "payment_id": self._payment_id,
            "reference_number": self._reference_number,
            "transaction_id": self._transaction_id,
            "completion_date": self._completion_date.strftime("%Y-%m-%d %H:%M:%S") if self._completion_date else None
        }


# ===== PAYMENT CLASS =====
class Payment:
    """Payment class with encapsulation"""
    def __init__(self, payment_id: str, request_id: str, username: str, amount: int, 
                 payment_method: str, reference_number: str = None, online_app: str = None):
        self._payment_id = payment_id
        self._request_id = request_id
        self._username = username
        self._amount = amount
        self._payment_method = payment_method
        self._online_app = online_app
        self._reference_number = reference_number
        self._status = PaymentStatus.FOR_VERIFICATION if payment_method == 'online' else PaymentStatus.PENDING_CASH
        self._payment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._transaction_id = f"TXN-{username[:3].upper()}{payment_id}{datetime.now().strftime('%m%d%H%M')}"
        self._verified_date = None
        self._verified_by = None
        self._rejected_date = None
        self._rejected_by = None
        self._cash_confirmed_date = None
        self._confirmed_by = None
    
    @property
    def payment_id(self):
        return self._payment_id
    
    @property
    def request_id(self):
        return self._request_id
    
    @property
    def username(self):
        return self._username
    
    @property
    def amount(self):
        return self._amount
    
    @property
    def payment_method(self):
        return self._payment_method
    
    @property
    def online_app(self):
        return self._online_app
    
    @property
    def reference_number(self):
        return self._reference_number
    
    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, value):
        self._status = value
    
    @property
    def payment_date(self):
        return self._payment_date
    
    @property
    def transaction_id(self):
        return self._transaction_id
    
    @property
    def verified_date(self):
        return self._verified_date
    
    @property
    def verified_by(self):
        return self._verified_by
    
    @property
    def rejected_date(self):
        return self._rejected_date
    
    @property
    def rejected_by(self):
        return self._rejected_by
    
    @property
    def cash_confirmed_date(self):
        return self._cash_confirmed_date
    
    def approve(self, verified_by: str):
        self._status = PaymentStatus.PAID
        self._verified_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._verified_by = verified_by
    
    def reject(self, rejected_by: str):
        self._status = PaymentStatus.REJECTED
        self._rejected_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._rejected_by = rejected_by
    
    def confirm_cash(self, confirmed_by: str):
        self._status = PaymentStatus.PAID
        self._cash_confirmed_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._confirmed_by = confirmed_by
    
    def to_dict(self) -> Dict:
        return {
            "payment_id": self._payment_id,
            "request_id": self._request_id,
            "username": self._username,
            "amount": self._amount,
            "payment_method": self._payment_method,
            "online_app": self._online_app,
            "reference_number": self._reference_number,
            "status": self._status.value if self._status else "pending",
            "payment_date": self._payment_date,
            "transaction_id": self._transaction_id,
            "verified_date": self._verified_date,
            "verified_by": self._verified_by,
            "rejected_date": self._rejected_date,
            "rejected_by": self._rejected_by,
            "cash_confirmed_date": self._cash_confirmed_date,
            "confirmed_by": self._confirmed_by
        }


# ===== ACTIVITY LOG CLASS =====
class ActivityLog:
    """Activity Log class"""
    def __init__(self, activity_id: int, username: str, action: str, details: str = ""):
        self._id = activity_id
        self._username = username
        self._action = action
        self._details = details
        self._timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    @property
    def id(self):
        return self._id
    
    @property
    def username(self):
        return self._username
    
    @property
    def action(self):
        return self._action
    
    @property
    def details(self):
        return self._details
    
    @property
    def timestamp(self):
        return self._timestamp
    
    def to_dict(self) -> Dict:
        return {
            "id": self._id,
            "username": self._username,
            "action": self._action,
            "details": self._details,
            "timestamp": self._timestamp
        }


# ===== SERVICE HISTORY MANAGER CLASS =====
class ServiceHistoryManager:
    """Service History Manager for tracking and filtering requests"""
    def __init__(self):
        self._transactions: List[Transaction] = []
        self._next_transaction_id = 1
    
    def create_transaction(self, request: ServiceRequest) -> Optional[Transaction]:
        """Create a transaction when service is completed and paid"""
        if request.status == RequestStatus.COMPLETED and request.payment_status == PaymentStatus.PAID:
            transaction = Transaction(
                transaction_id=self._next_transaction_id,
                request_id=request.id,
                amount=request.payment_amount or 0,
                transaction_date=request.completion_date or datetime.now(),
                payment_method=request.payment_method or "unknown",
                username=request.username,
                category=request.category
            )
            self._transactions.append(transaction)
            self._next_transaction_id += 1
            return transaction
        return None
    
    @property
    def transactions(self):
        return self._transactions


# ===== FILE MANAGER CLASS WITH CLOUDINARY =====
class CloudinaryFileManager:
    """Cloudinary file management class for Vercel deployment"""
    def __init__(self, config: Config):
        self._config = config
        self._is_configured = bool(
            os.environ.get('CLOUDINARY_CLOUD_NAME') and 
            os.environ.get('CLOUDINARY_API_KEY') and 
            os.environ.get('CLOUDINARY_API_SECRET')
        )
        if not self._is_configured:
            print("⚠️ WARNING: Cloudinary not configured!")
    
    def allowed_file(self, filename: str) -> bool:
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self._config.allowed_extensions
    
    def upload_file(self, file, folder_type: str) -> Optional[str]:
        if not self._is_configured:
            print("❌ Cloudinary not configured")
            return None
            
        try:
            file.seek(0)
            folder = f"servicehub/{folder_type}"
            
            upload_result = cloudinary.uploader.upload(
                file,
                folder=folder,
                resource_type="auto",
                transformation=[
                    {'quality': 'auto:good'},
                    {'fetch_format': 'auto'}
                ]
            )
            
            if upload_result and 'secure_url' in upload_result:
                return upload_result['secure_url']
            return None
                
        except Exception as e:
            print(f"❌ Cloudinary upload error: {str(e)}")
            return None
    
    def delete_file(self, public_id: str):
        try:
            if public_id:
                cloudinary.uploader.destroy(public_id)
        except Exception as e:
            print(f"Cloudinary delete error: {e}")


# ===== QR CODE GENERATOR CLASS =====
class QRCodeGenerator:
    """QR Code generation class"""
    @staticmethod
    def generate_payment_qr(payment_method: str, amount: int, request_id: str, username: str) -> Dict:
        payment_data = QRCodeGenerator._create_payment_data(payment_method, amount, request_id, username)
        
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(payment_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {'qr_code': img_str, 'payment_data': payment_data}
    
    @staticmethod
    def _create_payment_data(payment_method: str, amount: int, request_id: str, username: str) -> str:
        current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        templates = {
            'GCash': f"""GCash Payment
Amount: ₱{amount}
Account: 0999-888-7777
Account Name: ServiceHub PH
Reference: {request_id}
Customer: {username}
Date: {current_date}""",
            'PayMaya': f"""PayMaya Payment
Amount: ₱{amount}
Account: 0988-777-6666
Account Name: ServiceHub
Reference: {request_id}
Customer: {username}
Date: {current_date}""",
            'PayPal': f"""PayPal Payment
Amount: ₱{amount}
Email: payments@servicehub.com
Account Name: ServiceHub Solutions
Reference: {request_id}
Customer: {username}
Date: {current_date}""",
            'Bank Transfer': f"""Bank Transfer Payment
Amount: ₱{amount}
Bank: BDO
Account: 0045-1234-5678
Account Name: ServiceHub Solutions Inc.
Reference: {request_id}
Customer: {username}
Date: {current_date}"""
        }
        
        return templates.get(payment_method, f"Payment Amount: ₱{amount}\nReference: {request_id}\nCustomer: {username}")


# ===== SERVICE HUB MANAGER CLASS =====
class ServiceHubManager:
    """Main application manager class"""
    def __init__(self, config: Config):
        self._config = config
        self._users: Dict[str, User] = {}
        self._technicians: List[Technician] = []
        self._service_requests: List[ServiceRequest] = []
        self._payments: List[Payment] = []
        self._activities: List[ActivityLog] = []
        self._file_manager = CloudinaryFileManager(config)
        self._qr_generator = QRCodeGenerator()
        self._service_history_manager = ServiceHistoryManager()
        self._request_id_counter = 1000
        self._payment_id_counter = 1
        self._activity_id_counter = 1
        self._login_count = 0
        
        self._init_default_admin()
        self._init_default_technicians()
    
    def _init_default_admin(self):
        admin = User("admin", "1234", "System", "Administrator", "admin@system.com", "admin")
        self._users["admin"] = admin
    
    def _init_default_technicians(self):
        default_techs = [
            (1, "John Santos", "Appliances Repair", "09123456789", "john@servicehub.com", 
             ["aircon", "air conditioner", "ac", "cooling", "refrigerant", "compressor"], 4.8),
            (2, "Maria Reyes", "Plumbing Repair", "09123456780", "maria@servicehub.com",
             ["plumbing", "pipe", "leak", "faucet", "toilet", "drain", "water"], 4.9),
            (3, "Robert Gomez", "Electrical Repair", "09123456781", "robert@servicehub.com",
             ["electrical", "wiring", "circuit", "breaker", "light", "outlet", "switch", "power"], 4.7),
            (4, "Cristina Lopez", "Electronics Repair", "09123456782", "cristina@servicehub.com",
             ["phones", "tablets", "headphones", "game consoles", "smartwatches"], 4.6),
            (5, "Robert Martinez", "Appliances Repair", "09123456789", "robert@servicehub.com",
             ["aircon", "air conditioner", "ac", "cooling", "refrigerant", "compressor"], 4.9)
        ]
        
        for tech_data in default_techs:
            technician = Technician(*tech_data)
            self._technicians.append(technician)
    
    def _generate_request_id(self) -> str:
        self._request_id_counter += 1
        return f"SRQ-{self._request_id_counter}"
    
    def _generate_payment_id(self) -> str:
        payment_id = f"PAY-{self._payment_id_counter}"
        self._payment_id_counter += 1
        return payment_id
    
    def log_activity(self, username: str, action: str, details: str = ""):
        activity = ActivityLog(self._activity_id_counter, username, action, details)
        self._activities.append(activity)
        self._activity_id_counter += 1
    
    def create_user(self, username: str, password: str, firstname: str, lastname: str, 
                   email: str, **kwargs) -> bool:
        if username in self._users:
            return False
        
        user = User(username, password, firstname, lastname, email, "user", **kwargs)
        self._users[username] = user
        self.log_activity(username, "Account Created", "New user registered")
        return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        if username not in self._users:
            return None
        
        user = self._users[username]
        if user.check_password(password):
            self._login_count += 1
            self.log_activity(username, "Login", "User logged in successfully")
            return user
        
        return None
    
    def detect_service_category(self, service_text: str) -> str:
        service_text_lower = service_text.lower()
        
        for technician in self._technicians:
            if technician.can_handle_service(service_text):
                return technician.specialty
        
        return "General Repair"
    
    def get_available_technicians_for_service(self, service_text: str) -> List[Technician]:
        available_techs = []
        
        for tech in self._technicians:
            if tech.status == TechnicianStatus.AVAILABLE and tech.can_handle_service(service_text):
                available_techs.append(tech)
        
        return available_techs
    
    def create_service_request(self, username: str, service: str, service_photo_url: str = None) -> Optional[ServiceRequest]:
        if username not in self._users:
            return None
        
        category = self.detect_service_category(service)
        request_id = self._generate_request_id()
        
        service_request = ServiceRequest(request_id, username, service, category, None, service_photo_url)
        self._service_requests.append(service_request)
        
        self._users[username].increment_requests()
        
        self.log_activity(username, "Service Request", f"{category}: {service[:50]}")
        return service_request
    
    def assign_technician_to_request(self, request_id: str, technician_id: int) -> bool:
        service_request = None
        for req in self._service_requests:
            if req.id == request_id:
                service_request = req
                break
        
        if not service_request:
            return False
        
        technician = None
        for tech in self._technicians:
            if tech.id == technician_id:
                technician = tech
                break
        
        if not technician:
            return False
        
        service_request.assign_technician(technician)
        technician.assign_request(request_id)
        
        self.log_activity(session.get('username'), "Assigned Technician", 
                         f"Request {request_id} -> {technician.name} ({technician.specialty}) - Contact: {technician.contact}")
        return True
    
    def unassign_technician_from_request(self, request_id: str) -> bool:
        service_request = None
        for req in self._service_requests:
            if req.id == request_id:
                service_request = req
                break
        
        if not service_request or not service_request.technician_id:
            return False
        
        technician = None
        for tech in self._technicians:
            if tech.id == service_request.technician_id:
                technician = tech
                break
        
        if technician:
            technician.unassign_request(request_id)
        
        service_request.unassign_technician()
        self.log_activity(session.get('username'), "Unassigned Technician", f"Request {request_id}")
        return True
    
    def add_technician(self, name: str, specialty: str, contact: str, email: str, keywords: str = "") -> Technician:
        new_id = max([t.id for t in self._technicians]) + 1 if self._technicians else 1
        
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
        
        technician = Technician(new_id, name, specialty, contact, email, tech_keywords)
        self._technicians.append(technician)
        self.log_activity(session.get('username'), "Added Technician", f"Added {name} ({specialty})")
        return technician
    
    def delete_technician(self, technician_id: int) -> bool:
        for tech in self._technicians:
            if tech.id == technician_id:
                for request_id in tech.assigned_requests:
                    for req in self._service_requests:
                        if req.id == request_id:
                            req.unassign_technician()
                            break
                
                self._technicians = [t for t in self._technicians if t.id != technician_id]
                self.log_activity(session.get('username'), "Deleted Technician", f"Deleted ID: {technician_id}")
                return True
        return False
    
    def create_payment(self, request_id: str, username: str, payment_method: str, 
                      amount: int, reference_number: str = None, online_app: str = None) -> Optional[Payment]:
        service_request = None
        for req in self._service_requests:
            if req.id == request_id and req.username == username:
                service_request = req
                break
        
        if not service_request:
            return None
        
        payment_id = self._generate_payment_id()
        payment = Payment(payment_id, request_id, username, amount, payment_method, 
                         reference_number, online_app)
        
        self._payments.append(payment)
        
        service_request.set_payment_info(payment_method, amount, payment_id, reference_number, payment.transaction_id)
        
        self.log_activity(username, "Payment Submitted", f"Request {request_id} - {payment_method}")
        return payment
    
    def verify_payment(self, payment_id: str, verified_by: str, action: str = 'approve') -> bool:
        for payment in self._payments:
            if payment.payment_id == payment_id:
                if action == 'approve':
                    payment.approve(verified_by)
                    for req in self._service_requests:
                        if req.id == payment.request_id:
                            req.payment_status = PaymentStatus.PAID
                            if req.status == RequestStatus.COMPLETED:
                                self._service_history_manager.create_transaction(req)
                            break
                    self.log_activity(verified_by, "Payment Verified", f"Payment {payment_id} approved")
                else:
                    payment.reject(verified_by)
                    self.log_activity(verified_by, "Payment Rejected", f"Payment {payment_id} rejected")
                return True
        return False
    
    def confirm_cash_payment(self, request_id: str, confirmed_by: str) -> bool:
        for req in self._service_requests:
            if req.id == request_id:
                if req.payment_status == PaymentStatus.PENDING_CASH:
                    req.payment_status = PaymentStatus.PAID
                    for payment in self._payments:
                        if payment.request_id == request_id:
                            payment.confirm_cash(confirmed_by)
                            break
                    if req.status == RequestStatus.COMPLETED:
                        self._service_history_manager.create_transaction(req)
                    self.log_activity(confirmed_by, "Cash Payment Confirmed", f"Request {request_id}")
                    return True
        return False
    
    def delete_user(self, username: str) -> bool:
        if username == 'admin' or username not in self._users:
            return False
        
        self._service_requests = [req for req in self._service_requests if req.username != username]
        del self._users[username]
        
        self.log_activity(session.get('username'), "Deleted User", username)
        return True
    
    def delete_service_request(self, request_id: str) -> bool:
        self._service_requests = [req for req in self._service_requests if req.id != request_id]
        self.log_activity(session.get('username'), "Deleted Request", request_id)
        return True
    
    def get_payment_summary(self) -> Dict:
        total_revenue = sum(p.amount for p in self._payments if p.status == PaymentStatus.PAID)
        online_revenue = sum(p.amount for p in self._payments 
                           if p.status == PaymentStatus.PAID and p.payment_method == 'online')
        cash_revenue = sum(p.amount for p in self._payments 
                          if p.status == PaymentStatus.PAID and p.payment_method == 'cash')
        pending_verification = sum(p.amount for p in self._payments 
                                  if p.status == PaymentStatus.FOR_VERIFICATION)
        pending_cash_total = sum(p.amount for p in self._payments 
                                if p.status == PaymentStatus.PENDING_CASH)
        
        return {
            'total_revenue': total_revenue,
            'online_revenue': online_revenue,
            'cash_revenue': cash_revenue,
            'pending_verification': pending_verification,
            'pending_cash_total': pending_cash_total,
            'total_transactions': len(self._payments)
        }
    
    def get_service_status_summary(self) -> Dict:
        """Get summary of REAL requests by status"""
        return {
            'pending': len([r for r in self._service_requests if r.status == RequestStatus.PENDING]),
            'ongoing': len([r for r in self._service_requests if r.status == RequestStatus.ONGOING]),
            'completed': len([r for r in self._service_requests if r.status == RequestStatus.COMPLETED]),
            'total': len(self._service_requests)
        }
    
    def get_real_transactions(self, limit: int = 5) -> List[Dict]:
        """Get REAL completed and paid transactions"""
        transactions = []
        for req in self._service_requests:
            if req.status == RequestStatus.COMPLETED and req.payment_status == PaymentStatus.PAID:
                transactions.append({
                    'transaction_id': req.id,
                    'request_id': req.id,
                    'username': req.username,
                    'category': req.category,
                    'amount': req.payment_amount or 0,
                    'transaction_date': req.completion_date or datetime.now()
                })
        transactions.sort(key=lambda x: x['transaction_date'], reverse=True)
        return transactions[:limit]
    
    def get_user_requests(self, username: str) -> List[Dict]:
        return [req.to_dict() for req in self._service_requests if req.username == username]
    
    def get_all_requests(self) -> List[Dict]:
        return [req.to_dict() for req in self._service_requests]
    
    def get_all_technicians(self) -> List[Dict]:
        return [tech.to_dict() for tech in self._technicians]
    
    def get_all_users(self) -> Dict:
        return {username: user.to_dict() for username, user in self._users.items()}
    
    def get_activities(self, limit: int = 10) -> List[Dict]:
        return [activity.to_dict() for activity in self._activities[-limit:]]
    
    def get_technician_by_id(self, technician_id: int) -> Optional[Technician]:
        for tech in self._technicians:
            if tech.id == technician_id:
                return tech
        return None
    
    def get_request_by_id(self, request_id: str) -> Optional[ServiceRequest]:
        for req in self._service_requests:
            if req.id == request_id:
                return req
        return None
    
    @property
    def login_count(self) -> int:
        return self._login_count
    
    @property
    def service_prices(self):
        return self._config.service_prices
    
    @property
    def service_history_manager(self):
        return self._service_history_manager
    
    def calculate_service_amount(self, category: str) -> int:
        return self._config.get_service_price(category)


# ===== FLASK APPLICATION SETUP =====
config = Config()
manager = ServiceHubManager(config)

app.config['PROFILE_UPLOAD_FOLDER'] = config.profile_upload_folder
app.config['SERVICE_UPLOAD_FOLDER'] = config.service_upload_folder
app.config['MAX_CONTENT_LENGTH'] = config.max_file_size

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

# ===== LOGIN ROUTE =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('username'):
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    
    message = ""
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            message = "Please enter both username and password"
        else:
            user = manager.authenticate_user(username, password)
            if user:
                session['username'] = user.username
                session['role'] = user.role
                
                if user.role == "admin":
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('user_dashboard'))
            else:
                message = "Invalid username or password"
    
    return render_template('login.html', message=message)

# ===== SIGNUP ROUTE =====
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
        
        if len(username) < 3:
            message = "Username must be at least 3 characters"
        elif len(password) < 4:
            message = "Password must be at least 4 characters"
        elif password != confirm_password:
            message = "Passwords do not match"
        elif not all([firstname, lastname, age, address, birthdate, email, cellphone]):
            message = "All fields are required"
        else:
            if manager.create_user(username, password, firstname, lastname, email,
                                  middlename=middlename, age=age, address=address,
                                  birthdate=birthdate, cellphone=cellphone):
                return redirect(url_for('login'))
            else:
                message = "Username already exists"
    
    return render_template('signup.html', message=message)

# ===== USER DASHBOARD ROUTE =====
@app.route('/userdashboard', methods=['GET', 'POST'])
@login_required
def user_dashboard():
    if session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    profile_message = ""
    service_message = ""
    
    if request.method == 'POST' and 'profile_photo' in request.files:
        photo = request.files['profile_photo']
        if photo.filename == '':
            profile_message = "No file selected"
        else:
            file_manager = CloudinaryFileManager(config)
            if not file_manager.allowed_file(photo.filename):
                profile_message = "Invalid file type"
            else:
                uploaded_url = file_manager.upload_file(photo, 'profiles')
                if uploaded_url:
                    user = manager._users.get(session['username'])
                    if user:
                        user.profile_pic_url = uploaded_url
                    profile_message = "Profile photo uploaded successfully!"
                    manager.log_activity(session['username'], "Profile Photo Upload", uploaded_url)
                else:
                    profile_message = "Upload failed. Please check Cloudinary configuration."
    
    elif request.method == 'POST' and 'service' in request.form:
        service = request.form.get('service', '').strip()
        service_photo_url = None
        
        if not service:
            service_message = "Please enter your service request"
        else:
            if 'service_photo' in request.files:
                photo = request.files['service_photo']
                if photo and photo.filename != '':
                    file_manager = CloudinaryFileManager(config)
                    if file_manager.allowed_file(photo.filename):
                        try:
                            service_photo_url = file_manager.upload_file(photo, 'service_requests')
                        except Exception as e:
                            print(f"Upload error: {str(e)}")
            
            service_request = manager.create_service_request(session['username'], service, service_photo_url)
            if service_request:
                service_message = "Service request submitted successfully!"
            else:
                service_message = "Failed to submit request"
    
    user = manager._users.get(session['username'])
    user_requests = manager.get_user_requests(session['username'])
    payment_success = request.args.get('payment_success')
    payment_amount = request.args.get('amount')
    payment_method = request.args.get('method')
    pay_request = request.args.get('pay_request')
    
    return render_template('userdashboard.html',
                         profile_message=profile_message,
                         service_message=service_message,
                         user_requests=user_requests,
                         user=user.to_dict() if user else {},
                         calculate_service_amount=manager.calculate_service_amount,
                         payment_success=payment_success,
                         payment_amount=payment_amount,
                         payment_method=payment_method,
                         pay_request=pay_request)

# ===== PAYMENT ROUTES =====
@app.route('/create_payment/<request_id>', methods=['GET'])
@login_required
def create_payment(request_id):
    service_req = manager.get_request_by_id(request_id)
    if not service_req or service_req.username != session['username']:
        return "Request not found", 404
    
    amount = manager.calculate_service_amount(service_req.category)
    return render_template('payment.html', request_id=request_id, amount=amount)

@app.route('/process_payment_direct', methods=['POST'])
@login_required
def process_payment_direct():
    request_id = request.form.get('request_id')
    payment_method = request.form.get('payment_method')
    online_app = request.form.get('online_app')
    reference_number = request.form.get('reference_number', '')
    amount = request.form.get('amount')
    
    service_req = manager.get_request_by_id(request_id)
    if not service_req or service_req.username != session['username']:
        return "Request not found", 404
    
    amount_int = int(amount)
    payment = manager.create_payment(request_id, session['username'], payment_method, 
                                     amount_int, reference_number, online_app)
    
    if not payment:
        return "Failed to create payment", 400
    
    if payment_method == 'online':
        return render_template('success.html',
            icon='✅',
            title='Payment Submitted!',
            amount=amount,
            method=online_app,
            reference=reference_number,
            transaction=payment.transaction_id,
            message='Pending verification by admin.')
    else:
        return render_template('success.html',
            icon='💵',
            title='Cash Payment Selected!',
            amount=amount,
            method='Cash',
            reference='',
            transaction='',
            message='Please prepare exact amount for the technician upon arrival.')

@app.route('/verify_payment/<payment_id>', methods=['POST'])
@admin_required
def verify_payment(payment_id):
    action = request.form.get('action', 'approve')
    if manager.verify_payment(payment_id, session['username'], action):
        return redirect(url_for('admin_dashboard', section='payments'))
    return redirect(url_for('admin_dashboard', section='payments', error='not_found'))

@app.route('/admin/confirm_cash_payment/<request_id>', methods=['POST'])
@admin_required
def confirm_cash_payment(request_id):
    if manager.confirm_cash_payment(request_id, session['username']):
        return redirect(url_for('admin_dashboard', section='payments'))
    return redirect(url_for('admin_dashboard', section='payments'))

@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    request_id = request.form.get('request_id')
    payment_method = request.form.get('payment_method')
    online_app = request.form.get('online_app', None)
    reference_number = request.form.get('reference_number', '')
    
    service_req = manager.get_request_by_id(request_id)
    if not service_req or service_req.username != session['username']:
        return "Request not found", 404
    
    if service_req.payment_status == PaymentStatus.PAID:
        return "Already paid", 400
    
    amount = manager.calculate_service_amount(service_req.category)
    payment = manager.create_payment(request_id, session['username'], payment_method, 
                                     amount, reference_number, online_app)
    
    if not payment:
        return "Failed to create payment", 400
    
    return redirect(url_for('user_dashboard', payment_success='true', amount=amount, method=payment_method))

# ===== QR CODE GENERATION =====
@app.route('/generate_qr/<payment_method>/<amount>/<request_id>')
@login_required
def generate_qr(payment_method, amount, request_id):
    qr_data = QRCodeGenerator.generate_payment_qr(payment_method, int(amount), request_id, session['username'])
    return jsonify(qr_data)

# ===== REQUEST MANAGEMENT ROUTES =====
@app.route('/edit_request/<request_id>', methods=['GET', 'POST'])
@login_required
def edit_request(request_id):
    service_req = manager.get_request_by_id(request_id)
    
    if not service_req or service_req.username != session['username']:
        return "Request not found", 404
    
    if service_req.status in [RequestStatus.ONGOING, RequestStatus.COMPLETED]:
        return "Cannot edit request that is ongoing or completed", 403
    
    if request.method == 'POST':
        new_service = request.form.get('service', '').strip()
        if new_service:
            service_req.service = new_service
            manager.log_activity(session['username'], "Edited Request", request_id)
            return redirect(url_for('user_dashboard'))
    
    return render_template('edit_request.html', request=service_req)

@app.route('/delete_my_request/<request_id>')
@login_required
def delete_my_request(request_id):
    service_req = manager.get_request_by_id(request_id)
    
    if service_req and service_req.username == session['username']:
        if service_req.status != RequestStatus.PENDING:
            return "Cannot delete request that is ongoing or completed", 403
        
        if manager.delete_service_request(request_id):
            return redirect(url_for('user_dashboard'))
    
    return redirect(url_for('user_dashboard'))

# ===== PHOTO VIEWING ROUTES =====
@app.route('/view_profile_photo/<username>')
@login_required
def view_profile_photo(username):
    user = manager._users.get(username)
    if not user or not user.profile_pic_url:
        return "No photo", 404
    return redirect(user.profile_pic_url)

@app.route('/view_service_photo/<request_id>')
@admin_required
def view_service_photo(request_id):
    service_req = manager.get_request_by_id(request_id)
    if not service_req or not service_req.service_photo_url:
        return "No photo", 404
    return redirect(service_req.service_photo_url)

# ===== TEST ROUTES =====
@app.route('/test-cloudinary')
def test_cloudinary():
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
    if not cloud_name:
        return "❌ Cloudinary NOT configured!"
    return f"✅ Cloudinary configured with cloud name: {cloud_name}"

# ===== SERVICE HISTORY & REPORTING ROUTES =====

@app.route('/admin/service-history')
@admin_required
def service_history():
    """View REAL service requests from actual users with filters"""
    status_filter = request.args.get('status', 'all')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    all_requests = manager._service_requests
    
    filtered_requests = all_requests
    if status_filter != 'all':
        filtered_requests = [r for r in filtered_requests if r.status.value == status_filter]
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            filtered_requests = [r for r in filtered_requests 
                               if datetime.strptime(r.date_requested, '%Y-%m-%d %H:%M:%S') >= start]
        except:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            filtered_requests = [r for r in filtered_requests 
                               if datetime.strptime(r.date_requested, '%Y-%m-%d %H:%M:%S') <= end]
        except:
            pass
    
    status_summary = manager.get_service_status_summary()
    
    return render_template('service_history.html',
                         requests=[req.to_dict() for req in filtered_requests],
                         current_filter=status_filter,
                         start_date=start_date,
                         end_date=end_date,
                         status_summary=status_summary)

@app.route('/admin/update-request-status/<request_id>', methods=['POST'])
@admin_required
def update_request_status(request_id):
    """Update service request status"""
    new_status = request.form.get('status')
    service_req = manager.get_request_by_id(request_id)
    
    if service_req and new_status:
        if new_status == 'pending':
            service_req.status = RequestStatus.PENDING
        elif new_status == 'ongoing':
            service_req.status = RequestStatus.ONGOING
        elif new_status == 'completed':
            service_req.status = RequestStatus.COMPLETED
            if service_req.payment_status == PaymentStatus.PAID:
                manager._service_history_manager.create_transaction(service_req)
        
        manager.log_activity(session['username'], "Updated Request Status", 
                           f"Request {request_id} -> {new_status}")
    
    return redirect(url_for('service_history'))

@app.route('/admin/reports/monthly', methods=['GET', 'POST'])
@admin_required
def monthly_report():
    """Generate and view monthly reports from REAL data"""
    report_data = None
    selected_year = None
    selected_month = None
    available_years = set()
    
    for req in manager._service_requests:
        if req.status == RequestStatus.COMPLETED and req.payment_status == PaymentStatus.PAID:
            if req.completion_date:
                available_years.add(req.completion_date.year)
    
    if not available_years:
        available_years.add(datetime.now().year)
    
    if request.method == 'POST':
        year = int(request.form.get('year'))
        month = int(request.form.get('month'))
        selected_year = year
        selected_month = month
        
        monthly_income = 0
        daily_breakdown = {}
        service_breakdown = {}
        transaction_count = 0
        
        for req in manager._service_requests:
            if req.status == RequestStatus.COMPLETED and req.payment_status == PaymentStatus.PAID:
                if req.completion_date:
                    if req.completion_date.year == year and req.completion_date.month == month:
                        amount = req.payment_amount or 0
                        monthly_income += amount
                        transaction_count += 1
                        
                        day = req.completion_date.day
                        daily_breakdown[day] = daily_breakdown.get(day, 0) + amount
                        
                        category = req.category
                        service_breakdown[category] = service_breakdown.get(category, 0) + amount
        
        days_with_income = len(daily_breakdown)
        avg_daily_income = monthly_income / days_with_income if days_with_income > 0 else 0
        
        report_data = {
            'year': year,
            'month': month,
            'total_income': monthly_income,
            'transaction_count': transaction_count,
            'average_daily_income': avg_daily_income,
            'daily_breakdown': daily_breakdown,
            'service_breakdown': service_breakdown
        }
    
    theme = request.cookies.get('theme', 'light')
    return render_template('monthly_report.html',
                         report=report_data,
                         available_years=sorted(available_years, reverse=True),
                         selected_year=selected_year,
                         selected_month=selected_month,
                         theme=theme)

@app.route('/admin/reports/daily')
@admin_required
def daily_report():
    """View daily income report from REAL data"""
    date_str = request.args.get('date')
    if date_str:
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except:
            date = datetime.now()
    else:
        date = datetime.now()
    
    daily_completed = []
    total_income = 0
    
    for req in manager._service_requests:
        if req.status == RequestStatus.COMPLETED and req.payment_status == PaymentStatus.PAID:
            if req.completion_date and req.completion_date.date() == date.date():
                daily_completed.append(req)
                total_income += (req.payment_amount or 0)
    
    report = {
        'date': date.strftime('%Y-%m-%d'),
        'total_income': total_income,
        'transaction_count': len(daily_completed),
        'average_per_transaction': total_income / len(daily_completed) if daily_completed else 0,
        'completed_services': len(daily_completed),
        'requests': daily_completed
    }
    
    theme = request.cookies.get('theme', 'light')
    return render_template('daily_report.html',
                         report=report,
                         selected_date=date_str,
                         theme=theme)

@app.route('/admin/reports/statistics')
@admin_required
def statistics_report():
    """View income statistics for a date range from REAL data"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    stats = None
    if start_date and end_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            
            period_completed = []
            for req in manager._service_requests:
                if req.status == RequestStatus.COMPLETED and req.payment_status == PaymentStatus.PAID:
                    if req.completion_date:
                        if start <= req.completion_date <= end:
                            period_completed.append(req)
            
            amounts = [req.payment_amount or 0 for req in period_completed]
            
            if amounts:
                stats = {
                    'total_income': sum(amounts),
                    'average_transaction': statistics.mean(amounts),
                    'median_transaction': statistics.median(amounts),
                    'max_transaction': max(amounts),
                    'min_transaction': min(amounts),
                    'transaction_count': len(amounts)
                }
            else:
                stats = {
                    'total_income': 0,
                    'average_transaction': 0,
                    'median_transaction': 0,
                    'max_transaction': 0,
                    'min_transaction': 0,
                    'transaction_count': 0
                }
        except:
            pass
    
    theme = request.cookies.get('theme', 'light')
    return render_template('statistics.html', stats=stats, theme=theme)

@app.route('/user/history/<username>')
@login_required
def user_history(username):
    """View service history for a specific user"""
    if session.get('username') != username and session.get('role') != 'admin':
        abort(403)
    
    user_requests = manager.get_user_requests(username)
    user = manager._users.get(username)
    
    total_spent = sum(req['payment_amount'] or 0 for req in user_requests 
                     if req['status'] == 'completed' and req['payment_status'] == 'paid')
    
    theme = request.cookies.get('theme', 'light')
    return render_template('user_history.html',
                         requests=user_requests,
                         user=user.to_dict() if user else {},
                         total_spent=total_spent,
                         theme=theme)

# ===== ADMIN DASHBOARD =====
@app.route('/admindashboard')
@admin_required
def admin_dashboard():
    section = request.args.get('section', 'dashboard')
    
    total_users = len([u for u in manager._users.keys() if u != 'admin'])
    total_requests = len(manager._service_requests)
    pending_requests = len([r for r in manager._service_requests if r.status == RequestStatus.PENDING])
    ongoing_requests = len([r for r in manager._service_requests if r.status == RequestStatus.ONGOING])
    completed_requests = len([r for r in manager._service_requests if r.status == RequestStatus.COMPLETED])
    users_with_photos = len([u for u in manager._users.values() if u.profile_pic_url])
    requests_with_photos = len([r for r in manager._service_requests if r.has_photo])
    
    week_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    week_data = [0] * 7
    
    for req in manager._service_requests:
        if req.date_requested:
            try:
                req_date = datetime.strptime(req.date_requested, "%Y-%m-%d %H:%M:%S")
                day_index = req_date.weekday()
                week_data[day_index] += 1
            except:
                pass
    
    max_week = max(week_data) if week_data and max(week_data) > 0 else 1
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    revenue_data = [0] * 12
    
    for req in manager._service_requests:
        if req.status == RequestStatus.COMPLETED and req.payment_status == PaymentStatus.PAID:
            if req.completion_date:
                month_index = req.completion_date.month - 1
                revenue_data[month_index] += (req.payment_amount or 0)
    
    max_revenue = max(revenue_data) if revenue_data and max(revenue_data) > 0 else 1
    
    hours = ['12 AM', '1 AM', '2 AM', '3 AM', '4 AM', '5 AM', '6 AM', '7 AM', '8 AM', '9 AM', '10 AM', '11 AM', 
             '12 PM', '1 PM', '2 PM', '3 PM', '4 PM', '5 PM', '6 PM', '7 PM', '8 PM', '9 PM', '10 PM', '11 PM']
    hourly_users = [0] * 24
    
    for activity in manager._activities:
        if activity.action == 'Login' and activity.timestamp:
            try:
                activity_time = datetime.strptime(activity.timestamp, "%Y-%m-%d %H:%M:%S")
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
    
    payment_summary = manager.get_payment_summary()
    status_summary = manager.get_service_status_summary()
    recent_transactions = manager.get_real_transactions(5)
    
    return render_template('admindashboard.html',
                         section=section,
                         total_users=total_users,
                         total_requests=total_requests,
                         pending_requests=pending_requests,
                         ongoing_requests=ongoing_requests,
                         completed_requests=completed_requests,
                         users_with_photos=users_with_photos,
                         requests_with_photos=requests_with_photos,
                         users={u: user.to_dict() for u, user in manager._users.items()},
                         service_requests=[req.to_dict() for req in manager._service_requests],
                         technicians=[tech.to_dict() for tech in manager._technicians],
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
                         login_count=manager.login_count,
                         activities=[act.to_dict() for act in manager._activities[-10:]],
                         payment_summary=payment_summary,
                         payments=[p.to_dict() for p in manager._payments],
                         status_summary=status_summary,
                         recent_transactions=recent_transactions,
                         calculate_service_amount=manager.calculate_service_amount)

# ===== REQUEST STATUS UPDATE =====
@app.route('/update_request/<request_id>', methods=['POST'])
@admin_required
def update_request(request_id):
    status = request.form.get('status')
    notes = request.form.get('notes', '')
    
    service_req = manager.get_request_by_id(request_id)
    if service_req:
        service_req.status = RequestStatus(status)
        if notes:
            service_req.admin_notes = notes
        
        if status == 'completed':
            if service_req.payment_status == PaymentStatus.PAID:
                manager._service_history_manager.create_transaction(service_req)
            if service_req.technician_id:
                manager.unassign_technician_from_request(request_id)
        
        manager.log_activity(session['username'], "Updated Request", f"{request_id} -> {status}")
    
    return redirect(url_for('admin_dashboard', section='requests'))

# ===== TECHNICIAN MANAGEMENT ROUTES =====
@app.route('/get_available_technicians/<request_id>')
@admin_required
def get_available_technicians(request_id):
    service_req = manager.get_request_by_id(request_id)
    if service_req:
        available_techs = manager.get_available_technicians_for_service(service_req.service)
        return jsonify([{
            'id': tech.id,
            'name': tech.name,
            'specialty': tech.specialty,
            'rating': tech.rating
        } for tech in available_techs])
    return jsonify([])

@app.route('/assign_technician/<request_id>', methods=['POST'])
@admin_required
def assign_technician(request_id):
    technician_id = request.form.get('technician_id')
    if manager.assign_technician_to_request(request_id, int(technician_id)):
        return redirect(url_for('admin_dashboard', section='requests'))
    return "Failed to assign technician", 400

@app.route('/assign_technician_to_request', methods=['POST'])
@admin_required
def assign_technician_to_request_route():
    technician_id = request.form.get('technician_id')
    request_id = request.form.get('request_id')
    if technician_id and request_id:
        if manager.assign_technician_to_request(request_id, int(technician_id)):
            return redirect(url_for('admin_dashboard', section='technicians'))
    return "Failed to assign technician", 400

@app.route('/unassign_technician/<request_id>', methods=['POST'])
@admin_required
def unassign_technician(request_id):
    if manager.unassign_technician_from_request(request_id):
        return redirect(url_for('admin_dashboard', section='requests'))
    return "Failed to unassign technician", 400

@app.route('/update_technician_status/<int:technician_id>', methods=['POST'])
@admin_required
def update_technician_status_manual(technician_id):
    status = request.form.get('status')
    technician = manager.get_technician_by_id(technician_id)
    if technician:
        technician.status = TechnicianStatus(status)
        manager.log_activity(session.get('username'), "Updated Technician Status", f"{technician.name} -> {status}")
    return redirect(url_for('admin_dashboard', section='technicians'))

@app.route('/add_technician', methods=['POST'])
@admin_required
def add_technician():
    name = request.form.get('name')
    specialty = request.form.get('specialty')
    contact = request.form.get('contact')
    email = request.form.get('email')
    keywords = request.form.get('keywords', '')
    if name and specialty:
        manager.add_technician(name, specialty, contact, email, keywords)
    return redirect(url_for('admin_dashboard', section='technicians'))

@app.route('/delete_technician/<int:technician_id>')
@admin_required
def delete_technician_route(technician_id):
    manager.delete_technician(technician_id)
    return redirect(url_for('admin_dashboard', section='technicians'))

# ===== USER AND REQUEST DELETION =====
@app.route('/delete_user/<username>')
@admin_required
def delete_user(username):
    if manager.delete_user(username):
        return redirect(url_for('admin_dashboard', section='dashboard'))
    return "Cannot delete admin or user not found", 403

@app.route('/delete_request/<request_id>')
@admin_required
def delete_request(request_id):
    manager.delete_service_request(request_id)
    return redirect(url_for('admin_dashboard', section='requests'))

# ===== SETTINGS AND PROFILE =====
@app.route('/save_settings', methods=['POST'])
@admin_required
def save_settings():
    theme = request.form.get('theme', 'light')
    language = request.form.get('language', 'english')
    response = make_response(redirect(url_for('admin_dashboard', section='settings')))
    response.set_cookie('theme', theme, max_age=31536000)
    response.set_cookie('language', language, max_age=31536000)
    return response

@app.route('/profile')
@login_required
def profile():
    user = manager._users.get(session['username'])
    if not user:
        return "User not found", 404
    user_requests = manager.get_user_requests(session['username'])
    return render_template('profile.html', user=user.to_dict(), user_requests=user_requests)

@app.route('/logout')
def logout():
    username = session.get('username')
    session.clear()
    if username:
        manager.log_activity(username, "Logout", "User logged out")
        
    return redirect(url_for('login'))

# ===== ERROR HANDLERS =====
@app.errorhandler(403)
def forbidden(e):
    return "<h1>403 Access Denied</h1><a href='/login'>Back to Login</a>", 403

@app.errorhandler(404)
def not_found(e):
    return "<h1>404 Page Not Found</h1><a href='/login'>Back to Login</a>", 404


# ===== VERCEL DEPLOYMENT =====
application = app

if __name__ == "__main__":
    app.run(debug=True)