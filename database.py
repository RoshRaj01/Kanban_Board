from models import db
from flask import Flask

def init_db(app):
    db.init_app(app)

    with app.app_context():
        db.create_all()