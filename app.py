from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Blueprint
from db import db
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date, datetime, timedelta
import json
from models import User, Product, Sale, SaleItem, Expense
from routes import admin, cashier
from sqlalchemy import func 

# Import decorators
from auth import login_required, role_required

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)

app.secret_key = "1234"

# Register blueprints
app.register_blueprint(admin.bp)
app.register_blueprint(cashier.bp)


# Routes

@app.route('/')
def index():
    if "role" in session:
        # Redirect based on role
        if session["role"] == "Admin":
            return redirect(url_for("admin_dashboard"))
        elif session["role"] == "Cashier":
            return redirect(url_for("cashier_dashboard"))
        else:
            return redirect(url_for("dashboard"))
    # If not logged in, show login page
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

# Manage Users routes
@app.route('/admin/users')
def manage_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
def add_user():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_pw, role=role)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('manage_users'))

@app.route('/admin/users/edit/<int:user_id>', methods=['POST'])
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    user.role = request.form['role']
    db.session.commit()
    return redirect(url_for('manage_users'))

@app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('manage_users'))

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

    # Fetch low stock products list
    low_stock_products = Product.query.filter(Product.stock < 5).all()

    # --- Monthly Sales Data ---
    results_sales = (
        db.session.query(
            db.func.strftime("%m", Sale.date).label("month"),   # SQLite
            db.func.sum(Sale.total).label("total")
        )
        .group_by("month")
        .order_by("month")
        .all()
    )

    # --- Monthly Expenses Data ---
    results_expenses = (
        db.session.query(
            db.func.strftime("%m", Expense.date).label("month"),   # SQLite
            db.func.sum(Expense.amount).label("total")
        )
        .group_by("month")
        .order_by("month")
        .all()
    )

    import calendar
    # Convert month numbers into names (Jan, Feb, Mar…)
    sales_labels = []
    sales_data = []
    expenses_data = []
    profit_data = []

    if results_sales:
        sales_labels = [calendar.month_abbr[int(r.month)] for r in results_sales]
    sales_data   = [float(r.total) for r in results_sales]

    if results_expenses:
        expenses_data = [float(r.total) for r in results_expenses]

    if sales_data and expenses_data:
        profit_data = [s - e for s, e in zip(sales_data, expenses_data)]

    print("results_sales:", results_sales)
    print("results_expenses:", results_expenses)
    

    return render_template(
        
        "dashboard_admin.html",
        products=products,
        total_sales=sum(sales_data),
        total_products=total_products,
        low_stock=low_stock,
        low_stock_products=low_stock_products,
        sales_labels=sales_labels,     # pass to template
        sales_data=sales_data,         # pass to template
        expenses_data=expenses_data,    # pass to template
        profit_data=profit_data         # pass to template  
    )




# Cashier Dashboard
@app.route("/cashier_dashboard")
@login_required
@role_required("Cashier")
def cashier_dashboard():

    products = Product.query.all()
    return render_template("dashboard_cashier.html", products=products)


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

@app.route("/products")
@login_required
@role_required("Admin")
def products_table():
    products = Product.query.all()
    return render_template("products.html", products=products)

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
    query = Sale.query.order_by(Sale.created_at.desc())


    # Manual date range
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            query = query.filter(Sale.created_at.between(start_date, end_date))
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "danger")

    sales = query.paginate(page=page, per_page=per_page)

    return render_template("sales_history.html", sales=sales.items, page=page,
                           start_date=start_date_str, end_date=end_date_str)

# JSON parsing filter
@app.template_filter("loads")
def loads_filter(s):
    return json.loads(s)

# Stop caching
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Session timeout
@app.before_request
def check_session_timeout():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=15)
    if "username" not in session and request.endpoint not in ("login", "register", "static"):
        return redirect(url_for("login"))

# -----------------------
# Run App
# -----------------------
if __name__ == "__main__":
    # with app.app_context():
    #     db.create_all()
    app.run(debug=True)
