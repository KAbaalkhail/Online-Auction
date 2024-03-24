from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import pytz
from datetime import datetime, timedelta
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                         current_user, login_required)

# Create Flask app
app = Flask(__name__)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure secret key for session
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'default-secret-key'
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True if you are using HTTPS
app.config['REMEMBER_COOKIE_SECURE'] = False  # Set to True if you are using HTTPS

# Configure database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI') or \
                                            f"mysql+pymysql://{os.environ.get('MYSQL_USER')}:{os.environ.get('MYSQL_PASSWORD')}@{os.environ.get('HOSTNAME')}/{os.environ.get('SCHEMA')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

STATIC_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static')

# Configure the 'UPLOAD_FOLDER' to save uploaded images directly in the 'static' folder
UPLOAD_FOLDER = STATIC_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}  # Specify the allowed file extensions

# Ensure the 'static' directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER




# Define the User model
class User(UserMixin, db.Model):
    __tablename__ = 'user'  # Ensure the table name is correctly set
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)

    # This method should be inside the User class
    def get_id(self):
        return str(self.user_id)

    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Define Flask forms
class RegistrationForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired(), Length(min=4, max=20)])
    email = StringField('البريد الالكتروني', validators=[DataRequired(), Email()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    submit = SubmitField('التسجيل')

class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    submit = SubmitField('تسجيل الدخول')

# Define Item model
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
    seller = db.relationship('User', foreign_keys=[seller_id], backref=db.backref('items_sold', lazy=True))  # Define relationship with User
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))  # Foreign key to User table
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref=db.backref('items_bought', lazy=True))

# Create database tables before first request
@app.before_first_request
def create_tables():
    db.create_all()

# Home route
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Check if the user exists in the database
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user, remember=True)  # Correct placement of login_user

            # Store user ID in session
            session['user_id'] = user.user_id

            flash('تم تسجيل الدخول بنجاح!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('اسم المستخدم أو كلمة المرور غير صحيحة. يرجى المحاولة مرة أخرى.', 'error')
    return render_template('login.html', form=form)


# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        user_by_email = User.query.filter_by(email=email).first()
        user_by_username = User.query.filter_by(username=username).first()

        if user_by_email or user_by_username:
            flash("A user with this email or username already exists.")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully!')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/user_profile')
def user_profile():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('user_profile.html', user=user)
    else:
        flash('Please log in to access your profile')
        return redirect(url_for('login'))

# Logout route
# Update logout route
@app.route('/logout')
def logout():
    logout_user()  # Use Flask-Login to end user session
    flash('تم تسجيل الخروج بنجاح!', 'success')
    return redirect(url_for('index'))

# Dashboard route
@app.route('/main')
 # Use login_required decorator to protect this route
def dashboard():
    # No need to check for 'user_id' in session
    return render_template('main.html', user=current_user)

# Contact us route
@app.route('/contactus')
def contactus():
    return render_template('contactus.html')

item_categories = ['الكترونيات', 'أثاث', 'ملابس', 'سيارات']
item_conditions = ['جديد', 'مستعمل', 'كأنه جديد', 'سيء']
# Auction listing route

@app.route('/auctions')
def auction_listing():

    timezone = pytz.timezone('Asia/Riyadh')
    now = datetime.now(timezone)
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

    # Get sorting parameters from the request
    sort_by = request.args.get('sort_by', 'time')  # Default sort by time
    sort_order = request.args.get('sort_order', 'asc')  # Default sort order

    if sort_by == 'price':
        sorted_items = sorted(formatted_items, key=lambda x: x['start_bid'], reverse=(sort_order == 'desc'))
    elif sort_by == 'location':
        sorted_items = sorted(formatted_items, key=lambda x: x['location'], reverse=(sort_order == 'desc'))
    elif sort_by == 'time':
        sorted_items = sorted(formatted_items, key=lambda x: x['end_time_iso'], reverse=(sort_order == 'desc'))

    # Render the template with the fetched and sorted items
    return render_template('auction.html', categories=item_categories, items=sorted_items)


# Item details route
@app.route('/item_details/<int:item_id>')
def item_details(item_id):
    # Fetch item details from the database using item_id
    item = Item.query.get(item_id)
    if not item:
        flash('العنصر غير موجود')
        return redirect(url_for('auction_listing'))  # Redirect back to the auction listing page
    return render_template('item_details.html', item=item)

# Place bid route
@app.route('/place_bid/<int:item_id>', methods=['POST'])
@login_required
def place_bid(item_id):
    user_id = session['user_id']
    item = Item.query.get(item_id)
    if not item:
        flash('العنصر غير موجود')
        return redirect(url_for('auction_listing'))
    
    bid_amount = float(request.form['bid_amount'])

    if item.seller_id == user_id:  # Check if the buyer is the same as the seller
        flash('لا يمكن للبائع المزايدة على العنصر الخاص به.')
        return redirect(url_for('auction_listing'))
    item.buyer_id = user_id
    item.start_bid += bid_amount

    db.session.commit()

    flash('تمت المزايدة بنجاح!', 'success')
    return redirect(url_for('auction_listing'))



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/form', methods=['GET', 'POST'])
def item_form():


    if request.method == 'POST':
        name = request.form['itemName']
        description = request.form['itemDescription']
        start_bid = float(request.form['startingBid'])
        auction_end_time = datetime.strptime(request.form['auctionEndTime'], '%Y-%m-%dT%H:%M')
        category = request.form['itemCategory']
        condition = request.form['itemCondition']
        location = request.form['sellerLocation']


        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        file = request.files['file']

        # If the user does not select a file, the browser submits an empty file without a filename
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Save the relative image file path to the database
            img = os.path.join('static', filename)

            # Get the seller's ID from the session
            if 'user_id' in session:
                seller_id = session['user_id']
            else:
                flash('الرجاء تسجيل الدخول لإضافة إعلان ', 'error')
                return redirect(url_for('login'))

            new_item = Item(name=name, description=description, start_bid=start_bid,
                            time_end=auction_end_time, category=category,
                            condition=condition, location=location, img=img,
                            seller_id=seller_id)

            db.session.add(new_item)
            db.session.commit()

            flash('تمت إضافة العنصر بنجاح!', 'success')
            return redirect(url_for('item_form'))

    return render_template('form.html', item_categories=item_categories, item_conditions=item_conditions)

@app.route('/user')
@login_required
def user_details():
    # Fetching items bought by the user
    items_bought = current_user.items_bought

    # Fetching items listed by the user
    items_sold = current_user.items_sold

    timezone = pytz.timezone('Asia/Riyadh')
    now = datetime.now(timezone)

    # Format the time left for each item bought by the user
    for item in items_bought:
        end_time = timezone.localize(item.time_end)
        time_left = end_time - now
        if time_left.total_seconds() > 0:
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            item.time_left = f"{days} days {hours} hours {minutes} minutes {seconds} seconds"
        else:
            item.time_left = "Auction Ended"
        item.end_time_iso = end_time.isoformat()

    # Format the time left for each item listed by the user
    for item in items_sold:
        end_time = timezone.localize(item.time_end)
        time_left = end_time - now
        if time_left.total_seconds() > 0:
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            item.time_left = f"{days} days {hours} hours {minutes} minutes {seconds} seconds"
        else:
            item.time_left = "Auction Ended"
        item.end_time_iso = end_time.isoformat()

    return render_template('user.html', items_bought=items_bought, items_sold=items_sold)

if __name__ == '__main__':
    app.run(debug=True)  # Turn off debug mode for production deployment
