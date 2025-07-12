import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import random
from datetime import datetime, timedelta
import secrets  # For secure session key
from sqlalchemy.ext.mutable import MutableList
import google.generativeai as genai  # Uncomment and pip install google-generativeai
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))  # Set GEMINI_API_KEY in env
model = genai.GenerativeModel('gemini-1.5-flash')  # Use this for real API calls; mock below

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecoextend.db'  # Local SQLite file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # WARNING: Plaintext; hash in production!
    cart = db.Column(MutableList.as_mutable(db.JSON), default=lambda: [])
    purchases = db.Column(MutableList.as_mutable(db.JSON), default=lambda: [])
    repairs = db.Column(MutableList.as_mutable(db.JSON), default=lambda: [])
    sell_backs = db.Column(MutableList.as_mutable(db.JSON), default=lambda: [])  # Renamed from returns
    rentals = db.Column(MutableList.as_mutable(db.JSON), default=lambda: [])
    donations = db.Column(MutableList.as_mutable(db.JSON), default=lambda: [])
    points = db.Column(db.Integer, default=0)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), nullable=False)
    age = db.Column(db.Integer, nullable=False)  # Age in months

# Create DB and seed data if empty
with app.app_context():
    db.create_all()
    if Product.query.count() == 0:
        # Seed refurbished products with age
        initial_products = [
            {'name': 'T-Shirt', 'description': 'Cotton t-shirt', 'price': 20.0, 'image': 'https://images.pexels.com/photos/996329/pexels-photo-996329.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'age': random.randint(1, 36)},
            {'name': 'Laptop', 'description': 'Refurbished laptop', 'price': 500.0, 'image': 'https://images.pexels.com/photos/18105/pexels-photo.jpg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'age': random.randint(1, 36)},
            {'name': 'Chair', 'description': 'Office chair', 'price': 100.0, 'image': 'https://images.pexels.com/photos/116910/pexels-photo-116910.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'age': random.randint(1, 36)},
            {'name': 'Electric Bike', 'description': 'Eco-friendly electric vehicle', 'price': 800.0, 'image': 'https://images.pexels.com/photos/2526128/pexels-photo-2526128.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'age': random.randint(1, 36)},
            {'name': 'Refrigerator', 'description': 'Energy-efficient fridge', 'price': 600.0, 'image': 'https://images.pexels.com/photos/2131620/pexels-photo-2131620.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'age': random.randint(1, 36)},
            {'name': 'Air Conditioner', 'description': 'Efficient cooling unit', 'price': 400.0, 'image': 'https://images.pexels.com/photos/577514/pexels-photo-577514.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'age': random.randint(1, 36)},
            {'name': 'Used Smartphone', 'description': 'Refurbished smartphone in good condition', 'price': 300.0, 'image': 'https://images.pexels.com/photos/248528/pexels-photo-248528.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'age': random.randint(1, 36)},
            {'name': 'Desk Lamp', 'description': 'Refurbished desk lamp in fair condition', 'price': 15.0, 'image': 'https://images.pexels.com/photos/1112598/pexels-photo-1112598.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'age': random.randint(1, 36)}
        ]
        for p in initial_products:
            db.session.add(Product(**p))
        db.session.commit()

def predict_lifespan(product):
    base = product.price / 10
    variation = random.randint(-5, 5)
    return max(1, int(base + variation))  # In years

def get_user():
    email = session.get('user_email')
    if email:
        return User.query.filter_by(email=email).first()
    return None

@app.context_processor
def inject_cart_count():
    user = get_user()
    cart_count = len(user.cart) if user else 0
    return dict(cart_count=cart_count)

def recommend_products(user_cart, all_products):
    if not user_cart:
        return all_products
    # Simple recommendation: sort by price similarity to average cart price
    avg_cart_price = sum(item['price'] for item in user_cart) / len(user_cart) if user_cart else 0
    sorted_products = sorted(all_products, key=lambda p: abs(p.price - avg_cart_price))
    return sorted_products

@app.route('/')
def home():
    products = Product.query.all()
    user = get_user()
    recommended = recommend_products(user.cart if user else [], products)
    enhanced_recommended = [p for p in recommended[:3]]
    for p in enhanced_recommended:
        setattr(p, 'lifespan', predict_lifespan(p))
    return render_template('home.html', featured=enhanced_recommended)

@app.route('/marketplace')
def marketplace():
    products = Product.query.all()
    user = get_user()
    recommended = recommend_products(user.cart if user else [], products)
    enhanced_products = [p for p in recommended]
    for p in enhanced_products:
        setattr(p, 'lifespan', predict_lifespan(p))
        setattr(p, 'type', 'refurb')
    return render_template('marketplace.html', products=enhanced_products, title='Marketplace')

@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    product = Product.query.get(product_id)
    if product:
        cart_item = {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': product.price,
            'image': product.image,
            'lifespan': predict_lifespan(product)
        }
        user.cart.append(cart_item)
        db.session.commit()
    return redirect(request.referrer or url_for('home'))

@app.route('/rent/<int:product_id>', methods=['POST'])
def rent_product(product_id):
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    duration_days = int(request.form.get('duration_days', 7))
    prod = Product.query.get(product_id)
    if prod:
        rental_cost = (prod.price / 30) * duration_days  # Simple daily rate
        end_date = datetime.now() + timedelta(days=duration_days)
        user.rentals.append({
            'product_name': prod.name,
            'duration_days': duration_days,
            'cost': rental_cost,
            'end_date': end_date.strftime('%Y-%m-%d')
        })
        db.session.commit()
    return redirect(request.referrer or url_for('home'))

@app.route('/cart')
def cart():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    cart_items = user.cart
    total = sum(item['price'] for item in cart_items)
    return render_template('cart.html', cart=cart_items, total=total)

@app.route('/remove_from_cart/<int:index>', methods=['POST'])
def remove_from_cart(index):
    user = get_user()
    if user and 0 <= index < len(user.cart):
        del user.cart[index]
        db.session.commit()
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    total = sum(item['price'] for item in user.cart)
    discount = min(user.points, 10) / 100 * total  # Max 10% discount
    # Apply discount (simulate)
    user.points -= min(user.points, 10)  # Use points
    user.points += int(total // 10)  # Gain points
    user.purchases.extend(user.cart)
    user.cart = []
    db.session.commit()
    return redirect(url_for('profile'))

@app.route('/sell', methods=['GET', 'POST'])
def sell_product():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    message = None
    error = None
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        condition = request.form.get('condition')
        sell_price_str = request.form.get('sell_price')
        if not sell_price_str:
            error = 'Sell price is required'
        else:
            try:
                sell_price = float(sell_price_str)
            except ValueError:
                error = 'Invalid sell price'
                sell_price = None
        if not error:
            prod = Product.query.get(product_id)
            if prod:
                days = random.randint(3, 7)
                pickup_date = datetime.now() + timedelta(days=days)
                new_listing = Product(
                    name=prod.name,
                    description=f'Sold {prod.name} in {condition} condition',
                    price=sell_price,
                    image=prod.image,
                    age=prod.age
                )
                db.session.add(new_listing)
                user.sell_backs.append({
                    'product_name': prod.name,
                    'condition': condition,
                    'sell_price': sell_price,
                    'pickup_date': pickup_date.strftime('%Y-%m-%d'),
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                db.session.commit()
                message = f"Pickup scheduled for {pickup_date.strftime('%Y-%m-%d')}."
                return redirect(url_for('marketplace'))
    prods = Product.query.all()
    return render_template('sell.html', products=prods, error=error, message=message)

@app.route('/donate', methods=['GET', 'POST'])
def donate_product():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    message = None
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        condition = request.form.get('condition')
        prod = Product.query.get(product_id)
        if prod:
            days = random.randint(3, 7)
            pickup_date = datetime.now() + timedelta(days=days)
            user.donations.append({
                'product_name': prod.name,
                'condition': condition,
                'pickup_date': pickup_date.strftime('%Y-%m-%d'),
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            db.session.delete(prod)  # Remove from marketplace
            db.session.commit()
            message = f"Pickup scheduled for {pickup_date.strftime('%Y-%m-%d')}."
    prods = Product.query.all()
    return render_template('donate.html', products=prods, message=message)

@app.route('/repair', methods=['GET', 'POST'])
def repair_product():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    message = None
    repair_guide = None
    repair_shops = None
    cost_estimate = None
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        condition = request.form.get('condition')
        location = request.form.get('location')
        repair_type = request.form.get('repair_type')  # 'diy' or 'professional'
        # Gemini for repair guide
        guide_response = model.generate_content(f"Step by step guide to repair {condition} on {product_name}")
        repair_guide = guide_response.text
        if repair_type == 'professional':
            # Gemini for nearest shop
            shop_response = model.generate_content(f"Nearest repair shops for {product_name} in {location}")
            repair_shops = shop_response.text
            # Gemini for cost estimation
            cost_response = model.generate_content(f"Estimate repair cost for {condition} on {product_name}")
            cost_estimate = cost_response.text
        # Estimate pickup if professional
        if repair_type == 'professional':
            days = random.randint(3, 7)
            pickup_date = datetime.now() + timedelta(days=days)
            message = f"Estimated pickup: {pickup_date.strftime('%Y-%m-%d')}."
            user.repairs.append({
                'product_name': product_name,
                'condition': condition,
                'pickup_date': pickup_date.strftime('%Y-%m-%d'),
                'request_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'cost_estimate': cost_estimate,
                'repair_shops': repair_shops,
                'repair_guide': repair_guide
            })
        else:
            user.repairs.append({
                'product_name': product_name,
                'condition': condition,
                'request_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'repair_guide': repair_guide
            })
        db.session.commit()
    return render_template('repair.html', message=message, repair_guide=repair_guide, repair_shops=repair_shops, cost_estimate=cost_estimate)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('profile.html', user={'name': user.name, 'email': user.email, 'points': user.points}, purchases=user.purchases, repairs=user.repairs, sell_backs=user.sell_backs, rentals=user.rentals, donations=user.donations)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered')
        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        session['user_email'] = email
        return redirect(url_for('profile'))
    return render_template('register.html', error=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and user.password == password:
            session['user_email'] = email
            return redirect(url_for('profile'))
        return render_template('login.html', error='Invalid email or password')
    return render_template('login.html', error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)