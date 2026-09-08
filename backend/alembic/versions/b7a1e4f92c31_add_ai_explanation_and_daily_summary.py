"""add alert explanation column and daily_summaries table

Revision ID: b7a1e4f92c31
Revises: 9d3f6a1c8b47
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7a1e4f92c31'
down_revision: Union[str, Sequence[str], None] = '9d3f6a1c8b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Nullable, no default -- existing alerts (and every alert at the
    # moment the anomaly detector creates it) simply have no explanation
    # yet. Filled in shortly after by ai/explainer.py.
    op.add_column(
        'alerts',
        sa.Column('explanation', sa.Text(), nullable=True),
    )

    op.create_table(
        'daily_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('summary_date', sa.Date(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_daily_summaries_id'), 'daily_summaries', ['id'], unique=False)
    op.create_index(op.f('ix_daily_summaries_summary_date'), 'daily_summaries', ['summary_date'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_daily_summaries_summary_date'), table_name='daily_summaries')
    op.drop_index(op.f('ix_daily_summaries_id'), table_name='daily_summaries')
    op.drop_table('daily_summaries')

    op.drop_column('alerts', 'explanation')
