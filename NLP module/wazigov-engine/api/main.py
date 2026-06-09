from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

from . import models, schemas
from .database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WaziGov API",
    description="Backend service for WaziGov UI module",
    version="1.0.0"
)

origins = [
    "http://localhost:3000",  # Keep this so your laptop still works locally
    "https://wazigov-ui-939561920912.us-central1.run.app"  # Your live Next.js UI
]


# CORS configuration to allow UI module to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Adjust this in production to match your UI domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to WaziGov API"}

@app.get("/counties", response_model=List[schemas.CountyBase])
def get_counties(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    counties = db.query(models.County).offset(skip).limit(limit).all()
    return counties

@app.get("/counties/{county_name}", response_model=schemas.County)
def get_county(county_name: str, db: Session = Depends(get_db)):
    county = db.query(models.County).filter(models.County.county_name == county_name).first()
    if county is None:
        raise HTTPException(status_code=404, detail="County not found")
    return county

@app.get("/projects", response_model=List[schemas.ProjectBase])
def get_projects(
    skip: int = 0, 
    limit: int = 100, 
    county_name: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Project)
    if county_name:
        query = query.filter(models.Project.county == county_name)
    if search:
        query = query.filter(models.Project.project_name.ilike(f"%{search}%"))
    
    projects = query.offset(skip).limit(limit).all()
    return projects

@app.get("/projects/{project_id}", response_model=schemas.Project)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.project_id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@app.get("/audit_runs", response_model=List[schemas.AuditRun])
def get_audit_runs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    runs = db.query(models.AuditRun).offset(skip).limit(limit).all()
    return runs
