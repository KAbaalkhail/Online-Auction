from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from decimal import Decimal
import os
import babel
import humanize
import pytz
from babel.numbers import format_currency
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
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20))  # Add phone number column
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
    confirm_password = PasswordField('تأكيد كلمة المرور', validators=[DataRequired(), EqualTo('password', message='كلمات المرور يجب أن تتطابق')])
    phone_number = StringField('رقم الهاتف')  # Add phone number field
    submit = SubmitField('التسجيل')

class LoginForm(FlaskForm):
    username = StringField('اسم المستخدم', validators=[DataRequired()])
    password = PasswordField('كلمة المرور', validators=[DataRequired()])
    submit = SubmitField('تسجيل الدخول')

class Bid(db.Model):
    __tablename__ = 'bids'
    bid_id = db.Column(db.Integer, primary_key=True)
    bid_amount = db.Column(db.Numeric(10, 2), nullable=False)
    bid_time = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp(), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)  # Changed from 'users.user_id' to 'user.user_id'
    item_id = db.Column(db.Integer, db.ForeignKey('items.item_id'), nullable=False)

    user = db.relationship('User', backref='bids')
    item = db.relationship('Item', backref='bids')

# Define Item model
class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column('item_id', db.Integer, primary_key=True)  # This should be 'item_id', not 'id'
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

@app.template_filter('time_ago')
def time_ago_filter(value):
    delta = datetime.utcnow() - value
    return humanize.naturaltime(delta)

@app.template_filter('currency')
def currency_filter(value, currency='SAR'):
    return format_currency(value, currency, locale='ar_SA')
# Home route
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('auction_listing'))
    else:
        return redirect(url_for('login'))


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if current_user.is_authenticated:
        return redirect(url_for('auction_listing'))
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
            return redirect(next_page or url_for('auction_listing'))
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
        phone_number = form.phone_number.data  # Retrieve phone number from the form

        user_by_email = User.query.filter_by(email=email).first()
        user_by_username = User.query.filter_by(username=username).first()

        if user_by_email or user_by_username:
            flash("هناك مستخدم بنفس هذا البريد الإلكتروني أو اسم المستخدم بالفعل.")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password, phone_number=phone_number)  # Store phone number in the database
        db.session.add(new_user)
        db.session.commit()

        flash('تم إنشاء الحساب بنجاح!')
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
        flash('الرجاء تسجيل الدخول للوصول إلى ملفك الشخصي')
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
seller_locations = ['الرياض', 'القصيم', 'الشرقية']
# Auction listing route

@app.route('/auctions')
def auction_listing():
    timezone = pytz.timezone('Asia/Riyadh')
    now = datetime.now(timezone)
    search_query = request.args.get('search', '')  # Get the search term from the request

    # Filter items by the search term if provided, otherwise get all items ending after now
    if search_query:
        items = Item.query.filter(Item.time_end > now, Item.name.ilike(f'%{search_query}%')).all()
    else:
        items = Item.query.filter(Item.time_end > now).all()

    # Function to create a time left dictionary
    def get_time_left_dict(end_time):
        time_left = end_time - now
        if time_left.total_seconds() > 0:
            return {
                'days': time_left.days,
                'hours': time_left.seconds // 3600,
                'minutes': (time_left.seconds % 3600) // 60,
                'seconds': time_left.seconds % 60
            }
        else:
            return None

    # Format items for the template
    formatted_items = [{
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'start_bid': item.start_bid,
        'time_left': get_time_left_dict(timezone.localize(item.time_end)),
        'time_end': item.time_end.strftime('%Y-%m-%d %H:%M:%S'),
        'end_time_iso': timezone.localize(item.time_end).isoformat(),
        'category': item.category,
        'condition': item.condition,
        'location': item.location,
        'img': item.img
    } for item in items]

    # Get sorting parameters from the request
    sort_by = request.args.get('sort_by', 'time')
    sort_order = request.args.get('sort_order', 'asc')

    # Sort items based on parameters
    if sort_by == 'price':
        formatted_items.sort(key=lambda x: x['start_bid'], reverse=(sort_order == 'desc'))
    elif sort_by == 'location':
        formatted_items.sort(key=lambda x: x['location'], reverse=(sort_order == 'desc'))
    else:  # Default to sorting by time
        formatted_items.sort(key=lambda x: x['end_time_iso'], reverse=(sort_order == 'desc'))

    return render_template('auction.html', items=formatted_items)

from datetime import datetime, timedelta

# Your Flask route function
@app.route('/item_details/<int:item_id>')
def item_details(item_id):
    # Fetch item details from the database using item_id
    item = Item.query.get(item_id)
    if not item:
        flash('العنصر غير موجود')
        return redirect(url_for('auction_listing'))  #
    # Calculate the remaining time for the auction
    seller_phone_number = item.seller.phone_number if item.seller else None
    now = datetime.utcnow()
    item_time_left = None
    if item.time_end and item.time_end > now:
        time_left = item.time_end - now
        days = time_left.days
        hours, remainder = divmod(time_left.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        item_time_left = {'days': days, 'hours': hours, 'minutes': minutes, 'seconds': seconds}

        bid_history = Bid.query.filter_by(item_id=item.id).order_by(Bid.bid_time.desc()).all()

        # Ensure the start_bid is a Decimal
        current_total_price = Decimal(item.start_bid)  # Convert start_bid to Decimal

        # Update the bids with the new total price, which accumulates the bid amounts
        for bid in reversed(bid_history):  # Reverse the list to start from the earliest bid
            current_total_price += bid.bid_amount  # Ensure bid.bid_amount is also Decimal
            bid.new_total_price = current_total_price  # Set the new total price for the bid

    return render_template(
        'item_details.html',
        item=item,
        seller_phone_number=seller_phone_number,  # Add this line
        item_time_left=item_time_left,
        bid_history=bid_history
    )



# Place bid route
@app.route('/place_bid/<int:item_id>', methods=['POST'])
@login_required
def place_bid(item_id):
    item = Item.query.get(item_id)
    if not item:
        flash('العنصر غير موجود')
        return redirect(url_for('auction_listing'))

    bid_amount = request.form.get('bid_amount', type=float)
    if bid_amount is None:
        flash('مبلغ خاطئ')
        return redirect(url_for('item_details', item_id=item_id))
    item.buyer_id = current_user.user_id  # Ensure the buyer is updated when a bid is placed

    # Further validation can be added here

    new_bid = Bid(item_id=item.id, user_id=current_user.user_id, bid_amount=bid_amount)
    db.session.add(new_bid)

    try:
        db.session.commit()
        flash('تمت المزايدة بنجاح!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('حدث خطأ. يرجى المحاولة مرة أخرى.', 'error')
        app.logger.error('Error on bid submission: %s', e)

    return redirect(url_for('item_details', item_id=item_id))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/form', methods=['GET', 'POST'])
def item_form():


    if request.method == 'POST':
        name = request.form['itemName']
        description = request.form['itemDescription']
        start_bid = float(request.form['startingBid'])
        auction_end_hours = int(request.form['auctionEndTime'])  # Extract the number of hours
        category = request.form['itemCategory']
        condition = request.form['itemCondition']
        location = request.form['sellerLocation']

        auction_end_time = datetime.now() + timedelta(hours=auction_end_hours)

        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('لا يوجد جزء ملف', 'error')
            return redirect(request.url)

        file = request.files['file']

        # If the user does not select a file, the browser submits an empty file without a filename
        if file.filename == '':
            flash('لم يتم تحديد ملف', 'error')
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

    return render_template('form.html', item_categories=item_categories, item_conditions=item_conditions,
                           seller_locations=seller_locations)


@app.route('/terms', methods=['GET', 'POST'])
def terms():
    if request.method == 'POST':
        user_response = request.form.get('user_response')
        if user_response == 'agree':
            # Redirect to the form page if the user agrees to the terms
            return redirect(url_for('item_form'))
        else:
            # Redirect to the main page if the user does not agree
            return redirect(url_for('index'))

    # Render the terms page
    return render_template('terms.html')

@app.route('/user')
@login_required
def user_details():
    # Fetching items bought by the user
    items_bought = current_user.items_bought

    # Fetching items listed by the user
    items_sold = current_user.items_sold

    # Format the time left for each item and add additional details as needed

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
            item.time_left = f"{days} أيام {hours} ساعات {minutes} دقائق {seconds} ثواني"
        else:
            item.time_left = "انتهى المزاد"
        item.end_time_iso = end_time.isoformat()

    # Format the time left for each item listed by the user
    for item in items_sold:
        end_time = timezone.localize(item.time_end)
        time_left = end_time - now
        if time_left.total_seconds() > 0:
            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            item.time_left = f"{days} أيام {hours} ساعات {minutes} دقائق {seconds} ثواني"
        else:
            item.time_left = "انتهى المزاد"
        item.end_time_iso = end_time.isoformat()

    return render_template('user.html', items_bought=items_bought, items_sold=items_sold)


# Update the user information route to handle POST requests
@app.route('/user_information', methods=['GET', 'POST'])
@login_required
def user_information():
    # Fetch the current user's information from the database
    user = User.query.get(current_user.user_id)

    # Check if the user exists
    if user is None:
        flash('المستخدم غير موجود', 'error')
        return redirect(url_for('index'))  # Redirect to the index page if user is not found

    # If the request method is POST, it means the form is submitted
    if request.method == 'POST':
        # Update the user's username, email, and phone number with the new values from the form
        new_username = request.form['username']
        new_email = request.form['email']
        new_phone_number = request.form['phone_number']

        # Check if the new username already exists in the database
        existing_user = User.query.filter_by(username=new_username).first()
        if existing_user and existing_user.user_id != user.user_id:
            flash('اسم المستخدم موجود بالفعل. الرجاء اختيار اسم مستخدم مختلف.', 'error')
        else:
            # Update the user's information
            user.username = new_username
            user.email = new_email
            user.phone_number = new_phone_number
            db.session.commit()  # Commit the changes to the database
            flash('تم تحديث المعلومات بنجاح!', 'success')

    # Render the user information page with the user's current information
    return render_template('user_information.html', user=user)


if __name__ == '__main__':
    app.run(debug=True)
