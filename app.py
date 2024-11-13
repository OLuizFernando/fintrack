from flask import Flask, redirect, render_template, request, session
from helpers import login_required

app = Flask(__name__)
app.secret_key = "ChaveDeTeste"

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