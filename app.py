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
import calendar

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
            return redirect(url_for("dashboard_cashier"))
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
                return redirect(url_for("dashboard_cashier"))
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

    # --- Top Products Data ---

    try:
        product_results = (
            db.session.query(
                Product.name,
                db.func.sum(SaleItem.quantity * SaleItem.price).label("total")
            )
            .select_from(SaleItem)
            .join(Product, SaleItem.product_id == Product.id)
            .group_by(Product.id)
            .order_by(func.sum(SaleItem.quantity * SaleItem.price).desc())
            .limit(5)
            .all()
        )
        print ("Top Products:", product_results)

    except Exception as e:
        print("Query failed:", e)



    # Build dicts keyed by month
    sales_dict = {int(r.month): float(r.total) for r in results_sales}
    expenses_dict = {int(r.month): float(r.total) for r in results_expenses}

    # Union of months
    all_months = sorted(set(sales_dict.keys()) | set(expenses_dict.keys()))
    product_names = [r[0] for r in product_results]
    product_sales = [float(r[1]) for r in product_results]

    print("Top Products:", product_results)


    sales_labels = [calendar.month_abbr[m] for m in all_months]
    sales_data = [sales_dict.get(m, 0) for m in all_months]
    expenses_data = [expenses_dict.get(m, 0) for m in all_months]
    profit_data = [s - e for s, e in zip(sales_data, expenses_data)]

    if results_sales:
        sales_labels = [calendar.month_abbr[int(r.month)] for r in results_sales]
    sales_data   = [float(r.total) for r in results_sales]

    if results_expenses:
        expenses_data = [float(r.total) for r in results_expenses]

    if sales_data and expenses_data:
        profit_data = [s - e for s, e in zip(sales_data, expenses_data)]
    

    return render_template(
        
        "dashboard_admin.html",
        products=products,
        total_sales=round(total_sales,2),
        total_products=total_products,
        low_stock=low_stock,
        low_stock_products=low_stock_products,
        sales_labels=sales_labels,    
        sales_data=sales_data,        
        expenses_data=expenses_data,   
        profit_data=profit_data,
        product_names=product_names,
        product_sales=product_sales
    )

# Restock product route  

@app.route('/restock/<int:product_id>', methods=['POST'])
def restock_product(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = int(request.form.get('quantity', 10))  # default 10
    product.stock += quantity
    db.session.commit()
    flash(f"{product.name} has been restocked by {quantity} units.", "success")
    return redirect(url_for('admin_dashboard'))




# Cashier Dashboard
@app.route("/cashier_dashboard")
@login_required
@role_required("Cashier")
def dashboard_cashier():
    cashier_id = session.get("user_id")

    # All products (if you want to show inventory)
    products = Product.query.all()

    # Today's sales total for this cashier
    today = datetime.utcnow().date()
    total_sales_today = db.session.query(func.sum(Sale.total))\
        .filter(func.date(Sale.date) == today, Sale.cashier_id == cashier_id)\
        .scalar() or 0

    # Recent 10 sales for this cashier
    recent_sales = Sale.query.filter_by(cashier_id=cashier_id)\
        .order_by(Sale.date.desc())\
        .limit(10).all()

    return render_template(
        "dashboard_cashier.html",
        products=products,
        total_sales_today=total_sales_today,
        recent_sales=recent_sales
    )


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
    customer_id = data.get("customer_id") or DEFAULT_CUSTOMER_ID
    cashier_id = session.get("user_id")

    # Validate stock
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
    sale = Sale(
        total=total,
        items=json.dumps(cart),
        cashier_id=cashier_id,
        customer_id=customer_id
    )
    db.session.add(sale)

    # Update stock
    for item in cart:
        product = Product.query.get(item["id"])
        product.stock -= item["qty"]

    db.session.commit()

    # Fetch customer name
    customer = Customer.query.get(customer_id)
    customer_name = customer.name if customer else "Walk-in"

    return jsonify({
        "message": "Sale successful",
        "receipt_id": sale.id,
        "total": total,
        "customer_name": customer_name
    })


#Cashier new sale 
@app.route("/new_sale", methods=["GET", "POST"])
@login_required
@role_required("Cashier")
def new_sale():
    products = Product.query.all()
    customers = Customer.query.all()

    if request.method == "POST":
        cashier_id = session.get("user_id")
        customer_id = request.form.get("customer_id") or DEFAULT_CUSTOMER_ID

        sale = Sale(cashier_id=cashier_id, customer_id=customer_id)
        db.session.add(sale)
        db.session.commit()

        flash("Sale created successfully!", "success")
        return redirect(url_for("cashier_sales_history"))

    return render_template(
        "new_sale.html",
        products=products,
        customers=customers,
        DEFAULT_CUSTOMER_ID=DEFAULT_CUSTOMER_ID
    )



#cashier sales history

@app.route("/cashier_sales_history")
@login_required
@role_required("Cashier")
def cashier_sales_history():
    page = request.args.get("page", 1, type=int)

    cashier_id = session.get("user_id")
    sales = (Sale.query
                  .filter_by(cashier_id=cashier_id)
                  .order_by(Sale.date.desc())
                  .paginate(page=page, per_page=10))

    return render_template("cashier_sales_history.html",
                           sales=sales.items,
                           page=page,
                           pagination=sales)










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
    with app.app_context():
        # Ensure Walk-in customer exists
        from models import Customer
        default_customer = Customer.query.filter_by(name="Walk-in").first()
        if not default_customer:
            default_customer = Customer(name="Walk-in", phone=None)
            db.session.add(default_customer)
            db.session.commit()
        DEFAULT_CUSTOMER_ID = default_customer.id

    app.run(debug=True)

