from sqlalchemy.orm import Session


class BaseRepository:
    """Base for tenancy-scoped repositories.

    All user-scoped repositories must filter by ``user_id``; centralising the pattern here
    keeps the isolation convention uniform and testable.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def commit(self) -> None:
        """Commit the shared session (services own multi-repository transactions)."""
        self.db.commit()
