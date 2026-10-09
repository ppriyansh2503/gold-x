from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Date, String, Numeric, BigInteger, DateTime, UniqueConstraint, func, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class DailyBhavcopy(Base):
    __tablename__ = "daily_bhavcopy"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    high: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    low: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    close: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, default=0)
    open_interest: Mapped[Optional[int]] = mapped_column(BigInteger, default=0)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("trade_date", "symbol", "expiry_date"),
        Index("idx_daily_bhavcopy_sym_exp_date", "symbol", "expiry_date", "trade_date"),
    )

    def __repr__(self):
        return f"<DailyBhavcopy(trade_date={self.trade_date}, symbol={self.symbol}, expiry_date={self.expiry_date}, close={self.close})>"

class NormalizedPrices(Base):
    __tablename__ = "normalized_prices"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    raw_close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    norm_close_10g_999: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    purity_multiplier: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    unit_multiplier: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger, default=0)
    open_interest: Mapped[Optional[int]] = mapped_column(BigInteger, default=0)

    __table_args__ = (
        UniqueConstraint("trade_date", "symbol", "expiry_date"),
        Index("idx_normalized_prices_sym_exp_date", "symbol", "expiry_date", "trade_date"),
    )

    def __repr__(self):
        return f"<NormalizedPrices(trade_date={self.trade_date}, symbol={self.symbol}, expiry_date={self.expiry_date}, norm_close={self.norm_close_10g_999})>"
