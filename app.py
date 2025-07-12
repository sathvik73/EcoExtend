from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import random
from datetime import datetime, timedelta
import secrets  # For secure session key

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
    cart = db.Column(db.JSON, default=list)  # Stored as JSON list
    purchases = db.Column(db.JSON, default=list)
    repairs = db.Column(db.JSON, default=list)
    returns = db.Column(db.JSON, default=list)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200), nullable=False)
    is_refurbished = db.Column(db.Boolean, default=False)  # Flag to distinguish

# Create DB and seed data if empty
with app.app_context():
    db.create_all()
    if Product.query.count() == 0:
        # Seed products
        initial_products = [
            {'name': 'T-Shirt', 'description': 'Cotton t-shirt', 'price': 20.0, 'image': 'https://images.pexels.com/photos/996329/pexels-photo-996329.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'is_refurbished': False},
            {'name': 'Laptop', 'description': 'Refurbished laptop', 'price': 500.0, 'image': 'https://images.pexels.com/photos/18105/pexels-photo.jpg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'is_refurbished': False},
            {'name': 'Chair', 'description': 'Office chair', 'price': 100.0, 'image': 'https://images.pexels.com/photos/116910/pexels-photo-116910.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'is_refurbished': False},
            {'name': 'Electric Bike', 'description': 'Eco-friendly electric vehicle', 'price': 800.0, 'image': 'https://images.pexels.com/photos/2526128/pexels-photo-2526128.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'is_refurbished': False},
            {'name': 'Refrigerator', 'description': 'Energy-efficient fridge', 'price': 600.0, 'image': 'https://images.pexels.com/photos/2131620/pexels-photo-2131620.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'is_refurbished': False},
            {'name': 'Air Conditioner', 'description': 'Efficient cooling unit', 'price': 400.0, 'image': 'https://images.pexels.com/photos/577514/pexels-photo-577514.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'is_refurbished': False},
            {'name': 'Used Smartphone', 'description': 'Refurbished smartphone in good condition', 'price': 300.0, 'image': 'https://images.pexels.com/photos/248528/pexels-photo-248528.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'is_refurbished': True},
            {'name': 'Desk Lamp', 'description': 'Refurbished desk lamp in fair condition', 'price': 15.0, 'image': 'https://images.pexels.com/photos/1112598/pexels-photo-1112598.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=1', 'is_refurbished': True}
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

@app.route('/')
def home():
    featured = random.sample(Product.query.filter_by(is_refurbished=False).all(), min(3, Product.query.filter_by(is_refurbished=False).count()))
    enhanced_featured = [p for p in featured]
    for p in enhanced_featured:
        setattr(p, 'lifespan', predict_lifespan(p))
    return render_template('home.html', featured=enhanced_featured)

@app.route('/products')
def list_products():
    prods = Product.query.filter_by(is_refurbished=False).all()
    enhanced_products = [p for p in prods]
    for p in enhanced_products:
        setattr(p, 'lifespan', predict_lifespan(p))
        setattr(p, 'type', 'normal')
    return render_template('products.html', products=enhanced_products, title='Products')

@app.route('/refurbished')
def refurbished_marketplace():
    refurbs = Product.query.filter_by(is_refurbished=True).all()
    enhanced_refurbished = [r for r in refurbs]
    for r in enhanced_refurbished:
        setattr(r, 'lifespan', predict_lifespan(r))
        setattr(r, 'type', 'refurb')
    return render_template('products.html', products=enhanced_refurbished, title='Refurbished Marketplace')

@app.route('/add_to_cart/<string:prod_type>/<int:product_id>', methods=['POST'])
def add_to_cart(prod_type, product_id):
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
            'type': prod_type,
            'lifespan': predict_lifespan(product)
        }
        user.cart.append(cart_item)
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
    user.purchases.extend(user.cart)
    user.cart = []
    db.session.commit()
    return redirect(url_for('profile'))

@app.route('/return', methods=['GET', 'POST'])
def return_product():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        condition = request.form.get('condition')
        prod = Product.query.get(product_id)
        if prod and not prod.is_refurbished:
            new_refurb = Product(
                name=prod.name,
                description=f'Refurbished {prod.name} in {condition} condition',
                price=prod.price * 0.7,
                image=prod.image,
                is_refurbished=True
            )
            db.session.add(new_refurb)
            user.returns.append({
                'product_name': prod.name,
                'condition': condition,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            db.session.commit()
        return redirect(url_for('refurbished_marketplace'))
    prods = Product.query.filter_by(is_refurbished=False).all()
    return render_template('return.html', products=prods)

@app.route('/repair', methods=['GET', 'POST'])
def repair_product():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    message = None
    if request.method == 'POST':
        product_name = request.form.get('product_name')
        condition = request.form.get('condition')
        days = random.randint(3, 7)
        pickup_date = datetime.now() + timedelta(days=days)
        message = f"Estimated pickup for {product_name} in {condition} condition: {pickup_date.strftime('%Y-%m-%d')}"
        user.repairs.append({
            'product_name': product_name,
            'condition': condition,
            'pickup_date': pickup_date.strftime('%Y-%m-%d'),
            'request_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        db.session.commit()
    return render_template('repair.html', message=message)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user = get_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('profile.html', user={'name': user.name, 'email': user.email}, purchases=user.purchases, repairs=user.repairs, returns=user.returns)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            return render_template('register.html', error='Email already registered')
        new_user = User(name=name, email=email, password=password, cart=[], purchases=[], repairs=[], returns=[])
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