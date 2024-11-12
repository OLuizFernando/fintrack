from flask import Flask, redirect, render_template, session
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

@app.route("/login")
def login():
    return render_template("login.html")

if __name__ == "__main__":
    app.run(debug=True)