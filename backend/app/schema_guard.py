from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


CASE_COLUMNS = {
    "source_type": "VARCHAR(30) DEFAULT 'SIMULATOR'",
    "source_name": "VARCHAR(80)",
    "source_record_id": "VARCHAR(150)",
    "raw_payload_id": "INTEGER",
    "complainant_hash": "VARCHAR(64)",
    "language": "VARCHAR(20) DEFAULT 'en'",
    "narrative_original": "TEXT",
    "narrative_translated": "TEXT",
    "outcome_tag": "VARCHAR(40)",
    "subject": "VARCHAR(240)",
    "category_subtype": "VARCHAR(80)",
    "complainant_type": "VARCHAR(40)",
    "is_synthetic": "BOOLEAN DEFAULT TRUE",
}
INSTITUTION_COLUMNS = {
    "is_synthetic": "BOOLEAN DEFAULT TRUE",
    "source_type": "VARCHAR(30) DEFAULT 'SIMULATOR'",
}


def ensure_columns(engine: Engine) -> None:
    insp = inspect(engine)
    with engine.begin() as conn:
        if "cases" in insp.get_table_names():
            existing = {c["name"] for c in insp.get_columns("cases")}
            for name, ddl in CASE_COLUMNS.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE cases ADD COLUMN {name} {ddl}"))
        if "institutions" in insp.get_table_names():
            existing = {c["name"] for c in insp.get_columns("institutions")}
            for name, ddl in INSTITUTION_COLUMNS.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE institutions ADD COLUMN {name} {ddl}"))
