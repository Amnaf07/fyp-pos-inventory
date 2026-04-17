from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from db import db
from models import User, Product, Sale
from werkzeug.security import generate_password_hash
from auth import login_required, role_required
import json
from datetime import datetime

bp = Blueprint("admin", __name__, url_prefix="/admin")

# Manage Users
@bp.route("/users")
@login_required
@role_required("Admin")
def manage_users():
    users = User.query.all()
    return render_template("admin_users.html", users=users)

@bp.route("/users/add", methods=["POST"])
@login_required
@role_required("Admin")
def add_user():
    username = request.form["username"]
    password = request.form["password"]
    role = request.form["role"]
    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_pw, role=role)
    db.session.add(new_user)
    db.session.commit()
    flash("User added successfully!", "success")
    return redirect(url_for("admin.manage_users"))

@bp.route("/users/edit/<int:user_id>", methods=["POST"])
@login_required
@role_required("Admin")
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    user.role = request.form["role"]
    db.session.commit()
    flash("User updated successfully!", "info")
    return redirect(url_for("admin.manage_users"))

@bp.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
@role_required("Admin")
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully!", "danger")
    return redirect(url_for("admin.manage_users"))

# Admin Dashboard
@bp.route("/dashboard")
@login_required
@role_required("Admin")
def admin_dashboard():
    products = Product.query.all()
    total_sales = db.session.query(db.func.sum(Sale.total)).scalar() or 0
    total_products = Product.query.count()
    low_stock = Product.query.filter(Product.stock < 5).count()
    low_stock_products = Product.query.filter(Product.stock < 5).all()

    return render_template(
        "dashboard_admin.html",
        products=products,
        total_sales=total_sales,
        total_products=total_products,
        low_stock=low_stock,
        low_stock_products=low_stock_products
    )

