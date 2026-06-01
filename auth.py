from functools import wraps
from flask import session, redirect, url_for, render_template, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "role" not in session or session["role"] != role:
                flash("You do not have permission to access this page.", "danger")
                return render_template("access_denied.html")
            return f(*args, **kwargs)
        return decorated_function
    return decorator