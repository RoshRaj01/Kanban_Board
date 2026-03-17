from flask import Flask
from flask_cors import CORS
from database import init_db
from routes import routes
from auth import init_oauth
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

google = init_oauth(app)
CORS(app)

init_db(app)

app.register_blueprint(routes)

if __name__ == "__main__":
    print("Server starting...")
    app.run(debug=True) 