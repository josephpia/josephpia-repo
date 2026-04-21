# Customer Service Request and Job Order Tracking System

## Title Description
CSR-JOTS is a comprehensive web-based system that records customer concerns, assigns technicians to specific job orders, and tracks the progress of each service request. It helps service centers improve workflow efficiency, monitor job status accurately, and ensure timely resolution of customer requests through organized and systematical tracking.


## Version: 1.0
---

## 👥 Developers (BSCS-1B)
* **Roma, Wilma C**
* **Cabudlan, Jheane Mae M**
* **Pia, Joseph A**
* **Ibañez, Cyril Jay L**

---

## Project Description
The system provides an end-to-end solution for:

* **Customer Request Management** – Record and track customer service concerns
* **Job Order Tracking** – Monitor the progress of each service request
* **Technician Assignment** – Assign qualified technicians to specific job orders
* **Workflow Efficiency** – Improve service center operations and response times
* **Status Monitoring** – Accurately track job status from pending to completion

---

## Prerequisites Tool

Before running the project, ensure you have the following installed:

* **Operating System:** Windows, macOS, or Linux
* **Python:** Version 3.8 or higher
* **RAM:** Minimum 2GB (recommended 4GB)

---

## Required Software

* **Python 3.1.3** (`python --version`)
* **Pip** (Python package manager)
* **Code Editor** (VS Code recommended)
* **Modern Web Browser** (Chrome, Edge, or Brave)

---

## Python Libraries (Installed via pip)

bash

* **Install Flask** (Web Framework)
pip install Flask

* **Install Cloudinary**(Storing upload picture)
  pip install cloudinary

* **Install QRCode** (For payment QR codes)
pip install qrcode

* **Install Pillow** (For image processing)
pip install Pillow

* **Install Git Bash**
latest version of Git Bash

## Browser

* Any modern web browser (Chrome, Firefox, Edge, Safari)

---

## Installation & Setup

## Step 1: Clone or Download the Project
* **Using Git:**
git clone https://github.com/josephpia/CSRJOTS.git
cd CSRJOTS

Or download manually:

1.Download the project as ZIP
2.Extract to your desired location
3.Open terminal/command prompt in the project directory

## Step 2: Create a Virtual Environment (Recommended)
* **On Windows:**

python -m venv venv
venv\Scripts\activate

* **On macOS/Linux:**
python3 -m venv venv
source venv/bin/activate

## Step 3: Install Required Dependencies
pip install flask==2.3.0

Or install from requirements.txt (if available):

pip install -r requirements.txt

## Step 4: Run the Application
python app.py
You should see output similar to:

 * Running on http://127.0.0.1:5000
 * DEBUG mode: on
 
## Step 5: Access the Application
Open your web browser and navigate to:

##For Vscode
http://127.0.0.1:5000/
You should see the ServiceHub login page.

##For Vercel
pyservicehub.vercel.app
You should see the ServiceHub login page.


## Step 6: Login with Demo Credentials
Admin Account:

* **Username:** admin
* **Password:** 1234

## User Account:

* **Username:** (Create your own account via Sign Up)
* **Password:** (Your chosen password)

---

##  Modules Descriptions
* **Module 1: Customer Service Request(Service Request setup)**
**Access**
**User** | Route: /userashboard
  
**Features**
**1.Enter Service**
 * Click the **Text Input Field**
 * Fill in the**Problem description**
 * Click **Click to upload a photo**
 * Click **Remove** to remove the upload photo
 * Click **Submit request**
 * System auto-generates product ID (#SRQ-1001, #SRQ-1002, etc.)
 * Service Request is immediately recieve to admin

**2.View Submitted Service Request**(All existing Service Request)
 * Access via /userdashboard
 * Display all existing service request
 * Shows: Service Request ID, Description, Technician, Status, Payment Status, Date of request, Admin note, Action
 * Service request status indacator: (Pending, On-going, Completed)
 * Payment status indacator: (Unpaid, Paid)
**To view the upload photo you need to configured Cloudinary**
**Or use the local storage for photos instead of cloudinary**(the code is in my new file)

**3.Update Service Request**
 * Click **Edit** botton on any available Service Request
 * Modify the **Problem Description**
 * Click **Save Changes** to saved the changes
 * Cannot edit service request with peding status

**4.Delete Service Request**
 * Click **Delete** botton on any available Service Request
 * Service Request removed from active**My service request**
 * Cannot delete service request with pending status

**Data Stored**
* Service Request ID(auto-generated)
* Description
* Photo
* Technician
* Date of request
* User who made changes

**Example WorkFlow**

1.User sign up → logs in → Dashboard
2.Click "Text Input Field"
3.Fill Problem Description → Click Enter
4.Click "Click to upload a photo"
5.Upload the Photo → Click "Submit request"
6. Service Request appears in "My service requests" list

---

* **Module 2: Technician Assignment**
**Access**
**Admin** | Route: /assign_technician

**Features**
**1.View Service Request List**
 * Access via/Service Request
 * Click the "Service Request" in the sidebar navigation
 * View the  "All Service Requests" to identify the request

**2.Assign Technicians**
 * Access via/Technician
 * Click the "Technician" in the sidebar navigation
 * View the Technician List and their Specialities
 * Click the "Assign" button for the available technician whose specialty matches the service request
 * Click the "pending requests list" that matches the technician specialty
 * After accepting the pending request, the technician's status will automatically become 'Busy'

**4.Update Technician Status**
 * Access via/Service Request
 * Click the "Service Request" in the sidebar navigation
 * In "Actions" chage the status to "completed"
 * After the user's service request status is changed, the technician's status will automatically become 'Available' again

**5.Add New Technician**
 * Access via/Technician
 * Fill the name = 'Juan', specialty = 'Electrical Repair', etc..)
 * Click "Add technician"
 * View new technician in "Technician List"

**6.Delete Technician**
 * Access via/Technician
 * View in **Technician List**
 * Click "Delete" botton
---

* **Module 3: Payment Processing**
**Acess**
**User** | Route: /process_payment_direct

**Features**
**1.Multiple Online Payment Method**
 * Access via/Userdashboard click pay
 * Click the "Pay" botton and select any online payment method
 * After choosing payment method the system automatic generate QR code
 * After scanning the QR code you can now process the payment(**reminder the contact number is not mine**)
 * After process you put the Payment Verification or the transaction reference number you receive
 * Click "Submit Payment" botton and wait for approval

**2.Payment using cash**
 * Give the money to technician
 * Click "Pay" botton and select Cash Payment
 * Click "Submit Payment" botton and wait for approval

**3.View Payment Status**(After Processing the Payment Method)
 * Click "Back to Dashboard" botton
 * View payment status(cash pending, gcash pending, etc..)

* **Module 4: Service History & Reporting**
  **Currently Working**

===
# Troubleshooting
___
## Issue:"Data disappears after restart"
Normal Behavior: In-memory database resets on app restart.
___
## Issue:CLOUDINARY NOT CONFIHURED
Solution:CLOUDINARY_CLOUD_NAME = dgegm9vs2
        CLOUDINARY_API_KEY = 987832455938487
        CLOUDINARY_API_SECRET = qkj9NH-P4Sa8XMClLfcqRf2FqOg
        FLASK_SECRET_KEY = secretkey123
___
## Issue: "Login credentials not working"
Solution:Check spelling

Admin: admin / 1234
Staff: (username you made) / (userpassword you made)
