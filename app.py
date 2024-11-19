from flask import Flask, render_template, request, redirect, url_for, session
from flask_pymongo import PyMongo
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
# --- App Configuration ---
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config["MONGO_URI"] = "mongodb://localhost:27017/perfume_store"

# --- Extensions ---
mongo = PyMongo(app)
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
    user = mongo.db.AdminUsers.find_one({"_id": ObjectId(user_id)})
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
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), Length(min=6)])

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
        return ['name', 'brand', 'price', 'category', 'size', 'gender', 'stock', 'rating', 'notes' ,'image_url']

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
            image_url = StringField('image_url')
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
        user = mongo.db.AdminUsers.find_one({'username': username})
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
admin.add_view(ProductView(mongo.db.Products, "Products"))
admin.add_view(CustomAdminModelView(mongo.db.Customers, "Customers"))
admin.add_view(OrderView(mongo.db.Orders, "Orders"))
admin.add_view(ReviewView(mongo.db.Reviews, "Reviews"))

# --- Public Routes ---
# Home page
@app.route('/')
def index():
    products = mongo.db.Products.find()
    return render_template('index.html', products=products)

# Product detail page
@app.route('/product/<product_id>')
def product_detail(product_id):
    product = mongo.db.Products.find_one({"_id": ObjectId(product_id)})
    reviews = mongo.db.Reviews.find({"product_id": ObjectId(product_id)})
    return render_template('product_detail.html', product=product, reviews=reviews)

# Add product to cart
@app.route('/add_to_cart/<product_id>', methods=['POST'])
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity'))
    cart = session.get('cart', [])
    cart.append({"product_id": product_id, "quantity": quantity})
    session['cart'] = cart
    return redirect(url_for('index'))

# View cart
@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    cart_details = []
    total_price = 0
    for item in cart:
        product = mongo.db.Products.find_one({"_id": ObjectId(item['product_id'])})
        cart_details.append({
            'name': product['name'],
            'price': product['price'],
            'quantity': item['quantity'],
            'total': product['price'] * item['quantity']
        })
        total_price += product['price'] * item['quantity']
    return render_template('checkout.html', cart_details=cart_details, total_price=total_price)

# Checkout
@app.route('/checkout', methods=['POST'])
def checkout():
    cart = session.get('cart', [])
    if not cart:
        return redirect(url_for('index'))
    
    # Here, you would process the order
    order = {
        'customer_id': 'customer_id_here',  # You would get customer info from session or login
        'products': cart,
        'total_price': sum(item['quantity'] * mongo.db.Products.find_one({"_id": ObjectId(item['product_id'])})['price'] for item in cart),
        'order_date': datetime.datetime.now(),
        'status': 'Pending'
    }
    mongo.db.Orders.insert_one(order)
    
    # Clear the cart after checkout
    session['cart'] = []
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # جستجو برای کاربر در MongoDB
        user = mongo.db.Customers.find_one({"email": email})
        
        if user and check_password_hash(user['password'], password):
            # اگر کاربر پیدا شد و رمز عبور درست بود
            session['user_id'] = str(user['_id'])  # ذخیره اطلاعات کاربر در سشن
            return redirect(url_for('index'))  # هدایت به صفحه اصلی
        else:
            # اگر ایمیل یا رمز عبور نادرست باشد
            return "Invalid credentials, please try again.", 401
    
    return render_template('login.html')

# --- User Registration Route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = CustomerRegistrationForm(request.form)
    if request.method == 'POST':
        if form.validate():
            print("Form validated successfully")
            if form.password.data != form.confirm_password.data:
                return "Passwords do not match", 400
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            existing_user = mongo.db.Customers.find_one({"email": form.email.data})
            if existing_user:
                return "Email already registered", 400

            customer = {
                "name": form.name.data,
                "email": form.email.data,
                "password": hashed_password,
                "registration_date": str(datetime.datetime.now())
            }
            mongo.db.Customers.insert_one(customer)
            return redirect(url_for('login'))
        else:
            print(f"Form errors: {form.errors}")  # چاپ خطاها برای بررسی مشکل
            return f"Form is not valid :{form.errors}", 400
    return render_template('register.html', form=form)



if __name__ == '__main__':
    app.run(debug=True)


