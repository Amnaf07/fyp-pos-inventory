from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from db import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)

    sales = relationship("Sale", back_populates="cashier")

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    barcode = Column(String, unique=True, nullable=False)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False)

    sale_items = relationship("SaleItem", back_populates="product")

class Sale(Base):
    __tablename__ = "sales"
    id = Column(Integer, primary_key=True, index=True)
    cashier_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    cashier = relationship("User", back_populates="sales")
    sale_items = relationship("SaleItem", back_populates="sale")

    class SaleItem(Base):
        __tablename__ = "sale_items"
        id = Column(Integer, primary_key=True, index=True)
        sale_id = Column(Integer, ForeignKey("sales.id"))
        product_id = Column(Integer, ForeignKey("products.id"))
        quantity = Column(Integer, nullable=False)

        sale = relationship("Sale", back_populates="sale_items")
        product = relationship("Product", back_populates="sale_items")