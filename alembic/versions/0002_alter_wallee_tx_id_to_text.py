"""alter wallee_tx_id to text

Revision ID: 0002
Revises: 0001
Create Date: 2024-06-14
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "payments",
        "wallee_tx_id",
        existing_type=sa.BigInteger(),
        type_=sa.String(),
        postgresql_using="wallee_tx_id::text",
    )


def downgrade() -> None:
    op.alter_column(
        "payments",
        "wallee_tx_id",
        existing_type=sa.String(),
        type_=sa.BigInteger(),
        postgresql_using="wallee_tx_id::bigint",
    )

