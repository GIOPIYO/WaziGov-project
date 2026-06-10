from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class ProjectBase(BaseModel):
    project_id: str
    county: str
    financial_year: Optional[str] = None
    project_name: Optional[str] = None
    contract_sum_kshs: Optional[float] = None
    amount_paid_kshs: Optional[float] = None
    implementation_pct: Optional[float] = None
    source_cob: Optional[bool] = None
    source_oag: Optional[bool] = None
    dev_threshold_breach: Optional[bool] = None
    cob_status: Optional[str] = None
    cob_dev_pct: Optional[float] = None
    cob_metric: Optional[str] = None
    oag_status: Optional[str] = None
    oag_match_confidence: Optional[float] = None
    triangulation_verdict: Optional[str] = None
    oag_risk_types: Optional[Any] = None
    oag_findings: Optional[Any] = None

class Project(ProjectBase):
    class Config:
        from_attributes = True

class CountyBase(BaseModel):
    county_name: str
    financial_year: Optional[str] = None
    oag_matched: Optional[bool] = None
    dev_status: Optional[str] = None
    dev_pct: Optional[float] = None
    absorption_pct: Optional[float] = None
    dev_metric: Optional[str] = None
    cob_projects: Optional[int] = None
    oag_findings: Optional[int] = None
    total_records: Optional[int] = None

class County(CountyBase):
    projects: List[Project] = []

    class Config:
        from_attributes = True

class AuditRun(BaseModel):
    id: int
    pipeline: Optional[str] = None
    financial_year: Optional[str] = None
    generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FinanceSummaryBase(BaseModel):
    county_name: str
    fiscal_year: Optional[str] = None
    executive_budget_kshs: Optional[float] = None
    assembly_budget_kshs: Optional[float] = None
    total_budget_kshs: Optional[float] = None
    budgeted_revenue_kshs: Optional[float] = None
    actual_revenue_kshs: Optional[float] = None
    revenue_achievement_pct: Optional[str] = None
    executive_expenditure_kshs: Optional[float] = None
    assembly_expenditure_kshs: Optional[float] = None
    total_expenditure_kshs: Optional[float] = None

class FinanceSummary(FinanceSummaryBase):
    class Config:
        from_attributes = True