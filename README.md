# Inventory Management System (IMS)

## Overview
The Inventory Management System (IMS) is a prototype built with **Flask** and **SQLAlchemy** to manage products, sales, and stock levels.  
It provides two main dashboards:
- **Admin Dashboard**: Manage products, restock items, view KPIs, and monitor low stock alerts.
- **Cashier Dashboard (POS)**: Search products, add to cart, checkout, and generate receipts.

---

##  Features
- User authentication (Admin & Cashier roles).
- Product management (Add, Edit, Delete, Restock).
- Low stock detection and alerts.
- Sales history tracking.
- Point of Sale (POS) interface with cart and receipt modal.
- Bootstrap styling for responsive UI.

---

##  Tech Stack
- **Backend**: Flask, Flask-SQLAlchemy
- **Frontend**: Jinja2 templates, Bootstrap 5
- **Database**: SQLite (default, can be swapped for PostgreSQL/MySQL)
- **Language**: Python 3.10+

---

##  Project Structure

ims-system/
│── app.py                # Main Flask app
│── database.db           # SQLite database (sample data)
│── requirements.txt      # Dependencies
│── static/               # CSS, JS, images
│    ├── style.css
│    ├── pos.js
│    └── img/logo.png
│── templates/            # HTML templates
│    ├── base.html
│    ├── dashboard_admin.html
│    ├── dashboard_cashier.html
│    ├── login.html
│    ├── register.html
│    ├── products_table.html
│    └── sales_history.html
│── README.md             # Documentation


---
## Installation
1. Clone the repository:

   git clone <repo-url>
   cd ims-system

Install dependencies:

pip install -r requirements.txt
Initialize the database:

Initialize database:
python
>>> from app import db 
>>> db.create_all()

Run the app:
python app.py


Open in browser:
http://127.0.0.1:5000


# Default Accounts:
Admin:
Username: admin  
Password: admin123

Cashier:
Username: ad  
Password: ad

(You can register new users via the Register page.)

