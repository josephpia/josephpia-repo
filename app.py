from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "secretkey123"

# Default admin account
users = {
    "admin": {
        "password": "1234",
        "role": "admin"
    }
}

login_count = 0
service_requests = []

@app.route('/')
def home():
    return redirect(url_for('login'))

# LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    global login_count
    message = ""

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username not in users:
            message = "User does not have an account"

        elif users[username]["password"] == password:
            session['username'] = username
            session['role'] = users[username]["role"]

            login_count += 1

            if users[username]["role"] == "admin":
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))

        else:
            message = "Wrong password"

    return render_template('login.html', message=message)

# SIGNUP
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    message = ""

    if request.method == 'POST':
        firstname = request.form['firstname']
        middlename = request.form['middlename']
        lastname = request.form['lastname']
        age = request.form['age']
        address = request.form['address']
        birthdate = request.form['birthdate']
        email = request.form['email']
        cellphone = request.form['cellphone']
        username = request.form['username']
        password = request.form['password']

        if username in users:
            message = "Username already exists"

        else:
            users[username] = {
                "firstname": firstname,
                "middlename": middlename,
                "lastname": lastname,
                "age": age,
                "address": address,
                "birthdate": birthdate,
                "email": email,
                "cellphone": cellphone,
                "password": password,
                "role": "user"
            }

            return redirect(url_for('login'))

    return render_template('signup.html', message=message)

# USER DASHBOARD
@app.route('/userdashboard', methods=['GET', 'POST'])
def user_dashboard():
    message = ""

    if request.method == 'POST':
        service = request.form['service']
        service_requests.append({
            "username": session['username'],
            "service": service
        })
        message = "Service request submitted"

    return render_template('userdashboard.html', message=message)

# ADMIN DASHBOARD
@app.route('/admindashboard')
def admin_dashboard():
    total_users = len(users)
    return render_template(
        'admindashboard.html',
        total_users=total_users,
        users=users,
        service_requests=service_requests
    )

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)