from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Category, Topic
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///learning_portal.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Fix for Render.com SQLite path
if os.environ.get('RENDER'):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/learning_portal.db'

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_admin():
    """Create admin user if not exists"""
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

# Create tables when app starts
with app.app_context():
    db.create_all()
    create_admin()

# Your existing routes here (they remain the same)
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
    topic.views = (topic.views or 0) + 1
    db.session.commit()
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
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return render_template('register.html')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return render_template('register.html')
        
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash('Email already registered', 'danger')
            return render_template('register.html')
        
        new_user = User(username=username, email=email, is_admin=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'User {username} created successfully!', 'success')
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
            difficulty=request.form.get('difficulty', 'Beginner'),
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
        try:
            topic.name = request.form['name']
            topic.definition = request.form['definition']
            topic.theory_notes = request.form['theory_notes']
            topic.code_examples = request.form['code_examples']
            topic.videos = request.form['videos']
            topic.images_diagrams = request.form['images_diagrams']
            topic.github_links = request.form['github_links']
            topic.project_links = request.form['project_links']
            topic.references = request.form['references']
            topic.difficulty = request.form.get('difficulty', 'Beginner')
            topic.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Topic updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating topic: {str(e)}', 'danger')
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

@app.route('/init-db')
def init_db():
    """Initialize database - emergency fix"""
    try:
        db.create_all()
        create_admin()
        return "✅ Database initialized successfully! Tables created.", 200
    except Exception as e:
        return f"❌ Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=10000)

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query and len(query) >= 2:
        topics = Topic.query.filter(
            db.or_(
                Topic.name.contains(query),
                Topic.definition.contains(query),
                Topic.theory_notes.contains(query),
                Topic.code_examples.contains(query)
            )
        ).all()
        categories = Category.query.filter(Category.name.contains(query)).all()
        return render_template('search.html', query=query, topics=topics, categories=categories)
    return render_template('search.html', query=query, topics=[], categories=[])
