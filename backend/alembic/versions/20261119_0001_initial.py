"""Initial schema. Later changes belong in new revisions, not hand-written ALTER statements."""

from pathlib import Path
import sys

from alembic import op

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

revision = "20261119_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app.models import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.models import Base

    Base.metadata.drop_all(bind=op.get_bind())
