import os
import json
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, Response
from config import Config
from database import get_db, close_db, query_db
from models import (
    get_all_districts,
    get_parks,
    get_park_by_id,
    get_park_anchors,
    get_park_lifecycle_events,
    get_park_annual_metrics,
    get_clean_commercial_nodes,
    get_transactions_paginated,
    add_new_transaction
)
from did_engine import run_did_regression, get_kpi_summary
from exporters import (
    export_dashboard_data,
    export_econometrics_data,
    export_parks_data,
    export_park_dossier,
    export_transactions_data
)
from table_exporters import (
    TABLE_REGISTRY,
    get_all_tables_info,
    generate_table_csv,
    generate_all_tables_zip
)
from replication_suite import (
    get_citations,
    generate_stata_dofile,
    generate_python_replication_script,
    generate_kml_export,
    get_table_schema_detail
)
from pollution_benchmarks import (
    get_pollution_kpis,
    get_filtered_pollution_benchmarks,
    get_single_park_pollution_history,
    get_pollution_vs_property_drag_data,
    seed_pollution_benchmarks
)
from land_intelligence import (
    get_historical_pricing_kpis,
    get_single_park_pricing_history,
    get_benchmark_comparison_series,
    get_plot_inventory_kpis,
    get_filtered_plots,
    get_all_intelligence_sources,
    get_single_plot_traceability,
    seed_intelligence_pipeline
)
from provenance_system import (
    get_source_registry_summary,
    get_all_registered_sources,
    get_source_by_id,
    get_filtered_provenance_records,
    get_provenance_for_entity,
    get_provenance_for_field,
    verify_source_integrity,
    get_source_version_history,
    seed_source_archive_and_registry,
    seed_data_provenance
)
from econometric_advanced import (
    compute_event_study_coefficients,
    compute_counterfactual_trajectories,
    compute_distance_decay_and_binscatter,
    compute_market_to_circle_rate_heat_matrix,
    compute_lifecycle_phase_distributions,
    compute_spatial_hexbin_and_kde,
    generate_stata_code,
    generate_ggplot2_code,
    run_empirical_gidc_did_regression,
    compute_empirical_event_study,
    compute_empirical_counterfactual,
    compute_empirical_corridor_decay_and_binscatter,
    generate_empirical_stata_code,
    generate_empirical_ggplot2_code
)
from plot_cadastral_engine import (
    get_plot_micro_intelligence,
    search_plots_autocomplete,
    get_estate_parcel_features,
    export_plot_boundary_cad
)
from plot_decay_engine import (
    get_plot_valuation_waterfall,
    get_estate_decay_profile,
    seed_plot_decay_data
)

app = Flask(__name__)
app.config.from_object(Config)

# Register database teardown
app.teardown_appcontext(close_db)

# Ensure Task T5 Source Archive and Data Provenance tables are seeded
with app.app_context():
    try:
        seed_source_archive_and_registry()
        seed_data_provenance()
        seed_plot_decay_data(get_db())
    except Exception as e:
        print(f"Provenance/Decay initialization note: {e}")

# Context processor for template globals
@app.context_processor
def inject_globals():
    return {
        'min': min,
        'max': max
    }

# -----------------------------------------------------------------------------
# Web Views
# -----------------------------------------------------------------------------

@app.route('/')
def dashboard():
    """Main executive dashboard view."""
    conn = get_db()
    kpis = get_kpi_summary(conn)
    
    # Baseline DiD Regression for Charts
    did_results = run_did_regression(conn, post_year=2018)
    
    # Flagship anchors for dashboard
    flagship_anchors = query_db("""
        SELECT 
            af.*,
            ip.park_name,
            d.district_name
        FROM anchor_facilities af
        JOIN industrial_parks ip ON af.park_id = ip.park_id
        JOIN subdistricts_talukas st ON ip.taluka_id = st.taluka_id
        JOIN districts d ON st.district_id = d.district_id
        ORDER BY af.proposed_investment_inr DESC
        LIMIT 6
    """)
    
    # Recent transactions
    recent_transactions = query_db("""
        SELECT 
            pt.*,
            p.property_type,
            p.distance_buffer_bin,
            p.distance_to_park_km,
            ip.park_name,
            did.lifecycle_phase_at_sale
        FROM property_transactions pt
        JOIN properties p ON pt.property_id = p.property_id
        JOIN industrial_parks ip ON p.nearest_park_id = ip.park_id
        LEFT JOIN did_panel_designations did ON pt.transaction_id = did.transaction_id
        ORDER BY pt.sale_date DESC
        LIMIT 6
    """)

    return render_template(
        'dashboard.html',
        kpis=kpis,
        chart_trajectories=did_results['trajectories'],
        chart_bar_data=did_results['bar_data'],
        chart_ratio_data=did_results['ratios'],
        flagship_anchors=flagship_anchors,
        recent_transactions=recent_transactions
    )

@app.route('/map')
def spatial_map_view():
    """Interactive Leaflet GIS map of all 312 Gujarat industrial parks."""
    districts = get_all_districts()
    parks = get_parks()
    
    # Convert parks to lightweight dict list for JS embedding
    parks_json = []
    for p in parks:
        parks_json.append({
            'park_id': p['park_id'],
            'park_name': p['park_name'],
            'district_name': p['district_name'],
            'taluka_name': p['taluka_name'],
            'authority_type': p['authority_type'],
            'sector_category': p['sector_category'],
            'total_area_acres': p['total_area_acres'],
            'notification_year': p['notification_year'],
            'has_cetp': p['has_cetp'],
            'latitude': p['latitude'],
            'longitude': p['longitude'],
            'address': p['address'],
            'phone': p['phone'],
            'email': p['email']
        })
        
    key_hubs = query_db("""
        SELECT 
            ip.park_id, ip.park_name, ip.latitude, ip.longitude, 
            ip.sector_category, d.district_name
        FROM industrial_parks ip
        JOIN subdistricts_talukas st ON ip.taluka_id = st.taluka_id
        JOIN districts d ON st.district_id = d.district_id
        WHERE ip.park_name LIKE '%Sanand%' 
           OR ip.park_name LIKE '%Dahej%' 
           OR ip.park_name LIKE '%Ankleshwar%' 
           OR ip.park_name LIKE '%Hazira%' 
           OR ip.park_name LIKE '%Halol%'
           OR ip.park_name LIKE '%Mandal%'
           OR ip.park_name LIKE '%Vapi%'
        GROUP BY ip.park_name
        LIMIT 6
    """)

    return render_template(
        'map.html',
        districts=districts,
        parks=parks,
        parks_json=parks_json,
        key_hubs=key_hubs
    )

@app.route('/econometrics')
def econometrics_view():
    """
    Difference-in-Differences Econometric Studio.
    Supports Dual-Mode Switcher:
    - Mode 1: 'empirical' (Official GIDC Statutory Land Price Panel: 8,448 observations across 312 estates)
    - Mode 2: 'synthetic' (Surrounding Micro-Transactions Simulation Panel: 4,000 transactions)
    """
    conn = get_db()
    data_mode = request.args.get('data_mode', 'empirical')
    
    if data_mode == 'empirical':
        policy_shock = request.args.get('policy_shock', 'anchor')
        post_year = int(request.args.get('post_year', 2008))
        sector_filter = request.args.get('sector_filter', 'ALL')
        
        did_results = run_empirical_gidc_did_regression(
            conn,
            policy_shock=policy_shock,
            post_year=post_year,
            sector_filter=sector_filter
        )
        if not did_results:
            did_results = run_empirical_gidc_did_regression(conn, policy_shock='anchor', post_year=2008)
            
        event_study_data = compute_empirical_event_study(conn, policy_shock=policy_shock, post_year=post_year, sector_filter=sector_filter)
        counterfactual_data = compute_empirical_counterfactual(conn, policy_shock=policy_shock, post_year=post_year, sector_filter=sector_filter)
        decay_binscatter_data = compute_empirical_corridor_decay_and_binscatter(conn)
        stata_code = generate_empirical_stata_code(post_year=post_year, policy_shock=policy_shock)
        ggplot2_code = generate_empirical_ggplot2_code(post_year=post_year, policy_shock=policy_shock)
        
        property_type = 'ALL'
        buffer_filter = 'ALL'
    else:
        # Mode 2: Synthetic transaction panel preserved intact for later research
        post_year = int(request.args.get('post_year', 2018))
        property_type = request.args.get('property_type', 'ALL')
        buffer_filter = request.args.get('buffer_filter', 'ALL')
        policy_shock = 'buffer_contrast'
        sector_filter = 'ALL'
        
        did_results = run_did_regression(
            conn,
            post_year=post_year,
            property_type=property_type,
            buffer_filter=buffer_filter
        )
        if not did_results:
            flash("Not enough observations to estimate regression for the selected filter combination.", "warning")
            did_results = run_did_regression(conn, post_year=2018)

        event_study_data = compute_event_study_coefficients(conn, anchor_year=post_year)
        counterfactual_data = compute_counterfactual_trajectories(conn, anchor_year=post_year)
        decay_binscatter_data = compute_distance_decay_and_binscatter(conn)
        stata_code = generate_stata_code(post_year=post_year)
        ggplot2_code = generate_ggplot2_code(post_year=post_year)

    # Cross-sectional tables shared across both modes
    heat_matrix_data = compute_market_to_circle_rate_heat_matrix(conn)
    lifecycle_dist_data = compute_lifecycle_phase_distributions(conn)
    spatial_hexbins = compute_spatial_hexbin_and_kde(conn)

    return render_template(
        'econometrics.html',
        data_mode=data_mode,
        policy_shock=policy_shock,
        sector_filter=sector_filter,
        did_results=did_results,
        chart_trajectories=did_results['trajectories'],
        chart_bar_data=did_results['bar_data'],
        post_year=post_year,
        property_type=property_type,
        buffer_filter=buffer_filter,
        event_study_data=event_study_data,
        counterfactual_data=counterfactual_data,
        decay_binscatter_data=decay_binscatter_data,
        heat_matrix_data=heat_matrix_data,
        lifecycle_dist_data=lifecycle_dist_data,
        spatial_hexbins=spatial_hexbins,
        stata_code=stata_code,
        ggplot2_code=ggplot2_code
    )

@app.route('/parks')
def parks_list():
    """Directory of all 312 Gujarat industrial parks."""
    district = request.args.get('district', 'ALL')
    category = request.args.get('category', 'ALL')
    search = request.args.get('search', '').strip()
    
    districts = get_all_districts()
    parks = get_parks(district=district, category=category, search=search)
    
    return render_template(
        'parks.html',
        districts=districts,
        parks=parks,
        selected_district=district,
        selected_category=category,
        search_query=search
    )

@app.route('/parks/<int:park_id>')
def park_detail(park_id):
    """Detailed profile of a single industrial park with spatial buffers and timeline."""
    park = get_park_by_id(park_id)
    if not park:
        flash("Industrial park not found.", "error")
        return redirect(url_for('parks_list'))
        
    anchors = get_park_anchors(park_id)
    events = get_park_lifecycle_events(park_id)
    metrics = get_park_annual_metrics(park_id)
    
    return render_template(
        'park_detail.html',
        park=park,
        anchors=anchors,
        events=events,
        metrics=metrics
    )

@app.route('/transactions')
def transactions_view():
    """Property transactions panel explorer with pagination and filters."""
    page = int(request.args.get('page', 1))
    buffer_bin = request.args.get('buffer_bin', 'ALL')
    property_type = request.args.get('property_type', 'ALL')
    year = request.args.get('year', 'ALL')
    search = request.args.get('search', '').strip()
    
    data = get_transactions_paginated(
        page=page,
        per_page=Config.ITEMS_PER_PAGE,
        buffer_bin=buffer_bin,
        property_type=property_type,
        year=year,
        search=search
    )
    
    # Sample properties for new transaction modal
    sample_properties = query_db("""
        SELECT property_id, property_type, distance_buffer_bin, built_up_area_sqm
        FROM properties
        ORDER BY property_id ASC
        LIMIT 20
    """)
    
    return render_template(
        'transactions.html',
        data=data,
        selected_buffer=buffer_bin,
        selected_type=property_type,
        selected_year=year,
        search_query=search,
        sample_properties=sample_properties
    )

@app.route('/transactions/new', methods=['POST'])
def new_transaction_action():
    """Action to insert a new property transaction."""
    property_id = int(request.form.get('property_id'))
    sale_date = request.form.get('sale_date')
    market_price = float(request.form.get('market_price'))
    circle_rate = float(request.form.get('circle_rate'))
    
    tx_id = add_new_transaction(property_id, sale_date, market_price, circle_rate)
    if tx_id:
        flash(f"Transaction #{tx_id} successfully recorded into the SQLite panel dataset!", "success")
    else:
        flash("Failed to record transaction. Invalid property parcel ID.", "error")
        
    return redirect(url_for('transactions_view'))

@app.route('/methodology')
def methodology_view():
    """Methodology, econometric formulation, and database schema documentation."""
    return render_template('methodology.html')

@app.route('/pollution-benchmark')
def pollution_benchmark_view():
    """
    Dedicated view for Benchmarking Pollution Figures across industrial entities 
    to identify lifecycle stages and real estate proximity drag.
    Covers:
      1. Aggregate CEPI Index (Air, Water, Land, Overall, CPCB Status: CPA/SPA/Normal)
      2. Ambient Air Quality (PM2.5, PM10, SO2, NOx)
      3. Water & CETP Effluent metrics (Inlet/Outlet COD, BOD, TDS, ZLD status)
      4. Factory Composition (% Red, % Orange, % Green, % White)
    """
    selected_district = request.args.get('district', 'ALL')
    selected_status = request.args.get('status', 'ALL')
    selected_stage = request.args.get('stage', 'ALL')
    selected_year = int(request.args.get('year', 2024))
    search = request.args.get('search', '').strip()
    
    kpis = get_pollution_kpis(selected_year)
    districts = get_all_districts()
    benchmarks = get_filtered_pollution_benchmarks(
        district=selected_district,
        cpcb_status=selected_status,
        stage=selected_stage,
        search=search,
        year=selected_year,
        limit=312
    )
    scatter_data = get_pollution_vs_property_drag_data()
    
    return render_template(
        'pollution_benchmark.html',
        kpis=kpis,
        districts=districts,
        benchmarks=benchmarks,
        scatter_data=scatter_data,
        selected_district=selected_district,
        selected_status=selected_status,
        selected_stage=selected_stage,
        selected_year=selected_year,
        search_query=search
    )

@app.route('/land-pricing-history')
def land_pricing_history_view():
    """
    Task T3: Historical Land Pricing Archive & Trajectory Explorer (2000–2026/27).
    Reconstructs formal GIDC circular allotment price revisions, auction rates,
    annual percentage changes, and 26-year CAGR.
    """
    parks = get_parks()
    default_park_id = parks[0]['park_id'] if parks else 1
    selected_park_id = int(request.args.get('park_id', default_park_id))
    
    kpis = get_historical_pricing_kpis()
    single_park = get_single_park_pricing_history(selected_park_id)
    comparison_series = get_benchmark_comparison_series()
    
    return render_template(
        'land_pricing_history.html',
        kpis=kpis,
        parks=parks,
        single_park=single_park,
        comparison_series=comparison_series,
        selected_park_id=selected_park_id
    )

@app.route('/data')
@app.route('/plot-intelligence')
def plot_intelligence_view():
    """
    Task T4: Industrial Plot Intelligence, Allocation Roster & Fine-Grain Traceability.
    Enables multi-parameter commercial query on plot availability, road widths,
    corner plot premiums, and MSME allocations with verified statutory provenance.
    """
    parks = get_parks()
    sources = get_all_intelligence_sources()
    selected_park_id = request.args.get('park_id', 'ALL')
    selected_status = request.args.get('status', 'ALL')
    selected_category = request.args.get('category', 'ALL')
    selected_source_id = request.args.get('source_id', 'ALL')
    selected_tier = request.args.get('tier', 'ALL')
    min_area = request.args.get('min_area', '')
    max_area = request.args.get('max_area', '')
    max_price = request.args.get('max_price', '')
    search = request.args.get('search', '').strip()
    
    kpis = get_plot_inventory_kpis()
    plots = get_filtered_plots(
        park_id=selected_park_id,
        status=selected_status,
        min_area=float(min_area) if min_area else None,
        max_area=float(max_area) if max_area else None,
        max_price=float(max_price) if max_price else None,
        category=selected_category,
        search=search,
        source_id=selected_source_id,
        tier=selected_tier,
        limit=200
    )
    
    conn = get_db()
    req_plot_id = request.args.get('plot_id', '')
    if req_plot_id:
        initial_plot_id = req_plot_id
    elif plots:
        initial_plot_id = plots[0]['plot_id']
    else:
        initial_plot_id = 'PLOT-001-001'

    initial_plot_intel = get_plot_micro_intelligence(conn, initial_plot_id)
    initial_park_id = initial_plot_intel['park_id'] if initial_plot_intel else (selected_park_id if selected_park_id != 'ALL' else 1)
    initial_estate_geojson = get_estate_parcel_features(conn, initial_park_id)

    return render_template(
        'plot_intelligence.html',
        kpis=kpis,
        parks=parks,
        sources=sources,
        plots=plots,
        selected_park_id=selected_park_id,
        selected_status=selected_status,
        selected_category=selected_category,
        selected_source_id=selected_source_id,
        selected_tier=selected_tier,
        selected_min_area=min_area,
        selected_max_area=max_area,
        selected_max_price=max_price,
        search_query=search,
        initial_plot=initial_plot_intel,
        initial_geojson=initial_estate_geojson
    )

# -----------------------------------------------------------------------------
# Task T5: Central Source Registry & Data Provenance Views
# -----------------------------------------------------------------------------

@app.route('/provenance')
@app.route('/sources')
def provenance_view():
    """
    Task T5: Source Archiving, Central Source Registry & Value-Level Data Provenance.
    Enables auditable inspection of all statutory source documents, local preserved files,
    file hashes, and exact value-level evidence (document, page, table, row, excerpt).
    """
    selected_org = request.args.get('org', 'ALL')
    selected_type = request.args.get('type', 'ALL')
    selected_status = request.args.get('status', 'ALL')
    selected_entity = request.args.get('entity_type', 'ALL')
    selected_source_id = request.args.get('source_id', 'ALL')
    search = request.args.get('search', '').strip()
    
    summary = get_source_registry_summary()
    sources = get_all_registered_sources(
        organisation=selected_org,
        source_type=selected_type,
        status=selected_status,
        search=search
    )
    provenance_records = get_filtered_provenance_records(
        entity_type=selected_entity,
        source_id=selected_source_id,
        search=search,
        limit=100
    )
    version_history = get_source_version_history()
    
    return render_template(
        'provenance.html',
        summary=summary,
        sources=sources,
        provenance_records=provenance_records,
        version_history=version_history,
        selected_org=selected_org,
        selected_type=selected_type,
        selected_status=selected_status,
        selected_entity=selected_entity,
        selected_source_id=selected_source_id,
        search_query=search
    )

@app.route('/sources/view/<source_id>')
def view_source_file_endpoint(source_id):
    """
    Serves the locally archived source file directly in browser
    (PDF / text / CSV / HTML).
    """
    source = get_source_by_id(source_id)
    if not source:
        flash(f"Source '{source_id}' not found.", "error")
        return redirect(url_for('provenance_view'))
        
    if source["source_status"] == "unavailable":
        flash(f"Source '{source_id}' is restricted or unavailable: {source.get('failure_reason')}", "warning")
        return redirect(url_for('provenance_view'))
        
    abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), source["local_path"])
    if not os.path.exists(abs_path):
        flash(f"Archived file not found on disk at {source['local_path']}.", "error")
        return redirect(url_for('provenance_view'))
        
    # Determine mimetype
    mime = "application/pdf"
    if source["local_filename"].endswith(".csv"):
        mime = "text/csv"
    elif source["local_filename"].endswith(".html"):
        mime = "text/html"
    elif source["local_filename"].endswith(".txt"):
        mime = "text/plain"
        
    return send_file(abs_path, mimetype=mime, as_attachment=False, download_name=source["local_filename"])

@app.route('/sources/download/<source_id>')
def download_source_file_endpoint(source_id):
    """Downloads the locally preserved source archive file."""
    source = get_source_by_id(source_id)
    if not source or source["source_status"] == "unavailable":
        flash(f"Source '{source_id}' cannot be downloaded.", "error")
        return redirect(url_for('provenance_view'))
        
    abs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), source["local_path"])
    if not os.path.exists(abs_path):
        flash(f"Archived file not found on disk at {source['local_path']}.", "error")
        return redirect(url_for('provenance_view'))
        
    return send_file(abs_path, as_attachment=True, download_name=source["local_filename"])

@app.route('/sources/metadata/<source_id>')
def source_metadata_json_endpoint(source_id):
    """Returns raw metadata.json for the archived source."""
    source = get_source_by_id(source_id)
    if not source:
        return jsonify({"error": f"Source '{source_id}' not found."}), 404
    return jsonify(source)

# -----------------------------------------------------------------------------
# RESTful API Endpoints
# -----------------------------------------------------------------------------

@app.route('/api/stats')
def api_stats():
    """Returns top-level KPIs in JSON."""
    conn = get_db()
    return jsonify(get_kpi_summary(conn))

@app.route('/api/parks')
def api_parks():
    """Returns JSON list of parks with coordinates and filters."""
    district = request.args.get('district')
    category = request.args.get('category')
    search = request.args.get('search')
    parks = get_parks(district=district, category=category, search=search)
    return jsonify([dict(p) for p in parks])

@app.route('/api/districts')
def api_districts():
    """Returns list of districts with park counts."""
    districts = get_all_districts()
    return jsonify([dict(d) for d in districts])

@app.route('/api/did-analysis')
def api_did_analysis():
    """Computes DiD regression coefficients and chart series dynamically."""
    conn = get_db()
    post_year = int(request.args.get('post_year', 2018))
    property_type = request.args.get('property_type', 'ALL')
    buffer_filter = request.args.get('buffer_filter', 'ALL')
    
    res = run_did_regression(conn, post_year=post_year, property_type=property_type, buffer_filter=buffer_filter)
    if not res:
        return jsonify({'error': 'Insufficient data'}), 400
    return jsonify(res)

@app.route('/api/pollution-benchmarks')
def api_pollution_benchmarks():
    """Returns filtered pollution benchmarks in JSON."""
    district = request.args.get('district', 'ALL')
    status = request.args.get('status', 'ALL')
    stage = request.args.get('stage', 'ALL')
    year = int(request.args.get('year', 2024))
    search = request.args.get('search', '').strip()
    
    records = get_filtered_pollution_benchmarks(
        district=district,
        cpcb_status=status,
        stage=stage,
        search=search,
        year=year,
        limit=312
    )
    return jsonify([dict(r) for r in records])

@app.route('/api/pollution-drag')
def api_pollution_drag():
    """Returns CEPI vs Property Proximity Drag scatter plot data."""
    return jsonify(get_pollution_vs_property_drag_data())

@app.route('/api/pollution/park/<int:park_id>')
def api_pollution_park(park_id):
    """Returns multi-year pollution history for an individual industrial park."""
    data = get_single_park_pollution_history(park_id)
    if not data['park']:
        return jsonify({"error": f"Park ID {park_id} not found."}), 404
    return jsonify(data)

@app.route('/api/price-history/<int:park_id>')
def api_price_history_endpoint(park_id):
    """Task T3 API: Returns multi-year historical pricing, YoY revisions, and CAGR for an individual park."""
    data = get_single_park_pricing_history(park_id)
    if not data['park']:
        return jsonify({"error": f"Park ID {park_id} not found."}), 404
    return jsonify(data)

@app.route('/api/plot-intelligence')
def api_plot_intelligence_endpoint():
    """Task T4 API: Returns filtered plot records with cadastral dimensions, companies, and verified sources."""
    park_id = request.args.get('park_id', 'ALL')
    status = request.args.get('status', 'ALL')
    category = request.args.get('category', 'ALL')
    source_id = request.args.get('source_id', 'ALL')
    tier = request.args.get('tier', 'ALL')
    min_area = request.args.get('min_area')
    max_area = request.args.get('max_area')
    max_price = request.args.get('max_price')
    search = request.args.get('search', '').strip()
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    plots = get_filtered_plots(
        park_id=park_id,
        status=status,
        min_area=float(min_area) if min_area else None,
        max_area=float(max_area) if max_area else None,
        max_price=float(max_price) if max_price else None,
        category=category,
        search=search,
        source_id=source_id,
        tier=tier,
        limit=limit,
        offset=offset
    )
    return jsonify([dict(p) for p in plots])

@app.route('/api/plot-intelligence/<plot_id>/traceability')
def api_plot_traceability_endpoint(plot_id):
    """Returns fine-grained statutory provenance dossier and traceability audit data for a single plot."""
    plot = get_single_plot_traceability(plot_id)
    if not plot:
        return jsonify({"error": f"Plot '{plot_id}' not found."}), 404
    return jsonify(dict(plot))

@app.route('/api/plot-intelligence/kpis')
def api_plot_intelligence_kpis_endpoint():
    """Task T4 API: Returns plot inventory and valuation summary KPIs."""
    return jsonify(get_plot_inventory_kpis())

# -----------------------------------------------------------------------------
# Task T5: Central Source Registry & Data Provenance REST APIs
# -----------------------------------------------------------------------------

@app.route('/api/provenance/kpis')
def api_provenance_kpis_endpoint():
    """Returns provenance and source archive executive KPIs."""
    return jsonify(get_source_registry_summary())

@app.route('/api/provenance/sources')
def api_provenance_sources_endpoint():
    """Returns registered sources with optional filters."""
    org = request.args.get('org', 'ALL')
    stype = request.args.get('type', 'ALL')
    status = request.args.get('status', 'ALL')
    search = request.args.get('search', '').strip()
    sources = get_all_registered_sources(organisation=org, source_type=stype, status=status, search=search)
    return jsonify([dict(s) for s in sources])

@app.route('/api/provenance/source/<source_id>')
def api_provenance_source_detail_endpoint(source_id):
    """Returns single source details with local file status."""
    source = get_source_by_id(source_id)
    if not source:
        return jsonify({"error": f"Source '{source_id}' not found."}), 404
    return jsonify(source)

@app.route('/api/provenance/source/<source_id>/verify')
def api_provenance_source_verify_endpoint(source_id):
    """Cryptographically verifies file on disk against registered SHA-256 hash."""
    return jsonify(verify_source_integrity(source_id))

@app.route('/api/provenance/records')
def api_provenance_records_endpoint():
    """Returns value-level provenance records with search and pagination."""
    entity_type = request.args.get('entity_type', 'ALL')
    source_id = request.args.get('source_id', 'ALL')
    search = request.args.get('search', '').strip()
    limit = int(request.args.get('limit', 50))
    offset = int(request.args.get('offset', 0))
    records = get_filtered_provenance_records(entity_type=entity_type, source_id=source_id, search=search, limit=limit, offset=offset)
    return jsonify([dict(r) for r in records])

@app.route('/api/provenance/trace/<entity_type>/<entity_id>')
def api_provenance_entity_trace_endpoint(entity_type, entity_id):
    """Returns all value-level provenance and audit evidence for a single entity."""
    records = get_provenance_for_entity(entity_type, entity_id)
    return jsonify([dict(r) for r in records])

@app.route('/api/provenance/versions')
def api_provenance_versions_endpoint():
    """Returns timeline of historical source versions."""
    return jsonify(get_source_version_history())

# -----------------------------------------------------------------------------
# Data + Metadata Export Endpoints (Across All Stops)
# -----------------------------------------------------------------------------

@app.route('/export/dashboard')
def export_dashboard_endpoint():
    """Export executive KPI dataset + metadata (CSV or JSON)."""
    fmt = request.args.get('format', 'json').lower()
    content, mime, filename = export_dashboard_data(fmt=fmt)
    return Response(
        content,
        mimetype=mime,
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/export/econometrics')
def export_econometrics_endpoint():
    """Export econometric OLS regression results, trajectories, or full model."""
    post_year = int(request.args.get('post_year', 2018))
    property_type = request.args.get('property_type', 'ALL')
    buffer_filter = request.args.get('buffer_filter', 'ALL')
    export_type = request.args.get('type', 'model_json')
    
    content, mime, filename = export_econometrics_data(
        post_year=post_year,
        property_type=property_type,
        buffer_filter=buffer_filter,
        export_type=export_type
    )
    return Response(
        content,
        mimetype=mime,
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/export/parks')
def export_parks_endpoint():
    """Export Gujarat industrial parks catalog (CSV, GeoJSON, JSON, or KML)."""
    district = request.args.get('district', 'ALL')
    category = request.args.get('category', 'ALL')
    search = request.args.get('search', '').strip()
    fmt = request.args.get('format', 'csv').lower()
    
    if fmt == 'kml':
        content, filename = generate_kml_export()
        mime = 'application/vnd.google-earth.kml+xml'
    else:
        content, mime, filename = export_parks_data(
            district=district,
            category=category,
            search=search,
            fmt=fmt
        )
    return Response(
        content,
        mimetype=mime,
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/export/park/<int:park_id>')
def export_park_dossier_endpoint(park_id):
    """Export comprehensive dossier factsheet for a single industrial park."""
    fmt = request.args.get('format', 'json').lower()
    content, mime, filename = export_park_dossier(park_id, fmt=fmt)
    if not content:
        flash("Industrial park not found.", "error")
        return redirect(url_for('parks_list'))
        
    return Response(
        content,
        mimetype=mime,
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/export/transactions')
def export_transactions_endpoint():
    """Export micro-level property transactions panel data."""
    buffer_bin = request.args.get('buffer_bin', 'ALL')
    property_type = request.args.get('property_type', 'ALL')
    year = request.args.get('year', 'ALL')
    search = request.args.get('search', '').strip()
    fmt = request.args.get('format', 'csv').lower()
    
    content, mime, filename = export_transactions_data(
        buffer_bin=buffer_bin,
        property_type=property_type,
        year=year,
        search=search,
        fmt=fmt
    )
    return Response(
        content,
        mimetype=mime,
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/export/database')
def export_database_endpoint():
    """Download the raw SQLite database binary file for external econometric analysis."""
    if not os.path.exists(Config.DB_PATH):
        flash("Database file not found.", "error")
        return redirect(url_for('dashboard'))
    return send_file(
        Config.DB_PATH,
        as_attachment=True,
        download_name="gujarat_industrial_estates_study.db"
    )

# -----------------------------------------------------------------------------
# 17 Core Schema Tables CSV & ZIP Export Endpoints (with Rich Metadata & Data Sources)
# -----------------------------------------------------------------------------

@app.route('/tables')
@app.route('/database-hub')
def database_hub():
    """Dedicated view displaying all 17 core tables with data sources and export buttons."""
    tables = get_all_tables_info()
    total_records = sum(t['row_count'] for t in tables)
    return render_template('tables_hub.html', tables=tables, total_records=total_records)

@app.route('/export/table/<table_name>')
def export_table_csv_endpoint(table_name):
    """Download single table data in CSV format including rich metadata header & data source."""
    if table_name not in TABLE_REGISTRY:
        flash(f"Table '{table_name}' does not exist in schema.", "error")
        return redirect(url_for('database_hub'))
        
    csv_content, filename = generate_table_csv(table_name)
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/export/tables/all-zip')
def export_all_tables_zip_endpoint():
    """Download all 17 Core Database Tables in individual CSVs + README inside a ZIP archive."""
    zip_bytes, filename = generate_all_tables_zip()
    return Response(
        zip_bytes,
        mimetype="application/zip",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# -----------------------------------------------------------------------------
# Academic Replication Suite & Schema Inspector Endpoints
# -----------------------------------------------------------------------------

@app.route('/api/citations')
def api_citations_endpoint():
    """Returns BibTeX, APA 7, and Chicago academic citation strings."""
    return jsonify(get_citations())

@app.route('/api/table-schema/<table_name>')
def api_table_schema_endpoint(table_name):
    """Returns column metadata, constraints, and live 5-row sample preview."""
    detail = get_table_schema_detail(table_name)
    if not detail:
        return jsonify({"error": f"Table '{table_name}' not found."}), 404
    return jsonify(detail)

@app.route('/export/replication/stata')
def export_replication_stata():
    """Download ready-to-run Stata .do replication script."""
    content = generate_stata_dofile()
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=did_replication_gujarat.do"}
    )

@app.route('/export/replication/python')
def export_replication_python():
    """Download standalone Python replication script."""
    content = generate_python_replication_script()
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment;filename=did_replication_gujarat.py"}
    )

# -----------------------------------------------------------------------------
# Task T6: Advanced Econometric Studio & Plot Micro-Intelligence REST APIs
# -----------------------------------------------------------------------------

@app.route('/api/econometrics/event-study')
def api_event_study():
    """Returns event-study point estimates, 95% CIs, and parallel trends validation."""
    conn = get_db()
    data_mode = request.args.get('data_mode', 'empirical')
    post_year = int(request.args.get('post_year', 2008 if data_mode == 'empirical' else 2018))
    policy_shock = request.args.get('policy_shock', 'anchor')
    sector_filter = request.args.get('sector_category', 'all')
    if data_mode == 'empirical':
        data = compute_empirical_event_study(conn, policy_shock=policy_shock, post_year=post_year, sector_filter=sector_filter)
    else:
        data = compute_event_study_coefficients(conn, anchor_year=post_year)
    return jsonify(data)

@app.route('/api/econometrics/counterfactual')
def api_counterfactual():
    """Returns treatment vs control observed trajectories and synthetic counterfactual."""
    conn = get_db()
    data_mode = request.args.get('data_mode', 'empirical')
    post_year = int(request.args.get('post_year', 2008 if data_mode == 'empirical' else 2018))
    policy_shock = request.args.get('policy_shock', 'anchor')
    sector_filter = request.args.get('sector_category', 'all')
    if data_mode == 'empirical':
        data = compute_empirical_counterfactual(conn, policy_shock=policy_shock, post_year=post_year, sector_filter=sector_filter)
    else:
        data = compute_counterfactual_trajectories(conn, anchor_year=post_year)
    return jsonify(data)

@app.route('/api/econometrics/decay-binscatter')
def api_decay_binscatter():
    """Returns non-parametric distance decay curve and binscatter dataset."""
    conn = get_db()
    data_mode = request.args.get('data_mode', 'empirical')
    if data_mode == 'empirical':
        data = compute_empirical_corridor_decay_and_binscatter(conn)
    else:
        data = compute_distance_decay_and_binscatter(conn)
    return jsonify(data)

@app.route('/api/econometrics/ratio-matrix')
def api_ratio_matrix():
    """Returns Market Price / Jantar Circle Rate ratio across Gujarat Talukas."""
    conn = get_db()
    data = compute_market_to_circle_rate_heat_matrix(conn)
    return jsonify(data)

@app.route('/api/econometrics/lifecycle-distributions')
def api_lifecycle_distributions():
    """Returns box and violin plot metrics across the 4 Lifecycle Phases."""
    conn = get_db()
    data = compute_lifecycle_phase_distributions(conn)
    return jsonify(data)

@app.route('/api/econometrics/spatial-hexbins')
def api_spatial_hexbins():
    """Returns hexagonal spatial bins and KDE surface points across Gujarat."""
    conn = get_db()
    data = compute_spatial_hexbin_and_kde(conn)
    return jsonify(data)

@app.route('/api/econometrics/replication-code/<lang>')
def api_replication_code(lang):
    """Returns exact reproducible ggplot2 (R) or Stata (.do) replication code."""
    data_mode = request.args.get('data_mode', 'empirical')
    post_year = int(request.args.get('post_year', 2008 if data_mode == 'empirical' else 2018))
    policy_shock = request.args.get('policy_shock', 'anchor')
    sector_filter = request.args.get('sector_category', 'all')
    if data_mode == 'empirical':
        if lang.lower() == 'stata':
            code = generate_empirical_stata_code(policy_shock=policy_shock, post_year=post_year, sector_filter=sector_filter)
            mimetype = "text/plain"
            fn = f"gidc_empirical_did_{policy_shock}_t{post_year}.do"
        else:
            code = generate_empirical_ggplot2_code(policy_shock=policy_shock, post_year=post_year, sector_filter=sector_filter)
            mimetype = "text/plain"
            fn = f"gidc_empirical_did_{policy_shock}_t{post_year}.R"
    else:
        if lang.lower() == 'stata':
            code = generate_stata_code(post_year=post_year)
            mimetype = "text/plain"
            fn = f"did_event_study_t{post_year}.do"
        else:
            code = generate_ggplot2_code(post_year=post_year)
            mimetype = "text/plain"
            fn = f"did_event_study_t{post_year}.R"
    return Response(code, mimetype=mimetype, headers={"Content-Disposition": f"attachment;filename={fn}"})

@app.route('/api/plot/detail/<plot_id>')
def api_plot_detail(plot_id):
    """Returns complete 5-axis scorecard, radial distances, valuation benchmarks, and comps."""
    conn = get_db()
    data = get_plot_micro_intelligence(conn, plot_id)
    if not data:
        return jsonify({"error": f"Plot '{plot_id}' not found"}), 404
    return jsonify(data)

@app.route('/api/plot/search')
def api_plot_search():
    """Smart autocomplete search across estate, plot, survey, and DILR ID."""
    conn = get_db()
    q = request.args.get('q', '').strip()
    results = search_plots_autocomplete(conn, q, limit=15)
    return jsonify(results)

@app.route('/api/plot/estate-parcels/<int:park_id>')
def api_estate_parcels(park_id):
    """Returns GeoJSON FeatureCollection of all plots in the estate for synchronized GIS map."""
    conn = get_db()
    geojson = get_estate_parcel_features(conn, park_id)
    return jsonify(geojson)

@app.route('/api/plot/export/<fmt>/<plot_id>')
def api_plot_export_boundary(fmt, plot_id):
    """Exports cadastral boundary in GeoJSON, KML, or AutoCAD DXF format."""
    conn = get_db()
    plot_intel = get_plot_micro_intelligence(conn, plot_id)
    if not plot_intel:
        return jsonify({"error": "Plot not found"}), 404
    content, mime, filename = export_plot_boundary_cad(plot_intel, fmt=fmt.lower())
    return Response(
        content,
        mimetype=mime,
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

@app.route('/api/plot/decay-waterfall/<plot_id>')
def api_plot_decay_waterfall(plot_id):
    """Returns step-by-step valuation waterfall from GIDC base rate to fair market value."""
    conn = get_db()
    data = get_plot_valuation_waterfall(conn, plot_id)
    if not data:
        return jsonify({"error": f"Plot '{plot_id}' not found"}), 404
    return jsonify(data)

@app.route('/api/estate/obsolescence-profile/<int:park_id>')
def api_estate_obsolescence_profile(park_id):
    """Returns estate-level obsolescence metrics (EDI, BMR, UFQ, internal distance decay spline)."""
    conn = get_db()
    data = get_estate_decay_profile(conn, park_id)
    if not data:
        return jsonify({"error": f"Park ID {park_id} not found"}), 404
    return jsonify(data)

@app.route('/plot-dossier/<plot_id>')
def plot_dossier_view(plot_id):
    """One-click Academic Appraisal Dossier ready for field logs and investment committee review."""
    conn = get_db()
    plot_intel = get_plot_micro_intelligence(conn, plot_id)
    if not plot_intel:
        flash(f"Plot '{plot_id}' not found.", "warning")
        return redirect(url_for('plot_intelligence_view'))
    return render_template('plot_dossier.html', plot=plot_intel)

# -----------------------------------------------------------------------------
# CLI Commands
# -----------------------------------------------------------------------------

@app.cli.command("init-db")
def init_db_command():
    """CLI command to re-initialize and populate the database."""
    from data_loader import load_data
    load_data(Config.DB_PATH, force=True)
    print("Database re-initialized from scratch.")

if __name__ == '__main__':
    # Auto-initialize database if not present
    if not os.path.exists(Config.DB_PATH):
        from data_loader import load_data
        load_data(Config.DB_PATH)
        
    print(f"Starting Industrial Estates Flask Web Application on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=True)
