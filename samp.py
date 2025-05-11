# Flask Diary App - Starter Code Structure

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///diary.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ------------------- DATABASE MODELS -------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)

class DiaryEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(200))
    note = db.Column(db.Text)
    reminder_datetime = db.Column(db.DateTime)

# ------------------- ROUTES -------------------
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists')
            return redirect(url_for('register'))
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Registered successfully! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    entries = DiaryEntry.query.filter_by(user_id=session['user_id']).order_by(DiaryEntry.timestamp.desc()).all()
    reminders = Reminder.query.filter_by(user_id=session['user_id']).order_by(Reminder.reminder_datetime).all()
    return render_template('dashboard.html', entries=entries, reminders=reminders)

@app.route('/add_entry', methods=['POST'])
def add_entry():
    content = request.form['content']
    new_entry = DiaryEntry(user_id=session['user_id'], content=content)
    db.session.add(new_entry)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/add_reminder', methods=['POST'])
def add_reminder():
    title = request.form['title']
    note = request.form['note']
    date = request.form['reminder_datetime']
    new_reminder = Reminder(user_id=session['user_id'], title=title, note=note, reminder_datetime=datetime.strptime(date, '%Y-%m-%dT%H:%M'))
    db.session.add(new_reminder)
    db.session.commit()
    return redirect(url_for('dashboard'))

# ------------------- INITIALIZATION -------------------
if __name__ == '__main__':
    if not os.path.exists('diary.db'):
        db.create_all()
    app.run(debug=True)
