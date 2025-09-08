"""create wallet_topups table

Revision ID: 0004_create_wallet_topups
Revises: 0003_add_user_id_to_payments
Create Date: 2025-09-08
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_create_wallet_topups"
down_revision = "0003_add_user_id_to_payments"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "wallet_topups",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount_decimal", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="CHF"),
        sa.Column("wallee_transaction_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade():
    op.drop_table("wallet_topups")
