"""Add normalized phone columns"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0007_add_phone_e164'
down_revision = '0006_drop_user_id_from_payments'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone_e164', sa.String(length=16), nullable=False))
    op.add_column('users', sa.Column('phone_region', sa.String(length=8), nullable=True))
    op.create_unique_constraint('uq_users_phone_e164', 'users', ['phone_e164'])


def downgrade() -> None:
    op.drop_constraint('uq_users_phone_e164', 'users', type_='unique')
    op.drop_column('users', 'phone_region')
    op.drop_column('users', 'phone_e164')
