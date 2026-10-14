from database import get_db, query_db, execute_db

def get_all_districts():
    """Returns districts with count of industrial parks."""
    return query_db("""
        SELECT 
            d.district_id,
            d.district_name,
            COUNT(ip.park_id) AS park_count
        FROM districts d
        LEFT JOIN subdistricts_talukas st ON d.district_id = st.district_id
        LEFT JOIN industrial_parks ip ON st.taluka_id = ip.taluka_id
        GROUP BY d.district_id, d.district_name
        ORDER BY d.district_name ASC
    """)

def get_parks(district=None, category=None, search=None, limit=None, offset=None):
    """Retrieves industrial parks with flexible filtering."""
    query = """
        SELECT 
            ip.park_id,
            ip.park_name,
            ip.authority_type,
            ip.sector_category,
            ip.total_area_acres,
            ip.planning_type,
            ip.notification_year,
            ip.has_cetp,
            ip.latitude,
            ip.longitude,
            ip.address,
            ip.phone,
            ip.email,
            ip.notes,
            ip.source,
            d.district_name,
            st.taluka_name,
            (SELECT COUNT(*) FROM anchor_facilities af WHERE af.park_id = ip.park_id) AS anchor_count
        FROM industrial_parks ip
        JOIN subdistricts_talukas st ON ip.taluka_id = st.taluka_id
        JOIN districts d ON st.district_id = d.district_id
        WHERE 1=1
    """
    params = []
    if district and district != 'ALL':
        query += " AND d.district_name = ?"
        params.append(district)
    if category and category != 'ALL':
        if category == 'GIDC':
            query += " AND ip.authority_type = 'GIDC'"
        elif category == 'Private':
            query += " AND ip.authority_type = 'Private SEZ/Park'"
        else:
            query += " AND ip.sector_category LIKE ?"
            params.append(f"%{category}%")
    if search:
        query += " AND (ip.park_name LIKE ? OR ip.address LIKE ? OR st.taluka_name LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
        
    query += " ORDER BY ip.park_name ASC"
    
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)
        if offset is not None:
            query += " OFFSET ?"
            params.append(offset)
            
    return query_db(query, params)

def get_park_by_id(park_id):
    """Retrieves full profile for a single industrial park."""
    return query_db("""
        SELECT 
            ip.*,
            d.district_name,
            st.taluka_name
        FROM industrial_parks ip
        JOIN subdistricts_talukas st ON ip.taluka_id = st.taluka_id
        JOIN districts d ON st.district_id = d.district_id
        WHERE ip.park_id = ?
    """, (park_id,), one=True)

def get_park_anchors(park_id):
    """Retrieves anchor manufacturing tenants for a park."""
    return query_db("""
        SELECT * FROM anchor_facilities WHERE park_id = ? ORDER BY proposed_investment_inr DESC
    """, (park_id,))

def get_park_lifecycle_events(park_id):
    """Retrieves chronological lifecycle events for a park."""
    return query_db("""
        SELECT * FROM park_lifecycle_events WHERE park_id = ? ORDER BY event_year ASC, event_date ASC
    """, (park_id,))

def get_park_annual_metrics(park_id):
    """Retrieves annual operational density and pollution metrics."""
    return query_db("""
        SELECT * FROM park_annual_metrics WHERE park_id = ? ORDER BY assessment_year ASC
    """, (park_id,))

def get_clean_commercial_nodes():
    """Retrieves clean commercial comparison baseline nodes."""
    return query_db("""
        SELECT 
            cn.*,
            st.taluka_name,
            d.district_name
        FROM clean_commercial_nodes cn
        JOIN subdistricts_talukas st ON cn.taluka_id = st.taluka_id
        JOIN districts d ON st.district_id = d.district_id
        ORDER BY cn.establishment_year ASC
    """)

def get_transactions_paginated(page=1, per_page=25, buffer_bin=None, property_type=None, year=None, search=None):
    """Returns paginated property transactions with joins."""
    where_clauses = ["1=1"]
    params = []
    
    if buffer_bin and buffer_bin != 'ALL':
        where_clauses.append("p.distance_buffer_bin = ?")
        params.append(buffer_bin)
    if property_type and property_type != 'ALL':
        where_clauses.append("p.property_type = ?")
        params.append(property_type)
    if year and year != 'ALL':
        where_clauses.append("pt.sale_year = ?")
        params.append(int(year))
    if search:
        where_clauses.append("(ip.park_name LIKE ? OR nj.neighborhood_name LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s])
        
    where_sql = " AND ".join(where_clauses)
    
    # Total count
    count_row = query_db(f"""
        SELECT COUNT(*) AS total
        FROM property_transactions pt
        JOIN properties p ON pt.property_id = p.property_id
        JOIN industrial_parks ip ON p.nearest_park_id = ip.park_id
        JOIN neighborhoods_jurisdictions nj ON p.neighborhood_id = nj.neighborhood_id
        WHERE {where_sql}
    """, params, one=True)
    total_count = count_row['total'] if count_row else 0
    
    # Paginated data
    offset = (page - 1) * per_page
    query = f"""
        SELECT 
            pt.transaction_id,
            pt.sale_date,
            pt.sale_year,
            pt.sale_quarter,
            pt.market_transaction_price,
            pt.price_per_sqm,
            pt.registered_circle_rate_sqm,
            pt.circle_to_market_ratio,
            p.property_id,
            p.property_type,
            p.built_up_area_sqm,
            p.distance_buffer_bin,
            p.distance_to_park_km,
            p.distance_to_highway_km,
            ip.park_name,
            nj.neighborhood_name,
            did.treatment_group,
            did.lifecycle_phase_at_sale,
            did.is_post_event
        FROM property_transactions pt
        JOIN properties p ON pt.property_id = p.property_id
        JOIN industrial_parks ip ON p.nearest_park_id = ip.park_id
        JOIN neighborhoods_jurisdictions nj ON p.neighborhood_id = nj.neighborhood_id
        LEFT JOIN did_panel_designations did ON pt.transaction_id = did.transaction_id
        WHERE {where_sql}
        ORDER BY pt.sale_date DESC
        LIMIT ? OFFSET ?
    """
    params.extend([per_page, offset])
    rows = query_db(query, params)
    
    total_pages = (total_count + per_page - 1) // per_page
    
    return {
        'records': rows,
        'page': page,
        'per_page': per_page,
        'total': total_count,
        'total_pages': max(1, total_pages)
    }

def add_new_transaction(property_id, sale_date, market_price, circle_rate):
    """Inserts a new property transaction into the database."""
    prop = query_db("SELECT built_up_area_sqm, distance_buffer_bin FROM properties WHERE property_id = ?", (property_id,), one=True)
    if not prop:
        return None
        
    area = prop['built_up_area_sqm']
    price_per_sqm = round(market_price / area, 2)
    ratio = round(circle_rate / price_per_sqm, 3)
    year = int(sale_date.split('-')[0])
    month = int(sale_date.split('-')[1])
    quarter = (month - 1) // 3 + 1
    
    tx_id = execute_db("""
        INSERT INTO property_transactions (
            property_id, sale_date, sale_year, sale_quarter,
            market_transaction_price, price_per_sqm, registered_circle_rate_sqm,
            circle_to_market_ratio, is_repeat_sale, is_arms_length
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
    """, (property_id, sale_date, year, quarter, market_price, price_per_sqm, circle_rate, ratio))
    
    buf = prop['distance_buffer_bin']
    is_treated = 0 if 'Control' in buf else 1
    is_post = 1 if year >= 2018 else 0
    phase = "Phase_3_Active_Ancillary" if year >= 2021 else ("Phase_2_Anchor_Commissioned" if year >= 2018 else "Phase_1_Announcement")
    
    execute_db("""
        INSERT INTO did_panel_designations (
            transaction_id, treatment_group, lifecycle_phase_at_sale,
            is_treated, is_post_event, did_interaction_term, years_since_event
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (tx_id, buf, phase, is_treated, is_post, is_treated * is_post, year - 2018))
    
    return tx_id
