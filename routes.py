from flask import Blueprint, request, jsonify
from models import db, Task, User
from flask import redirect, url_for, session
from auth import oauth
from auth_middleware import require_role
from flask import render_template

routes = Blueprint("routes", __name__)


# -------------------------
# PAGES
# -------------------------

@routes.route("/")
def login_page():
    return render_template("login.html")


@routes.route("/board_page")
def board_page():
    return render_template("board.html")


# -------------------------
# TASK APIs
# -------------------------

@routes.route("/tasks", methods=["GET"])
@require_role("teacher", "student")
def get_tasks():

    user_id = session.get("user_id")
    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "not_allowed"}), 403
    
    tasks = Task.query.all()

    data = []

    for t in tasks:

        user = User.query.get(t.assigned_to)

        data.append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "status": t.status,
            "progress": t.progress,
            "due_date": t.due_date,
            "assigned_user": user.name if user else None
        })

    return jsonify(data)


@routes.route("/tasks", methods=["POST"])
@require_role("teacher", "student")
def create_task():

    data = request.json

    user_id = session.get("user_id")
    current_user = User.query.get(user_id)

    assigned_to = data.get("assigned_to")

    if current_user.role == "student":
        assigned_to = user_id

    elif current_user.role in ["teacher", "admin"]:
        assigned_user = User.query.get(assigned_to)

        if not assigned_user or assigned_user.role != "student":
            return jsonify({"error": "Can assign only to students"}), 403

    task = Task(
        title=data["title"],
        description=data.get("description"),
        status="todo",
        progress=0,
        due_date=data.get("due_date"),
        assigned_to=assigned_to,
        priority=data.get("priority")
    )

    db.session.add(task)
    db.session.commit()

    return jsonify({"message": "Task created"})


@routes.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):

    task = Task.query.get(task_id)

    if not task:
        return jsonify({"error": "Task not found"}),404

    data = request.json

    task.title = data.get("title",task.title)
    task.description = data.get("description",task.description)
    task.assigned_to = data.get("assigned_to",task.assigned_to)
    task.due_date = data.get("due_date",task.due_date)
    task.priority = data.get("priority", task.priority)

    db.session.commit()

    return jsonify({"message":"Task updated"})


@routes.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):

    task = Task.query.get(task_id)

    if not task:
        return jsonify({"error":"Task not found"}),404

    db.session.delete(task)
    db.session.commit()

    return jsonify({"message":"Task deleted"})


@routes.route("/tasks/<int:task_id>/status", methods=["PUT"])
def update_status(task_id):

    data = request.json
    task = Task.query.get(task_id)

    if not task:
        return jsonify({"error": "Task not found"}), 404

    task.status = data["status"]

    db.session.commit()

    return jsonify({"message": "Status updated"})


# -------------------------
# BOARD API
# -------------------------

@routes.route("/board")
def board():

    role = session.get("role")
    user_id = session.get("user_id")

    if role == "student":
        tasks = Task.query.filter_by(assigned_to=user_id).all()
    else:
        tasks = Task.query.all()

    board = {
        "todo": [],
        "in_progress": [],
        "done": []
    }

    for t in tasks:

        user = User.query.get(t.assigned_to)

        board[t.status].append({
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "due_date": t.due_date,
            "assigned_user": user.name if user else "Unassigned",
            "priority": t.priority
        })

    return jsonify(board)


# -------------------------
# USER MANAGEMENT
# -------------------------

@routes.route("/users", methods=["POST"])
@require_role("admin", "teacher")
def create_user():

    data = request.json

    existing_user = User.query.filter_by(email=data["email"]).first()

    if existing_user:
        return jsonify({"error": "User already exists"}), 400

    user = User(
        name=data["name"],
        email=data["email"],
        role=data["role"]
    )

    db.session.add(user)
    db.session.commit() 

    return jsonify({"message": "User created"})


@routes.route("/users", methods=["GET"])
def get_users():

    users = User.query.all()

    result = []

    for u in users:
        result.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role
        })

    return jsonify(result)


@routes.route("/admin")
def admin_dashboard():

    # Only admins allowed
    if session.get("role") != "admin":
        return redirect("/board_page")

    return render_template("admin.html")


@routes.route("/users/<int:user_id>", methods=["DELETE"])
@require_role("admin")
def delete_user(user_id):

    # Prevent admin from deleting themselves
    if session.get("user_id") == user_id:
        return jsonify({"error": "You cannot delete your own account"}), 400

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "User deleted"})

# -------------------------
# GOOGLE LOGIN
# -------------------------

@routes.route("/auth/google")
def google_login():

    redirect_uri = url_for("routes.google_callback", _external=True)

    return oauth.google.authorize_redirect(
        redirect_uri,
        prompt="select_account"
    )


ADMIN_EMAIL = "rosh.r@bscdsh.christuniversity.in"

@routes.route("/auth/google/callback")
def google_callback():

    token = oauth.google.authorize_access_token()
    resp = oauth.google.get("userinfo")
    user_info = resp.json()

    email = user_info["email"]
    name = user_info["name"]

    user = User.query.filter_by(email=email).first()

    # ❌ BLOCK if not created by admin
    if not user:
        return redirect("/?error=not_allowed")

    # Optional: update name
    user.name = name
    db.session.commit()

    session["user_id"] = user.id
    session["role"] = user.role

    if user.role == "admin":
        return redirect("/admin")
    else:
        return redirect("/board_page")


# -------------------------
# SESSION APIs
# -------------------------

@routes.route("/me")
def current_user():

    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "not logged in"}), 401

    user = User.query.get(user_id)

    if not user:
        session.clear()
        return jsonify({"error": "not_allowed"}), 403

    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role
    })


@routes.route("/logout")
def logout():

    session.clear()

    return redirect("/")