"""widen tasks.approved_by

Revision ID: 104384f423d8
Revises: 59ecc84bfe63
Create Date: 2026-11-02 16:36:33.378956

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '104384f423d8'
down_revision: Union[str, None] = '59ecc84bfe63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # batch_alter_table: SQLite ALTER COLUMN TYPE'ı desteklemez; batch mode
    # tabloyu yeniden oluşturarak hem SQLite (dev/test) hem Postgres
    # (üretim) üzerinde çalışır.
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "approved_by",
            existing_type=sa.VARCHAR(length=100),
            type_=sa.String(length=255),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.alter_column(
            "approved_by",
            existing_type=sa.String(length=255),
            type_=sa.VARCHAR(length=100),
            existing_nullable=True,
        )
