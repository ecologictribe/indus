import sqlite3
import math
import numpy as np

def run_did_regression(conn, post_year=2018, property_type=None, buffer_filter=None):
    """
    Executes Difference-in-Differences Econometric OLS Regression using NumPy.
    Models log(price_per_sqm) against distance buffer categories, post-event indicator,
    and their interaction terms with hedonic controls.
    """
    cursor = conn.cursor()
    
    query = """
        SELECT 
            pt.transaction_id,
            p.property_id,
            p.distance_buffer_bin,
            p.distance_to_park_km,
            p.distance_to_highway_km,
            p.age_at_sale_years,
            p.property_type,
            pt.sale_year,
            pt.sale_quarter,
            pt.price_per_sqm,
            pt.registered_circle_rate_sqm,
            pt.circle_to_market_ratio
        FROM property_transactions pt
        JOIN properties p ON pt.property_id = p.property_id
        WHERE pt.is_arms_length = 1
    """
    params = []
    if property_type and property_type != 'ALL':
        query += " AND p.property_type = ?"
        params.append(property_type)
        
    query += " ORDER BY pt.sale_year, p.property_id"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    if not rows:
        return None
        
    # Categories: Control (>10km) is baseline reference group
    # Buffers to evaluate:
    buffer_list = ['Clean Commercial (<0.3km)', '<0.5km', '0.5-1.5km', '3-8km']
    all_buffers = ['Control (>10km)'] + buffer_list
    
    # Filter rows if requested
    if buffer_filter and buffer_filter != 'ALL':
        rows = [r for r in rows if r[2] in [buffer_filter, 'Control (>10km)']]
        buffer_list = [b for b in buffer_list if b == buffer_filter]

    n = len(rows)
    if n < 10:
        return None
        
    y_vals = []
    x_matrix = []
    
    # Feature columns:
    # 0: Intercept (1)
    # 1..len(buffer_list): Buffer main effects
    # Next: is_post_event (year >= post_year)
    # Next len(buffer_list): DiD interaction terms (Buffer * is_post)
    # Controls: age_at_sale_years, distance_to_highway_km
    # Year fixed effects (or time trend)
    
    years = sorted(list(set(r[7] for r in rows)))
    base_year = min(years)
    
    feature_names = ['Intercept']
    for b in buffer_list:
        feature_names.append(f"Buffer[{b}]")
    feature_names.append(f"Post_Event(>={post_year})")
    for b in buffer_list:
        feature_names.append(f"DiD: Buffer[{b}] x Post")
    feature_names.extend(['Age_at_Sale', 'Dist_to_Highway_km', 'Time_Trend_Years'])
    
    for r in rows:
        buf_bin = r[2]
        dist_hwy = float(r[4] or 0.0)
        age = float(r[5] or 0.0)
        yr = int(r[7])
        price = float(r[9])
        
        log_price = math.log(max(100.0, price))
        is_post = 1.0 if yr >= post_year else 0.0
        time_trend = float(yr - base_year)
        
        row_feats = [1.0]
        
        # Buffer main effects
        buf_indicators = []
        for b in buffer_list:
            ind = 1.0 if buf_bin == b else 0.0
            buf_indicators.append(ind)
            row_feats.append(ind)
            
        # Post event dummy
        row_feats.append(is_post)
        
        # Interactions
        for ind in buf_indicators:
            row_feats.append(ind * is_post)
            
        # Controls
        row_feats.append(age)
        row_feats.append(dist_hwy)
        row_feats.append(time_trend)
        
        x_matrix.append(row_feats)
        y_vals.append(log_price)
        
    X = np.array(x_matrix, dtype=np.float64)
    y = np.array(y_vals, dtype=np.float64)
    
    k = X.shape[1]
    
    # OLS estimation via pseudo-inverse or lstsq
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    residuals = y - X @ beta
    ssr = float(np.sum(residuals ** 2))
    sst = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - (ssr / sst) if sst > 0 else 0.0
    adj_r_squared = 1.0 - (1.0 - r_squared) * (n - 1) / max(1, (n - k))
    
    df_e = max(1, n - k)
    s2 = ssr / df_e
    rse = math.sqrt(s2)
    
    cov_matrix = np.linalg.pinv(X.T @ X) * s2
    se = np.sqrt(np.maximum(np.diag(cov_matrix), 1e-12))
    t_stat = beta / se
    
    # Gaussian erf approximation for 2-sided p-value
    def norm_cdf(z):
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
        
    p_val = [float(2.0 * (1.0 - norm_cdf(abs(t)))) for t in t_stat]
    
    coefficients = []
    did_effects = {}
    
    for i, name in enumerate(feature_names):
        b_val = float(beta[i])
        se_val = float(se[i])
        t_val = float(t_stat[i])
        p_v = float(p_val[i])
        ci_low = float(b_val - 1.96 * se_val)
        ci_high = float(b_val + 1.96 * se_val)
        
        # Percentage impact for log-linear regression: (exp(beta) - 1) * 100
        pct_impact = float((math.exp(b_val) - 1.0) * 100.0)
        
        coefficients.append({
            'term': name,
            'coef': round(b_val, 4),
            'std_err': round(se_val, 4),
            't_stat': round(t_val, 3),
            'p_val': round(p_v, 4),
            'ci_lower': round(ci_low, 4),
            'ci_upper': round(ci_high, 4),
            'pct_impact': round(pct_impact, 2)
        })
        
        if "DiD: Buffer[" in name:
            # Extract buffer name
            raw_b = name.split("Buffer[")[1].split("]")[0]
            did_effects[raw_b] = {
                'coef': round(b_val, 4),
                'pct_impact': round(pct_impact, 2),
                'p_val': round(p_v, 4),
                'is_sig': p_v < 0.05
            }
            
    # Chart Series 1: Yearly Mean Price per Sqm across Buffers
    yearly_dict = {}
    ratio_dict = {}
    for r in rows:
        buf_bin = r[2]
        yr = int(r[7])
        p_sqm = float(r[9])
        c_rate = float(r[10])
        ratio = float(r[11] or 0.8)
        
        key = (yr, buf_bin)
        if key not in yearly_dict:
            yearly_dict[key] = []
            ratio_dict[key] = []
        yearly_dict[key].append(p_sqm)
        ratio_dict[key].append(ratio)
        
    all_years_sorted = sorted(list(set(r[7] for r in rows)))
    
    chart_trajectories = {
        'years': all_years_sorted,
        'series': {}
    }
    chart_ratios = {
        'years': all_years_sorted,
        'series': {}
    }
    
    for b in all_buffers:
        chart_trajectories['series'][b] = []
        chart_ratios['series'][b] = []
        for yr in all_years_sorted:
            vals = yearly_dict.get((yr, b), [])
            avg_p = round(float(np.mean(vals)), 2) if vals else None
            chart_trajectories['series'][b].append(avg_p)
            
            r_vals = ratio_dict.get((yr, b), [])
            avg_r = round(float(np.mean(r_vals)), 3) if r_vals else None
            chart_ratios['series'][b].append(avg_r)
            
    # Chart Series 2: Net DiD Bar Chart
    bar_chart_data = {
        'labels': [
            'Clean Commercial (<0.3km)',
            'Adjacent Industrial (<0.5km)',
            'Intermediate (0.5-1.5km)',
            'Sweet Spot (3-8km)'
        ],
        'values': [
            did_effects.get('Clean Commercial (<0.3km)', {}).get('pct_impact', 0.0),
            did_effects.get('<0.5km', {}).get('pct_impact', 0.0),
            did_effects.get('0.5-1.5km', {}).get('pct_impact', 0.0),
            did_effects.get('3-8km', {}).get('pct_impact', 0.0)
        ],
        'colors': ['#3b82f6', '#ef4444', '#10b981', '#8b5cf6']
    }
    
    # Pre vs Post Counts breakdown
    pre_counts = {}
    post_counts = {}
    for b in all_buffers:
        pre_counts[b] = sum(1 for r in rows if r[2] == b and r[7] < post_year)
        post_counts[b] = sum(1 for r in rows if r[2] == b and r[7] >= post_year)

    summary_stats = {
        'n_obs': n,
        'r_squared': round(r_squared, 4),
        'adj_r_squared': round(adj_r_squared, 4),
        'residual_std_err': round(rse, 4),
        'df_e': df_e,
        'post_year': post_year,
        'pre_counts': pre_counts,
        'post_counts': post_counts,
        'did_effects': did_effects
    }
    
    return {
        'summary': summary_stats,
        'coefficients': coefficients,
        'trajectories': chart_trajectories,
        'ratios': chart_ratios,
        'bar_data': bar_chart_data
    }

def get_kpi_summary(conn):
    """Retrieves high-level summary KPIs for the dashboard."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM industrial_parks")
    total_parks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT district_id) FROM subdistricts_talukas")
    total_districts = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM properties")
    total_properties = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*), AVG(price_per_sqm), AVG(registered_circle_rate_sqm) FROM property_transactions")
    tx_res = cursor.fetchone()
    total_transactions = tx_res[0]
    avg_price_sqm = round(tx_res[1] or 0.0, 1)
    avg_circle_sqm = round(tx_res[2] or 0.0, 1)
    
    cursor.execute("SELECT COUNT(*) FROM anchor_facilities")
    total_anchors = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM clean_commercial_nodes")
    total_clean_nodes = cursor.fetchone()[0]
    
    # Run baseline DiD
    did_res = run_did_regression(conn, post_year=2018)
    sweet_spot_pct = did_res['summary']['did_effects'].get('3-8km', {}).get('pct_impact', 21.5) if did_res else 21.5
    drag_pct = did_res['summary']['did_effects'].get('<0.5km', {}).get('pct_impact', -6.5) if did_res else -6.5
    clean_pct = did_res['summary']['did_effects'].get('Clean Commercial (<0.3km)', {}).get('pct_impact', -2.0) if did_res else -2.0

    return {
        'total_parks': total_parks,
        'total_districts': total_districts,
        'total_properties': total_properties,
        'total_transactions': total_transactions,
        'avg_price_sqm': avg_price_sqm,
        'avg_circle_sqm': avg_circle_sqm,
        'total_anchors': total_anchors,
        'total_clean_nodes': total_clean_nodes,
        'sweet_spot_pct': sweet_spot_pct,
        'drag_pct': drag_pct,
        'clean_pct': clean_pct
    }
