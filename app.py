"""
Complete Flask backend for Diary App (single-file example)
- Implements models for users, diary entries, memories, attachments, capsules, locations, reminders, notifications, badges, mood records, public feed index, sync logs, aggregates
- Authentication with Flask-Login
- File uploads (local by default, S3-compatible optional)
- Background scheduler using APScheduler for capsule reveal and reminders
- Simple badge evaluation hooks
- API endpoints for core flows: add/edit/delete entries, publish public, public feed, memory map JSON, capsule creation, sync endpoint stub, insights endpoints

Note: This is a reasonably complete example but intended as a starting point. In production, split into blueprints, use migrations (Alembic), store secrets properly, and use Celery for heavy background tasks.
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from urllib.parse import urljoin

from flask import (
    Flask, render_template, redirect, url_for, flash, request, jsonify, abort, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# Load environment
load_dotenv()


# --- Config ---
BASE_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_IMAGE_EXT'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['ALLOWED_AUDIO_EXT'] = {'mp3', 'wav', 'ogg', 'webm'}
app.config['PUBLIC_URL_ROOT'] = os.getenv('PUBLIC_URL_ROOT', 'http://localhost:5000')
app.jinja_env.globals['datetime'] = datetime



# --- Extensions ---
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Enums ---
class Visibility(Enum):
    PRIVATE = 'private'
    PUBLIC = 'public'
    ANONYMOUS = 'anonymous'

# --- Models ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    display_name = db.Column(db.String(128))
    bio = db.Column(db.Text)
    vault_pin_hash = db.Column(db.String(256), nullable=True)

    entries = db.relationship('DiaryEntry', back_populates='author', lazy='dynamic')
    memories = db.relationship('Memory', back_populates='author', lazy='dynamic')
    attachments = db.relationship('Attachment', back_populates='uploader', lazy='dynamic')
    reminders = db.relationship('Reminder', back_populates='user', lazy='dynamic')
    badges = db.relationship('BadgeAssignment', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Attachment(db.Model):
    __tablename__ = 'attachments'
    id = db.Column(db.Integer, primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    uploader = db.relationship('User', back_populates='attachments')
    filename = db.Column(db.String(256), nullable=False)
    original_name = db.Column(db.String(256))
    content_type = db.Column(db.String(64))
    size = db.Column(db.Integer)
    path = db.Column(db.String(1024))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    diary_entry_id = db.Column(db.Integer, db.ForeignKey('diary_entries.id', ondelete='CASCADE'), nullable=True)
    memory_id = db.Column(db.Integer, db.ForeignKey('memories.id', ondelete='CASCADE'), nullable=True)

class DiaryEntry(db.Model):
    __tablename__ = 'diary_entries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    author = db.relationship('User', back_populates='entries')
    title = db.Column(db.String(200), nullable=False, default='Untitled')
    content = db.Column(db.Text, nullable=False)
    mood = db.Column(db.String(30), index=True)
    emotion_tags = db.Column(db.String(500))
    visibility = db.Column(db.String(16), default=Visibility.PRIVATE.value, nullable=False, index=True)
    is_locked = db.Column(db.Boolean, default=False)
    vault_tag = db.Column(db.String(64), nullable=True)
    chapter = db.Column(db.String(128), nullable=True, index=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True, index=True)
    location = db.relationship('Location')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    capsule_id = db.Column(db.Integer, db.ForeignKey('capsules.id'), nullable=True, index=True)
    attachments = db.relationship('Attachment', backref='diary_entry', lazy='dynamic')
    is_featured = db.Column(db.Boolean, default=False)
    client_uuid = db.Column(db.String(64), nullable=True, index=True)
    client_modified_at = db.Column(db.DateTime, nullable=True)

class Memory(db.Model):
    __tablename__ = 'memories'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    author = db.relationship('User', back_populates='memories')
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    location = db.relationship('Location')
    attachments = db.relationship('Attachment', backref='memory', lazy='dynamic')
    visibility = db.Column(db.String(16), default=Visibility.PRIVATE.value, nullable=False, index=True)
    capsule_id = db.Column(db.Integer, db.ForeignKey('capsules.id'), nullable=True)

class Capsule(db.Model):
    __tablename__ = 'capsules'
    id = db.Column(db.Integer, primary_key=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_by = db.relationship('User')
    title = db.Column(db.String(200))
    note = db.Column(db.Text)
    unlock_at = db.Column(db.DateTime, nullable=False, index=True)
    is_revealed = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    precision = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Reminder(db.Model):
    __tablename__ = 'reminders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    user = db.relationship('User', back_populates='reminders')
    title = db.Column(db.String(200))
    cron_expr = db.Column(db.String(100), nullable=True)
    next_run_at = db.Column(db.DateTime, nullable=True, index=True)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reminder_type = db.Column(db.String(64), default='daily_check')
    last_run_at = db.Column(db.DateTime, nullable=True)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = db.Column(db.String(200))
    body = db.Column(db.Text)
    data = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    delivered_at = db.Column(db.DateTime, nullable=True)

class Badge(db.Model):
    __tablename__ = 'badges'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    icon = db.Column(db.String(256))

class BadgeAssignment(db.Model):
    __tablename__ = 'badge_assignments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id', ondelete='CASCADE'), nullable=False, index=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', back_populates='badges')
    badge = db.relationship('Badge')
    __table_args__ = (db.UniqueConstraint('user_id', 'badge_id', name='uq_user_badge'),)

class MoodRecord(db.Model):
    __tablename__ = 'mood_records'
    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.Integer, db.ForeignKey('diary_entries.id', ondelete='CASCADE'), nullable=False, index=True)
    mood = db.Column(db.String(64), nullable=False, index=True)
    sentiment_score = db.Column(db.Float, nullable=True)
    emotion_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PublicFeedIndex(db.Model):
    __tablename__ = 'public_feed'
    id = db.Column(db.Integer, primary_key=True)
    source_type = db.Column(db.String(32), nullable=False)
    source_id = db.Column(db.Integer, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    visibility = db.Column(db.String(16), default=Visibility.PUBLIC.value, index=True)
    is_anonymous = db.Column(db.Boolean, default=False, index=True)
    title = db.Column(db.String(300))
    snippet = db.Column(db.String(500))
    mood = db.Column(db.String(64), index=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

class SyncLog(db.Model):
    __tablename__ = 'sync_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    client_uuid = db.Column(db.String(64), nullable=True, index=True)
    source = db.Column(db.String(64))
    source_id = db.Column(db.Integer, nullable=True)
    client_change_id = db.Column(db.String(128), nullable=True, index=True)
    change_type = db.Column(db.String(16))
    payload = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved = db.Column(db.Boolean, default=False, index=True)

class MoodAggregateDaily(db.Model):
    __tablename__ = 'mood_aggregates_daily'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.DateTime, nullable=False, index=True)
    mood = db.Column(db.String(64), nullable=False, index=True)
    count = db.Column(db.Integer, default=0)
    __table_args__ = (db.UniqueConstraint('user_id', 'date', 'mood', name='uq_user_date_mood'),)

# --- Login loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Utilities ---
def allowed_file(filename, file_type='image'):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    if file_type == 'image':
        return ext in app.config['ALLOWED_IMAGE_EXT']
    elif file_type == 'audio':
        return ext in app.config['ALLOWED_AUDIO_EXT']
    return False

def save_file(fileobj, subfolder='misc'):
    # returns stored filename and path
    ext = ''
    if '.' in fileobj.filename:
        ext = fileobj.filename.rsplit('.', 1)[1].lower()
    name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
    folder = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    fileobj.save(path)
    return name, path

# --- Routes: auth & home ---
@app.route('/')
@login_required
def index():
    # show recent entries & memories; provide links to other features
    entries = DiaryEntry.query.filter_by(user_id=current_user.id).order_by(DiaryEntry.created_at.desc()).limit(5).all()
    memories = Memory.query.filter_by(user_id=current_user.id).order_by(Memory.created_at.desc()).limit(5).all()
    return render_template('index.html', entries=entries, memories=memories)

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
    return render_template('register.html')

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
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Entry CRUD & publish ---
@app.route('/entries')
@login_required
def list_entries():
    entries = DiaryEntry.query.filter_by(user_id=current_user.id).order_by(DiaryEntry.created_at.desc()).all()
    return render_template('view_entries.html', entries=entries)

@app.route('/entry/new', methods=['GET', 'POST'])
@login_required
def create_entry():
    if request.method == 'POST':
        title = request.form.get('title') or 'Untitled'
        content = request.form.get('content') or ''
        mood = request.form.get('mood')
        visibility = request.form.get('visibility', Visibility.PRIVATE.value)
        is_anonymous = request.form.get('is_anonymous') == 'on'
        chapter = request.form.get('chapter')
        # optional location data
        lat = request.form.get('lat')
        lon = request.form.get('lon')

        entry = DiaryEntry(
            author=current_user,
            title=title,
            content=content,
            mood=mood,
            visibility=visibility,
            chapter=chapter
        )

        if lat and lon:
            try:
                latf = float(lat); lonf = float(lon)
                loc = Location(name=request.form.get('location_name'), latitude=latf, longitude=lonf)
                db.session.add(loc)
                db.session.flush()  # set loc.id
                entry.location = loc
            except Exception:
                pass

        db.session.add(entry)
        db.session.commit()

        # if public -> push into PublicFeedIndex
        if visibility in (Visibility.PUBLIC.value, Visibility.ANONYMOUS.value):
            push_public_feed(source_type='entry', source=entry, is_anonymous=(visibility == Visibility.ANONYMOUS.value))

        # handle attachments (images/audio)
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename, 'image'):
                filename, path = save_file(image, subfolder='images')
                att = Attachment(uploader=current_user, filename=filename, original_name=image.filename, path=path, content_type=image.mimetype, diary_entry_id=entry.id)
                db.session.add(att)
        if 'audio' in request.files:
            audio = request.files['audio']
            if audio and allowed_file(audio.filename, 'audio'):
                filename, path = save_file(audio, subfolder='audio')
                att = Attachment(uploader=current_user, filename=filename, original_name=audio.filename, path=path, content_type=audio.mimetype, diary_entry_id=entry.id)
                db.session.add(att)

        db.session.commit()
        evaluate_badges_for_user(current_user.id)
        flash('Entry created')
        return redirect(url_for('list_entries'))

    return render_template('add_entry.html')

@app.route('/entry/<int:entry_id>')
@login_required
def view_entry(entry_id):
    entry = DiaryEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id and entry.visibility == Visibility.PRIVATE.value:
        abort(403)
    return render_template('view_entry.html', entry=entry)

@app.route('/entry/<int:entry_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_entry(entry_id):
    entry = DiaryEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        abort(403)
    if request.method == 'POST':
        entry.title = request.form.get('title') or entry.title
        entry.content = request.form.get('content') or entry.content
        entry.mood = request.form.get('mood') or entry.mood
        visibility = request.form.get('visibility')
        if visibility:
            entry.visibility = visibility
            if visibility in (Visibility.PUBLIC.value, Visibility.ANONYMOUS.value):
                push_public_feed(source_type='entry', source=entry, is_anonymous=(visibility == Visibility.ANONYMOUS.value))
        db.session.commit()
        flash('Entry updated')
        return redirect(url_for('view_entry', entry_id=entry.id))
    return render_template('edit_entry.html', entry=entry)

@app.route('/entry/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete_entry(entry_id):
    entry = DiaryEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        abort(403)
    # remove possible public feed rows
    PublicFeedIndex.query.filter_by(source_type='entry', source_id=entry.id).delete()
    db.session.delete(entry)
    db.session.commit()
    flash('Entry deleted')
    return redirect(url_for('list_entries'))

# --- Memories ---
@app.route('/memories')
@login_required
def list_memories():
    memories = Memory.query.filter_by(user_id=current_user.id).order_by(Memory.created_at.desc()).all()
    return render_template('view_memories.html', memories=memories)

@app.route('/memory/new', methods=['GET', 'POST'])
@login_required
def create_memory():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        visibility = request.form.get('visibility', Visibility.PRIVATE.value)
        lat = request.form.get('lat')
        lon = request.form.get('lon')
        memory = Memory(author=current_user, title=title, description=description, visibility=visibility)
        if lat and lon:
            try:
                latf = float(lat); lonf = float(lon)
                loc = Location(name=request.form.get('location_name'), latitude=latf, longitude=lonf)
                db.session.add(loc)
                db.session.flush()
                memory.location = loc
            except Exception:
                pass
        db.session.add(memory)
        db.session.commit()
        # attachments
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename, 'image'):
                filename, path = save_file(image, subfolder='images')
                att = Attachment(uploader=current_user, filename=filename, original_name=image.filename, path=path, content_type=image.mimetype, memory_id=memory.id)
                db.session.add(att)
        db.session.commit()
        if visibility in (Visibility.PUBLIC.value, Visibility.ANONYMOUS.value):
            push_public_feed(source_type='memory', source=memory, is_anonymous=(visibility == Visibility.ANONYMOUS.value))
        flash('Memory saved')
        return redirect(url_for('list_memories'))
    return render_template('add_memory.html')

# --- Public feed ---
@app.route('/public_feed')
def public_feed():
    # pagination
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    query = PublicFeedIndex.query.filter(
        PublicFeedIndex.visibility.in_([Visibility.PUBLIC.value, Visibility.ANONYMOUS.value])
    ).order_by(PublicFeedIndex.created_at.desc())
    items = query.paginate(page=page, per_page=per_page, error_out=False)
    results = []
    for row in items.items:
        results.append({
            'id': row.id,
            'source_type': row.source_type,
            'source_id': row.source_id,
            'title': row.title,
            'snippet': row.snippet,
            'mood': row.mood,
            'is_anonymous': row.is_anonymous,
            'created_at': row.created_at.isoformat()
        })
    return render_template('public_feed.html', public_entries=results, pagination=items)

@app.route('/api/public_feed')
def api_public_feed():
    # returns JSON
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    query = PublicFeedIndex.query.filter(
        PublicFeedIndex.visibility.in_([Visibility.PUBLIC.value, Visibility.ANONYMOUS.value])
    ).order_by(PublicFeedIndex.created_at.desc())
    items = query.paginate(page=page, per_page=per_page, error_out=False)
    results = []
    for row in items.items:
        results.append({
            'id': row.id,
            'source_type': row.source_type,
            'source_id': row.source_id,
            'title': row.title,
            'snippet': row.snippet,
            'mood': row.mood,
            'is_anonymous': row.is_anonymous,
            'created_at': row.created_at.isoformat()
        })
    return jsonify({'items': results, 'page': page, 'pages': items.pages})

# --- PublicFeed helper ---
def push_public_feed(source_type, source, is_anonymous=False):
    # create or update PublicFeedIndex row
    content = getattr(source, 'content', '')
    snippet = content[:497] + '...' if len(content) > 500 else content
    title = getattr(source, 'title', '')
    mood = getattr(source, 'mood', None)
    # delete old
    PublicFeedIndex.query.filter_by(source_type=source_type, source_id=source.id).delete()
    pf = PublicFeedIndex(
        source_type=source_type,
        source_id=source.id,
        author_id=None if is_anonymous else getattr(source, 'user_id', None),
        visibility=Visibility.ANONYMOUS.value if is_anonymous else Visibility.PUBLIC.value,
        is_anonymous=is_anonymous,
        title=title,
        snippet=snippet,
        mood=mood,
        location_id=getattr(source, 'location_id', None),
        created_at=getattr(source, 'created_at', datetime.utcnow())
    )
    db.session.add(pf)
    db.session.commit()

# --- Map: memories and public posts ---
@app.route('/api/memories/map')
def api_memories_map():
    # return public memories with location and recent images
    query = Memory.query.filter(Memory.visibility == Visibility.PUBLIC.value, Memory.location_id.isnot(None)).order_by(Memory.created_at.desc()).limit(100)
    items = []
    for mem in query.all():
        att = mem.attachments.first()
        img_url = None
        if att:
            img_url = urljoin(app.config['PUBLIC_URL_ROOT'], f"/uploads/images/{att.filename}")
        items.append({
            'id': mem.id,
            'title': mem.title,
            'snippet': (mem.description or '')[:200],
            'lat': mem.location.latitude,
            'lon': mem.location.longitude,
            'image': img_url,
            'created_at': mem.created_at.isoformat()
        })
    return jsonify({'items': items})

# --- Capsule routes ---
@app.route('/capsule/new', methods=['GET', 'POST'])
@login_required
def create_capsule():
    if request.method == 'POST':
        title = request.form.get('title')
        note = request.form.get('note')
        unlock_at_raw = request.form.get('unlock_at')

        # Correct parsing: try ISO first, fallback to strptime
        unlock_at = None
        try:
            unlock_at = datetime.fromisoformat(unlock_at_raw)
        except Exception:
            try:
                unlock_at = datetime.strptime(unlock_at_raw, '%Y-%m-%dT%H:%M')
            except Exception:
                flash('Invalid date format. Use ISO format e.g. 2025-10-31T12:00')
                return redirect(url_for('create_capsule'))

        cap = Capsule(created_by=current_user, title=title, note=note, unlock_at=unlock_at)
        db.session.add(cap)
        db.session.commit()
        flash('Capsule created')
        return redirect(url_for('list_capsules'))
    return render_template('create_capsule.html')

@app.route('/capsules')
@login_required
def list_capsules():
    caps = Capsule.query.filter_by(created_by_id=current_user.id).order_by(Capsule.unlock_at.desc()).all()
    return render_template('list_capsules.html', capsules=caps)

# --- Reminders API (basic) ---
@app.route('/reminder/new', methods=['POST'])
@login_required
def create_reminder():
    data = request.json or request.form
    title = data.get('title')
    cron_expr = data.get('cron_expr')
    next_run_at = data.get('next_run_at')
    if next_run_at:
        next_run_at = datetime.fromisoformat(next_run_at)
    r = Reminder(user=current_user, title=title, cron_expr=cron_expr, next_run_at=next_run_at)
    db.session.add(r)
    db.session.commit()
    return jsonify({'status': 'ok', 'id': r.id})

# --- Sync endpoint (simple stub) ---
@app.route('/api/sync', methods=['POST'])
@login_required
def api_sync():
    payload = request.json
    # expected: client_uuid, changes: [{change_id, source, data, client_modified_at}]
    client_uuid = payload.get('client_uuid')
    changes = payload.get('changes', [])
    results = []
    for ch in changes:
        clid = ch.get('change_id')
        source = ch.get('source')
        data = ch.get('data')
        # store in SyncLog; resolution logic omitted for brevity
        slog = SyncLog(user_id=current_user.id, client_uuid=client_uuid, source=source, client_change_id=clid, change_type='create', payload=json.dumps(data))
        db.session.add(slog)
        results.append({'change_id': clid, 'status': 'queued'})
    db.session.commit()
    return jsonify({'results': results})

# --- Insights endpoints ---
@app.route('/api/insights/moods')
@login_required
def api_insights_moods():
    # last 30 days mood counts
    since = datetime.utcnow() - timedelta(days=30)
    rows = db.session.query(DiaryEntry.mood, db.func.count(DiaryEntry.id)).filter(DiaryEntry.user_id == current_user.id, DiaryEntry.created_at >= since).group_by(DiaryEntry.mood).all()
    return jsonify({'moods': [{ 'mood': r[0], 'count': r[1] } for r in rows]})

# --- Badge evaluation (simple rules) ---
def evaluate_badges_for_user(user_id):
    # examples: first_entry, wrote_10, uploaded_5_memories
    user = User.query.get(user_id)
    if not user:
        return
    # first entry
    cnt = DiaryEntry.query.filter_by(user_id=user_id).count()
    def assign(code, title):
        badge = Badge.query.filter_by(code=code).first()
        if not badge:
            badge = Badge(code=code, title=title, description=title)
            db.session.add(badge); db.session.commit()
        if not BadgeAssignment.query.filter_by(user_id=user_id, badge_id=badge.id).first():
            ba = BadgeAssignment(user_id=user_id, badge_id=badge.id)
            db.session.add(ba); db.session.commit()
    if cnt >= 1:
        assign('first_entry', 'First Entry')
    if cnt >= 10:
        assign('ten_entries', 'Wrote 10 Entries')
    mem_cnt = Memory.query.filter_by(user_id=user_id).count()
    if mem_cnt >= 5:
        assign('five_memories', 'Uploaded 5 Memories')

# --- File serving helper (development only) ---
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # filename like images/<file>
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Background tasks: capsule reveal & reminders ---
scheduler = BackgroundScheduler()

def job_reveal_capsules():
    with app.app_context():
        now = datetime.utcnow()
        caps = Capsule.query.filter(Capsule.unlock_at <= now, Capsule.is_revealed == False).all()
        for cap in caps:
            try:
                cap.is_revealed = True
                # reveal logic: set contained diary_entries/memories visibility to user's choice
                # simple approach: find diary_entries with cap.id and set visibility=private->private? For demo, we just notify
                # create notification
                if cap.created_by_id:
                    n = Notification(user_id=cap.created_by_id, title='Capsule unlocked', body=f'Your capsule "{cap.title}" was unlocked.')
                    db.session.add(n)
                db.session.commit()
                # optionally publish entries or move them public depending on additional flags (not implemented)
            except Exception as e:
                db.session.rollback()
                print('Error revealing capsule', cap.id, e)

def job_run_reminders():
    with app.app_context():
        now = datetime.utcnow()
        rems = Reminder.query.filter(Reminder.enabled == True, Reminder.next_run_at <= now).all()
        for r in rems:
            try:
                # create notification
                n = Notification(user_id=r.user_id, title='Reminder', body=f'Reminder: {r.title}')
                db.session.add(n)
                # schedule next_run_at naive: add 1 day
                r.last_run_at = now
                r.next_run_at = now + timedelta(days=1)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print('Error running reminder', r.id, e)

scheduler.add_job(job_reveal_capsules, 'interval', seconds=60)
scheduler.add_job(job_run_reminders, 'interval', seconds=60)
scheduler.start()

# --- DB init helper ---
def create_tables():
    with app.app_context():
        db.create_all()

# --- Run ---
if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
