import os
import psycopg2
from dotenv import load_dotenv
from flask import Flask, flash, g, redirect, render_template, request, session
from helpers import login_required
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config["SESSION_PERMANENT"] = True
app.config["DATABASE"] = {
    "host": os.getenv("PGHOST"),
    "dbname": os.getenv("PGDATABASE"),
    "user": os.getenv("PGUSER"),
    "password": os.getenv("PGPASSWORD")
}


@app.route("/")
def index():
    if session:
        return redirect("/dashboard")
    else:
        return redirect("/login")


@app.route("/add-transaction", methods=["POST"])
def add_transaction():
    transaction_type = request.form.get("transactionTypeRadio")
    category = request.form.get("categorySelect")
    title = request.form.get("titleInput")
    date = request.form.get("dateInput")
    amount = request.form.get("amountInput")
    if amount:
        amount = float(amount.replace("$", "").replace(",", ""))
    
    if not transaction_type:
        flash("You must choose the type of transaction.", "warning")
        return redirect("/dashboard")
    
    if not date:
        db_execute("""
            INSERT INTO transactions (user_id, title, amount, type, category, created_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
        """, params=[session["user_id"], title, amount, transaction_type, category])
    else:
        db_execute("""
            INSERT INTO transactions (user_id, title, amount, type, category, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, params=[session["user_id"], title, amount, transaction_type, category, date])

    flash("You've successfully added a new transaction.", "success")
    return redirect("/dashboard")

@app.route("/dashboard")
@login_required
def dashboard():
    total_income = db_execute("""
        SELECT SUM(amount) AS total_income
        FROM transactions
        WHERE type = 'income'
        AND user_id = %s
    """, params=[session["user_id"]], return_value=True)[0][0]

    total_expenses = db_execute("""
        SELECT SUM(amount) AS total_expenses
        FROM transactions
        WHERE type = 'expense'
        AND user_id = %s
    """, params=[session["user_id"]], return_value=True)[0][0]

    if not total_income:
        total_income = 0
    
    if not total_expenses:
        total_expenses = 0

    current_balance = total_income - total_expenses

    transactions = db_execute("""
        SELECT category, title, amount, created_at, type AS transactions
        FROM transactions
        WHERE user_id = %s
        ORDER BY created_at
    """, params=[session["user_id"]], return_value=True)

    return render_template("dashboard.html", current_balance=current_balance, total_income=total_income, total_expenses=total_expenses, transactions=transactions)


@app.route("/expenses")
@login_required
def expenses():
    return render_template("expenses.html")


@app.route("/income")
@login_required
def income():
    return render_template("income.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "GET":
        return render_template("login.html")
    
    username = request.form.get("usernameInput")
    password = request.form.get("passwordInput")

    if not username or not password:
        flash("You must fill in all fields.", "warning")
        return render_template("login.html")
    
    rows = db_execute("""
        SELECT *
        FROM users
        WHERE username = %s
    """, params=[username], return_value=True) # gets the user information

    if len(rows) != 1 or not check_password_hash(
        rows[0][2], password # compares "hash" field with the typed password in hash function
    ):
        flash("Invalid username and/or password.", "warning")
        return render_template("login.html")
    
    session["user_id"] = rows[0][0] # creates a new active session with the user id

    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()

    if request.method == "GET":
        return render_template("register.html")
    
    username = request.form.get("usernameInput")
    password = request.form.get("passwordInput")
    confirm_password = request.form.get("confirmPasswordInput")

    if not username or not password or not confirm_password:
        flash("You must fill in all fields.", "warning")
        return render_template("register.html")
    
    if password != confirm_password:
        flash("Check if you confirmed your password correctly.", "warning")
        return render_template("register.html")
    
    username_is_already_taken = db_execute("""
        SELECT 1
        FROM users
        WHERE username = %s
    """, params=[username], return_value=True)

    if username_is_already_taken:
        flash("Sorry, this username is already taken. Please choose another.", "warning")
        return render_template("register.html")
    
    password_hash = generate_password_hash(password)

    db_execute("""
        INSERT INTO users (username, hash)
        VALUES (%s, %s)
    """, params=[username, password_hash])

    flash("Registration successful! You can now log in to your account.", "success")
    return render_template("login.html")


@app.template_filter("money")
def format_money(value):
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return value


def get_db():
    return psycopg2.connect(
        host=app.config["DATABASE"]["host"],
        dbname=app.config["DATABASE"]["dbname"],
        user=app.config["DATABASE"]["user"],
        password=app.config["DATABASE"]["password"]
    )


def db_execute(query, params=None, return_value=False):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(query, params)
    
    if return_value:
        results = cursor.fetchall()
        db.close()
        return results
    else:
        db.commit()
        db.close()
    

if __name__ == "__main__":
    app.run(debug=True)