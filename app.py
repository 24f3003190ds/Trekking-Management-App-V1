from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tma.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'trek_secret_key'

# Initialize database
from models import db, User, Staff, Trek, Booking
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

    total_treks = Trek.query.count()
    total_users = User.query.filter_by(role='trekker').count()
    total_staff = Staff.query.count()
    total_bookings = Booking.query.count()
    all_bookings = Booking.query.order_by(Booking.booking_date.desc()).all()

    return render_template('admin_dashboard.html',
                            total_treks=total_treks,
                            total_users=total_users,
                            total_staff=total_staff,
                            total_bookings=total_bookings,
                            all_bookings=all_bookings)

@app.route('/admin/treks')
@login_required
def admin_treks():
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403

    search_query = request.args.get('q', '')
    if search_query:
        treks = Trek.query.filter(Trek.name.ilike(f'%{search_query}%')).all()
    else:
        treks = Trek.query.all()

    return render_template('admin_manage_treks.html', treks=treks, search_query=search_query)


@app.route('/admin/treks/delete/<int:trek_id>')
@login_required
def admin_delete_trek(trek_id):
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403

    trek = Trek.query.get_or_404(trek_id)
    db.session.delete(trek)
    db.session.commit()
    return redirect(url_for('admin_treks'))


@app.route('/admin/treks/add', methods=['GET', 'POST'])
@login_required
def admin_add_trek():
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403

    approved_staff = Staff.query.filter_by(is_approved=True).all()

    if request.method == 'POST':
        name = request.form.get('name')
        location = request.form.get('location')
        difficulty = request.form.get('difficulty')
        duration = request.form.get('duration')
        price = request.form.get('price')
        total_slots = request.form.get('total_slots')
        available_slots = request.form.get('available_slots')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        status = request.form.get('status')
        assigned_staff_id = request.form.get('assigned_staff_id') or None
        description = request.form.get('description')

        new_trek = Trek(
            name=name,
            location=location,
            difficulty=difficulty,
            duration=int(duration),
            price=float(price),
            total_slots=int(total_slots),
            available_slots=int(available_slots),
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
            status=status,
            assigned_staff_id=int(assigned_staff_id) if assigned_staff_id else None,
            description=description
        )
        db.session.add(new_trek)
        db.session.commit()
        return redirect(url_for('admin_treks'))

    return render_template('admin_trek_form.html', trek=None, approved_staff=approved_staff)


@app.route('/admin/treks/edit/<int:trek_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_trek(trek_id):
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403

    trek = Trek.query.get_or_404(trek_id)
    approved_staff = Staff.query.filter_by(is_approved=True).all()

    if request.method == 'POST':
        trek.name = request.form.get('name')
        trek.location = request.form.get('location')
        trek.difficulty = request.form.get('difficulty')
        trek.duration = int(request.form.get('duration'))
        trek.price = float(request.form.get('price'))
        trek.total_slots = int(request.form.get('total_slots'))
        trek.available_slots = int(request.form.get('available_slots'))
        trek.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        trek.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
        trek.status = request.form.get('status')
        assigned_staff_id = request.form.get('assigned_staff_id') or None
        trek.assigned_staff_id = int(assigned_staff_id) if assigned_staff_id else None
        trek.description = request.form.get('description')

        db.session.commit()
        return redirect(url_for('admin_treks'))

    return render_template('admin_trek_form.html', trek=trek, approved_staff=approved_staff)


@app.route('/admin/staff')
@login_required
def admin_staff():
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403

    search_query = request.args.get('q', '')
    if search_query:
        staff_list = Staff.query.join(User).filter(User.username.ilike(f'%{search_query}%')).all()
    else:
        staff_list = Staff.query.all()

    return render_template('admin_manage_staff.html', staff_list=staff_list, search_query=search_query)


@app.route('/admin/staff/approve/<int:staff_id>')
@login_required
def admin_approve_staff(staff_id):
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403

    staff = Staff.query.get_or_404(staff_id)
    staff.is_approved = True
    db.session.commit()
    return redirect(url_for('admin_staff'))


@app.route('/admin/staff/blacklist/<int:staff_id>')
@login_required
def admin_blacklist_staff(staff_id):
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403

    staff = Staff.query.get_or_404(staff_id)
    staff.is_approved = False
    db.session.commit()
    return redirect(url_for('admin_staff'))


@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403

    search_query = request.args.get('q', '')
    if search_query:
        users = User.query.filter_by(role='trekker').filter(User.username.ilike(f'%{search_query}%')).all()
    else:
        users = User.query.filter_by(role='trekker').all()

    return render_template('admin_manage_users.html', users=users, search_query=search_query)


@app.route('/admin/users/deactivate/<int:user_id>')
@login_required
def admin_deactivate_user(user_id):
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403

    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    return redirect(url_for('admin_users'))


@app.route('/admin/users/activate/<int:user_id>')
@login_required
def admin_activate_user(user_id):
    if current_user.role != 'admin':
        return "Access denied: Admins only", 403

    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()
    return redirect(url_for('admin_users'))


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