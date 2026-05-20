from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from sqlalchemy import event
from db import db



class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)
    sales = db.relationship("Sale", back_populates="cashier")

class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    barcode = db.Column(db.String, unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    sale_items = db.relationship("SaleItem", back_populates="product")
    flagged = db.Column(db.Boolean, default=False)  

class SaleItem(db.Model):
    __tablename__ = "sale_items"
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"))
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)
    discount = db.Column(db.Float, default=0.0)  # percentage or flat amount

    sale = db.relationship("Sale", back_populates="sale_items")
    product = db.relationship("Product", back_populates="sale_items")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.product and self.price == 0.0:
            self.price = self.product.price


class Sale(db.Model):
    __tablename__ = "sales"
    id = db.Column(db.Integer, primary_key=True)
    cashier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    total = db.Column(db.Float, nullable=False, default=0.0)
    items = db.Column(db.Integer, nullable=False, default=0)
    customer_id = db.Column(db.Integer, db.ForeignKey("customers.id"), nullable=False)
    customer = db.relationship("Customer", back_populates="sales")
    discount = db.Column(db.Float, nullable=False, server_default="0")  # percentage or flat amount
    voided = db.Column(db.Integer, nullable=False, server_default="0")

    sale_items = db.relationship("SaleItem", back_populates="sale")
    cashier = db.relationship("User", back_populates="sales")
    

    def update_totals(self):
        self.total = sum(i.quantity * i.price for i in self.sale_items)
        self.items = sum(i.quantity for i in self.sale_items)


# Whenever a SaleItem is added or changed, update its parent Sale totals
@event.listens_for(SaleItem, "after_insert")
@event.listens_for(SaleItem, "after_update")
@event.listens_for(SaleItem, "after_delete")
def update_sale_totals(mapper, connection, target):
    sale_id = target.sale_id
    if sale_id:
        # Recalculate totals directly in SQL
        result = connection.execute(
            db.select(
                db.func.sum(SaleItem.quantity * SaleItem.price).label("total"),
                db.func.sum(SaleItem.quantity).label("items")
            ).where(SaleItem.sale_id == sale_id)
        ).first()

        total = result.total or 0.0
        items = result.items or 0

        connection.execute(
            db.update(Sale)
            .where(Sale.id == sale_id)
            .values(total=total, items=items)
        )

class Customer(db.Model):
    __tablename__ = "customers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    phone = db.Column(db.String, nullable=True)

    sales = db.relationship("Sale", back_populates="customer")





class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255))



