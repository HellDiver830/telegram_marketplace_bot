import enum
import datetime as dt
from typing import Optional, List

from sqlalchemy import ForeignKey, Enum, Text, String, BigInteger, Integer
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.db.base import Base


class ProductStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WithdrawalStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)

    products: Mapped[List["Product"]] = relationship(back_populates="user")
    withdrawals: Mapped[List["WithdrawalRequest"]] = relationship(back_populates="user")
    purchases: Mapped[List["Purchase"]] = relationship(back_populates="buyer")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer)
    photo_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus),
        default=ProductStatus.PENDING,
    )
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(
        default=dt.datetime.utcnow,
        onupdate=dt.datetime.utcnow,
    )

    user: Mapped["User"] = relationship(back_populates="products")
    purchases: Mapped[List["Purchase"]] = relationship(back_populates="product")


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(primary_key=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    amount: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)

    buyer: Mapped["User"] = relationship(back_populates="purchases")
    product: Mapped["Product"] = relationship(back_populates="purchases")


class WithdrawalRequest(Base):
    __tablename__ = "withdrawal_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(Integer)
    details: Mapped[str] = mapped_column(Text)
    status: Mapped[WithdrawalStatus] = mapped_column(
        Enum(WithdrawalStatus),
        default=WithdrawalStatus.PENDING,
    )
    created_at: Mapped[dt.datetime] = mapped_column(default=dt.datetime.utcnow)
    paid_at: Mapped[Optional[dt.datetime]] = mapped_column(nullable=True)

    user: Mapped["User"] = relationship(back_populates="withdrawals")
