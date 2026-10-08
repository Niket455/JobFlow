import uuid

from sqlalchemy import select

from app.models.company import Company
from app.repositories.base import BaseRepository


class CompanyRepository(BaseRepository):
    def get(self, company_id: uuid.UUID) -> Company | None:
        return self.db.get(Company, company_id)

    def get_by_normalized_name(self, normalized_name: str) -> Company | None:
        return self.db.scalar(select(Company).where(Company.normalized_name == normalized_name))

    def get_many(self, ids: set[uuid.UUID]) -> dict[uuid.UUID, Company]:
        if not ids:
            return {}
        rows = self.db.scalars(select(Company).where(Company.id.in_(ids)))
        return {company.id: company for company in rows}

    def get_or_create(self, name: str, normalized_name: str) -> Company:
        existing = self.get_by_normalized_name(normalized_name)
        if existing is not None:
            return existing
        company = Company(name=name, normalized_name=normalized_name)
        self.db.add(company)
        self.db.flush()
        return company
