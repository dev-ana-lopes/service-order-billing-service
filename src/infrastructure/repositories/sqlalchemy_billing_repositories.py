from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Column, MetaData, String, Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from src.domain.payment import (
    Money,
    Payment,
    PaymentPreference,
    PaymentStatus,
    Quote,
    QuoteStatus,
)

metadata = MetaData()

quotes = Table(
    "quotes",
    metadata,
    Column("quote_id", String(64), primary_key=True),
    Column("service_order_id", String(64), nullable=False, index=True),
    Column("items", JSON, nullable=False),
    Column("amount", String(32), nullable=False),
    Column("currency", String(8), nullable=False),
    Column("status", String(64), nullable=False),
)

payments = Table(
    "payments",
    metadata,
    Column("payment_id", String(64), primary_key=True),
    Column("quote_id", String(64), nullable=False, index=True),
    Column("service_order_id", String(64), nullable=False, index=True),
    Column("amount", String(32), nullable=False),
    Column("currency", String(8), nullable=False),
    Column("status", String(64), nullable=False),
    Column("preference", JSON, nullable=True),
)


def normalize_sync_database_url(database_url: str) -> str:
    return (
        database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")
        .replace("sqlite+aiosqlite://", "sqlite+pysqlite://")
        .replace("?ssl=require", "?sslmode=require")
    )


class SqlAlchemyQuoteRepository:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(normalize_sync_database_url(database_url))
        metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    @classmethod
    def from_engine(cls, engine: Engine) -> "SqlAlchemyQuoteRepository":
        repository = cls.__new__(cls)
        repository._engine = engine
        metadata.create_all(engine)
        repository._session_factory = sessionmaker(bind=engine)
        return repository

    def save(self, quote: Quote) -> None:
        values = {
            "quote_id": quote.quote_id,
            "service_order_id": quote.service_order_id,
            "items": quote.items,
            "amount": str(quote.total.amount),
            "currency": quote.total.currency,
            "status": quote.status.value,
        }
        with self._session_factory() as session:
            existing = session.execute(
                select(quotes.c.quote_id).where(quotes.c.quote_id == quote.quote_id)
            ).scalar_one_or_none()
            if existing is None:
                session.execute(quotes.insert().values(**values))
            else:
                session.execute(
                    quotes.update()
                    .where(quotes.c.quote_id == quote.quote_id)
                    .values(**values)
                )
            session.commit()

    def get(self, quote_id: str) -> Quote:
        with self._session_factory() as session:
            row = (
                session.execute(select(quotes).where(quotes.c.quote_id == quote_id))
                .mappings()
                .first()
            )
        if row is None:
            raise KeyError(f"Quote not found: {quote_id}")
        return self._from_row(dict(row))

    def get_by_service_order_id(self, service_order_id: str) -> Quote:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(quotes).where(quotes.c.service_order_id == service_order_id)
                )
                .mappings()
                .first()
            )
        if row is None:
            raise KeyError(f"Quote not found for service order: {service_order_id}")
        return self._from_row(dict(row))

    def _from_row(self, row: dict[str, Any]) -> Quote:
        items = row["items"]
        if isinstance(items, str):
            items = json.loads(items)
        return Quote(
            quote_id=str(row["quote_id"]),
            service_order_id=str(row["service_order_id"]),
            items=[str(item) for item in items],
            total=Money(Decimal(str(row["amount"])), str(row["currency"])),
            status=QuoteStatus(str(row["status"])),
        )


class SqlAlchemyPaymentRepository:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(normalize_sync_database_url(database_url))
        metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    @classmethod
    def from_engine(cls, engine: Engine) -> "SqlAlchemyPaymentRepository":
        repository = cls.__new__(cls)
        repository._engine = engine
        metadata.create_all(engine)
        repository._session_factory = sessionmaker(bind=engine)
        return repository

    def save(self, payment: Payment) -> None:
        preference = None
        if payment.preference is not None:
            preference = {
                "preference_id": payment.preference.preference_id,
                "checkout_url": payment.preference.checkout_url,
            }
        values = {
            "payment_id": payment.payment_id,
            "quote_id": payment.quote_id,
            "service_order_id": payment.service_order_id,
            "amount": str(payment.total.amount),
            "currency": payment.total.currency,
            "status": payment.status.value,
            "preference": preference,
        }
        with self._session_factory() as session:
            existing = session.execute(
                select(payments.c.payment_id).where(
                    payments.c.payment_id == payment.payment_id
                )
            ).scalar_one_or_none()
            if existing is None:
                session.execute(payments.insert().values(**values))
            else:
                session.execute(
                    payments.update()
                    .where(payments.c.payment_id == payment.payment_id)
                    .values(**values)
                )
            session.commit()

    def get(self, payment_id: str) -> Payment:
        with self._session_factory() as session:
            row = (
                session.execute(
                    select(payments).where(payments.c.payment_id == payment_id)
                )
                .mappings()
                .first()
            )
        if row is None:
            raise KeyError(f"Payment not found: {payment_id}")
        return self._from_row(dict(row))

    def _from_row(self, row: dict[str, Any]) -> Payment:
        preference = row["preference"]
        if isinstance(preference, str):
            preference = json.loads(preference)
        return Payment(
            payment_id=str(row["payment_id"]),
            quote_id=str(row["quote_id"]),
            service_order_id=str(row["service_order_id"]),
            total=Money(Decimal(str(row["amount"])), str(row["currency"])),
            status=PaymentStatus(str(row["status"])),
            preference=None
            if preference is None
            else PaymentPreference(
                preference_id=str(preference["preference_id"]),
                checkout_url=str(preference["checkout_url"]),
            ),
        )
