from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Category, Topic, Document
from datetime import datetime
import os
import subprocess
import sys
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///learning_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'csv', 'txt', 'zip', 'ipynb', 'py', 'jpg', 'jpeg', 'png', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def create_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Admin created: admin/admin123")
        print("⚠️ Please change this password after first login!")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

with app.app_context():
    db.create_all()
    create_admin()

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please login to access this page', 'danger')
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash('Admin privileges required', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ========== BASIC ROUTES ==========
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

# ========== AUTHENTICATION ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm_password']
        
        if password != confirm:
            flash('Passwords do not match', 'danger')
        elif len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
        else:
            is_admin = current_user.is_authenticated and current_user.is_admin and request.form.get('is_admin') == 'true'
            new_user = User(username=username, email=email, is_admin=is_admin)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash(f'User {username} created successfully!', 'success')
            if current_user.is_authenticated and current_user.is_admin:
                return redirect(url_for('manage_users'))
            login_user(new_user)
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    if not current_user.check_password(request.form['current_password']):
        flash('Current password is incorrect', 'danger')
    elif request.form['new_password'] != request.form['confirm_password']:
        flash('New passwords do not match', 'danger')
    elif len(request.form['new_password']) < 6:
        flash('Password must be at least 6 characters', 'danger')
    else:
        current_user.set_password(request.form['new_password'])
        db.session.commit()
        flash('Password changed successfully!', 'success')
    return redirect(url_for('profile'))

# ========== CATEGORY MANAGEMENT ==========
@app.route('/add_category', methods=['GET', 'POST'])
@admin_required
def add_category():
    if request.method == 'POST':
        category = Category(name=request.form['name'], description=request.form['description'])
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_category.html')

@app.route('/delete_category/<int:category_id>')
@admin_required
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('index'))

# ========== TOPIC MANAGEMENT - COMPLETE WORKING VERSION ==========
@app.route('/add_topic/<int:category_id>', methods=['GET', 'POST'])
@admin_required
def add_topic(category_id):
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        try:
            print("=" * 50)
            print("ADDING NEW TOPIC")
            print(f"Category ID: {category_id}")
            
            # Get form data
            topic_name = request.form.get('name', '').strip()
            if not topic_name:
                flash('Topic name is required!', 'danger')
                return render_template('add_topic.html', category=category)
            
            # Create topic object with all fields
            topic = Topic(
                name=topic_name,
                definition=request.form.get('definition', ''),
                theory_notes=request.form.get('theory_notes', ''),
                code_examples=request.form.get('code_examples', ''),
                videos=request.form.get('videos', ''),
                images=request.form.get('images', ''),
                github_links=request.form.get('github_links', ''),
                project_links=request.form.get('project_links', ''),
                references=request.form.get('references', ''),
                difficulty=request.form.get('difficulty', 'Beginner'),
                category_id=category_id
            )
            
            # Log what we're saving
            print(f"Topic Name: {topic.name}")
            print(f"Code Examples length: {len(topic.code_examples) if topic.code_examples else 0}")
            print(f"Videos: {topic.videos[:50] if topic.videos else 'None'}")
            
            db.session.add(topic)
            db.session.flush()  # This assigns an ID to the topic
            
            # Handle document uploads
            if 'documents' in request.files:
                files = request.files.getlist('documents')
                print(f"Processing {len(files)} document(s)")
                
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        # Create unique filename to avoid collisions
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(filepath)
                        
                        doc = Document(
                            topic_id=topic.id,
                            filename=filename,
                            file_path=unique_filename,
                            file_type=filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown',
                            file_size=os.path.getsize(filepath)
                        )
                        db.session.add(doc)
                        print(f"  - Saved document: {filename}")
            
            db.session.commit()
            print(f"✅ Topic '{topic.name}' added successfully!")
            print("=" * 50)
            
            flash(f'Topic "{topic.name}" added successfully!', 'success')
            return redirect(url_for('view_category', category_id=category_id))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR adding topic: {str(e)}")
            flash(f'Error adding topic: {str(e)}', 'danger')
            return render_template('add_topic.html', category=category)
    
    return render_template('add_topic.html', category=category)


@app.route('/edit_topic/<int:topic_id>', methods=['GET', 'POST'])
@admin_required
def edit_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    
    if request.method == 'POST':
        try:
            print("=" * 50)
            print(f"EDITING TOPIC ID: {topic_id}")
            print(f"Original Name: {topic.name}")
            
            # Update all topic fields
            topic.name = request.form.get('name', topic.name)
            topic.definition = request.form.get('definition', '')
            topic.theory_notes = request.form.get('theory_notes', '')
            topic.code_examples = request.form.get('code_examples', '')
            topic.videos = request.form.get('videos', '')
            topic.images = request.form.get('images', '')
            topic.github_links = request.form.get('github_links', '')
            topic.project_links = request.form.get('project_links', '')
            topic.references = request.form.get('references', '')
            topic.difficulty = request.form.get('difficulty', 'Beginner')
            topic.updated_at = datetime.utcnow()
            
            print(f"Updated Name: {topic.name}")
            print(f"Code Examples length: {len(topic.code_examples) if topic.code_examples else 0}")
            print(f"Videos: {topic.videos[:50] if topic.videos else 'None'}")
            
            # Handle new document uploads
            if 'documents' in request.files:
                files = request.files.getlist('documents')
                print(f"Processing {len(files)} new document(s)")
                
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(filepath)
                        
                        doc = Document(
                            topic_id=topic.id,
                            filename=filename,
                            file_path=unique_filename,
                            file_type=filename.rsplit('.', 1)[1].lower() if '.' in filename else 'unknown',
                            file_size=os.path.getsize(filepath)
                        )
                        db.session.add(doc)
                        print(f"  - Added document: {filename}")
            
            db.session.commit()
            print(f"✅ Topic '{topic.name}' updated successfully!")
            print("=" * 50)
            
            flash(f'Topic "{topic.name}" updated successfully!', 'success')
            return redirect(url_for('view_topic', topic_id=topic.id))
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERROR editing topic: {str(e)}")
            flash(f'Error updating topic: {str(e)}', 'danger')
            return render_template('edit_topic.html', topic=topic)
    
    return render_template('edit_topic.html', topic=topic)


@app.route('/delete_topic/<int:topic_id>')
@admin_required
def delete_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    category_id = topic.category_id
    topic_name = topic.name
    
    # Delete associated documents from filesystem
    for doc in topic.documents:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    db.session.delete(topic)
    db.session.commit()
    flash(f'Topic "{topic_name}" deleted successfully!', 'success')
    return redirect(url_for('view_category', category_id=category_id))

# ========== CODE EXECUTION ==========
@app.route('/run_code', methods=['POST'])
@login_required
def run_code():
    try:
        code = request.json.get('code', '')
        if not code.strip():
            return {'output': '⚠️ Please enter some code to run'}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        # Run with timeout to prevent infinite loops
        result = subprocess.run(
            [sys.executable, temp_file],
            capture_output=True,
            text=True,
            timeout=15,
            cwd='/tmp'
        )
        
        os.unlink(temp_file)
        
        output = ""
        if result.stdout:
            output = result.stdout
        if result.stderr:
            if output:
                output += "\n" + "="*40 + "\n"
            output += "⚠️ ERRORS/WARNINGS:\n" + result.stderr
        
        if not output:
            output = "✅ Code executed successfully (no output)"
        
        return {'output': output}
        
    except subprocess.TimeoutExpired:
        return {'output': '⏰ Code execution timed out (15 seconds). Check for infinite loops.'}
    except Exception as e:
        return {'output': f'❌ Error: {str(e)}'}

# ========== DOCUMENT MANAGEMENT ==========
@app.route('/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.file_path)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True, download_name=doc.filename)
    flash('File not found', 'danger')
    return redirect(request.referrer)

@app.route('/delete_doc/<int:doc_id>')
@admin_required
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], doc.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)
    db.session.delete(doc)
    db.session.commit()
    flash('Document deleted successfully', 'success')
    return redirect(request.referrer)

# ========== USER MANAGEMENT ==========
@app.route('/admin/users')
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users, current_user=current_user)

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
    elif user.username == 'admin':
        flash('Cannot delete the main admin account', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} deleted', 'success')
    return redirect(url_for('manage_users'))

# ========== SEARCH ==========
@app.route('/search')
def search():
    query = request.args.get('q', '')
    topics = []
    categories = []
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

# ========== DEBUG ROUTE ==========
@app.route('/debug_topic/<int:topic_id>')
@admin_required
def debug_topic(topic_id):
    topic = Topic.query.get_or_404(topic_id)
    return f"""
    <h2>Debug Info: {topic.name}</h2>
    <p><strong>ID:</strong> {topic.id}</p>
    <p><strong>Category:</strong> {topic.category.name}</p>
    <p><strong>Difficulty:</strong> {topic.difficulty}</p>
    <p><strong>Views:</strong> {topic.views}</p>
    <p><strong>Code Examples:</strong></p>
    <pre style="background:#f0f0f0; padding:10px;">{topic.code_examples or 'EMPTY'}</pre>
    <p><strong>Videos:</strong> {topic.videos or 'EMPTY'}</p>
    <p><strong>Images:</strong> {topic.images or 'EMPTY'}</p>
    <p><strong>Documents:</strong> {len(topic.documents)} files</p>
    <ul>
    {% for doc in topic.documents %}
    <li>{doc.filename} ({doc.file_size} bytes)</li>
    {% endfor %}
    </ul>
    <a href="/edit_topic/{topic_id}">✏️ Edit Topic</a> | 
    <a href="/topic/{topic_id}">👁️ View Topic</a>
    """

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=10000)