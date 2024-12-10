import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
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
    called_in = request.form.get("called_in")

    if amount:
        amount = float(amount.replace("$", "").replace(",", ""))
    
    if not transaction_type:
        flash("You must choose the type of transaction.", "warning")
        return redirect("/dashboard")
    
    category_id = db_execute("""
        SELECT id
        FROM categories
        WHERE name = %s
        AND user_id IN (0, %s)
        LIMIT 1
    """, params=[category, session["user_id"]], return_value=True)[0]["id"]

    if not date:
        db_execute("""
            INSERT INTO transactions (user_id, title, amount, type, category_id, created_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_DATE)
        """, params=[session["user_id"], title, amount, transaction_type, category_id])
    else:
        db_execute("""
            INSERT INTO transactions (user_id, title, amount, type, category_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, params=[session["user_id"], title, amount, transaction_type, category_id, date])

    if called_in == "/dashboard":
        flash("You've successfully added a new transaction.", "success")
    elif called_in == "/income":
        flash("You've successfully added a new income.", "success")
    elif called_in == "/expenses":
        flash("You've successfully added a new expense.", "success")

    return redirect(called_in)


@app.route("/create-category", methods=["POST"])
@login_required
def create_category():
    name = request.form.get("nameInput")
    called_in = request.form.get("called_in")
    
    if not name:
        flash("You must provide a name for the category.", "warning")
        return redirect(called_in)
    
    db_execute("""
        INSERT INTO categories (user_id, name)
        VALUES (%s, %s)
    """, params=[session["user_id"], name])

    flash("You've successfully created a new category.", "success")
    return redirect(called_in)


@app.route("/dashboard")
@login_required
def dashboard():
    total_income = db_execute("""
        SELECT SUM(amount) AS total_income
        FROM transactions
        WHERE type = 'income'
        AND user_id = %s
    """, params=[session["user_id"]], return_value=True)[0]["total_income"]

    total_expenses = db_execute("""
        SELECT SUM(amount) AS total_expenses
        FROM transactions
        WHERE type = 'expense'
        AND user_id = %s
    """, params=[session["user_id"]], return_value=True)[0]["total_expenses"]

    if not total_income:
        total_income = 0
    
    if not total_expenses:
        total_expenses = 0

    current_balance = total_income - total_expenses

    available_categories = db_execute("""
        SELECT name
        FROM categories
        WHERE user_id IN (0, %s)
        ORDER BY name
    """, params=[session["user_id"]], return_value=True)

    transactions = db_execute("""
        SELECT title, amount, created_at, type, id, (
            SELECT name FROM categories WHERE id = t.category_id LIMIT 1
        ) AS category
        FROM transactions t
        WHERE user_id = %s
        ORDER BY created_at DESC;
    """, params=[session["user_id"]], return_value=True)

    return render_template("dashboard.html", current_balance=current_balance, total_income=total_income, total_expenses=total_expenses, transactions=transactions, available_categories=available_categories)


@app.route("/delete-transaction", methods=["POST"])
@login_required
def delete_transaction():
    transaction_id = request.form.get("transaction_id")
    called_in = request.form.get("called_in")

    if transaction_id:
        db_execute("""
            DELETE FROM transactions
            WHERE user_id = %s
            AND id = %s
        """, params=[session["user_id"], transaction_id])
        flash("You've deleted a transaction!", "danger")
    else:
        flash("Transaction ID not provided.", "warning")
    return redirect(called_in)

@app.route("/expenses")
@login_required
def expenses():
    expenses = db_execute("""
        SELECT title, amount, created_at, type, id, (
            SELECT name FROM categories WHERE id = t.category_id LIMIT 1
        ) AS category
        FROM transactions t
        WHERE user_id = %s
        AND type = 'expense'
        ORDER BY created_at DESC
    """, params=[session["user_id"]], return_value=True)

    total_expenses = db_execute("""
        SELECT SUM(amount) AS total_expenses
        FROM transactions
        WHERE type = 'expense'
        AND user_id = %s
    """, params=[session["user_id"]], return_value=True)[0]["total_expenses"]

    if not total_expenses:
        total_expenses = 0

    available_categories = db_execute("""
        SELECT name
        FROM categories
        WHERE user_id IN (0, %s)
        ORDER BY name
    """, params=[session["user_id"]], return_value=True)

    categories = db_execute("""
        SELECT DISTINCT (
            SELECT name FROM categories WHERE id = t.category_id LIMIT 1
        ) AS category
        FROM transactions t
        WHERE t.type = 'expense'
        AND t.user_id = %s;
    """, params=[session["user_id"]], return_value=True)

    categories = [item["category"] for item in categories]

    amount_per_category = db_execute("""
        SELECT SUM(amount) AS amount_per_category
        FROM transactions
        WHERE type = 'expense'
        AND user_id = %s
        GROUP BY category_id;
    """, params=[session["user_id"]], return_value=True)

    amount_per_category = [item["amount_per_category"] for item in amount_per_category]

    amount_per_month = db_execute("""
        SELECT TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY/MM') AS month,
        SUM(amount) AS amount
        FROM transactions
        WHERE type = 'expense'
        AND user_id = %s
        GROUP BY DATE_TRUNC('month', created_at)
        ORDER BY month DESC
    """, params=[session["user_id"]], return_value=True)

    return render_template("expenses.html", expenses=expenses, total_expenses=total_expenses, amount_per_month=amount_per_month, available_categories=available_categories, categories=categories, amount_per_category=amount_per_category)


@app.route("/income")
@login_required
def income():
    income_list = db_execute("""
        SELECT title, amount, created_at, type, id, (
            SELECT name FROM categories WHERE id = t.category_id LIMIT 1
        ) AS category
        FROM transactions t
        WHERE user_id = %s
        AND type = 'income'
        ORDER BY created_at DESC
    """, params=[session["user_id"]], return_value=True)

    total_income = db_execute("""
        SELECT SUM(amount) AS total_income
        FROM transactions
        WHERE type = 'income'
        AND user_id = %s
    """, params=[session["user_id"]], return_value=True)[0]["total_income"]

    if not total_income:
        total_income = 0

    available_categories = db_execute("""
        SELECT name
        FROM categories
        WHERE user_id IN (0, %s)
        ORDER BY name
    """, params=[session["user_id"]], return_value=True)

    categories = db_execute("""
        SELECT DISTINCT (
            SELECT name FROM categories WHERE id = t.category_id LIMIT 1
        ) AS category
        FROM transactions t
        WHERE t.type = 'income'
        AND t.user_id = %s;
    """, params=[session["user_id"]], return_value=True)

    categories = [item["category"] for item in categories]

    amount_per_category = db_execute("""
        SELECT SUM(amount) AS amount_per_category
        FROM transactions
        WHERE type = 'income'
        AND user_id = %s
        GROUP BY category_id;
    """, params=[session["user_id"]], return_value=True)

    amount_per_category = [item["amount_per_category"] for item in amount_per_category]

    amount_per_month = db_execute("""
        SELECT TO_CHAR(DATE_TRUNC('month', created_at), 'YYYY/MM') AS month,
        SUM(amount) AS amount
        FROM transactions
        WHERE type = 'income'
        AND user_id = %s
        GROUP BY DATE_TRUNC('month', created_at)
        ORDER BY month DESC
    """, params=[session["user_id"]], return_value=True)

    return render_template("income.html", income_list=income_list, total_income=total_income, amount_per_month=amount_per_month, available_categories=available_categories, categories=categories, amount_per_category=amount_per_category)


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
        WHERE username ILIKE %s
    """, params=[username], return_value=True) # gets the user information

    if len(rows) != 1 or not check_password_hash(
        rows[0]["hash"], password # compares "hash" field with the typed password in hash function
    ):
        flash("Invalid username and/or password.", "warning")
        return render_template("login.html")
    
    session["user_id"] = rows[0]["id"] # creates a new active session with the user id

    return redirect("/")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
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


@app.route("/tester-login")
def tester_login():
    session.clear()
    session["user_id"] = 3
    
    return redirect("/")


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
    cursor_factory = RealDictCursor if return_value else None
    cursor = db.cursor(cursor_factory=cursor_factory)
    
    try:
        cursor.execute(query, params)
        if return_value:
            results = cursor.fetchall()
            return results
        else:
            db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        cursor.close()
        db.close()
    

if __name__ == "__main__":
    app.run(debug=True)