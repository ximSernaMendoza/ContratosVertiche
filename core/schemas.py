from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Evidence(BaseModel):
    quote: str = Field(..., description="Fragmento literal del contrato")
    page: Optional[int] = Field(None, description="Página (si está disponible)")
    rationale: str = Field(..., description="Por qué este fragmento soporta el hallazgo")

class ExtractedLease(BaseModel):
    lease_type: str  # habitacional | comercial | industrial | retail
    parties: Dict[str, Any]
    property: Dict[str, Any]
    term: Dict[str, Any]
    rent: Dict[str, Any]
    deposits_guarantees: Dict[str, Any]
    penalties: Dict[str, Any]
    increases: Dict[str, Any]
    termination: Dict[str, Any]
    permitted_use: Dict[str, Any]
    sublease_assignment: Dict[str, Any]
    jurisdiction: Dict[str, Any]
    annexes: Dict[str, Any]
    evidence: List[Evidence] = []

class AgentFinding(BaseModel):
    title: str
    severity: str  # low | medium | high
    description: str
    recommendation: str
    evidence: List[Evidence] = []

class AgentReport(BaseModel):
    agent: str
    summary: str
    findings: List[AgentFinding]

class RiskScore(BaseModel):
    total_score_0_100: int
    level: str  # Bajo | Medio | Alto
    breakdown: List[Dict[str, Any]]  # factor, peso, score, motivo

class FinanceProjection(BaseModel):
    assumptions: Dict[str, Any]
    table_rows: List[Dict[str, Any]]
    total_contract_value: float
    max_exposure: float
    break_even: Optional[float] = None

class CalendarItem(BaseModel):
    name: str
    date_iso: str
    reminder_days_before: List[int]
    notes: str
