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
from decimal import Decimal

# Import decorators
from auth import login_required, role_required

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
migrate = Migrate(app, db)

app.secret_key = "1234"


# Routes

@app.route('/')
def index():
    if "role" in session:
        # Redirect based on role
        if session["role"] == "Admin":
            return redirect(url_for("admin_dashboard"))
        elif session["role"] == "Cashier":
            return redirect(url_for("cashier_dashboard"))
        elif session["role"] == "Manager":
            return redirect(url_for("manager_dashboard"))
        else:
            return redirect(url_for("login"))
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
            elif user.role == "Manager":
                return redirect(url_for("manager_dashboard"))
            else:
                flash("Role not recognized", "danger")
                return redirect(url_for("login"))
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
@login_required
@role_required("Admin")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    # Ensure a default cashier exists
    default_cashier = User.query.filter_by(username="Walk-in").first()
    if not default_cashier:
        default_cashier = User(username="Walk-in", role="Cashier")
        default_cashier.password_hash = generate_password_hash("default")
        db.session.add(default_cashier)
        db.session.commit()

    # Reassign sales BEFORE deleting the user
    Sale.query.filter_by(cashier_id=user.id).update(
        {"cashier_id": default_cashier.id}
    )
    db.session.commit()

    # Now delete the user safely
    db.session.delete(user)
    db.session.commit()

    flash("User deleted and their sales reassigned.", "success")
    return redirect(url_for('manage_users'))


# Admin Dashboard
@app.route("/admin_dashboard")
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
def cashier_dashboard():
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

     # Low stock summary (threshold = 5)
    low_stock_products = Product.query.filter(Product.stock < 5).all()
    low_stock_count = len(low_stock_products)



     # Top selling products (last 7 days)
    seven_days_ago = datetime.utcnow().date() - timedelta(days=7)
    top_products = db.session.query(
    Product.name,
    func.sum(SaleItem.quantity).label("total_qty")
).join(SaleItem, Product.id == SaleItem.product_id)\
 .join(Sale, Sale.id == SaleItem.sale_id)\
 .group_by(Product.name)\
 .order_by(func.sum(SaleItem.quantity).desc())\
 .limit(5).all()
    
     # Sales trend (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)    
    sales_trend = db.session.query(
        func.date(Sale.date).label("sale_date"),
        func.sum(Sale.total).label("daily_total")
    ).filter(Sale.date >= seven_days_ago, Sale.cashier_id == cashier_id)\
     .group_by(func.date(Sale.date))\
     .order_by(func.date(Sale.date)).all()

    # Prepare data for Chart.js
    labels = [str(row.sale_date) for row in sales_trend]
    totals = [float(row.daily_total) for row in sales_trend]

     # Product breakdown (last 7 days)
    seven_days_ago = datetime.utcnow().date() - timedelta(days=7)

    product_sales = db.session.query(
    Product.name,
    func.sum(SaleItem.quantity).label("product_total")
).join(SaleItem, SaleItem.product_id == Product.id)\
 .join(Sale, Sale.id == SaleItem.sale_id)\
 .group_by(Product.name).all()




    product_labels = [row.name for row in product_sales]
    product_totals = [int(row.product_total or 0) for row in product_sales]

    all_sales = Sale.query.all()
    for s in all_sales:
       print(s.id, s.date, s.cashier_id)

    all_items = SaleItem.query.all()
    for i in all_items:
       print("SaleItem:", i.id, i.sale_id, i.product_id, i.quantity, i.price)




    
    return render_template(
        "dashboard_cashier.html",
        products=products,
        total_sales_today=total_sales_today,
        recent_sales=recent_sales,
        low_stock_count=low_stock_count,
        top_products=top_products,
        labels=labels,
        totals=totals,
        product_labels=product_labels,
        product_totals=product_totals
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
        stock=int(request.form["stock"]),
        category=request.form["category"]
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
    product.category = request.form["category"]
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
# Checkout (Cashier)
@app.route("/checkout", methods=["POST"])
@login_required
@role_required("Cashier")
def checkout():
    data = request.get_json()
    cart = data.get("cart", [])
    customer_id = data.get("customer_id") or DEFAULT_CUSTOMER_ID
    discount = float(data.get("discount", 0))  # discount percentage
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
    if discount > 0:
        total = total - (total * discount / 100)

    # Save sale
    sale = Sale(
        total=total,
        cashier_id=cashier_id,
        customer_id=customer_id,
        date=datetime.utcnow(),
        discount=discount
    )
    db.session.add(sale)
    db.session.flush()  # ensures sale.id is available

    # Save sale items
    for item in cart:
        product = Product.query.get(item["id"])
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            quantity=item["qty"],
            price=float(item["price"]),
            discount=discount
        )
        db.session.add(sale_item)

        # Update stock
        product.stock -= item["qty"]

    # Update totals based on items
    sale.update_totals()
    db.session.commit()

    # Fetch customer and cashier names
    customer = Customer.query.get(customer_id)
    customer_name = customer.name if customer else "Walk-in"

    cashier = User.query.get(cashier_id)
    cashier_name = cashier.username if cashier else "Unknown"

    # Build item details for receipt (with category)
    items = []
    for si in sale.sale_items:
        subtotal = si.quantity * si.price
        if si.discount > 0:
            subtotal -= (subtotal * si.discount / 100)
        items.append({
            "name": si.product.name,
            "qty": si.quantity,
            "price": si.price,
            "discount": si.discount,
            "category": si.product.category,   # NEW
            "total": subtotal
        })

    return jsonify({
        "message": "Sale successful",
        "receipt_id": sale.id,
        "total": sale.total,
        "customer_name": customer_name,
        "cashier_name": cashier_name,
        "timestamp": sale.date.strftime("%Y-%m-%d %H:%M:%S"),
        "items": items
    })


#new sale route (form based)
@app.route("/new_sale", methods=["GET", "POST"])
@login_required
@role_required("Cashier")
def new_sale():
    products = Product.query.all()
    customers = Customer.query.all()

    if request.method == "POST":
        cashier_id = session.get("user_id")
        customer_id = request.form.get("customer_id") or DEFAULT_CUSTOMER_ID

        # Create the sale record
        sale = Sale(cashier_id=cashier_id, customer_id=customer_id, date=datetime.utcnow())
        db.session.add(sale)
        db.session.flush()  # ensures sale.id is available before adding items

        # Loop through cart items sent from the form/JS
        cart_items = request.form.getlist("cart")  # e.g. [{"product_id":1,"quantity":2}, ...]
        for item in cart_items:
            product_id = int(item["product_id"])
            qty = int(item["quantity"])

            product = Product.query.get(product_id)
            if not product:
                continue

            # Create SaleItem with product’s current price
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                quantity=qty,
                price=product.price  # auto‑assign from Product
            )
            db.session.add(sale_item)

            # Reduce stock
            product.stock -= qty

        db.session.commit()

        flash("Sale created successfully!", "success")
        return redirect(url_for("cashier_sales_history"))
    last_customer_id = session.pop("last_added_customer_id", None)        
    return render_template(
        "new_sale.html",
        products=products,
        customers=customers,
        DEFAULT_CUSTOMER_ID=DEFAULT_CUSTOMER_ID,
        last_customer_id=last_customer_id
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

    return render_template("sales_history.html",                 sales=sales.items, 
                           page=page,
                           start_date=start_date_str, end_date=end_date_str)


#cashier inventory view (read‑only)
@app.route("/inventory")
@login_required
@role_required("Cashier")
def cashier_inventory():
    products = Product.query.all()
    return render_template("cashier_inventory.html", products=products)

@app.route("/cashier/add_customer", methods=["POST"])
@login_required
@role_required("Cashier")
def cashier_add_customer():
    name = request.form["name"].strip()
    phone = request.form["phone"].strip()

    if not name:
        flash("Customer name is required", "danger")
        return redirect(url_for("new_sale"))

    new_customer = Customer(name=name, phone=phone or None)
    db.session.add(new_customer)
    db.session.commit()

    # Save the new customer ID in session
    session["last_added_customer_id"] = new_customer.id

    flash("Customer added successfully!", "success")
    return redirect(url_for("new_sale"))



#MANAGER DASHBOARD
@app.route('/manager_dashboard')
@login_required
@role_required("Manager")
def manager_dashboard():
    # Sales today
    sales_today = db.session.query(func.sum(Sale.total))\
        .filter(func.date(Sale.date) == date.today()).scalar() or 0

    # Low stock count
    low_stock_count = Product.query.filter(Product.stock < 5).count()

    # Top cashier by sales
    top_cashier = db.session.query(User.username)\
        .join(Sale, Sale.cashier_id == User.id)\
        .group_by(User.username)\
        .order_by(func.sum(Sale.total).desc())\
        .first()
    top_cashier = top_cashier[0] if top_cashier else "N/A"

    # Customer count
    customer_count = Customer.query.count()

    # Sales trend chart (last 7 days)
    sales_data = db.session.query(func.date(Sale.date), func.sum(Sale.total))\
        .group_by(func.date(Sale.date))\
        .order_by(func.date(Sale.date).desc())\
        .limit(7).all()
    sales_labels = [str(row[0]) for row in sales_data][::-1]
    sales_values = [row[1] for row in sales_data][::-1]

    # Stock distribution by category
    stock_distribution = db.session.query(
    Product.category,
    func.sum(Product.stock).label("total_stock")
).group_by(Product.category).all()

    
    stock_labels = [row[0] for row in stock_distribution]
    stock_values = [row[1] for row in stock_distribution]

    return render_template(
        "manager_dashboard.html",
        sales_today=sales_today,
        low_stock_count=low_stock_count,
        top_cashier=top_cashier,
        customer_count=customer_count,
        sales_labels=json.dumps(sales_labels),
        sales_data=json.dumps(sales_values),
        products=Product.query.all(),
        stock_labels=json.dumps(stock_labels),   
        stock_values=json.dumps(stock_values) 
    )

@app.route('/manager/reports')
@login_required
@role_required("Manager")
def manager_reports():
    range_type = request.args.get("range", "daily")

    if range_type == "daily":
        reports = db.session.query(
            func.date(Sale.date).label("date"),
            func.sum(Sale.total).label("total"),
            func.count(Sale.id).label("count")
        ).group_by("date").all()

    elif range_type == "weekly":
        reports = db.session.query(
            func.strftime("%Y-%W", Sale.date).label("date"),
            func.sum(Sale.total).label("total"),
            func.count(Sale.id).label("count")
        ).group_by("date").all()

    else:  # monthly
        reports = db.session.query(
            func.strftime("%Y-%m", Sale.date).label("date"),
            func.sum(Sale.total).label("total"),
            func.count(Sale.id).label("count")
        ).group_by("date").all()

    # Format totals to 2 decimal places
    formatted_reports = []
    for r in reports:
        formatted_reports.append({
            "date": r.date,
            "total": round(float(r.total), 2),   # ✅ clean decimals
            "count": r.count
        })

    labels = [fr["date"] for fr in formatted_reports]
    data = [fr["total"] for fr in formatted_reports]

    # If AJAX request, return JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"labels": labels, "data": data})

    return render_template(
        "manager_reports.html",
        reports=formatted_reports,
        labels=json.dumps(labels),
        data=json.dumps(data)
    )



@app.route('/manager/inventory')
@login_required
@role_required("Manager")
def manager_inventory():
    products = Product.query.all()
    return render_template("manager_inventory.html", products=products)


@app.route('/manager/cashiers')
@login_required
@role_required("Manager")
def manager_cashiers():
    cashiers = db.session.query(
        User.username.label("name"),
        func.sum(Sale.total).label("sales_total"),
        func.count(Sale.id).label("transactions"),
        func.sum(Sale.discount).label("discounts"),
        func.sum(Sale.voided).label("voided")
    ).join(Sale, Sale.cashier_id == User.id)\
     .filter(User.role == "Cashier")\
     .group_by(User.username).all()

    cashier_labels = [c.name for c in cashiers]
    cashier_sales = [c.sales_total for c in cashiers]

    return render_template(
        "manager_cashiers.html",
        cashiers=cashiers,
        cashier_labels=json.dumps(cashier_labels),
        cashier_sales=json.dumps(cashier_sales),
        top_threshold=10000,  # adjust thresholds
        avg_threshold=5000,
        top_cashier=max(cashiers, key=lambda c: c.sales_total).name if cashiers else "N/A",
        total_sales=sum(c.sales_total for c in cashiers),
        total_discounts=sum(c.discounts for c in cashiers)
    )


@app.route('/manager/customers')
@login_required
@role_required("Manager")
def manager_customers():
    customers = db.session.query(
        Customer.name,
        Customer.phone,
        func.count(Sale.id).label("total_purchases"),
        func.avg(Sale.total).label("avg_spend")
    ).join(Sale, Sale.customer_id == Customer.id)\
     .group_by(Customer.id).all()

    customer_count = len(customers)
    repeat_customers = sum(1 for c in customers if c.total_purchases > 5)
    avg_basket_size = round(sum(c.avg_spend for c in customers) / customer_count, 2) if customer_count else 0

    # Discount usage chart
    discount_data = db.session.query(
        Sale.discount, func.count(Sale.id)
    ).group_by(Sale.discount).all()
    discount_labels = [f"{d[0]}%" for d in discount_data]
    discount_values = [d[1] for d in discount_data]

    return render_template(
        "manager_customers.html",
        customers=customers,
        customer_count=customer_count,
        repeat_customers=repeat_customers,
        avg_basket_size=avg_basket_size,
        discount_labels=json.dumps(discount_labels),
        discount_data=json.dumps(discount_values)
    )

@app.route('/manager/flag_product/<int:id>', methods=['POST'])
@login_required
@role_required("Manager")
def flag_product(id):
    product = Product.query.get_or_404(id)
    # Example: mark product as flagged
    product.flagged = True
    db.session.commit()
    flash(f"Product {product.name} flagged for Admin review.", "warning")
    return redirect(url_for('manager_inventory'))

@app.route('/admin/flagged_products')
@login_required
@role_required("Admin")
def flagged_products():
    flagged_items = Product.query.filter_by(flagged=True).all()
    return render_template("admin_flagged_products.html", flagged_items=flagged_items)


@app.route('/admin/unflag_product/<int:id>', methods=['POST'])
@login_required
@role_required("Admin")
def unflag_product(id):
    product = Product.query.get_or_404(id)
    product.flagged = False
    db.session.commit()
    flash(f"Product {product.name} marked as reviewed.", "success")
    return redirect(url_for('flagged_products'))


@app.route('/admin/discounts_over_time')
@login_required
@role_required("Admin")
def discounts_over_time():
    # Group discounts by date
    discount_data = db.session.query(
        func.date(Sale.date).label("sale_date"),
        func.sum(Sale.discount).label("total_discount")
    ).group_by(func.date(Sale.date)).order_by(func.date(Sale.date)).all()

    labels = [str(d.sale_date) for d in discount_data]
    values = [float(d.total_discount or 0) for d in discount_data]

    return render_template(
        "admin_discounts_chart.html",
        labels=json.dumps(labels),
        values=json.dumps(values)
    )

@app.route("/customers")
@login_required
@role_required("Manager")
def customers_list():
    customers = Customer.query.all()
    return render_template("customers.html", customers=customers)

@app.route("/customers/add", methods=["POST"])
@login_required
@role_required("Manager")
def add_customer():
    name = request.form["name"].strip()
    phone = request.form["phone"].strip()

    if not name:
        flash("Customer name is required", "danger")
        return redirect(url_for("customers_list"))

    new_customer = Customer(name=name, phone=phone or None)
    db.session.add(new_customer)
    db.session.commit()
    flash("Customer added successfully!", "success")
    return redirect(url_for("customers_list"))

@app.route("/customers/delete/<int:id>", methods=["POST"])
@login_required
@role_required("Manager")
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    db.session.delete(customer)
    db.session.commit()
    flash("Customer deleted successfully!", "info")
    return redirect(url_for("customers_list"))


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

