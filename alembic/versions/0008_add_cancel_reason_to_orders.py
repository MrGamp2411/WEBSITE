"""Add cancel reason to orders"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0008_add_cancel_reason_to_orders'
down_revision = '0007_add_phone_e164'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('cancel_reason', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('orders', 'cancel_reason')
