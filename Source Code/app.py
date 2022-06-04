import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd

from datetime import datetime, timezone, timedelta


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///BooksDB.db")

#Error hadling method
def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

#Login method
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure email was submitted
        if not request.form.get("email"):
            return apology("must provide email", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for email
        rows = db.execute("SELECT * FROM user WHERE email = ?", request.form.get("email"))

        # Ensure email exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["password"], request.form.get("password")):
            return apology("invalid email and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# Register method
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    # check email and password
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")
    referrer = request.form.get("referrer")
    if name == "":
        return apology("Invalid name: Blank, or already exists")
    if email == "" or len(db.execute('SELECT email FROM user WHERE email = ?', email)) > 0:
        return apology("Invalid email: Blank, or already exists")
    if password == "" or password != confirmation:
        return apology("Invalid Password: Blank, or does not match")
    # Add new user to user db (includes: email and HASH of password)
    db.execute('INSERT INTO user (name, email, password, referrer) VALUES(?, ?, ?, ?)', name, email, generate_password_hash(password), referrer)
    # Query database for email
    rows = db.execute("SELECT * FROM user WHERE email = ?", email)
    # Log user in, i.e. Remember that this user has logged in
    session["user_id"] = rows[0]["id"]
    # Redirect user to home page
    return redirect("/")

# Logout method
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


#Index page - Buy Page
@app.route("/")
def index():
    """Index page - Buy Page """
    books = db.execute("SELECT * FROM book")
    return render_template("index.html", books = books)


@app.route("/buy")
@login_required
def buy():
    user_id = session["user_id"]
    user = db.execute("SELECT * FROM user WHERE id=?", user_id)
    book_id = request.args.get("id")
    book = db.execute("SELECT * FROM book WHERE id=?", book_id)
    price = book[0]["price"]
    #if the user's refree count is higher than or equal 10 the do the following
    refree_count = user[0]["refree_count"]
    if refree_count >= 10:
        # Give the user 3 dollars discount
        price = price - 3
        # Then decrement the refree_count by one so the user don't abuse the system
        refree_count - 1
        db.execute("UPDATE user SET refree_count= ?", refree_count)
    db.execute("INSERT INTO user_books (user_id, book_id, title, Author, price) VALUES (?, ?, ?, ?, ?)", user_id, book[0]["id"], book[0]["title"], book[0]["author"], price)
    # Check if the user has a referrer if so then update the referrer's count
    referrer = user[0]["referrer"]
    if referrer != "":
        # Get the referrer by it's email from the DB
        referrer_user = db.execute('SELECT * FROM user WHERE email=?', referrer)
        # Increment the refree_count
        refree_count = referrer_user[0]["refree_count"]
        refree_count += 1
        # Then store the new count in the Database
        db.execute('UPDATE user SET refree_count=? WHERE email=?', refree_count, referrer)
    return redirect("/history")


@app.route("/history")
@login_required
def allBooks():
    user_id = session["user_id"]
    books = db.execute("SELECT id, title, author, price, purchase_date FROM user_books WHERE user_id = ?", user_id)
    return render_template("history.html", books=books)


@app.route("/refund")
@login_required
def refund():
    user_id = session["user_id"]
    order_id = request.args.get("id")
    date = db.execute("SELECT purchase_date FROM user_books WHERE id=? AND user_id=?", order_id, user_id)
    pruchase_date_str = date[0]["purchase_date"]

    # Convert the pruchase date from string to date
    pruchase_date = datetime.strptime(pruchase_date_str, '%Y-%m-%d')
    # Get the current day
    today = datetime.today().strftime("%Y-%m-%d")
    # Convert today from string to a date
    today = datetime.strptime(today, "%Y-%m-%d")
    # Add 14 days to the purchase day
    end_date = pruchase_date + timedelta(days=14)
    end_date = end_date.strftime("%Y-%m-%d")
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    print(end_date)
    # Check if 14 days has passed of day of purchase
    if (today < end_date):
        db.execute("DELETE FROM user_books WHERE user_id=? AND id=?", user_id, order_id)
    return redirect("/history")