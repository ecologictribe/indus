"""
plot_decay_engine.py
Institutional Micro-Metrics, Valuation Waterfall, and Industrial Lifecycle Decay Framework.
Implements the 5 Archetypes of Decay, 4-Tier Plot Metrics (FEI, LIF, SAM, SFR, MPSP),
Estate Decay Index (EDI), and In-Estate Distance Decay Splines.
"""

import math
import sqlite3
import random

def init_plot_decay_tables(conn):
    """Initializes the three relational tables for plot decay and estate obsolescence."""
    cursor = conn.cursor()

    # 1. Micro-level plot obsolescence and logistical decay metrics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plot_decay_metrics (
            plot_id TEXT PRIMARY KEY REFERENCES industrial_plots(plot_id),
            frontage_efficiency_index REAL,
            logistical_ingress_factor REAL,
            speculation_arbitrage_multiple REAL,
            stranded_footprint_ratio REAL,
            micro_pollution_shadow REAL,
            is_pencil_plot INTEGER DEFAULT 0,
            is_truck_choked INTEGER DEFAULT 0,
            decay_vulnerability_score REAL,
            lifecycle_state TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Estate-level macro senescence and capacity depletion audit
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS estate_obsolescence_audit (
            park_id INTEGER PRIMARY KEY REFERENCES industrial_parks(park_id),
            estate_decay_index REAL,
            brownfield_morbidity_ratio REAL,
            urban_friction_quotient REAL,
            cetp_hydraulic_strain_ratio REAL,
            freight_curfew_hours_per_day INTEGER,
            average_aspect_ratio REAL,
            obsolescence_stage TEXT,
            evaluated_year INTEGER DEFAULT 2026
        )
    """)

    # 3. Historical plot lifecycle transitions for Markov churn modeling
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plot_lifecycle_transitions (
            transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
            plot_id TEXT REFERENCES industrial_plots(plot_id),
            from_status TEXT,
            to_status TEXT,
            event_trigger TEXT,
            effective_date DATE,
            source_citation TEXT
        )
    """)

    conn.commit()


def seed_plot_decay_data(conn):
    """
    Populates plot_decay_metrics and estate_obsolescence_audit deterministically
    across all 3,478 plots and 312 industrial estates in Gujarat.
    """
    init_plot_decay_tables(conn)
    cursor = conn.cursor()

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM plot_decay_metrics")
    if cursor.fetchone()[0] >= 3400:
        return

    # 1. Compute Estate-Level Obsolescence Audit
    cursor.execute("""
        SELECT 
            park_id, 
            park_name, 
            current_cepi_score, 
            has_moratorium, 
            has_cetp, 
            notification_year,
            latitude,
            longitude
        FROM industrial_parks
    """)
    parks = cursor.fetchall()

    for p in parks:
        pid, name, cepi, morat, cetp, n_year, lat, lng = p
        cepi = float(cepi or 48.0)
        morat = int(morat or 0)
        cetp = int(cetp or 0)
        n_year = int(n_year or 1995)
        age = max(4, 2026 - n_year)

        # Urban proximity heuristic (Ahmedabad, Surat, Vadodara, Rajkot coordinates)
        major_cities = [(23.02, 72.57), (21.17, 72.83), (22.30, 73.18), (22.30, 70.80)]
        min_city_dist = min(
            math.sqrt((lat - clat)**2 + (lng - clng)**2) * 111.0
            for clat, clng in major_cities
        )

        # Urban Friction Quotient (UFQ)
        ufq = round(max(0.6, min(3.8, 3.8 - (min_city_dist / 30.0))), 2)

        # Freight curfew hours per day (dense urban periphery faces daytime bans)
        if ufq > 2.8:
            curfew_hrs = 12 # 08:00 - 20:00
        elif ufq > 1.8:
            curfew_hrs = 6
        else:
            curfew_hrs = 0

        # CETP hydraulic strain ratio
        if cetp == 1:
            cetp_strain = round(0.70 + (cepi / 100.0) * 0.55, 2)
        else:
            cetp_strain = 0.0

        # Brownfield Morbidity Ratio (BMR)
        bmr = round(min(0.42, 0.05 + (cepi / 100.0) * 0.20 + (age / 50.0) * 0.12), 3)

        # Estate Decay Index (EDI 0 to 100)
        s_env = min(100.0, (cepi / 85.0) * 80.0 + (morat * 20.0))
        s_cadastral = min(100.0, (age / 45.0) * 60.0 + (30.0 if "old" in name.lower() or age > 35 else 10.0))
        s_morb = bmr * 200.0
        s_urban = (ufq / 3.8) * 100.0
        s_infra = (age / 50.0) * 70.0 + (0.0 if cetp == 1 else 30.0)

        edi = round(0.25 * s_env + 0.25 * s_cadastral + 0.20 * s_morb + 0.15 * s_urban + 0.15 * s_infra, 1)
        edi = max(10.0, min(95.0, edi))

        # Lifecycle stage categorization
        if edi < 30.0:
            stage = 'STAGE_1_PRISTINE'
        elif edi < 50.0:
            stage = 'STAGE_2_MATURE'
        elif edi < 68.0:
            stage = 'STAGE_3_CONGESTED'
        elif edi < 82.0:
            stage = 'STAGE_4_MORIBUND'
        else:
            stage = 'STAGE_5_POST_INDUSTRIAL_REDEVELOPMENT'

        avg_aspect = round(1.8 + (age / 50.0) * 0.8, 2)

        cursor.execute("""
            INSERT OR REPLACE INTO estate_obsolescence_audit (
                park_id, estate_decay_index, brownfield_morbidity_ratio, urban_friction_quotient,
                cetp_hydraulic_strain_ratio, freight_curfew_hours_per_day, average_aspect_ratio,
                obsolescence_stage, evaluated_year
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 2026)
        """, (pid, edi, bmr, ufq, cetp_strain, curfew_hrs, avg_aspect, stage))

    # 2. Compute Plot-Level Micro Metrics
    cursor.execute("""
        SELECT 
            p.plot_id, 
            p.park_id, 
            p.plot_number, 
            p.plot_area_sqm, 
            p.road_width_m, 
            p.frontage_m, 
            p.status, 
            p.allotment_price_sqm,
            ip.current_cepi_score,
            ip.has_moratorium,
            oa.estate_decay_index,
            oa.freight_curfew_hours_per_day
        FROM industrial_plots p
        JOIN industrial_parks ip ON p.park_id = ip.park_id
        JOIN estate_obsolescence_audit oa ON p.park_id = oa.park_id
    """)
    plot_rows = cursor.fetchall()

    decay_records = []
    for pr in plot_rows:
        (p_id, park_id, plot_no, area, road_w, frontage, status, price,
         cepi, morat, edi, curfew) = pr

        area = float(area or 1500.0)
        road_w = float(road_w or 18.0)
        frontage = float(frontage or 30.0)
        price = float(price or 3500.0)
        cepi = float(cepi or 48.0)
        morat = int(morat or 0)
        edi = float(edi or 40.0)
        curfew = int(curfew or 0)

        # Safe integer extraction from alphanumeric plot identifier
        digits = ''.join(c for c in str(plot_no) if c.isdigit())
        p_int = int(digits) if digits else 1

        # A. Frontage Efficiency Index (FEI)
        fei = round(frontage / math.sqrt(area), 2)
        is_pencil = 1 if fei < 0.50 else 0

        # B. Logistical Ingress Factor (LIF)
        lif = round(road_w / 15.5, 2)
        is_truck_choked = 1 if (road_w < 12.0 or lif < 0.65) else 0

        # C. Speculation Arbitrage Multiple (SAM)
        # In speculative high-growth parks, SAM > 1.8; in decaying parks, SAM < 0.85
        if edi > 70.0:
            sam = round(max(0.62, 0.95 - (edi - 70.0) * 0.012), 2)
        else:
            sam = round(1.10 + (80.0 - edi) * 0.015, 2)

        # D. Stranded Footprint Ratio (SFR)
        if status == 'Available':
            sfr = 1.0 # Completely unbuilt
        elif status == 'Occupied':
            sfr = round(max(0.10, 0.40 - (p_int % 4) * 0.08), 2)
        else:
            sfr = 0.75

        # E. Micro-Pollution Shadow (MPSP)
        mpsp = round(min(100.0, (cepi * 0.8) + (20.0 if morat else 0.0) + (p_int % 7) * 2.5), 1)

        # F. Decay Vulnerability Score (0 to 100)
        # Weighted combination of road narrowness, shape inefficiency, estate decay, and environmental drag
        decay_score = round(
            0.30 * (100.0 - min(100.0, lif * 66.0)) +
            0.25 * (100.0 if is_pencil else 20.0) +
            0.25 * edi +
            0.20 * mpsp,
            1
        )
        decay_score = max(5.0, min(95.0, decay_score))

        # G. Dynamic Lifecycle State
        if morat == 1 and cepi >= 70.0 and (p_int % 3 == 0):
            lifecycle_state = 'Environmental_Brownfield'
        elif is_truck_choked and status != 'Available' and (p_int % 5 == 0):
            lifecycle_state = 'Distressed_Auction'
        elif status == 'Available' or sfr > 0.8:
            lifecycle_state = 'Underutilized_Speculative'
        elif decay_score > 65.0:
            lifecycle_state = 'At_Risk_Stagnant'
        elif status == 'Occupied' and sfr < 0.35:
            lifecycle_state = 'Active_Production'
        else:
            lifecycle_state = 'Stable_Mature'

        decay_records.append((
            p_id, fei, lif, sam, sfr, mpsp, is_pencil, is_truck_choked,
            decay_score, lifecycle_state
        ))

    cursor.executemany("""
        INSERT OR REPLACE INTO plot_decay_metrics (
            plot_id, frontage_efficiency_index, logistical_ingress_factor,
            speculation_arbitrage_multiple, stranded_footprint_ratio,
            micro_pollution_shadow, is_pencil_plot, is_truck_choked,
            decay_vulnerability_score, lifecycle_state
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, decay_records)

    conn.commit()


def get_plot_valuation_waterfall(conn, plot_id):
    """
    Deconstructs price formation from official GIDC base allotment rate to
    net appraised fair market value taking all decay/obsolescence penalties into account.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.allotment_price_sqm,
            p.road_width_m,
            p.is_corner_plot,
            p.frontage_m,
            p.plot_area_sqm,
            ip.current_cepi_score,
            ip.has_moratorium,
            dm.logistical_ingress_factor,
            dm.frontage_efficiency_index,
            dm.decay_vulnerability_score,
            oa.freight_curfew_hours_per_day
        FROM industrial_plots p
        JOIN industrial_parks ip ON p.park_id = ip.park_id
        JOIN plot_decay_metrics dm ON p.plot_id = dm.plot_id
        JOIN estate_obsolescence_audit oa ON p.park_id = oa.park_id
        WHERE p.plot_id = ?
    """, (plot_id,))
    row = cursor.fetchone()
    if not row:
        return None

    (base_price, road_w, is_corner, frontage, area, cepi, morat,
     lif, fei, decay_score, curfew) = row

    base_price = float(base_price or 3500.0)
    is_corner = bool(is_corner)
    cepi = float(cepi or 48.0)
    morat = int(morat or 0)
    lif = float(lif or 1.1)
    fei = float(fei or 0.7)
    curfew = int(curfew or 0)

    # 1. Corner Frontage Premium
    corner_pct = 12.0 if is_corner else 0.0
    corner_val = round(base_price * (corner_pct / 100.0), 1)

    # 2. Wide Road / Highway Arterial Ingress Premium
    if lif >= 1.5:
        road_prem_pct = 15.0
    elif lif >= 1.0:
        road_prem_pct = 5.0
    else:
        road_prem_pct = 0.0
    road_prem_val = round(base_price * (road_prem_pct / 100.0), 1)

    # 3. Logistical Choke / Road Narrowness Drag (Negative)
    if lif < 0.65:
        choke_pct = -18.0
    elif lif < 0.85:
        choke_pct = -8.0
    else:
        choke_pct = 0.0
    choke_val = round(base_price * (choke_pct / 100.0), 1)

    # 4. Environmental Pollution Drag (Removed / Neutralized from computation)
    cepi_pct = 0.0
    cepi_val = 0.0

    # 5. Urban Encroachment & Daytime Freight Curfew Penalty (Negative)
    if curfew >= 10:
        curfew_pct = -12.0
    elif curfew >= 6:
        curfew_pct = -6.0
    else:
        curfew_pct = 0.0
    curfew_val = round(base_price * (curfew_pct / 100.0), 1)

    # 6. Pencil Plot / Deep Narrow Geometry Drag (Negative)
    if fei < 0.50:
        shape_pct = -10.0
    else:
        shape_pct = 0.0
    shape_val = round(base_price * (shape_pct / 100.0), 1)

    # Net Fair Value Calculation (Pollution penalty excluded from computation)
    net_val = round(base_price + corner_val + road_prem_val + choke_val + curfew_val + shape_val, 1)
    net_val = max(500.0, net_val)
    net_diff_pct = round(((net_val - base_price) / base_price) * 100.0, 1)

    waterfall_steps = [
        {"step_name": "1. GIDC Statutory Base Allotment Rate", "amount": base_price, "type": "base", "pct": 0.0},
        {"step_name": "2. Corner Lot Visibility Premium", "amount": corner_val, "type": "positive" if corner_val > 0 else "neutral", "pct": corner_pct},
        {"step_name": "3. Multilane Freight Arterial Ingress", "amount": road_prem_val, "type": "positive" if road_prem_val > 0 else "neutral", "pct": road_prem_pct},
        {"step_name": "4. Logistical Choke (<12m Road) Drag", "amount": choke_val, "type": "negative" if choke_val < 0 else "neutral", "pct": choke_pct},
        {"step_name": "5. Environmental Drag (Neutralized)", "amount": 0.0, "type": "neutral", "pct": 0.0},
        {"step_name": "6. Urban Daytime Freight Curfew Penalty", "amount": curfew_val, "type": "negative" if curfew_val < 0 else "neutral", "pct": curfew_pct},
        {"step_name": "7. Inefficient Pencil Plot Aspect Drag", "amount": shape_val, "type": "negative" if shape_val < 0 else "neutral", "pct": shape_pct},
        {"step_name": "8. Net Appraised Fair Market Value", "amount": net_val, "type": "total", "pct": net_diff_pct}
    ]

    return {
        "plot_id": plot_id,
        "base_allotment_price": base_price,
        "base_gidc_price_sqm": base_price,
        "net_appraised_fair_value": net_val,
        "net_model_fair_value_sqm": net_val,
        "net_diff_pct": net_diff_pct,
        "road_width_premium_sqm": road_prem_val,
        "corner_premium_sqm": corner_val,
        "distance_decay_drag_sqm": abs(shape_val),
        "truck_choke_penalty_sqm": abs(choke_val),
        "cepi_pollution_discount_sqm": abs(cepi_val),
        "urban_curfew_discount_sqm": abs(curfew_val),
        "waterfall_steps": waterfall_steps
    }


def get_estate_decay_profile(conn, park_id):
    """
    Returns estate-level obsolescence metrics (EDI, BMR, UFQ, CETP strain),
    internal distance decay spline, and phase-plane coordinates for all 312 estates.
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            oa.park_id,
            ip.park_name,
            d.district_name,
            t.taluka_name,
            ip.current_cepi_score,
            ip.has_moratorium,
            oa.estate_decay_index,
            oa.brownfield_morbidity_ratio,
            oa.urban_friction_quotient,
            oa.cetp_hydraulic_strain_ratio,
            oa.freight_curfew_hours_per_day,
            oa.obsolescence_stage,
            ip.total_area_acres,
            ip.notification_year
        FROM estate_obsolescence_audit oa
        JOIN industrial_parks ip ON oa.park_id = ip.park_id
        JOIN subdistricts_talukas t ON ip.taluka_id = t.taluka_id
        JOIN districts d ON t.district_id = d.district_id
        WHERE oa.park_id = ?
    """, (park_id,))
    row = cursor.fetchone()
    if not row:
        return None

    (pid, name, dist, taluka, cepi, morat, edi, bmr, ufq, cetp_strain,
     curfew, stage, acres, n_year) = row

    # Generate in-estate distance decay spline (Gate to Cul-de-Sac distance vs price realization)
    # In pristine estates, internal price is flat; in decaying estates (high EDI), interior drops by 45%
    internal_decay_curve = []
    base_gate_price = 4500.0 if edi < 50 else 3200.0
    decay_rate = 0.05 if edi < 35.0 else (0.25 if edi < 65.0 else 0.50)

    for dist_m in [0, 150, 300, 500, 750, 1000, 1300, 1600, 2000]:
        drop = (dist_m / 2000.0) * decay_rate * base_gate_price
        realized = round(max(1200.0, base_gate_price - drop), 1)
        internal_decay_curve.append({
            "distance_from_gate_m": dist_m,
            "realized_price_sqm": realized
        })

    # Phase plane comparison for Gujarat estates
    cursor.execute("""
        SELECT 
            oa.park_id,
            ip.park_name,
            oa.estate_decay_index,
            oa.brownfield_morbidity_ratio,
            oa.obsolescence_stage
        FROM estate_obsolescence_audit oa
        JOIN industrial_parks ip ON oa.park_id = ip.park_id
        LIMIT 40
    """)
    comparison_estates = []
    for comp in cursor.fetchall():
        comparison_estates.append({
            "park_id": comp[0],
            "park_name": comp[1],
            "edi": comp[2],
            "bmr_pct": round(comp[3] * 100.0, 1),
            "stage": comp[4],
            "is_selected": comp[0] == park_id
        })

    return {
        "park_id": pid,
        "park_name": name,
        "district": dist,
        "taluka": taluka,
        "cepi_score": cepi,
        "has_moratorium": bool(morat),
        "estate_decay_index": edi,
        "brownfield_morbidity_ratio": bmr,
        "brownfield_morbidity_ratio_pct": round(bmr * 100.0, 1),
        "urban_friction_quotient": ufq,
        "cetp_hydraulic_strain_ratio": cetp_strain,
        "freight_curfew_hours_per_day": curfew,
        "obsolescence_stage": stage,
        "internal_distance_decay": internal_decay_curve,
        "internal_decay_curve": internal_decay_curve,
        "comparison_estates": comparison_estates
    }
