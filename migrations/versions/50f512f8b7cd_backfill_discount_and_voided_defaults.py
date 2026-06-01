"""Backfill discount and voided defaults

Revision ID: 50f512f8b7cd
Revises: 94535519ec2c
Create Date: 2026-05-21 00:01:57.339405

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '50f512f8b7cd'
down_revision = '94535519ec2c'
branch_labels = None
depends_on = None


def upgrade():
     op.execute("UPDATE sales SET discount = 0 WHERE discount IS NULL;")
     op.execute("UPDATE sales SET voided = 0 WHERE voided IS NULL;")


def downgrade():
    op.execute("UPDATE sales SET discount = NULL WHERE discount = 0;")
    op.execute("UPDATE sales SET voided = NULL WHERE voided = 0;")
