"""add symbol_summaries table

Revision ID: f3c92a7e4d18
Revises: b7a1e4f92c31
Create Date: 2026-09-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3c92a7e4d18'
down_revision: Union[str, Sequence[str], None] = 'b7a1e4f92c31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'symbol_summaries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol_id', sa.Integer(), nullable=False),
        sa.Column('summary_text', sa.Text(), nullable=False),
        sa.Column('through_tick_id', sa.Integer(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['symbol_id'], ['symbols.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_symbol_summaries_id'), 'symbol_summaries', ['id'], unique=False)
    op.create_index(op.f('ix_symbol_summaries_symbol_id'), 'symbol_summaries', ['symbol_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_symbol_summaries_symbol_id'), table_name='symbol_summaries')
    op.drop_index(op.f('ix_symbol_summaries_id'), table_name='symbol_summaries')
    op.drop_table('symbol_summaries')
