from flask import Flask, render_template, redirect, url_for, request, flash
import sqlite3
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['password'])
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM user WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            login_user(User(user['id'], user['username'], user['password']))
            return redirect(url_for('dashboard'))
        flash('Login inválido')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        conn = get_db_connection()
        conn.execute('INSERT INTO user (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    imoveis = conn.execute('SELECT * FROM imovel WHERE user_id = ?', (current_user.id,)).fetchall()
    conn.close()
    return render_template('dashboard.html', imoveis=imoveis)

@app.route('/add_imovel', methods=['GET', 'POST'])
@login_required
def add_imovel():
    if request.method == 'POST':
        endereco = request.form['endereco']
        aluguel = float(request.form['aluguel'])
        conn = get_db_connection()
        conn.execute('INSERT INTO imovel (endereco, aluguel, user_id) VALUES (?, ?, ?)', (endereco, aluguel, current_user.id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('add_imovel.html')

@app.route('/edit_imovel/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_imovel(id):
    conn = get_db_connection()
    imovel = conn.execute('SELECT * FROM imovel WHERE id = ?', (id,)).fetchone()
    if request.method == 'POST':
        endereco = request.form['endereco']
        aluguel = float(request.form['aluguel'])
        conn.execute('UPDATE imovel SET endereco = ?, aluguel = ? WHERE id = ?', (endereco, aluguel, id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    conn.close()
    return render_template('edit_imovel.html', imovel=imovel)

@app.route('/delete_imovel/<int:id>')
@login_required
def delete_imovel(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM imovel WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS user (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS imovel (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        endereco TEXT NOT NULL,
                        aluguel REAL NOT NULL,
                        user_id INTEGER NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES user (id)
                    )''')
    conn.commit()
    conn.close()
    app.run(debug=True)
