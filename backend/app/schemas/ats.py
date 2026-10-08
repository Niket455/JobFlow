from pydantic import BaseModel


class AtsCheck(BaseModel):
    id: str
    label: str
    score: int
    max_score: int
    passed: bool
    detail: str


class AtsParseTest(BaseModel):
    passed: bool
    extracted: dict[str, bool]
    missing: list[str]


class AtsKeyword(BaseModel):
    matched: list[str]
    missing: list[str]
    coverage: float


class AtsReport(BaseModel):
    score: int
    grade: str
    parse_test: AtsParseTest
    checks: list[AtsCheck]
    keywords: AtsKeyword | None = None
    recommendations: list[str] = []
