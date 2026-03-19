from flask import Flask, render_template, redirect, request, abort, flash
from models import db, User, Feedback
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from textblob import TextBlob
from datetime import timedelta
import csv

app = Flask(__name__)

# 🔐 CONFIG
app.config['SECRET_KEY'] = 'secret123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)

db.init_app(app)

# 🔐 LOGIN MANAGER
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# 🏠 HOME
@app.route('/')
def home():
    return redirect('/login')


# 🔐 REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash("⚠️ All fields required", "error")
            return redirect('/register')

        existing = User.query.filter_by(username=username).first()
        if existing:
            flash("❌ User already exists", "error")
            return redirect('/register')

        hashed_password = generate_password_hash(password)

        role = 'admin' if User.query.count() == 0 else 'user'

        user = User(username=username, password=hashed_password, role=role)
        db.session.add(user)
        db.session.commit()

        flash("🎉 Account created successfully! Please login.", "success")
        return redirect('/login')

    return render_template('register.html')

# 🔐 LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/dashboard')

    error = False

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)
            return redirect('/dashboard')
        else:
            error = True

    return render_template('login.html', error=error)


# 📊 DASHBOARD
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():

    # 📁 CSV Upload
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']

        if file and file.filename.endswith('.csv'):
            reader = csv.DictReader(file.stream.read().decode("UTF-8").splitlines())

            for row in reader:
                text = row.get('feedback', '')

                analysis = TextBlob(text)
                sentiment = "Positive" if analysis.sentiment.polarity > 0 else "Negative"

                fb = Feedback(
                    name=row.get('name'),
                    phone=row.get('phone'),
                    service=row.get('service'),
                    text=text,
                    sentiment=sentiment
                )

                db.session.add(fb)

            db.session.commit()

    # 🧠 Manual Input
    elif request.method == 'POST':
        text = request.form.get('feedback')

        if text:
            analysis = TextBlob(text)
            sentiment = "Positive" if analysis.sentiment.polarity > 0 else "Negative"

            fb = Feedback(
                name=request.form.get('name'),
                phone=request.form.get('phone'),
                service=request.form.get('service'),
                text=text,
                sentiment=sentiment
            )

            db.session.add(fb)
            db.session.commit()

    feedbacks = Feedback.query.all()

    # 📊 Stats
    total = len(feedbacks)
    positive = sum(1 for f in feedbacks if f.sentiment == "Positive")
    negative = total - positive
    positive_percent = round((positive / total) * 100, 2) if total > 0 else 0

    # 📈 Chart data
    labels = list(range(1, total + 1))
    data_values = [1 if f.sentiment == "Positive" else 0 for f in feedbacks]

    # 🚨 Alert
    alert = "⚠️ Warning: High negative feedback!" if negative > positive else None

    return render_template(
        'dashboard.html',
        feedbacks=feedbacks,
        total=total,
        positive=positive,
        negative=negative,
        positive_percent=positive_percent,
        labels=labels,
        data_values=data_values,
        alert=alert
    )


# 👑 ADMIN PANEL
@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        abort(403)

    users = User.query.all()
    return render_template('admin.html', users=users)


# 📈 ANALYTICS PAGE
@app.route('/analytics')
@login_required
def analytics():
    feedbacks = Feedback.query.all()

    positive = sum(1 for f in feedbacks if f.sentiment == "Positive")
    negative = len(feedbacks) - positive

    return render_template('analytics.html', positive=positive, negative=negative)


# 👥 CUSTOMERS PAGE
@app.route('/customers')
@login_required
def customers():
    feedbacks = Feedback.query.all()
    return render_template('customers.html', feedbacks=feedbacks)


# 📄 REPORTS PAGE
@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')


# ⚙️ SETTINGS
@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')


# ℹ️ ABOUT
@app.route('/about')
@login_required
def about():
    return render_template('about.html')


# 🚪 LOGOUT
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')


# 🚀 RUN
if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)