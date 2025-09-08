"""drop user_id from payments"""

from alembic import op
import sqlalchemy as sa

revision = "0006_drop_user_id_from_payments"
down_revision = "0005_update_wallet_topups"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_column("user_id")


def downgrade():
    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
