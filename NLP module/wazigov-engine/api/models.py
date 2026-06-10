from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .database import Base

class AuditRun(Base):
    __tablename__ = "audit_runs"
    id = Column(Integer, primary_key=True, index=True)
    pipeline = Column(String(255))
    financial_year = Column(String(255))
    generated_at = Column(DateTime)

class County(Base):
    __tablename__ = "counties"
    county_name = Column(String(255), primary_key=True, index=True)
    financial_year = Column(String(255))
    oag_matched = Column(Boolean)
    dev_status = Column(String(50))
    dev_pct = Column(Numeric)
    absorption_pct = Column(Numeric)
    dev_metric = Column(String)
    cob_projects = Column(Integer)
    oag_findings = Column(Integer)
    total_records = Column(Integer)
    
    projects = relationship("Project", back_populates="county_details")

class Project(Base):
    __tablename__ = "projects"
    project_id = Column(String(255), primary_key=True, index=True)
    county = Column(String(255), ForeignKey("counties.county_name"))
    financial_year = Column(String(255))
    project_name = Column(String)
    contract_sum_kshs = Column(Numeric)
    amount_paid_kshs = Column(Numeric)
    implementation_pct = Column(Numeric)
    source_cob = Column(Boolean)
    source_oag = Column(Boolean)
    dev_threshold_breach = Column(Boolean)
    cob_status = Column(String(50))
    cob_dev_pct = Column(Numeric)
    cob_metric = Column(String)
    oag_status = Column(String(50))
    oag_match_confidence = Column(Numeric)
    triangulation_verdict = Column(String(255))
    oag_risk_types = Column(JSON)
    oag_findings = Column(JSON)

    county_details = relationship("County", back_populates="projects")

class FinanceSummary(Base):
    __tablename__ = "county_finances" # Change this if your table is named differently
    
    county_name = Column(String(255), primary_key=True, index=True)
    fiscal_year = Column(String(255))
    executive_budget_kshs = Column(Numeric)
    assembly_budget_kshs = Column(Numeric)
    total_budget_kshs = Column(Numeric)
    budgeted_revenue_kshs = Column(Numeric)
    actual_revenue_kshs = Column(Numeric)
    revenue_achievement_pct = Column(String(50))
    executive_expenditure_kshs = Column(Numeric)
    assembly_expenditure_kshs = Column(Numeric)
    total_expenditure_kshs = Column(Numeric)