from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, datetime, timedelta
import json

# Import decorators
from auth import login_required, role_required

app = Flask(__name__)
app.secret_key = "1234"

# Database configuration

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Models

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    barcode = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Float, nullable=False)
    items = db.Column(db.Text, nullable=False)

# Routes

@app.route("/")
def home():
    if "role" in session:
        # Redirect based on role
        if session["role"] == "Admin":
            return redirect(url_for("admin_dashboard"))
        elif session["role"] == "Cashier":
            return redirect(url_for("cashier_dashboard"))
        else:
            return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# Login Route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role

            flash(f"Welcome {user.username}! You are logged in as {user.role}.", "success")

            # Redirect based on role
            if user.role == "Admin":
                return redirect(url_for("admin_dashboard"))
            elif user.role == "Cashier":
                return redirect(url_for("cashier_dashboard"))
            else:
                return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password.", "danger")
    return render_template("login.html")

# Register Route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        role = request.form["role"].strip().capitalize()

        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return redirect(url_for("register"))

        
        if User.query.filter_by(username=username).first():
            flash("Username already taken", "danger")
            return redirect(url_for("register"))

        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()
        flash("User registered successfully!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")

# General Dashboard
@app.route("/dashboard")
@login_required
def dashboard():
    total_sales = db.session.query(db.func.sum(Sale.total)).scalar() or 0
    total_products = Product.query.count()
    low_stock = Product.query.filter(Product.stock < 5).count()

    return render_template("dashboard.html",
                           total_sales=total_sales,
                           total_products=total_products,
                           low_stock=low_stock)

# Admin Dashboard
@app.route("/admin_dashboard")
@login_required
@role_required("Admin") 

def admin_dashboard():

    # Get all products
    products = Product.query.all()

    # KPIs
    total_sales = db.session.query(db.func.sum(Sale.total)).scalar() or 0
    total_products = Product.query.count()
    low_stock = Product.query.filter(Product.stock < 5).count()

    #Fetch low stock products list
    low_stock_products = Product.query.filter(Product.stock < 5).all()

    return render_template(
        "dashboard_admin.html",
        products=products,
        total_sales=total_sales,
        total_products=total_products,
        low_stock=low_stock,
        low_stock_products=low_stock_products
    )


# Cashier Dashboard
@app.route("/cashier_dashboard")
@login_required
@role_required("Cashier")
def cashier_dashboard():

    products = Product.query.all()
    return render_template("dashboard_cashier.html", products=products)

#Sales History
@app.route("/sales_history")
@login_required
@role_required("Admin")
def sales_history():
    sales = Sale.query.order_by(Sale.date.desc()).all()
    return render_template("sales_history.html", sales=sales)

# Logout Route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# Product Management
@app.route("/add_product", methods=["POST"])
@login_required
@role_required("Admin")
def add_product():
    product = Product(
        name=request.form["name"],
        barcode=request.form["barcode"],
        price=float(request.form["price"]),
        stock=int(request.form["stock"])
    )
    db.session.add(product)
    db.session.commit()
    flash("Product added successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/edit_product/<int:id>", methods=["POST"])
@login_required
@role_required("Admin")
def edit_product(id):
    product = Product.query.get_or_404(id)
    product.name = request.form["name"]
    product.barcode = request.form["barcode"]
    product.price = float(request.form["price"])
    product.stock = int(request.form["stock"])
    db.session.commit()
    flash("Product updated successfully!", "info")
    return redirect(url_for("admin_dashboard"))

@app.route("/delete_product/<int:id>", methods=["POST"])
@login_required
@role_required("Admin")
def delete_product(id):
    product = Product.query.get_or_404(id)
    db.session.delete(product)
    db.session.commit()
    flash("Product deleted successfully!", "danger")
    return redirect(url_for("admin_dashboard"))

# Checkout (Cashier)
@app.route("/checkout", methods=["POST"])
@login_required
@role_required("Cashier")
def checkout():
    data = request.get_json()
    cart = data.get("cart", [])

    # Validate stock before calculating total
    for item in cart:
        product = Product.query.get(item["id"])
        if not product:
            return jsonify({"error": f"Product ID {item['id']} not found"}), 400
        if product.stock <= 0:
            return jsonify({"error": f"{product.name} is out of stock"}), 400
        if product.stock < item["qty"]:
            return jsonify({"error": f"Insufficient stock for {product.name}"}), 400

    # Calculate total
    total = sum(item["qty"] * float(item["price"]) for item in cart)

    # Save sale
    sale = Sale(total=total, items=json.dumps(cart))
    db.session.add(sale)

    # Update stock
    for item in cart:
        product = Product.query.get(item["id"])
        product.stock -= item["qty"]

    db.session.commit()
    return jsonify({"message": "Sale successful", "receipt_id": sale.id})

@app.route("/products_table")
@login_required
@role_required("Admin")
def products_table():
    products = Product.query.all()
    return render_template("products_table.html", products=products)

# Sales History (Admin only)
@app.route("/sales_history")
@login_required
@role_required("Admin")
def sales_history_paginated():
    page = request.args.get("page", 1, type=int)
    per_page = 10

    #filters

    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    quick_filter = request.args.get("quick_filter")
    query = Sale.query.order_by(Sale.date.desc())

    # Quick filters
    
    if quick_filter == "today":
        start_date = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = datetime.today().replace(hour=23, minute=59, second=59)
        query = query.filter(Sale.date.between(start_date, end_date))
    elif quick_filter == "7 days":
        start_date = datetime.today() - timedelta(days=7)
        end_date = datetime.today()
        query = query.filter(Sale.date.between(start_date, end_date))
    elif quick_filter == "30 days":
        start_date = datetime.today() - timedelta(days=30)
        end_date = datetime.today()
        query = query.filter(Sale.date.between(start_date, end_date))

    # Manual date range
    elif start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            query = query.filter(Sale.date.between(start_date, end_date))
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")

    sales = query.paginate(page=page, per_page=per_page)

    return render_template("sales_history.html", sales=sales.items, page=page,
                           start_date=start_date_str, end_date=end_date_str, quick_filter=quick_filter)

# # JSON parsing filter
# @app.template_filter("loads")
# def loads_filter(s):
#     return json.loads(s)

# # Stop caching
# @app.after_request
# def add_header(response):
#     response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
#     response.headers["Pragma"] = "no-cache"
#     response.headers["Expires"] = "0"
#     return response

# # Session timeout
# @app.before_request
# def check_session_timeout():
#     session.permanent = True
#     app.permanent_session_lifetime = timedelta(minutes=15)
#     if "username" not in session and request.endpoint not in ("login", "register", "static"):
#         return redirect(url_for("login"))

# -----------------------
# Run App
# -----------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
