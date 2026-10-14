import unittest
import json
from app import app

class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_dashboard(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Industrial Park Property Dynamics', response.data)
        self.assertIn(b'Sweet Spot Premium', response.data)

    def test_map(self):
        response = self.client.get('/map')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'leaflet-map', response.data)
        self.assertIn(b'Export GIS', response.data)

    def test_econometrics(self):
        # Mode 1: Empirical GIDC (Default)
        response = self.client.get('/econometrics')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Difference-in-Differences (DiD) Econometrics Studio', response.data)
        self.assertIn(b'Model Fit (R-Squared)', response.data)
        self.assertIn(b'Official GIDC Statutory Land Price Panel', response.data)
        self.assertIn(b'8,448 empirical allotment rate observations', response.data)

        # Mode 2: Synthetic Secondary Market
        response_synth = self.client.get('/econometrics?data_mode=synthetic')
        self.assertEqual(response_synth.status_code, 200)
        self.assertIn(b'Mode 2: Secondary Market Panel', response_synth.data)
        self.assertIn(b'Surrounding Real Estate Secondary Market Panel', response_synth.data)

    def test_parks_list(self):
        response = self.client.get('/parks')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Gujarat Industrial Parks & GIDC Estates', response.data)
        self.assertIn(b'Estates Found', response.data)

    def test_park_detail(self):
        # Park 1 (Apparel Park)
        response = self.client.get('/parks/1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Estate Specifications', response.data)
        self.assertIn(b'Spatial Distance Buffer Gradients', response.data)

    def test_transactions(self):
        response = self.client.get('/transactions')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Property Transactions & DiD Panel', response.data)

    def test_methodology(self):
        response = self.client.get('/methodology')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Empirical Framework & Database Design', response.data)

    def test_api_stats(self):
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('total_parks', data)
        self.assertEqual(data['total_parks'], 312)

    def test_api_parks(self):
        response = self.client.get('/api/parks')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 312)

    def test_api_did(self):
        response = self.client.get('/api/did-analysis?post_year=2018')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('summary', data)
        self.assertIn('coefficients', data)
        self.assertIn('trajectories', data)

    # --- Export Facilities Tests Across All Stops ---

    def test_export_dashboard_json(self):
        response = self.client.get('/export/dashboard?format=json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/json')
        data = json.loads(response.data)
        self.assertIn('_metadata', data)
        self.assertIn('kpis', data)

    def test_export_dashboard_csv(self):
        response = self.client.get('/export/dashboard?format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn(b'# Project,Gujarat Industrial Estates Property Dynamics Study', response.data)

    def test_export_econometrics_coefficients(self):
        response = self.client.get('/export/econometrics?type=coefficients_csv&post_year=2018')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn(b'Parameter_Variable,Coefficient_Beta', response.data)

    def test_export_econometrics_trajectories(self):
        response = self.client.get('/export/econometrics?type=trajectories_csv&post_year=2018')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn(b'Sale_Year', response.data)

    def test_export_econometrics_model_json(self):
        response = self.client.get('/export/econometrics?type=model_json&post_year=2018')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/json')
        data = json.loads(response.data)
        self.assertIn('_metadata', data)
        self.assertIn('model_summary', data)

    def test_export_parks_csv(self):
        response = self.client.get('/export/parks?format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn(b'Park_ID,Park_Name,District', response.data)

    def test_export_parks_geojson(self):
        response = self.client.get('/export/parks?format=geojson')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data.get('type'), 'FeatureCollection')
        self.assertIn('_metadata', data)
        self.assertTrue(len(data.get('features', [])) > 0)

    def test_export_park_dossier_json(self):
        response = self.client.get('/export/park/1?format=json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('_metadata', data)
        self.assertIn('park_profile', data)
        self.assertIn('lifecycle_events', data)

    def test_export_park_dossier_csv(self):
        response = self.client.get('/export/park/1?format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn(b'--- LIFECYCLE MILESTONES ---', response.data)

    def test_export_transactions_csv(self):
        response = self.client.get('/export/transactions?format=csv')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')
        self.assertIn(b'Transaction_ID,Sale_Date', response.data)

    def test_export_transactions_json(self):
        response = self.client.get('/export/transactions?format=json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('_metadata', data)
        self.assertIn('transactions', data)
        self.assertTrue(len(data['transactions']) >= 4000)

    def test_export_database(self):
        response = self.client.get('/export/database')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) > 10000)

    def test_database_hub(self):
        response = self.client.get('/database-hub')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'18 Core Relational Tables', response.data)
        self.assertIn(b'DATA SOURCE:', response.data)
        self.assertIn(b'source_registry', response.data)
        self.assertIn(b'data_provenance', response.data)

    def test_export_all_tables_zip(self):
        import zipfile
        import io
        response = self.client.get('/export/tables/all-zip')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/zip')
        
        zf = zipfile.ZipFile(io.BytesIO(response.data))
        names = zf.namelist()
        self.assertEqual(len(names), 19) # 18 CSVs + 1 README
        self.assertIn('05_industrial_parks.csv', names)
        self.assertIn('11_property_transactions.csv', names)
        self.assertIn('14_intelligence_sources.csv', names)
        self.assertIn('15_estate_aliases_master.csv', names)
        self.assertIn('16_industrial_land_price_history.csv', names)
        self.assertIn('17_industrial_plots.csv', names)
        self.assertIn('18_source_registry.csv', names)
        self.assertIn('19_data_provenance.csv', names)
        self.assertIn('README_METADATA_AND_DATA_SOURCES.md', names)

    def test_export_all_18_tables_individually(self):
        tables = [
            "states", "districts", "subdistricts_talukas", "neighborhoods_jurisdictions",
            "industrial_parks", "anchor_facilities", "park_lifecycle_events",
            "park_annual_metrics", "clean_commercial_nodes", "properties",
            "property_transactions", "did_panel_designations",
            "intelligence_sources", "estate_aliases_master", "industrial_land_price_history",
            "industrial_plots", "source_registry", "data_provenance"
        ]
        for tbl in tables:
            response = self.client.get(f'/export/table/{tbl}')
            self.assertEqual(response.status_code, 200, f"Failed for table: {tbl}")
            self.assertEqual(response.mimetype, 'text/csv')
            self.assertIn(b'# DATA SOURCE:', response.data, f"Data source missing in {tbl}")
            self.assertIn(b'# Table Name:', response.data, f"Table header missing in {tbl}")

    def test_land_pricing_history_view(self):
        response = self.client.get('/land-pricing-history')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Industrial Land Allotment Price Trajectories', response.data)
        self.assertIn(b'Statewide Allotment CAGR', response.data)
        self.assertIn(b'REVISED_ALLOTMENT', response.data)

    def test_plot_intelligence_view(self):
        # Test standard route
        response = self.client.get('/plot-intelligence')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Industrial Plots Cadastral Intelligence', response.data)
        self.assertIn(b'Industrial Plots Inventory & Allocation Roster', response.data)
        self.assertIn(b'Fine-Grain Institutional Provenance & Traceability Statistics', response.data)
        self.assertIn(b'Institutional Source & Provenance', response.data)
        self.assertIn(b'100% Traceable', response.data)
        self.assertIn(b'Total Monitored Plots', response.data)
        self.assertIn(b'Available Inventory', response.data)

        # Test /data alias route
        res_data = self.client.get('/data')
        self.assertEqual(res_data.status_code, 200)
        self.assertIn(b'Industrial Plots Inventory & Allocation Roster', res_data.data)
        self.assertIn(b'Estate Cadastral Parcel Map', res_data.data)

        # Test source filter
        res_source = self.client.get('/plot-intelligence?source_id=1')
        self.assertEqual(res_source.status_code, 200)
        self.assertIn(b'Statutory Baseline Order FY 2000-01', res_source.data)

    def test_api_price_history(self):
        response = self.client.get('/api/price-history/1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('park', data)
        self.assertIn('history', data)
        self.assertIn('cagr', data)
        self.assertTrue(len(data['history']) >= 27)

    def test_api_plot_intelligence(self):
        response = self.client.get('/api/plot-intelligence?limit=20')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 20)
        sample = data[0]
        self.assertIn('plot_id', sample)
        self.assertIn('plot_area_sqm', sample)
        self.assertIn('allotment_price_sqm', sample)
        self.assertIn('status', sample)
        self.assertIn('source_doc', sample)
        self.assertIn('source_tier', sample)
        self.assertIn('source_authority', sample)
        self.assertIn('source_checksum', sample)

    def test_api_plot_traceability_dossier(self):
        response = self.client.get('/api/plot-intelligence/PLOT-001-001/traceability')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['plot_id'], 'PLOT-001-001')
        self.assertIn('park_name', data)
        self.assertIn('district_name', data)
        self.assertIn('document_name', data)
        self.assertIn('tier_level', data)
        self.assertIn('authority', data)
        self.assertIn('checksum', data)
        self.assertIn('source_url', data)

    def test_api_plot_intelligence_kpis(self):
        response = self.client.get('/api/plot-intelligence/kpis')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('total_plots', data)
        self.assertIn('available_plots', data)
        self.assertIn('occupancy_rate_pct', data)
        self.assertIn('source_stats', data)
        self.assertIn('tier_stats', data)
        self.assertIn('authority_stats', data)
        self.assertEqual(data['traceability_rate_pct'], 100.0)
        self.assertTrue(data['total_plots'] > 3000)

    def test_pollution_data_excised_from_schema(self):
        """Verifies pollution benchmark table and columns are completely excised from the database schema."""
        import sqlite3
        conn = sqlite3.connect('db/industrial_estates.db')
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='park_pollution_benchmarks'")
        self.assertIsNone(c.fetchone(), "park_pollution_benchmarks table must NOT exist in database")
        conn.close()

        # Pollution drag API returns empty list (neutralized)
        res_drag = self.client.get('/api/pollution-drag')
        self.assertEqual(res_drag.status_code, 200)
        self.assertEqual(json.loads(res_drag.data), [])

    def test_api_citations(self):
        response = self.client.get('/api/citations')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('bibtex', data)
        self.assertIn('apa', data)
        self.assertIn('chicago', data)

    def test_api_table_schema(self):
        response = self.client.get('/api/table-schema/industrial_parks')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['table_name'], 'industrial_parks')
        self.assertIn('columns', data)
        self.assertIn('sample_preview', data)
        self.assertEqual(len(data['sample_preview']), 5)

    def test_export_replication_stata(self):
        response = self.client.get('/export/replication/stata')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'GUJARAT INDUSTRIAL ESTATES PROPERTY DYNAMICS STUDY', response.data)
        self.assertIn(b'regress ln_price_sqm', response.data)

    def test_export_replication_python(self):
        response = self.client.get('/export/replication/python')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'SPATIAL DIFFERENCE-IN-DIFFERENCES OLS RESULTS', response.data)

    def test_export_parks_kml(self):
        response = self.client.get('/export/parks?format=kml')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<kml xmlns="http://www.opengis.net/kml/2.2">', response.data)
        self.assertIn(b'<coordinates>', response.data)

    # -------------------------------------------------------------------------
    # Task T5: Central Source Registry & Value-Level Data Provenance Tests
    # -------------------------------------------------------------------------

    def test_provenance_view(self):
        response = self.client.get('/provenance')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Source Archiving, Data Provenance & Traceability', response.data)
        self.assertIn(b'Master Source Registry & Local Archive', response.data)
        self.assertIn(b'Value-Level Evidence Explorer', response.data)
        self.assertIn(b'Multi-Year Version Lineage', response.data)
        self.assertIn(b'Inaccessible / Restricted Source Audit Log', response.data)

    def test_provenance_alias_sources(self):
        response = self.client.get('/sources')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Master Source Registry & Local Archive', response.data)

    def test_view_and_download_source_file(self):
        # 1. View in browser
        res_view = self.client.get('/sources/view/SRC-GIDC-2026-001')
        self.assertEqual(res_view.status_code, 200)
        self.assertEqual(res_view.mimetype, 'application/pdf')
        self.assertIn(b'%PDF-', res_view.data)

        # 2. Download attachment
        res_dl = self.client.get('/sources/download/SRC-GIDC-2026-001')
        self.assertEqual(res_dl.status_code, 200)
        self.assertIn('attachment', res_dl.headers.get('Content-Disposition', ''))

    def test_source_metadata_json(self):
        response = self.client.get('/sources/metadata/SRC-GIDC-2026-001')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['source_id'], 'SRC-GIDC-2026-001')
        self.assertIn('file_hash', data)
        self.assertIn('local_path', data)
        self.assertTrue(data['file_exists_on_disk'])

    def test_api_provenance_kpis(self):
        response = self.client.get('/api/provenance/kpis')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['total_sources'] >= 11)
        self.assertTrue(data['total_provenance_records'] > 8000)
        self.assertEqual(data['verification_rate_pct'], 100.0)
        self.assertIn('org_breakdown', data)
        self.assertIn('entity_breakdown', data)

    def test_api_provenance_source_verify(self):
        response = self.client.get('/api/provenance/source/SRC-GIDC-2026-001/verify')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'VERIFIED_MATCH')
        self.assertTrue(data['is_tamper_evident'])
        self.assertEqual(data['db_hash'], data['disk_hash'])

    def test_api_provenance_records_and_trace(self):
        # Filtered records
        res_rec = self.client.get('/api/provenance/records?limit=10')
        self.assertEqual(res_rec.status_code, 200)
        recs = json.loads(res_rec.data)
        self.assertEqual(len(recs), 10)
        self.assertIn('source_location', recs[0])
        self.assertIn('source_excerpt', recs[0])

        # Entity trace
        res_trace = self.client.get('/api/provenance/trace/industrial_plots/PLOT-001-001')
        self.assertEqual(res_trace.status_code, 200)
        trace_data = json.loads(res_trace.data)
        self.assertTrue(len(trace_data) >= 1)
        self.assertEqual(trace_data[0]['entity_id'], 'PLOT-001-001')

    def test_api_provenance_versions(self):
        response = self.client.get('/api/provenance/versions')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('GIDC Allotment Pricing Circulars', data)
        self.assertTrue(len(data['GIDC Allotment Pricing Circulars']) >= 4)

    # -------------------------------------------------------------------------
    # Task T6: Econometric Studio & Plot Intelligence Advanced Suite Tests
    # -------------------------------------------------------------------------

    def test_econometric_event_study_api(self):
        # Empirical (default)
        response_emp = self.client.get('/api/econometrics/event-study?data_mode=empirical&post_year=2008&policy_shock=anchor')
        self.assertEqual(response_emp.status_code, 200)
        data_emp = json.loads(response_emp.data)
        self.assertIn('points_sweet_spot', data_emp)
        self.assertIn('parallel_trends_valid', data_emp)
        self.assertTrue(len(data_emp['points_sweet_spot']) >= 10)
        self.assertEqual(data_emp['anchor_year'], 2008)

        # Synthetic mode
        response_syn = self.client.get('/api/econometrics/event-study?data_mode=synthetic&post_year=2018')
        self.assertEqual(response_syn.status_code, 200)
        data_syn = json.loads(response_syn.data)
        self.assertIn('points_sweet_spot', data_syn)
        self.assertEqual(data_syn['anchor_year'], 2018)

    def test_econometric_counterfactual_api(self):
        # Empirical (default)
        response_emp = self.client.get('/api/econometrics/counterfactual?data_mode=empirical&post_year=2008')
        self.assertEqual(response_emp.status_code, 200)
        data_emp = json.loads(response_emp.data)
        self.assertIn('years', data_emp)
        self.assertIn('treat_observed', data_emp)
        self.assertIn('counterfactual', data_emp)
        self.assertTrue(len(data_emp['years']) >= 15)

        # Synthetic mode
        response_syn = self.client.get('/api/econometrics/counterfactual?data_mode=synthetic&post_year=2018')
        self.assertEqual(response_syn.status_code, 200)
        data_syn = json.loads(response_syn.data)
        self.assertIn('years', data_syn)
        self.assertTrue(len(data_syn['years']) >= 10)

    def test_econometric_decay_binscatter_api(self):
        # Empirical (default)
        response_emp = self.client.get('/api/econometrics/decay-binscatter?data_mode=empirical')
        self.assertEqual(response_emp.status_code, 200)
        data_emp = json.loads(response_emp.data)
        self.assertIn('binscatter', data_emp)
        self.assertIn('decay_curve', data_emp)
        self.assertTrue(len(data_emp['binscatter']) >= 10)
        self.assertTrue(len(data_emp['decay_curve']) >= 20)

        # Synthetic mode
        response_syn = self.client.get('/api/econometrics/decay-binscatter?data_mode=synthetic')
        self.assertEqual(response_syn.status_code, 200)
        data_syn = json.loads(response_syn.data)
        self.assertIn('binscatter', data_syn)
        self.assertIn('decay_curve', data_syn)

    def test_econometric_ratio_matrix_api(self):
        response = self.client.get('/api/econometrics/ratio-matrix')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(len(data) >= 10)
        self.assertIn('district_name', data[0])
        self.assertIn('ratio', data[0])
        self.assertIn('color_class', data[0])

    def test_econometric_lifecycle_distributions_api(self):
        response = self.client.get('/api/econometrics/lifecycle-distributions')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(len(data) >= 3)
        self.assertIn('phase_name', data[0])
        self.assertIn('median', data[0])
        self.assertIn('iqr', data[0])
        self.assertIn('skewness', data[0])

    def test_econometric_spatial_hexbins_api(self):
        response = self.client.get('/api/econometrics/spatial-hexbins')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(len(data) >= 50)
        self.assertIn('vertices', data[0])
        self.assertIn('intensity', data[0])

    def test_econometric_replication_code_downloads(self):
        # Empirical Stata
        res_stata_emp = self.client.get('/api/econometrics/replication-code/stata?data_mode=empirical&post_year=2008')
        self.assertEqual(res_stata_emp.status_code, 200)
        self.assertIn(b'reghdfe log_allotment_price', res_stata_emp.data)
        self.assertIn(b'gen tau', res_stata_emp.data)

        # Empirical R
        res_r_emp = self.client.get('/api/econometrics/replication-code/r?data_mode=empirical&post_year=2008')
        self.assertEqual(res_r_emp.status_code, 200)
        self.assertIn(b'library(fixest)', res_r_emp.data)
        self.assertIn(b'log(price_per_sqm)', res_r_emp.data)

        # Synthetic Stata
        res_stata_syn = self.client.get('/api/econometrics/replication-code/stata?data_mode=synthetic&post_year=2018')
        self.assertEqual(res_stata_syn.status_code, 200)
        self.assertIn(b'reghdfe', res_stata_syn.data)

    def test_plot_intelligence_split_view_page(self):
        response = self.client.get('/plot-intelligence')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Estate Cadastral Parcel Map', response.data)
        self.assertIn(b'btnModeStandard', response.data)
        self.assertIn(b'btnModeDecay', response.data)
        self.assertIn(b'drawerRadarCanvas', response.data)
        self.assertIn(b'drawerDispersionCanvas', response.data)
        self.assertIn(b'estateDecaySplineCanvas', response.data)
        self.assertIn(b'drawerCompsBody', response.data)
        self.assertIn(b'Brownfield Decay &amp; Lifecycle Audit', response.data)
        self.assertIn(b'Valuation Waterfall Deconstruction', response.data)

    def test_plot_detail_api(self):
        response = self.client.get('/api/plot/detail/PLOT-001-001')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['plot_id'], 'PLOT-001-001')
        self.assertIn('radar_scores', data)
        self.assertEqual(len(data['radar_scores']['labels']), 5)
        self.assertIn('radial_infrastructure', data)
        self.assertIn('valuation_gauge', data)
        self.assertIn('comps_matrix', data)
        self.assertIn('dispersion_points', data)
        self.assertIn('cad_polygon', data)
        # Decay Metrics and Valuation Waterfall
        self.assertIn('decay_metrics', data)
        self.assertIn('decay_vulnerability_score', data['decay_metrics'])
        self.assertIn('frontage_efficiency_index', data['decay_metrics'])
        self.assertIn('logistical_ingress_factor', data['decay_metrics'])
        self.assertIn('vulnerability_radar', data)
        self.assertEqual(len(data['vulnerability_radar']['labels']), 6)
        self.assertIn('valuation_waterfall', data)
        self.assertIn('waterfall_steps', data['valuation_waterfall'])

    def test_plot_decay_waterfall_api(self):
        response = self.client.get('/api/plot/decay-waterfall/PLOT-001-001')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['plot_id'], 'PLOT-001-001')
        self.assertIn('waterfall_steps', data)
        self.assertTrue(len(data['waterfall_steps']) >= 6)
        self.assertIn('net_appraised_fair_value', data)
        self.assertIn('base_allotment_price', data)

    def test_estate_obsolescence_profile_api(self):
        response = self.client.get('/api/estate/obsolescence-profile/1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['park_id'], 1)
        self.assertIn('estate_decay_index', data)
        self.assertIn('brownfield_morbidity_ratio', data)
        self.assertIn('internal_decay_curve', data)
        self.assertTrue(len(data['internal_decay_curve']) >= 5)

    def test_plot_search_autocomplete_api(self):
        response = self.client.get('/api/plot/search?q=PLOT')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(len(data) >= 1)
        self.assertIn('plot_id', data[0])
        self.assertIn('park_name', data[0])

    def test_plot_estate_parcels_geojson(self):
        response = self.client.get('/api/plot/estate-parcels/1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['type'], 'FeatureCollection')
        self.assertTrue(len(data['features']) >= 1)
        self.assertEqual(data['features'][0]['geometry']['type'], 'Polygon')
        # Check enriched decay properties
        props = data['features'][0]['properties']
        self.assertIn('decay_fill_color', props)
        self.assertIn('lifecycle_state', props)
        self.assertIn('decay_score', props)
        self.assertIn('lif', props)
        self.assertIn('stroke_color', props)

    def test_plot_export_cad_boundary(self):
        # GeoJSON
        res_geo = self.client.get('/api/plot/export/geojson/PLOT-001-001')
        self.assertEqual(res_geo.status_code, 200)
        data = json.loads(res_geo.data)
        self.assertEqual(data['type'], 'Feature')
        self.assertEqual(data['properties']['plot_id'], 'PLOT-001-001')

        # KML
        res_kml = self.client.get('/api/plot/export/kml/PLOT-001-001')
        self.assertEqual(res_kml.status_code, 200)
        self.assertIn(b'<kml xmlns="http://www.opengis.net/kml/2.2">', res_kml.data)

        # DXF
        res_dxf = self.client.get('/api/plot/export/dxf/PLOT-001-001')
        self.assertEqual(res_dxf.status_code, 200)
        self.assertIn(b'CADASTRAL_BOUNDARY', res_dxf.data)

    def test_plot_dossier_view(self):
        response = self.client.get('/plot-dossier/PLOT-001-001')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cadastral Plot Appraisal & Intelligence Report', response.data)
        self.assertIn(b'Micro-Location 5-Axis Scorecard', response.data)
        self.assertIn(b'Econometric Valuation Benchmarking', response.data)
        self.assertIn(b'Brownfield Obsolescence &amp; Lifecycle Decay Audit', response.data)
        self.assertIn(b'Valuation Waterfall Deconstruction', response.data)

if __name__ == '__main__':
    unittest.main()
