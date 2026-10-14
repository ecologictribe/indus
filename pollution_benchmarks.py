"""
Pollution Benchmarks Module (Decommissioned & Excised from Database Schema)
===========================================================================
Per institutional instructions, environmental and pollution benchmark tables
have been completely excised from the database schema and excluded from all
hedonic valuations and econometric computations.
"""

from database import get_db, query_db

def init_pollution_table(conn=None):
    """Decommissioned: pollution table excised from schema."""
    pass

def seed_pollution_benchmarks(conn=None, force=False):
    """Decommissioned: no pollution figures considered or seeded."""
    pass

def get_pollution_kpis(year=2024):
    """Returns neutralized empty KPI indicators."""
    return {
        "assessment_year": year,
        "total_parks_monitored": 0,
        "avg_cepi_score": 0.0,
        "total_cpa_clusters": 0,
        "total_zld_compliant": 0,
        "avg_red_pct": 0.0,
        "avg_pm25": 0.0,
        "avg_outlet_cod": 0.0,
        "stage_distribution": {}
    }

def get_filtered_pollution_benchmarks(district=None, cpcb_status=None, stage=None, search=None, year=2024, limit=100):
    """Returns empty list: pollution benchmark data removed from computations."""
    return []

def get_single_park_pollution_history(park_id):
    """Returns empty history: pollution data removed from schema."""
    park = query_db("""
        SELECT ip.*, d.district_name, st.taluka_name
        FROM industrial_parks ip
        JOIN subdistricts_talukas st ON ip.taluka_id = st.taluka_id
        JOIN districts d ON st.district_id = d.district_id
        WHERE ip.park_id = ?
    """, (park_id,), one=True)
    return {
        "park": dict(park) if park else None,
        "history": []
    }

def get_pollution_vs_property_drag_data():
    """Pollution drag completely removed from real estate computations."""
    return []
