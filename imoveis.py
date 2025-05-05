from flask import Flask, render_template, redirect, url_for, request, flash
import sqlite3
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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

from datetime import datetime
from flask import render_template
from flask_login import login_required, current_user

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    imoveis = conn.execute('SELECT * FROM imovel WHERE user_id = ?', (current_user.id,)).fetchall()
    conn.close()

    hoje = datetime.today()
    mes_atual = hoje.month
    ano_atual = hoje.year

    imoveis_tratados = []

    for imovel in imoveis:
        reajuste_aviso = False
        try:
            inicio_contrato_str = imovel['inicio_contrato']
            mes_reajuste = imovel['mes_reajuste']
            ultimo_reajuste_str = imovel['data_ultimo_reajuste']

            if inicio_contrato_str and mes_reajuste:
                inicio_contrato = datetime.strptime(inicio_contrato_str, '%Y-%m-%d')
                ano_inicio = inicio_contrato.year
                mes_reajuste = int(mes_reajuste)

                # Verifica se estamos no mês do reajuste ou após, no mesmo ano ou anos posteriores
                if (ano_atual > ano_inicio or (ano_atual == ano_inicio and mes_atual >= mes_reajuste)):
                    if not ultimo_reajuste_str:
                        reajuste_aviso = True
                    else:
                        ultimo_reajuste = datetime.strptime(ultimo_reajuste_str, '%Y-%m-%d')
                        if ultimo_reajuste.year < ano_atual:
                            reajuste_aviso = True
        except Exception as e:
            print(f'Erro ao processar imóvel ID {imovel["id"]}: {e}')

        imovel_dict = dict(imovel)
        imovel_dict['reajuste_aviso'] = reajuste_aviso
        imoveis_tratados.append(imovel_dict)

    return render_template('dashboard.html', imoveis=imoveis_tratados)




@app.route('/add_imovel', methods=['GET', 'POST'])
@login_required
def add_imovel():
    if request.method == 'POST':
        endereco = request.form['endereco']
        aluguel = float(request.form['aluguel'])
        inicio_contrato = request.form['inicio_contrato']
        fim_contrato = request.form['fim_contrato']
        mes_reajuste = int(request.form['mes_reajuste'])
        data_ultimo_reajuste = request.form['data_ultimo_reajuste']
        
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO imovel (endereco, aluguel, user_id, inicio_contrato, fim_contrato, mes_reajuste, data_ultimo_reajuste)
                VALUES (?, ?, ?, ?, ?, ?,?)''',
                (endereco, aluguel, current_user.id, inicio_contrato, fim_contrato, mes_reajuste, data_ultimo_reajuste))
            conn.commit()
        except Exception as e:
            conn.close()
            flash(f'Erro ao salvar imóvel: {e}')
            return render_template('add_imovel.html')
        
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
        novo_aluguel = float(request.form['aluguel'])
        inicio_contrato = request.form['inicio_contrato']
        fim_contrato = request.form['fim_contrato']
        mes_reajuste = int(request.form['mes_reajuste'])

        # Verificar se o aluguel foi alterado
        data_ultimo_reajuste = imovel['data_ultimo_reajuste']
        if imovel['aluguel'] != novo_aluguel:
            data_ultimo_reajuste = datetime.today().strftime('%Y-%m-%d')

        conn.execute('''
            UPDATE imovel
            SET endereco = ?, aluguel = ?, inicio_contrato = ?, fim_contrato = ?, mes_reajuste = ?, data_ultimo_reajuste = ?
            WHERE id = ?
        ''', (endereco, novo_aluguel, inicio_contrato, fim_contrato, mes_reajuste, data_ultimo_reajuste, id))
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
