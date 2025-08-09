import sqlite3

def init_db():
    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cuentas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        imap TEXT NOT NULL
    )''')
    conn.commit()
    conn.close()

def get_cuentas():
    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()
    c.execute("SELECT email, password, imap FROM cuentas")
    cuentas = [{"email": row[0], "password": row[1], "imap": row[2]} for row in c.fetchall()]
    conn.close()
    return cuentas

def add_cuenta(email, password, imap):
    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()
    c.execute("INSERT INTO cuentas (email, password, imap) VALUES (?, ?, ?)", (email, password, imap))
    conn.commit()
    conn.close()

def delete_cuenta(email):
    conn = sqlite3.connect('accounts.db')
    c = conn.cursor()
    c.execute("DELETE FROM cuentas WHERE email=?", (email,))
    conn.commit()
    conn.close()
