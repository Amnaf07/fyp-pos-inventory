import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("database.db")
c = conn.cursor()

# --- Users table ---
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL
)
""")

# Insert sample users
admin_pw = generate_password_hash("admin123")
cashier_pw = generate_password_hash("cashier123")

c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
          ("amna_admin", admin_pw, "Admin"))
c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
          ("ali_cashier", cashier_pw, "Cashier"))

# --- Products table ---
c.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    barcode TEXT UNIQUE NOT NULL,
    price REAL NOT NULL,
    stock INTEGER NOT NULL
)
""")

# Insert sample products
sample_products = [
    ("Milk", "111111", 120.0, 50),
    ("Bread", "222222", 80.0, 30),
    ("Eggs", "333333", 200.0, 100),
]

for product in sample_products:
    c.execute("INSERT OR IGNORE INTO products (name, barcode, price, stock) VALUES (?, ?, ?, ?)", product)

# Commit and close at the very end
conn.commit()
conn.close()

print("Database initialized with sample users and products.")
