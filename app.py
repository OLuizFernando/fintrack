import os
import psycopg2
from dotenv import load_dotenv
from flask import Flask, g, redirect, render_template, request, session
from helpers import login_required

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['DATABASE'] = {
    'host': os.getenv("PGHOST"),
    'dbname': os.getenv("PGDATABASE"),
    'user': os.getenv("PGUSER"),
    'password': os.getenv("PGPASSWORD")
}

def get_db():
    return psycopg2.connect(
        host=app.config['DATABASE']['host'],
        dbname=app.config['DATABASE']['dbname'],
        user=app.config['DATABASE']['user'],
        password=app.config['DATABASE']['password']
    )

def db_execute(query, params=None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    db.close()
    return results

@app.route("/")
def index():
    if session:
        return redirect("/dashboard")
    else:
        return redirect("/login")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

if __name__ == "__main__":
    app.run(debug=True)