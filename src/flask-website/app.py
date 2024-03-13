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
    seller_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))  # Foreign key to User table
    seller = db.relationship('User', foreign_keys=[seller_id], backref=db.backref('items_listed', lazy=True))  # Define relationship with User
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))  # Foreign key to User table
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref=db.backref('items_bought', lazy=True))

    def delete_if_ended(self):
        timezone = pytz.timezone('Asia/Riyadh')
        now = datetime.now(timezone)

        # Make self.time_end aware by adding timezone information
        self.time_end = timezone.localize(self.time_end)

        if self.time_end < now - timedelta(minutes=1):
            db.session.delete(self)
            db.session.commit()

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
            session['user_id'] = user.user_id
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
    if 'user_id' in session:
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

    # Fetch items from the database
    items = Item.query.filter(Item.time_end > now).all()

    formatted_items = []

    # Format the fetched items into dictionaries
    for item in items:
        formatted_item = {
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'start_bid': item.start_bid,
            'time_end': item.time_end.strftime('%Y-%m-%d %H:%M:%S'),
            'category': item.category,
            'condition': item.condition,
            'location': item.location,
            'img': item.img
        }
        formatted_items.append(formatted_item)

    # Calculate time left for each item
    for item in formatted_items:
        end_time = timezone.localize(datetime.strptime(item['time_end'], '%Y-%m-%d %H:%M:%S'))
        time_left = end_time - now
        if time_left.total_seconds() > 0:
            # If time_left is positive, calculate and format the time left string
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            item['time_left'] = f"{days} days {hours} hours {minutes} minutes {seconds} seconds"
        else:
            # If time_left is non-positive, set the time_left string to "Auction Ended"
            item['time_left'] = "Auction Ended"
        item['end_time_iso'] = end_time.isoformat()

    # Sort the items by end time
    sorted_items = sorted(formatted_items, key=lambda x: x['time_left'])

    # Render the template with the fetched items
    return render_template('auction.html', categories=popular_categories, items=sorted_items)

@app.route('/item_details/<int:item_id>')
def item_details(item_id):
    # Fetch item details from the database using item_id
    item = Item.query.get(item_id)
    if not item:
        flash("Item not found")
        return redirect(url_for('auction_listing'))  # Redirect back to the auction listing page
    return render_template('item_details.html', item=item)

@app.route('/place_bid/<int:item_id>', methods=['POST'])
def place_bid(item_id):
    if 'user_id' not in session:
        flash('Please log in to bid on items')
        return redirect(url_for('login'))

    user_id = session['user_id']
    item = Item.query.get(item_id)
    if not item:
        flash('Item not found')
        return redirect(url_for('auction_listing'))

    # Increment the bid by 50
    item.start_bid += 50

    # Associate the buyer's user ID with the item
    item.buyer_id = user_id

    db.session.commit()
    flash('Bid placed successfully!')
    return redirect(url_for('auction_listing'))

@app.route('/form', methods=['GET', 'POST'])
def item_form():
    item_categories = ['الكترونيات', 'أثاث', 'ملابس', 'سيارات']
    item_conditions = ['جديد', 'مستعمل', 'كأنه جديد', 'سيء']

    if request.method == 'POST':
        # Process form submission here
        name = request.form['itemName']
        description = request.form['itemDescription']
        start_bid = float(request.form['startingBid'])
        auction_end_time = datetime.strptime(request.form['auctionEndTime'], '%Y-%m-%dT%H:%M')
        category = request.form['itemCategory']
        condition = request.form['itemCondition']
        location = request.form['sellerLocation']
        # Save the uploaded image file to a directory or cloud storage and get the file path
        img = 'path_to_image'  # Replace 'path_to_image' with the actual file path

        # Get the seller's ID from the session
        if 'user_id' in session:
            seller_id = session['user_id']
        else:
            flash('Please log in to add an item')
            return redirect(url_for('login'))

        # Here, you should add code to store the form data in the database
        new_item = Item(name=name, description=description, start_bid=start_bid,
                        time_end=auction_end_time, category=category,
                        condition=condition, location=location, img=img,
                        seller_id=seller_id)  # Assign the seller's ID to the item

        # Add the new item to the database session
        db.session.add(new_item)
        db.session.commit()

        flash('Item added successfully!')
        # Redirect to the same page after form submission
        return redirect(url_for('item_form'))

    return render_template('form.html', item_categories=item_categories, item_conditions=item_conditions)

if __name__ == '__main__':
    app.run(debug=True)  # Turn off debug mode for production deployment
