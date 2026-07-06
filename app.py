from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'trek_secret_key'

# Initialize database
from models import db, User, Staff
db.init_app(app)

# ===== Create tables and seed admin (runs once at startup) =====
with app.app_context():
    db.create_all()

    admin_exists = User.query.filter_by(role='admin').first()
    if not admin_exists:
        admin = User(
            username='admin',
            email='admin@ruyahorizons.com',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created.")
    else:
        print("Admin already exists.")

# ===== Flask-Login Setup =====
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ===== Routes =====

@app.route('/')
def index():
    return render_template('index.html')

# ===== Register =====

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match",
                                    username=username, email=email)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return render_template('register.html', error="Email already registered",
                                    username=username, email=email)

        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role=role
        )
        db.session.add(new_user)
        db.session.commit()

        if role == 'trek_staff':
            new_staff = Staff(user_id=new_user.id, is_approved=False)
            db.session.add(new_staff)
            db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

# ===== Login =====

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            return render_template('login.html', error="Invalid email or password", email=email)

        if user.role == 'trek_staff':
            staff_profile = Staff.query.filter_by(user_id=user.id).first()
            if not staff_profile or not staff_profile.is_approved:
                return render_template('login.html', error="Your account is pending admin approval", email=email)

        login_user(user)

        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role == 'trek_staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))

    return render_template('login.html')

# ===== Logout =====

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ===== Placeholder Dashboards (role-restricted) =====

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403
    return "Admin dashboard coming soon"

@app.route('/staff/dashboard')
@login_required
def staff_dashboard():
    if current_user.role != 'trek_staff':
        return "Access denied: Trek Staff only", 403
    return "Staff dashboard coming soon"

@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role != 'trekker':
        return "Access denied: Trekkers only", 403
    return "Trekker dashboard coming soon"

# ===== Run App =====

if __name__ == '__main__':
    app.run(debug=True)