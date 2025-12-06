from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_session import Session
from flask_mysqldb import MySQL
from send_email import send_mail 
from otp import generate_otp
from itsdangerous import URLSafeTimedSerializer as Serializer


app = Flask(__name__)
app.secret_key = '0000'
app.config['SESSION_TYPE'] = 'filesystem'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '$$$$'
app.config['MYSQL_DB'] = 'mahitha'
Session(app)
mysql = MySQL(app)

@app.route('/')
def home_page():
    return render_template('home.html')

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        phone = request.form["phone"]
        bank_name = request.form["bank_name"]
        account_no = request.form["account_no"]

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM registration WHERE email=%s", (email,))
        account = cur.fetchone()
        cur.close()

        if account:
            flash("Email already registered!")
            return redirect(url_for("register"))

        otp = str(generate_otp())
        session['reg_otp'] = otp
        session['reg_details'] = {
            "name": name,
            "email": email,
            "password": password,
            "phone": phone,
            "bank_name": bank_name,
            "account_no": account_no
        }

        subject = "Registration OTP"
        body = f"Your OTP for registration is: {otp}"
        send_mail(email, subject, body)

        flash("OTP sent to your email. Please verify.")
        return redirect(url_for("verify_register_otp"))

    return render_template("registration.html")

@app.route("/verify_register_otp", methods=["GET", "POST"])
def verify_register_otp():
    if request.method == "POST":
        entered_otp = request.form['otp']
        if entered_otp == str(session.get('reg_otp')):
            details = session.get('reg_details')
            if details:
                cur = mysql.connection.cursor()
                cur.execute("""INSERT INTO registration(name, email, password, phone, bank_name, account_no) 
                            VALUES (%s,%s,%s,%s,%s,%s)""",
                            (details['name'], details['email'], details['password'],
                             details['phone'], details['bank_name'], details['account_no']))
                mysql.connection.commit()
                cur.close()
                session.pop('reg_otp', None)
                session.pop('reg_details', None)
                flash("Registration successful! Please login.")
                return redirect(url_for("login"))
        else:
            flash("Incorrect OTP! Try again.")
            return redirect(url_for("verify_register_otp"))
    return render_template("verify_register_otp.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM registration WHERE email = %s AND password = %s', (email, password))
        account = cursor.fetchone()
        cursor.close()
        if account:
            session['user'] = email 
            flash('Login successful!')
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password')
            return redirect('/login')
    return render_template('login.html')

@app.route('/index')
def index():
    if not session.get('user'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/add', methods=['GET','POST'])
def add():
    if not session.get('user'):  
        flash("Please login first.")
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT category_name FROM categories")
    categories = cursor.fetchall()
    cursor.execute("SELECT payment_name FROM payment_modes")
    payments = cursor.fetchall()
    if request.method == 'POST':
        date = request.form['date']
        category_name = request.form['category'] 
        payment_name = request.form['payment']    
        description = request.form['description']
        amount = float(request.form['amount'])
        user_email = session['user'] 
        cursor.execute("SELECT category_id FROM categories WHERE category_name=%s", (category_name,))
        category_row = cursor.fetchone()
        if category_row:
            category_id = category_row[0]
        else:
            flash("Invalid category selected!")
            cursor.close()
            return redirect(url_for('add'))
        cursor.execute("SELECT payment_id FROM payment_modes WHERE payment_name=%s", (payment_name,))
        payment_row = cursor.fetchone()
        if payment_row:
            payment_id = payment_row[0]
        else:
            flash("Invalid payment selected!")
            cursor.close()
            return redirect(url_for('add'))
        cursor.execute("""INSERT INTO expenses(expense_date, category_id, description, amount, payment_id, user_email) VALUES (%s, %s, %s, %s, %s, %s)""",(date, category_id, description, amount, payment_id, user_email))
        mysql.connection.commit()
        cursor.close()
        flash("Expense added successfully!")
        return redirect('/add')
    cursor.close()
    return render_template('add.html', categories=categories, payments=payments)

@app.route('/view')
def view():
    if not session.get('user'):
        flash("Please login first.")
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT e.id, e.expense_date, c.category_name, e.description, e.amount, p.payment_name
        FROM expenses e
        JOIN categories c ON e.category_id = c.category_id
        JOIN payment_modes p ON e.payment_id = p.payment_id
        WHERE e.user_email = %s
        ORDER BY e.expense_date DESC
    """, (session['user'],))
    expenses = cursor.fetchall()
    cursor.close()
    return render_template('view.html', expenses=expenses)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if not session.get('user'):  
        flash("Please login first.")
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()
    results = []
    if request.method == 'POST':
        query = request.form['query']
        cursor.execute("""
            SELECT e.id, e.expense_date, c.category_name, e.description, e.amount, p.payment_name 
            FROM expenses e 
            JOIN categories c ON e.category_id = c.category_id 
            JOIN payment_modes p ON e.payment_id = p.payment_id 
            WHERE e.user_email=%s AND (c.category_name LIKE %s OR e.description LIKE %s)
            ORDER BY e.expense_date DESC
        """, (session['user'], f"%{query}%", f"%{query}%"))
        results = cursor.fetchall()
    else:
        cursor.execute("""
            SELECT e.id, e.expense_date, c.category_name, e.description, e.amount, p.payment_name 
            FROM expenses e 
            JOIN categories c ON e.category_id = c.category_id 
            JOIN payment_modes p ON e.payment_id = p.payment_id 
            WHERE e.user_email=%s 
            ORDER BY e.expense_date DESC
        """, (session['user'],))
        results = cursor.fetchall()
    cursor.close()
    return render_template('search.html', results=results)

@app.route('/summary')
def summary():
    if not session.get('user'): 
        flash("Please login first.")
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()
    cursor.execute("""SELECT c.category_name, SUM(e.amount) 
                      FROM expenses e 
                      JOIN categories c ON e.category_id=c.category_id 
                      WHERE e.user_email=%s GROUP BY c.category_name""", (session['user'],))
    summary = cursor.fetchall()
    cursor.close()
    return render_template('summary.html', summary=summary)

@app.route('/monthly')
def monthly():
    if not session.get('user'):  
        flash("Please login first.")
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor()
    cursor.execute(r"""
        SELECT DATE_FORMAT(expense_date, '%%Y-%%m') AS month, SUM(amount) AS total
        FROM expenses
        WHERE user_email=%s
        GROUP BY month
        ORDER BY month DESC
    """, (session['user'],))
    monthly_totals = cursor.fetchall()
    cursor.close()
    return render_template('monthly.html', monthly_totals=monthly_totals)

@app.route('/forgot_password', methods=['GET','POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT count(*) FROM registration WHERE email=%s', (email,))
        count = cursor.fetchone()[0]
        if count == 1:
            s = Serializer(app.secret_key)
            token = s.dumps({'user_email': email}, salt='password-reset-salt')
            cursor.execute('UPDATE registration SET reset_token=%s WHERE email=%s', (token, email))
            mysql.connection.commit()
            cursor.close()
            reset_link = request.host_url.rstrip('/') + url_for('reset_password', token=token)
            subject = 'Reset Password'
            body = f'Click this link to reset your password:\n{reset_link}\nNote: Link expires in 5 minutes.'
            send_mail(email, subject, body)
            flash('Password reset link sent to your email!')
            return redirect(url_for('forgot_password'))
        else:
            flash('Email not registered!')
            return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    s = Serializer(app.secret_key)
    cursor = mysql.connection.cursor()
    cursor.execute('SELECT email, reset_token FROM registration WHERE reset_token=%s', (token,))
    row = cursor.fetchone()
    if not row:
        flash('Invalid or expired link!')
        return redirect(url_for('forgot_password'))
    email, db_token = row
    data = s.loads(token, salt='password-reset-salt', max_age=300)
    if data['user_email'] != email:
        flash('Invalid link!')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['newpassword']
        confirm_password = request.form['confirmpassword']

        if new_password != confirm_password:
            flash('Passwords do not match!')
            return redirect(url_for('reset_password', token=token))
        cursor.execute('UPDATE registration SET password=%s, reset_token=NULL WHERE email=%s',(new_password, email))
        mysql.connection.commit()
        cursor.close()
        flash('Password updated successfully! Please login.')
        return redirect(url_for('login'))

    cursor.close()
    return render_template('reset_password.html', token=token)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.")
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
