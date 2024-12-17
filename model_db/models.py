import enum
from datetime import date
from typing import Optional

from sqlalchemy import Integer, ForeignKey, Float, String
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

engine = create_async_engine('sqlite+aiosqlite:///./data_learning.db', echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class CandleMy(Base):
    __tablename__ = 'candle_my'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time: Mapped[date]
    open: Mapped[float]
    high: Mapped[float]
    low: Mapped[float]
    close: Mapped[float]

class OrderBookMy(Base):
    __tablename__ = 'order_book_my'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    figi: Mapped[str]
    time: Mapped[date]
    bids_count: Mapped[int]
    volume_order: Mapped[float]
    asks_count: Mapped[int]
    volume_ask: Mapped[float]
    depth: Mapped[float]
    limit_up: Mapped[float]
    limit_down: Mapped[float]
    instrument_uid: Mapped[str]

class CurrencyExchangeRateDollar(Base):
    __tablename__ = 'currency_exchange_rate_dollar'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time: Mapped[date]
    nominal: Mapped[float]

class CurrencyExchangeRateEuro(Base):
    __tablename__ = 'currency_exchange_rate_euro'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time: Mapped[date]
    nominal: Mapped[float]
