import sqlite3
from werkzeug.security import generate_password_hash

with sqlite3.connect("database.db") as conn:
    c = conn.cursor()

#Users table 
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL
)
""")
c.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)")

# Insert sample users
admin_pw = generate_password_hash("admin123")
cashier_pw = generate_password_hash("cashier123")

users =[
    ("amna_admin", admin_pw, "Admin"),
    ("ali_cashier", cashier_pw, "Cashier")  
]

c.executemany(
    "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",users

)

#Products table 
c.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    barcode TEXT UNIQUE NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL CHECK (stock >= 0)
)
""")

c.execute("CREATE INDEX IF NOT EXISTS idx_products_barcode ON products (barcode)")


# Insert sample products
sample_products = [
    ("Milk", "111111", 120.0, 50),
    ("Bread", "222222", 80.0, 30),
    ("Eggs", "333333", 200.0, 100),
]

c.executemany("INSERT OR IGNORE INTO products (name, barcode, price, stock) VALUES (?, ?, ?, ?)", sample_products)

print(f"Database initialize with {len(users)} users and {len(sample_products)} products.")


