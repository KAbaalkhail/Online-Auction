from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

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

# this is for just example you could remove it
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

# this is for just example you could remove it
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if a user with the provided username or email already exists
        user_by_email = User.query.filter_by(email=email).first()
        user_by_username = User.query.filter_by(username=username).first()

        if user_by_email or user_by_username:
            # If found, flash a message to inform the user
            message = "A user with this email or username already exists."
            flash(message)
            return render_template('register.html', message=message)

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Log the exception e or flash a generic error message
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

from flask import Flask, render_template



@app.route('/auction')
def auction_listing():
    # Dummy data for illustration purposes
    popular_categories = ['Mobile', 'Furniture', 'Cars']
    items = [
        {
            'title': 'Samsung',
            'category': 'Mobile',
            'image_url': 'path_to_image',
            'time_left': '0h 5m',
            'current_bid': '100'
        },
        {
            'title': 'Iphone',
            'category': 'Mobile',
            'image_url': url_for('static', filename='iphone.jpg'),
            'time_left': '1h 15m',
            'current_bid': '100'
        },
        {
            'title': 'Iphone',
            'category': 'Mobile',
            'image_url': url_for('static', filename='iphone.jpg'),
            'time_left': '3h 15m',
            'current_bid': '100'
        },
    ]
    # Sort items based on the time left in ascending order
    sorted_items = sorted(items, key=lambda x: x['time_left'])
    return render_template('auction.html', categories=popular_categories, items=sorted_items)

if __name__ == '__main__':
    app.run(debug=True)
