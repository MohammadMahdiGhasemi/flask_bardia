from flask import Flask, render_template, request, redirect, url_for, session
from bson import ObjectId
import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_admin import Admin
from flask_admin.contrib.pymongo import ModelView
from wtforms import StringField, IntegerField, PasswordField, FormField
from wtforms.validators import DataRequired, Email, Length
from flask_admin.form import BaseForm
import secrets
from pymongo import MongoClient
import datetime

# --- App Configuration ---
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


from tkinter import Tk, Label, Button, Entry, Text, StringVar, messagebox, Frame, Scrollbar, Canvas
from tkinter import font

# MongoDB connection information
MONGO_URI = "mongodb://dbadmin:dbImp!14%402@78.38.35.219:27017/?authMechanism=DEFAULT"
client = MongoClient(MONGO_URI)
db = client['BardiyaSaati']




# --- Extensions ---
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'adlogin'
admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')

# --- User Class ---
class AdminUser(UserMixin):
    def __init__(self, user):
        self.id = str(user['_id'])
        self.username = user['username']

@login_manager.user_loader
def load_user(user_id):
    user = db.AdminUsers.find_one({"_id": ObjectId(user_id)})
    return AdminUser(user) if user else None

# --- Custom Address Form ---
class AddressForm(BaseForm):
    street = StringField('Street', validators=[DataRequired()])
    city = StringField('City', validators=[DataRequired()])
    state = StringField('State', validators=[DataRequired()])
    zip = StringField('ZIP', validators=[DataRequired()])

# --- Customer Registration Form ---
class CustomerRegistrationForm(BaseForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = PasswordField('Phone', validators=[DataRequired(), Length(min=6)])

# --- Flask-Admin Custom ModelView ---
class CustomAdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('adlogin'))

    def scaffold_list_columns(self):
        return ['name', 'email', 'phone', 'address', 'registration_date', 'loyalty_points']

    def scaffold_sortable_columns(self):
        return ['name', 'email', 'loyalty_points']

    def scaffold_form(self):
        class CustomerForm(BaseForm):
            name = StringField('Name', validators=[DataRequired()])
            email = StringField('Email', validators=[DataRequired()])
            phone = StringField('Phone', validators=[DataRequired()])
            address = FormField(AddressForm)
            registration_date = StringField('Registration Date', default=str(datetime.datetime.now()))
            loyalty_points = IntegerField('Loyalty Points')
        return CustomerForm

# --- Product View ---
class ProductView(CustomAdminModelView):
    def scaffold_list_columns(self):
        return ['name', 'brand', 'price', 'category', 'size', 'gender', 'stock', 'rating', 'notes', 'image_url']

    def scaffold_sortable_columns(self):
        return ['name', 'brand', 'price', 'rating']

    def scaffold_form(self):
        class ProductForm(BaseForm):
            name = StringField('Product Name', validators=[DataRequired()])
            brand = StringField('Brand', validators=[DataRequired()])
            price = IntegerField('Price', validators=[DataRequired()])
            category = StringField('Category', validators=[DataRequired()])
            size = StringField('Size', validators=[DataRequired()])
            gender = StringField('Gender', validators=[DataRequired()])
            stock = IntegerField('Stock', validators=[DataRequired()])
            rating = IntegerField('Rating')
            notes = StringField('Notes')
            image_url = StringField('Image URL')
        return ProductForm

# --- Order View ---
class OrderView(CustomAdminModelView):
    def scaffold_list_columns(self):
        return ['customer_id', 'products', 'total_price', 'order_date', 'status']

    def scaffold_sortable_columns(self):
        return ['order_date', 'total_price', 'status']

    def scaffold_form(self):
        class OrderForm(BaseForm):
            customer_id = StringField('Customer ID', validators=[DataRequired()])
            products = StringField('Products', validators=[DataRequired()])
            total_price = IntegerField('Total Price', validators=[DataRequired()])
            order_date = StringField('Order Date', default=str(datetime.datetime.now()))
            status = StringField('Status', validators=[DataRequired()])
        return OrderForm

# --- Review View ---
class ReviewView(CustomAdminModelView):
    def scaffold_list_columns(self):
        return ['product_id', 'customer_id', 'rating', 'comment', 'review_date']

    def scaffold_sortable_columns(self):
        return ['rating', 'review_date']

    def scaffold_form(self):
        class ReviewForm(BaseForm):
            product_id = StringField('Product ID', validators=[DataRequired()])
            customer_id = StringField('Customer ID', validators=[DataRequired()])
            rating = IntegerField('Rating', validators=[DataRequired()])
            comment = StringField('Comment')
            review_date = StringField('Review Date', default=str(datetime.datetime.now()))
        return ReviewForm

# --- Flask-Login Routes ---
@app.route('/adlogin', methods=['GET', 'POST'])
def adlogin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.AdminUsers.find_one({'username': username})
        if user and bcrypt.check_password_hash(user['password'], password):
            login_user(AdminUser(user))
            return redirect(url_for('admin.index'))
        else:
            return "Invalid credentials, please try again.", 401
    return render_template('adlogin.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Admin Views Registration ---
admin.add_view(ProductView(db.Products, "Products"))
admin.add_view(CustomAdminModelView(db.Customers, "Customers"))
admin.add_view(OrderView(db.Orders, "Orders"))
admin.add_view(ReviewView(db.Reviews, "Reviews"))

# --- Public Routes ---
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/home')
def home():
    products = db.Products.find()
    return render_template('index.html', products=products)

@app.route('/product/<product_id>')
def product_detail(product_id):
    product = db.Products.find_one({"_id": ObjectId(product_id)})
    reviews = db.Reviews.find({"product_id": ObjectId(product_id)})
    return render_template('product_detail.html', product=product, reviews=reviews)

@app.route('/add_to_cart/<product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity'))
    product = db.Products.find_one({"_id": ObjectId(product_id)})
    
    if product:
        cart = session.get('cart', [])
        cart.append({
            "product_id": product_id,
            "name": product['name'],
            "price": product['price'],
            "quantity": quantity
        })
        session['cart'] = cart
    return redirect(url_for('home'))

@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    cart_details = []
    total_price = 0
    for item in cart:
        product = db.Products.find_one({"_id": ObjectId(item['product_id'])})
        if product:
            cart_details.append({
                'name': product['name'],
                'price': product['price'],
                'quantity': item['quantity'],
                'total': product['price'] * item['quantity']
            })
            total_price += product['price'] * item['quantity']
    return render_template('checkout.html', cart_details=cart_details, total_price=total_price)

@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('home'))
    
    customer_id = session['user_id']
    
    order = {
        'customer_id': customer_id,
        'products': cart,
        'total_price': sum(item['price'] * item['quantity'] for item in cart),
        'order_date': str(datetime.datetime.now()),
        'status': 'pending'
    }
    db.Orders.insert_one(order)
    session.pop('cart', None)
    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        phone = request.form['phone']
        user = db.Customers.find_one({"email": email})
        if user and (user['phone'] == phone):
            session['user_id'] = str(user['_id'])
            return redirect(url_for('home'))
        else:
            return "Invalid credentials, please try again.", 401
    
    return render_template('login.html')

# --- User Registration Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = CustomerRegistrationForm(request.form)
    if request.method == 'POST':
        if form.validate():
            existing_user = db.Customers.find_one({"email": form.email.data})
            if existing_user:
                return "Email already registered", 400

            customer = {
                "name": form.name.data,
                "email": form.email.data,
                "phone": form.phone.data,
                "registration_date": str(datetime.datetime.now())
            }
            db.Customers.insert_one(customer)
            return redirect(url_for('login'))
        else:
            return f"Form is not valid: {form.errors}", 400
    return render_template('register.html', form=form)

if __name__ == '__main__':
    app.run(debug=True)
