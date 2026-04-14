# Customer Service Request and Job Order Tracking System

CSR-JOTS is a comprehensive web-based system that records customer concerns, assigns technicians to specific job orders, and tracks the progress of each service request. It helps service centers improve workflow efficiency, monitor job status accurately, and ensure timely resolution of customer requests through organized and systematical tracking.

---

## 👥 Developers (BSCS-1B)
* **Wilma Roma**
* **Jheane Mae Cabudlan**
* **Joseph Pia**
* **Cyril Jay Ibanez**

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
* **Python 3.1.3** (`python --version`)
* **Pip** (Python package manager)
* **Code Editor** (VS Code recommended)
* **Modern Web Browser** (Chrome, Edge, or Brave)

---

## Installation & Setup

bash
# Install Flask (Web Framework)
pip install Flask

# Install QRCode (For payment QR codes)
pip install qrcode

# Install Pillow (For image processing)
pip install Pillow

# Or install all at once
pip install Flask qrcode Pillow

# Install Git Bash
latest version of Git Bash

* **The system will be live at**: http://127.0.0.1:5000/

---
# Usage Guide

## Home Page
The system landing page provides an overview of the Customer Service Request and Job Order Tracking System

Users can view descriptions and choose to "Login" or "Sign Up" to access the system

## Authentication
Use the following credentials to access the system:

Role	Username	Password
Admin	admin	    1234
User	(Create your own account via Sign Up)	(Your chosen password)

---
# Module Description

## Completed Modules:
* **Module 1**: Customer Service Request
Submit service requests with descriptions
Upload supporting photos
Submit Service Request
Display Existing Service Request
Edit the Description(Available if not already Approved by the admin)
Track request status (pendeng, on-going, completed)


* **Module 2**: Technician Assignment
View technician list and specialties
Assign technicians to job orders
Update technician status
Auto-unassign on completion

* **Module 3**: Payment Processing
Multiple payment method support
QR code generation for digital payments
Receipt upload and verification
Wallet system for balance payments