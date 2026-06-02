from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Category, Topic
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-to-something-secure'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///learning_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create admin user if not exists
def create_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("="*50)
        print("Admin user created!")
        print("Username: admin")
        print("Password: admin123")
        print("="*50)
        print("Please change the password after first login!")

# Routes
@app.route('/')
def index():
    categories = Category.query.all()
    return render_template('index.html', categories=categories, current_user=current_user)

@app.route('/category/<int:category_id>')
def view_category(category_id):
    category = Category.query.get_or_404(category_id)
    return render_template('category.html', category=category, current_user=current_user)

@app.route('/topic/<int:topic_id>')
def view_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    return render_template('topic.html', topic=topic, current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Allow anyone to register or only admins based on your preference
    # For security, you might want to restrict registration to admins only
    # Uncomment the line below if only admins can create users:
    # if current_user.is_authenticated and not current_user.is_admin:
    #     flash('Only administrators can create new users', 'danger')
    #     return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        is_admin = request.form.get('is_admin') == 'true'
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return render_template('register.html')
        
        # Check if username exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        # Check if email exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        # Create new user
        new_user = User(username=username, email=email, is_admin=is_admin)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'User {username} created successfully!', 'success')
        
        # If admin is creating user, stay in admin panel
        if current_user.is_authenticated and current_user.is_admin:
            return redirect(url_for('manage_users'))
        else:
            # Auto-login after registration
            login_user(new_user)
            return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/profile/<int:user_id>')
@login_required
def view_user_profile(user_id):
    if not current_user.is_admin and current_user.id != user_id:
        flash('You can only view your own profile', 'danger')
        return redirect(url_for('profile'))
    
    user = User.query.get_or_404(user_id)
    return render_template('profile.html', user=user)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    if not current_user.check_password(current_password):
        flash('Current password is incorrect', 'danger')
    elif new_password != confirm_password:
        flash('New passwords do not match', 'danger')
    elif len(new_password) < 6:
        flash('Password must be at least 6 characters', 'danger')
    else:
        current_user.set_password(new_password)
        db.session.commit()
        flash('Password changed successfully!', 'success')
    
    return redirect(url_for('profile'))

# Admin required decorator
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/add_category', methods=['GET', 'POST'])
@admin_required
def add_category():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = Category(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_category.html')

@app.route('/add_topic/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def add_topic(category_id):
    category = Category.query.get_or_404(category_id)
    if request.method == 'POST':
        topic = Topic(
            name=request.form['name'],
            definition=request.form['definition'],
            theory_notes=request.form['theory_notes'],
            code_examples=request.form['code_examples'],
            videos=request.form['videos'],
            images_diagrams=request.form['images_diagrams'],
            github_links=request.form['github_links'],
            project_links=request.form['project_links'],
            references=request.form['references'],
            category_id=category_id
        )
        db.session.add(topic)
        db.session.commit()
        flash('Topic added successfully!', 'success')
        return redirect(url_for('view_category', category_id=category_id))
    return render_template('add_topic.html', category=category)

@app.route('/edit_topic/<int:topic_id>', methods=['GET', 'POST'])
@admin_required
def edit_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    if request.method == 'POST':
        topic.name = request.form['name']
        topic.definition = request.form['definition']
        topic.theory_notes = request.form['theory_notes']
        topic.code_examples = request.form['code_examples']
        topic.videos = request.form['videos']
        topic.images_diagrams = request.form['images_diagrams']
        topic.github_links = request.form['github_links']
        topic.project_links = request.form['project_links']
        topic.references = request.form['references']
        topic.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Topic updated successfully!', 'success')
        return redirect(url_for('view_topic', topic_id=topic_id))
    return render_template('edit_topic.html', topic=topic)

@app.route('/delete_topic/<int:topic_id>')
@admin_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    category_id = topic.category_id
    db.session.delete(topic)
    db.session.commit()
    flash('Topic deleted successfully!', 'success')
    return redirect(url_for('view_category', category_id=category_id))

@app.route('/delete_category/<int:category_id>')
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/admin/users')
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/admin/make_admin/<int:user_id>')
@admin_required
def make_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot change your own admin status', 'danger')
    else:
        user.is_admin = True
        db.session.commit()
        flash(f'{user.username} is now an admin', 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin/remove_admin/<int:user_id>')
@admin_required
def remove_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot change your own admin status', 'danger')
    else:
        user.is_admin = False
        db.session.commit()
        flash(f'{user.username} is no longer an admin', 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin/delete_user/<int:user_id>')
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} has been deleted', 'success')
    return redirect(url_for('manage_users'))

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        is_admin = request.form.get('is_admin') == 'true'
        
        # Check if username exists (excluding current user)
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user.id:
            flash('Username already exists', 'danger')
            return render_template('edit_user.html', user=user)
        
        # Check if email exists (excluding current user)
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != user.id:
            flash('Email already exists', 'danger')
            return render_template('edit_user.html', user=user)
        
        user.username = username
        user.email = email
        user.is_admin = is_admin
        db.session.commit()
        
        flash(f'User {username} updated successfully!', 'success')
        return redirect(url_for('manage_users'))
    
    return render_template('edit_user.html', user=user)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin()
    print("="*50)
    print("Server starting...")
    print("Visit: http://localhost:5000")
    print("="*50)
    app.run(debug=True, host='0.0.0.0', port=5000)
@app.route('/admin/reset_password/<int:user_id>', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form['new_password']
    
    if len(new_password) < 6:
        flash('Password must be at least 6 characters', 'danger')
    else:
        user.set_password(new_password)
        db.session.commit()
        flash(f'Password reset for {user.username}. New password: {new_password}', 'success')
    
    return redirect(url_for('edit_user', user_id=user_id))
