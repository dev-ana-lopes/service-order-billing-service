from __future__ import annotations

from sqlalchemy import MetaData

from src.infrastructure.repositories.processed_event_repositories import (
    metadata as processed_event_metadata,
)
from src.infrastructure.repositories.sqlalchemy_billing_repositories import (
    metadata as billing_metadata,
)

ALL_METADATA = (
    billing_metadata,
    processed_event_metadata,
)


def build_combined_metadata() -> MetaData:
    metadata = MetaData()
    for source_metadata in ALL_METADATA:
        for table in source_metadata.tables.values():
            table.to_metadata(metadata)
    return metadata
