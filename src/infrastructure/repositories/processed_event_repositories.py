from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, MetaData, String, Table, create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.repositories.sqlalchemy_billing_repositories import (
    normalize_sync_database_url,
)

metadata = MetaData()

processed_events = Table(
    "processed_events",
    metadata,
    Column("event_id", String(64), primary_key=True),
    Column("event_type", String(128), nullable=False),
    Column("correlation_id", String(128), nullable=False),
    Column("processed_at", DateTime(timezone=True), nullable=False),
)


class InMemoryProcessedEventRepository:
    def __init__(self) -> None:
        self.events: set[str] = set()

    def is_processed(self, event_id: str) -> bool:
        return event_id in self.events

    def mark_processed(
        self, event_id: str, event_type: str, correlation_id: str
    ) -> None:
        self.events.add(event_id)


class SqlAlchemyProcessedEventRepository:
    def __init__(self, database_url: str) -> None:
        self._engine = create_engine(normalize_sync_database_url(database_url))
        metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    @classmethod
    def from_engine(cls, engine: Engine) -> "SqlAlchemyProcessedEventRepository":
        repository = cls.__new__(cls)
        repository._engine = engine
        metadata.create_all(engine)
        repository._session_factory = sessionmaker(bind=engine)
        return repository

    def is_processed(self, event_id: str) -> bool:
        with self._session_factory() as session:
            return (
                session.execute(
                    select(processed_events.c.event_id).where(
                        processed_events.c.event_id == event_id
                    )
                ).scalar_one_or_none()
                is not None
            )

    def mark_processed(
        self, event_id: str, event_type: str, correlation_id: str
    ) -> None:
        if self.is_processed(event_id):
            return
        with self._session_factory() as session:
            session.execute(
                processed_events.insert().values(
                    event_id=event_id,
                    event_type=event_type,
                    correlation_id=correlation_id,
                    processed_at=datetime.now(UTC),
                )
            )
            session.commit()
