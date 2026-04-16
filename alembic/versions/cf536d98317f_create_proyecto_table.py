"""create-proyecto-table

Revision ID: cf536d98317f
Revises: 
Create Date: 2026-03-26 22:49:44.525158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf536d98317f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear tabla proyecto
    op.create_table(
        'proyecto',
        sa.Column('pk_row', sa.Integer(), nullable=False),
        sa.Column('nombre', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('pk_row')
    )
    
    # Opcional: crear índice en el campo nombre si se va a buscar frecuentemente
    # op.create_index('ix_proyecto_nombre', 'proyecto', ['nombre'])


def downgrade() -> None:
    # Eliminar tabla proyecto
    op.drop_table('proyecto')