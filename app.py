from flask import Flask, render_template, request, session, jsonify, url_for, redirect, flash
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import select
from tenacity import retry, stop_after_attempt, wait_fixed
import json
from datetime import datetime
import pymysql

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Database configuration
DB_USERNAME = "uscueat2lrsqezsd"
DB_PASSWORD = "Kn1Gjdc6pRHtdZOXHPay"
DB_HOST = "bkvxone7ctnvwq99kvji-mysql.services.clever-cloud.com"
DB_NAME = "bkvxone7ctnvwq99kvji"
DB_PORT = 3306

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?ssl_ca=/path/to/clever-cloud-ca.pem"  # Update with actual path if needed
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_size": 5,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 1800,
    "connect_args": {
        "connect_timeout": 60,
        "ssl": {"ssl": True},
    },
}

# Initialize SQLAlchemy and LoginManager (only once)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Load products from JSON (for product data)
with open('data/products.json', 'r') as file:
    products = json.load(file)


# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # Store hashed passwords in production
    email = db.Column(db.String(100), unique=True, nullable=False)  # Added email
    is_admin = db.Column(db.Boolean, default=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, cancelled
    user = db.relationship('User', backref='orders')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)  # Reference to product from products.json
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    order = db.relationship('Order', backref='items')


# Routes
@app.route('/')
def home():
    return render_template('home.html', products=products[:8], top_sellers=products[8:12], discount_items=products[12:16])


@app.route('/cart', methods=['GET', 'POST', 'DELETE'])
@login_required
def cart():
    if 'cart' not in session or not isinstance(session['cart'], dict):
        session['cart'] = {}

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        quantity = int(request.form.get('quantity', 1))
        product = next((p for p in products if str(p['id']) == str(product_id)), None)
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 400

        if product_id in session['cart']:
            session['cart'][product_id]['quantity'] += quantity
        else:
            session['cart'][product_id] = {
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity
            }

        cart_count = sum(item['quantity'] for item in session['cart'].values())
        cart_items = [
            {
                'name': item['name'],
                'quantity': item['quantity'],
                'total': item['price'] * item['quantity'],
                'product_id': pid
            }
            for pid, item in session['cart'].items()
        ]
        total = sum(item['total'] for item in cart_items) if cart_items else 0
        return jsonify({'success': True, 'cart_count': cart_count, 'cart_items': cart_items, 'total': total})

    elif request.method == 'DELETE':
        product_id = request.path.split('/')[-1]
        if product_id not in session['cart']:
            return jsonify({'success': False, 'message': 'Item not found in cart'}), 400
        del session['cart'][product_id]
        session.modified = True
        cart_count = sum(item['quantity'] for item in session['cart'].values()) if session['cart'] else 0
        cart_items = [
            {
                'name': item['name'],
                'quantity': item['quantity'],
                'total': item['price'] * item['quantity'],
                'product_id': pid
            }
            for pid, item in session['cart'].items()
        ]
        total = sum(item['total'] for item in cart_items) if cart_items else 0
        return jsonify({'success': True, 'cart_count': cart_count, 'cart_items': cart_items, 'total': total})

    cart_count = sum(item['quantity'] for item in session['cart'].values()) if session['cart'] else 0
    cart_items = [
        {
            'name': item['name'],
            'quantity': item['quantity'],
            'total': item['price'] * item['quantity'],
            'product_id': pid
        } for pid, item in session['cart'].items()
    ]
    total = sum(item['total'] for item in cart_items) if cart_items else 0
    return jsonify({'cart_items': cart_items, 'total': total, 'cart_count': cart_count})


@app.route('/category/<category>')
def category(category):
    filtered_items = [p for p in products if p['category'].lower() == category.lower()]
    return render_template('category.html', category=category, items=filtered_items)


@app.route('/product/<int:product_id>')
def product_details(product_id):
    product = next((p for p in products if p['id'] == product_id), None)
    return render_template('product_details.html', product=product)


@app.route('/payment')
@login_required
def payment():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty. Please add items before checkout.', 'error')
        return redirect(url_for('home'))
    cart_items = [{'name': item['name'], 'quantity': item['quantity'], 'total': item['price'] * item['quantity']} for item in session['cart'].values()]
    total = sum(item['total'] for item in cart_items) if cart_items else 0
    print(f"Cart items in payment: {cart_items}")
    return render_template('payment.html', cart_items=cart_items, total=total)


@app.route('/process_payment', methods=['POST'])
@login_required
def process_payment():
    if 'cart' not in session or not session['cart']:
        flash('Cart is empty. Please add items before payment.', 'error')
        return jsonify({'success': False, 'message': 'Cart is empty'}), 400

    payment_method = request.form.get('payment_method')
    if not payment_method or payment_method not in ['cash_on_delivery', 'online_pay']:
        flash('Please select a valid payment method.', 'error')
        return jsonify({'success': False, 'message': 'Invalid payment method'}), 400

    cart_items = session['cart']
    total_amount = sum(item['price'] * item['quantity'] for item in cart_items.values())
    order = Order(user_id=current_user.id, total_amount=total_amount, status='processing')
    db.session.add(order)
    db.session.commit()

    for product_id, item in cart_items.items():
        product = next((p for p in products if str(p['id']) == str(product_id)), None)
        if product:
            order_item = OrderItem(order_id=order.id, product_id=product_id, quantity=item['quantity'], price=item['price'])
            db.session.add(order_item)
    db.session.commit()

    session.pop('cart', None)
    message = 'Order placed successfully via Cash on Delivery!' if payment_method == 'cash_on_delivery' else 'Order placed successfully via Online Pay (GPay)!'
    flash(message, 'success')
    return redirect(url_for('payment_success'))


@app.route('/payment_success')
@login_required
def payment_success():
    return render_template('payment_success.html', message='Order placed successfully!')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:  # Direct comparison (to be updated to hashing)
            session['user_id'] = user.id
            login_user(user)  # Use Flask-Login's login_user
            if user.is_admin:
                flash('Logged in as admin.', 'success')
                return redirect(url_for('admin_panel'))
            else:
                flash('Logged in successfully.', 'success')
                return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            flash(f'You have logged out. Goodbye, {user.username}!', 'success')
        logout_user()  # Clear Flask-Login session
        session.pop('user_id', None)  # Remove manual user_id
    session.clear()  # Clear entire session to ensure no residual data
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/user_orders_json')
@login_required
def user_orders_json():
    print(f"User authenticated: {current_user.is_authenticated}, ID: {current_user.id}")
    try:
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
        order_data = [{
            'id': order.id,
            'order_date': order.order_date.strftime('%Y-%m-%d %H:%M:%S'),
            'total_amount': order.total_amount,
            'status': order.status
        } for order in orders]
        print(f"Orders fetched for user {current_user.id}: {order_data}")
        return jsonify({'orders': order_data})
    except Exception as e:
        print(f"Error fetching orders: {e}")
        return jsonify({'orders': [], 'error': 'Server error'}), 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return redirect(url_for('register'))
        new_user = User(username=username, password=password, email=email, is_admin=False)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Access denied. Admins only.', 'error')
        return redirect(url_for('home'))
    users = User.query.all()
    orders = Order.query.all()
    return render_template('admin_panel.html', users=users, orders=orders)


@app.route('/user_orders')
@login_required
def user_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.order_date.desc()).all()
    return render_template('user_orders.html', orders=orders)




@app.route('/order_details/<int:order_id>')
@login_required
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        flash('You are not authorized to view this order.', 'error')
        return redirect(url_for('user_orders'))
    return render_template('order_details.html', order=order)


@app.route('/admin/order/<int:order_id>/ok', methods=['POST'])
@login_required
def approve_order(order_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    order = Order.query.get_or_404(order_id)
    order.status = 'completed'
    db.session.commit()
    flash('Order approved successfully!', 'success')
    return jsonify({'success': True, 'message': 'Order approved'})


@app.route('/admin/order/<int:order_id>/delete', methods=['POST'])
@login_required
def delete_order(order_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash('Order deleted successfully!', 'success')
    return jsonify({'success': True, 'message': 'Order deleted'})


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Updated to use Session.get


# Create database tables with retry mechanism
@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def create_tables():
    with app.app_context():
        db.create_all()


if __name__ == '__main__':
    try:
        create_tables()
        app.run(debug=True)
    except Exception as e:
        print(f"Failed to initialize database after retries: {e}")
        raise