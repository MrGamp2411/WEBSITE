"""rename wallee_transaction_id to wallee_tx_id and add default status"""

from alembic import op
import sqlalchemy as sa

revision = "0005_update_wallet_topups"
down_revision = "0004_create_wallet_topups"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "wallet_topups",
        "wallee_transaction_id",
        new_column_name="wallee_tx_id",
    )
    op.alter_column(
        "wallet_topups",
        "status",
        existing_type=sa.String(),
        server_default="PENDING",
        nullable=False,
    )


def downgrade():
    op.alter_column(
        "wallet_topups",
        "status",
        existing_type=sa.String(),
        server_default=None,
        nullable=False,
    )
    op.alter_column(
        "wallet_topups",
        "wallee_tx_id",
        new_column_name="wallee_transaction_id",
    )
