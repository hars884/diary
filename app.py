import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static/uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav', 'webm'}

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    entries = db.relationship('DiaryEntry', backref='author', lazy=True)
    memories = db.relationship('Memory', backref='author', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class DiaryEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Memory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    image_path = db.Column(db.String(200))
    audio_path = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Utility functions
def allowed_file(filename, file_type='image'):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if file_type == 'image':
        return ext in {'png', 'jpg', 'jpeg', 'gif'}
    elif file_type == 'audio':
        return ext in {'mp3', 'wav', 'ogg', 'webm'}
    return False

# Routes
@app.route('/')
@login_required
def index():
    entries = DiaryEntry.query.filter_by(user_id=current_user.id).order_by(DiaryEntry.timestamp.desc()).limit(3).all()
    memories = Memory.query.filter_by(user_id=current_user.id).order_by(Memory.timestamp.desc()).limit(3).all()
    return render_template('index.html', entries=entries, memories=memories,datetime=datetime)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user)
        return redirect(url_for('index'))
    return render_template('login.html',datetime=datetime)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('register'))
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login')
        return redirect(url_for('login'))
    return render_template('register.html',datetime=datetime)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add_entry', methods=['GET', 'POST'])
@login_required
def add_entry():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        mood = request.form.get('mood')
        entry = DiaryEntry(title=title, content=content, mood=mood, author=current_user)
        db.session.add(entry)
        db.session.commit()
        flash('Entry added successfully!')
        return redirect(url_for('index'))
    return render_template('add_entry.html',datetime=datetime)

@app.route('/view_entries')
@login_required
def view_entries():
    entries = DiaryEntry.query.filter_by(user_id=current_user.id).order_by(DiaryEntry.timestamp.desc()).all()
    return render_template('view_entries.html', entries=entries,datetime=datetime)

@app.route('/add_memory', methods=['GET', 'POST'])
@login_required
def add_memory():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        memory = Memory(title=title, description=description, author=current_user)
        
        # Handle image upload
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename, 'image'):
                filename = secure_filename(f"memory_{current_user.id}_{datetime.now().timestamp()}.{image.filename.rsplit('.', 1)[1].lower()}")
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'images', filename)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                image.save(image_path)
                memory.image_path = filename
        
        # Handle audio upload
        if 'audio' in request.files:
            audio = request.files['audio']
            if audio and allowed_file(audio.filename, 'audio'):
                filename = secure_filename(f"memory_{current_user.id}_{datetime.now().timestamp()}.{audio.filename.rsplit('.', 1)[1].lower()}")
                audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', filename)
                os.makedirs(os.path.dirname(audio_path), exist_ok=True)
                audio.save(audio_path)
                memory.audio_path = filename
        
        db.session.add(memory)
        db.session.commit()
        flash('Memory saved successfully!')
        return redirect(url_for('index'))
    return render_template('add_memory.html',datetime=datetime)

@app.route('/view_memories')
@login_required
def view_memories():
    memories = Memory.query.filter_by(user_id=current_user.id).order_by(Memory.timestamp.desc()).all()
    return render_template('view_memories.html', memories=memories,datetime=datetime)
@app.route('/edit_entry/<int:entry_id>', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):
    entry = DiaryEntry.query.get_or_404(entry_id)
    if entry.author != current_user:
        abort(403)
    if request.method == 'POST':
        entry.title = request.form.get('title')
        entry.content = request.form.get('content')
        entry.mood = request.form.get('mood')
        db.session.commit()
        flash('Entry updated successfully!')
        return redirect(url_for('view_entries'))
    return render_template('edit_entry.html', entry=entry,datetime=datetime)

@app.route('/delete_entry/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    entry = DiaryEntry.query.get_or_404(entry_id)
    if entry.author != current_user:
        abort(403)
    db.session.delete(entry)
    db.session.commit()
    flash('Entry deleted successfully!')
    return redirect(url_for('view_entries'))

# Initialize database
def create_tables():
    with app.app_context():
        db.create_all()

@app.route('/record_audio', methods=['POST'])
@login_required
def record_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file part'}), 400
    audio = request.files['audio']
    if audio.filename == '':
        return jsonify({'error': 'No selected audio file'}), 400

    # Debug logging
    print(f"Received audio filename: {audio.filename}")
    ext = audio.filename.rsplit('.', 1)[1].lower() if '.' in audio.filename else ''
    print(f"Audio file extension: {ext}")
    print(f"Audio mimetype: {audio.mimetype}")

    # Relaxed check: accept any audio mimetype
    if audio and audio.mimetype.startswith('audio/'):
        filename = secure_filename(f"recording_{current_user.id}_{datetime.now().timestamp()}.{ext if ext else 'webm'}")
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', filename)
        os.makedirs(os.path.dirname(audio_path), exist_ok=True)
        audio.save(audio_path)
        return jsonify({'filename': filename})
    else:
        return jsonify({'error': 'Invalid audio file type'}), 400

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
