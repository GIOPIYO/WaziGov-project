import json
import psycopg2
import sys
import os

def create_tables(cursor):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_runs (
        id SERIAL PRIMARY KEY,
        pipeline VARCHAR(255),
        financial_year VARCHAR(255),
        generated_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS counties (
        county_name VARCHAR(255) PRIMARY KEY,
        financial_year VARCHAR(255),
        oag_matched BOOLEAN,
        dev_status VARCHAR(50),
        dev_pct NUMERIC,
        absorption_pct NUMERIC,
        dev_metric TEXT,
        cob_projects INT,
        oag_findings INT,
        total_records INT
    );

    CREATE TABLE IF NOT EXISTS projects (
        project_id VARCHAR(255) PRIMARY KEY,
        county VARCHAR(255) REFERENCES counties(county_name),
        financial_year VARCHAR(255),
        project_name TEXT,
        contract_sum_kshs NUMERIC,
        amount_paid_kshs NUMERIC,
        implementation_pct NUMERIC,
        source_cob BOOLEAN,
        source_oag BOOLEAN,
        dev_threshold_breach BOOLEAN,
        cob_status VARCHAR(50),
        cob_dev_pct NUMERIC,
        cob_metric TEXT,
        oag_status VARCHAR(50),
        oag_match_confidence NUMERIC,
        triangulation_verdict VARCHAR(255),
        oag_risk_types JSONB,
        oag_findings JSONB
    );
    """)

def ingest_data(conn, json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f, strict=False)

    cursor = conn.cursor()
    create_tables(cursor)
    
    # Ingest audit run
    cursor.execute(
        "INSERT INTO audit_runs (pipeline, financial_year, generated_at) VALUES (%s, %s, %s)",
        (data.get("pipeline"), data.get("financial_year"), data.get("generated_at"))
    )

    for county_data in data.get("counties", []):
        county_name = county_data.get("county")
        
        # Ingest county
        dev_signal = county_data.get("dev_signal") or {}
        stats = county_data.get("stats") or {}
        
        cursor.execute("""
            INSERT INTO counties (
                county_name, financial_year, oag_matched, dev_status, dev_pct, 
                absorption_pct, dev_metric, cob_projects, oag_findings, total_records
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (county_name) DO UPDATE SET
                financial_year = EXCLUDED.financial_year,
                oag_matched = EXCLUDED.oag_matched,
                dev_status = EXCLUDED.dev_status,
                dev_pct = EXCLUDED.dev_pct,
                absorption_pct = EXCLUDED.absorption_pct,
                dev_metric = EXCLUDED.dev_metric,
                cob_projects = EXCLUDED.cob_projects,
                oag_findings = EXCLUDED.oag_findings,
                total_records = EXCLUDED.total_records
        """, (
            county_name,
            data.get("financial_year"),
            county_data.get("oag_matched"),
            dev_signal.get("status"),
            dev_signal.get("dev_pct"),
            dev_signal.get("absorption_pct"),
            dev_signal.get("metric"),
            stats.get("cob_projects"),
            stats.get("oag_findings"),
            stats.get("total_records")
        ))
        
        # Ingest projects
        projects = county_data.get("projects") or []
        for project in projects:
            cob_signal = project.get("cob_signal") or {}
            oag_forensics = project.get("oag_forensics") or {}
            
            cursor.execute("""
                INSERT INTO projects (
                    project_id, county, financial_year, project_name, contract_sum_kshs,
                    amount_paid_kshs, implementation_pct, source_cob, source_oag,
                    dev_threshold_breach, cob_status, cob_dev_pct, cob_metric,
                    oag_status, oag_match_confidence, triangulation_verdict,
                    oag_risk_types, oag_findings
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (project_id) DO NOTHING
            """, (
                project.get("project_id"),
                county_name,
                project.get("financial_year"),
                project.get("project_name"),
                project.get("contract_sum_kshs"),
                project.get("amount_paid_kshs"),
                project.get("implementation_pct"),
                project.get("source_cob"),
                project.get("source_oag"),
                project.get("dev_threshold_breach"),
                cob_signal.get("status"),
                cob_signal.get("dev_pct"),
                cob_signal.get("metric"),
                oag_forensics.get("status"),
                oag_forensics.get("match_confidence"),
                project.get("triangulation_verdict"),
                json.dumps(oag_forensics.get("risk_types", [])),
                json.dumps(oag_forensics.get("findings", []))
            ))

    conn.commit()
    cursor.close()
    print("Ingestion completed successfully.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python json_to_postgres.py <path_to_json>")
        sys.exit(1)
        
    json_file_path = sys.argv[1]
    
    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "wazigov_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "Govan@2003"),
            port=os.getenv("DB_PORT", "5444")
        )
        print("Connected to the database.")
        ingest_data(connection, json_file_path)
        connection.close()
    except Exception as e:
        print("Error during ingestion:", e)
