from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "5a708883bd7e"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def upgrade() -> None:
    if not _has_table("quotes"):
        op.create_table(
            "quotes",
            sa.Column("quote_id", sa.String(length=64), primary_key=True),
            sa.Column("service_order_id", sa.String(length=64), nullable=False),
            sa.Column("items", sa.JSON(), nullable=False),
            sa.Column("amount", sa.String(length=32), nullable=False),
            sa.Column("currency", sa.String(length=8), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
        )
        op.create_index(
            "ix_quotes_service_order_id",
            "quotes",
            ["service_order_id"],
            unique=False,
        )

    if not _has_table("payments"):
        op.create_table(
            "payments",
            sa.Column("payment_id", sa.String(length=64), primary_key=True),
            sa.Column("quote_id", sa.String(length=64), nullable=False),
            sa.Column("service_order_id", sa.String(length=64), nullable=False),
            sa.Column("amount", sa.String(length=32), nullable=False),
            sa.Column("currency", sa.String(length=8), nullable=False),
            sa.Column("status", sa.String(length=64), nullable=False),
            sa.Column("preference", sa.JSON(), nullable=True),
        )
        op.create_index(
            "ix_payments_quote_id",
            "payments",
            ["quote_id"],
            unique=False,
        )
        op.create_index(
            "ix_payments_service_order_id",
            "payments",
            ["service_order_id"],
            unique=False,
        )

    if not _has_table("processed_events"):
        op.create_table(
            "processed_events",
            sa.Column("event_id", sa.String(length=64), primary_key=True),
            sa.Column("event_type", sa.String(length=128), nullable=False),
            sa.Column("correlation_id", sa.String(length=128), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    if _has_table("processed_events"):
        op.drop_table("processed_events")
    if _has_table("payments"):
        op.drop_index("ix_payments_service_order_id", table_name="payments")
        op.drop_index("ix_payments_quote_id", table_name="payments")
        op.drop_table("payments")
    if _has_table("quotes"):
        op.drop_index("ix_quotes_service_order_id", table_name="quotes")
        op.drop_table("quotes")
