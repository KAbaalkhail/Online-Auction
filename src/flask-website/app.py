
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pytz
from datetime import datetime, timedelta

app = Flask(__name__)

# Configure database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI') or \
                                            f"mysql+pymysql://{os.environ.get('MYSQL_USER')}:{os.environ.get('MYSQL_PASSWORD')}@{os.environ.get('HOSTNAME')}/{os.environ.get('SCHEMA')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'default-secret-key'

# Initialize extensions
db = SQLAlchemy(app)

# Define the User model
class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            return redirect(url_for('dashboard'))  # Redirect to the dashboard page
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user_by_email = User.query.filter_by(email=email).first()
        user_by_username = User.query.filter_by(username=username).first()

        if user_by_email or user_by_username:
            flash("A user with this email or username already exists.")
            return render_template('register.html')

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while registering the user. Please try again.')
            return render_template('register.html')

        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/main')
def dashboard():
    if 'username' in session:
        return render_template('main.html')
    else:
        flash('Please log in to access the dashboard')
        return redirect(url_for('login'))

@app.route('/auction')
def auction_listing():
    popular_categories = ['Mobile', 'Furniture', 'Cars']
    timezone = pytz.timezone('Asia/Riyadh')
    now = datetime.now(timezone)
    items = [
        {
            'title': 'Samsung Galaxy',
            'category': 'Mobile',
            'image_url': 'path_to_image_samsung',
            'end_time': '2024-04-30 17:00:00',
            'current_bid': '100'
        },
        {
            'title': 'Iphone 13',
            'category': 'Mobile',
            'image_url': 'path_to_image_iphone',
            'end_time': '2024-04-30 16:00:00',
            'current_bid': '200'
        },
        {
            'title': 'Nokia 3310',
            'category': 'Mobile',
            'image_url': 'path_to_image_nokia',
            'end_time': '2024-04-30 18:00:00',
            'current_bid': '50'
        },

    ]

    for item in items:
        end_time = timezone.localize(datetime.strptime(item['end_time'], '%Y-%m-%d %H:%M:%S'))
        time_left = end_time - now
        item['time_left'] = str(time_left) if time_left.total_seconds() > 0 else "Auction Ended"
        item['end_time_iso'] = end_time.isoformat()

    sorted_items = sorted(items, key=lambda x: x['time_left'])
    return render_template('auction.html', categories=popular_categories, items=sorted_items)

@app.route('/form')
def items_form():

if __name__ == '__main__':
        app.run(debug=True)  # Turn off debug mode for production deployment
