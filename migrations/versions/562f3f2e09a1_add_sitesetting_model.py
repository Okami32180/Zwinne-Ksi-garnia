"""Add SiteSetting model

Revision ID: 562f3f2e09a1
Revises: 657307c145ee
Create Date: 2025-05-27 15:57:20.124774

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '562f3f2e09a1'
down_revision = '657307c145ee'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('SiteSetting',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=50), nullable=False),
    sa.Column('value', sa.String(length=255), nullable=True),
    sa.Column('value_type', sa.String(length=20), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('SiteSetting')
    # ### end Alembic commands ###
