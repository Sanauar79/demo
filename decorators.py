from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'email' not in session:
                flash('You must be logged in to access this page.', 'warning')
                return redirect(url_for('login'))

            if role and session.get('role') != role:
                flash('Access denied. Insufficient permissions.', 'danger')
                return redirect(url_for('login'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

