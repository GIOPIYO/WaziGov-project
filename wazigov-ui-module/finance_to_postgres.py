import json
import psycopg2
import sys
import os

def create_finance_tables(cursor):
    """Creates the table structure for county financial summaries."""
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS county_finances (
        county_name VARCHAR(255),
        fiscal_year VARCHAR(50),
        executive_budget_kshs NUMERIC,
        assembly_budget_kshs NUMERIC,
        total_budget_kshs NUMERIC,
        budgeted_revenue_kshs NUMERIC,
        actual_revenue_kshs NUMERIC,
        revenue_achievement_pct VARCHAR(20),
        executive_expenditure_kshs NUMERIC,
        assembly_expenditure_kshs NUMERIC,
        total_expenditure_kshs NUMERIC,
        PRIMARY KEY (county_name, fiscal_year)
    );
    """)

def clean_numeric(val):
    """Handles cases where numbers might be strings with commas."""
    if isinstance(val, str):
        return float(val.replace(',', ''))
    return val

def ingest_finance_data(conn, json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    metadata = data.get("metadata", {})
    fiscal_year = metadata.get("fiscal_year", "Unknown")
    financial_data = data.get("financial_data", {})

    # We need to merge the three lists (budget, revenue, expenditure) by county name
    merged_records = {}

    # 1. Process Budget Summary
    for entry in financial_data.get("budget_summary", {}).get("data", []):
        county = entry["county"]
        merged_records[county] = {
            "exec_budget": entry.get("executive_budget_kshs"),
            "assemb_budget": entry.get("assembly_budget_kshs"),
            "total_budget": clean_numeric(entry.get("total_budget_kshs"))
        }

    # 2. Process Own Source Revenue
    for entry in financial_data.get("own_source_revenue", {}).get("data", []):
        county = entry["county"]
        if county not in merged_records: merged_records[county] = {}
        merged_records[county].update({
            "budgeted_rev": entry.get("budgeted_kshs"),
            "actual_rev": entry.get("actual_kshs"),
            "rev_pct": entry.get("achievement_pct")
        })

    # 3. Process County Expenditure
    for entry in financial_data.get("county_expenditure", {}).get("data", []):
        county = entry["county"]
        if county not in merged_records: merged_records[county] = {}
        merged_records[county].update({
            "exec_exp": entry.get("executive_expenditure_kshs"),
            "assemb_exp": entry.get("assembly_expenditure_kshs"),
            "total_exp": clean_numeric(entry.get("total_expenditure_kshs"))
        })

    cursor = conn.cursor()
    create_finance_tables(cursor)

    for county, info in merged_records.items():
        cursor.execute("""
            INSERT INTO county_finances (
                county_name, fiscal_year, executive_budget_kshs, assembly_budget_kshs,
                total_budget_kshs, budgeted_revenue_kshs, actual_revenue_kshs,
                revenue_achievement_pct, executive_expenditure_kshs,
                assembly_expenditure_kshs, total_expenditure_kshs
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (county_name, fiscal_year) DO UPDATE SET
                executive_budget_kshs = EXCLUDED.executive_budget_kshs,
                assembly_budget_kshs = EXCLUDED.assembly_budget_kshs,
                total_budget_kshs = EXCLUDED.total_budget_kshs,
                budgeted_revenue_kshs = EXCLUDED.budgeted_revenue_kshs,
                actual_revenue_kshs = EXCLUDED.actual_revenue_kshs,
                revenue_achievement_pct = EXCLUDED.revenue_achievement_pct,
                executive_expenditure_kshs = EXCLUDED.executive_expenditure_kshs,
                assembly_expenditure_kshs = EXCLUDED.assembly_expenditure_kshs,
                total_expenditure_kshs = EXCLUDED.total_expenditure_kshs
        """, (
            county, fiscal_year,
            info.get("exec_budget"), info.get("assemb_budget"), info.get("total_budget"),
            info.get("budgeted_rev"), info.get("actual_rev"), info.get("rev_pct"),
            info.get("exec_exp"), info.get("assemb_exp"), info.get("total_exp")
        ))

    conn.commit()
    cursor.close()
    print(f"Ingestion successful: {len(merged_records)} county summaries processed for {fiscal_year}.")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "src/data/finance_summary_output.json"
    try:
        connection = psycopg2.connect(
            host="localhost", database="wazigov_db", user="postgres",
            password="Govan@2003", port="5433",
            sslmode="disable"
        )
        ingest_finance_data(connection, path)
        connection.close()
    except Exception as e:
        print("Ingestion failed:", e)
