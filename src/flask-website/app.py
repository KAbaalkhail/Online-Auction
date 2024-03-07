# app.py

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

# Define the Item model
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    start_bid = db.Column(db.Float)
    time_end = db.Column(db.DateTime)
    category = db.Column(db.String(50))
    condition = db.Column(db.String(50))
    location = db.Column(db.String(100))
    img = db.Column(db.String(255))

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

@app.route('/contactus')
def contactus():
    return render_template('contactus.html')

@app.route('/auction')
def auction_listing():
    popular_categories = ['Mobile', 'Furniture', 'Cars']
    timezone = pytz.timezone('Asia/Riyadh')
    now = datetime.now(timezone)
    items = [
        {
            'id': 1,
            'name': 'Samsung Galaxy',
            'description': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
            'start_bid': '100',
            'time_end': '2024-04-30 17:00:00',
            'category': 'Mobile',
            'condition': 'Used',
            'location': 'Riyadh',
            'img': 'path_to_image_samsung'
        },
        {
            'id': 2,
            'name': 'Iphone 13',
            'description': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
            'start_bid': '200',
            'time_end': '2024-04-30 16:00:00',
            'category': 'Mobile',
            'condition': 'New',
            'location': 'Jeddah',
            'img': 'path_to_image_iphone'
        },
        {
            'id': 3,
            'name': 'Nokia 3310',
            'description': 'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
            'start_bid': '50',
            'time_end': '2024-04-30 18:00:00',
            'category': 'Mobile',
            'condition': 'Like New',
            'location': 'Dammam',
            'img': 'path_to_image_nokia'
        }
    ]

    for item in items:
        end_time = timezone.localize(datetime.strptime(item['time_end'], '%Y-%m-%d %H:%M:%S'))
        time_left = end_time - now
        item['time_left'] = str(time_left) if time_left.total_seconds() > 0 else "Auction Ended"
        item['end_time_iso'] = end_time.isoformat()

    sorted_items = sorted(items, key=lambda x: x['time_left'])
    return render_template('auction.html', categories=popular_categories, items=sorted_items)

@app.route('/item_details/<int:item_id>')
def item_details(item_id):
    print("Item ID:", item_id)  # Add debug print to check item_id
    # Fetch item details from the database using item_id
    item = Item.query.get(item_id)
    if not item:
        flash("Item not found")
        return redirect(url_for('auction_listing'))  # Redirect back to the auction listing page
    return render_template('item_details.html', item=item)

@app.route('/form')
def item_form():
    item_categories = ['Electronics', 'Furniture', 'Clothing']
    item_conditions = ['New', 'Used', 'Like New']
    return render_template('form.html', item_categories=item_categories, item_conditions=item_conditions)

if __name__ == '__main__':
    app.run(debug=True)  # Turn off debug mode for production deployment
