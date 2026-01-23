import os, sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "dmart_clean_2026"
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS products 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price REAL, img TEXT, cat TEXT)''')
    db.execute('''CREATE TABLE IF NOT EXISTS users 
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    db.close()

# Security: Don't allow browsing without login
@app.before_request
def require_login():
    allowed = ['user_login', 'register', 'login', 'static']
    if 'user_id' not in session and 'admin' not in session and request.endpoint not in allowed:
        return redirect(url_for('user_login'))

@app.route('/')
def index():
    db = get_db()
    cat = request.args.get('cat')
    search = request.args.get('search')
    if cat: products = db.execute("SELECT * FROM products WHERE cat = ?", (cat,)).fetchall()
    elif search: products = db.execute("SELECT * FROM products WHERE name LIKE ?", ('%'+search+'%',)).fetchall()
    else: products = db.execute("SELECT * FROM products").fetchall()
    cats = db.execute("SELECT DISTINCT cat FROM products").fetchall()
    db.close()
    return render_template('index.html', page='shop', products=products, cats=cats)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        u, p = request.form['u'], request.form['p']
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?,?)", (u, p))
            db.commit()
            flash("Registered! Now Login.")
            return redirect(url_for('user_login'))
        except: flash("Username taken!")
    return render_template('index.html', page='user_register')

@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        u, p = request.form['u'], request.form['p']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ? AND password = ?", (u, p)).fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
        flash("Invalid User Credentials")
    return render_template('index.html', page='user_login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('pw') == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin_page'))
        flash("Wrong Admin Password")
    return render_template('index.html', page='login')

@app.route('/admin_page')
def admin_page():
    if not session.get('admin'): return redirect(url_for('login'))
    db = get_db()
    products = db.execute("SELECT * FROM products").fetchall()
    db.close()
    return render_template('index.html', page='admin', products=products)

@app.route('/add', methods=['POST'])
def add():
    if not session.get('admin'): return redirect(url_for('login'))
    f = request.files['img']
    fname = secure_filename(f.filename) if f else 'dmart.jpg'
    if f: f.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
    db = get_db()
    db.execute("INSERT INTO products (name, price, img, cat) VALUES (?,?,?,?)",
               (request.form['n'], request.form['p'], fname, request.form['c']))
    db.commit()
    return redirect(url_for('admin_page'))

@app.route('/delete/<int:id>')
def delete(id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for('admin_page'))

@app.route('/cart_add/<int:id>')
def cart_add(id):
    cart = session.get('cart', [])
    cart.append(id)
    session['cart'] = cart
    return "OK", 200

@app.route('/cart_view')
def cart_view():
    cart_ids = session.get('cart', [])
    if not cart_ids: return render_template('index.html', page='cart', items=[], total=0)
    db = get_db()
    placeholders = ','.join(['?'] * len(cart_ids))
    items = db.execute(f"SELECT * FROM products WHERE id IN ({placeholders})", cart_ids).fetchall()
    total = sum(i['price'] for i in items)
    return render_template('index.html', page='cart', items=items, total=total)

@app.route('/pay', methods=['POST'])
def pay():
    card = request.form.get('card_number')
    address = request.form.get('address')
    if card == '12345' and address:
        session.pop('cart', None)
        return render_template('index.html', page='success', address=address)
    flash("Need Address & Card: 12345")
    return redirect(url_for('cart_view'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user_login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)