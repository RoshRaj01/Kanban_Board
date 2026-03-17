from functools import wraps
from flask import session, jsonify

def require_role(*roles):

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):

            if "role" not in session:
                return jsonify({"error": "Not logged in"}), 401

            user_role = session["role"]

            # Admin can do everything
            if user_role == "admin":
                return f(*args, **kwargs)

            # Check allowed roles
            if user_role not in roles:
                return jsonify({"error": "Access denied"}), 403

            return f(*args, **kwargs)

        return wrapper

    return decorator