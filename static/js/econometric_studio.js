/**
 * Advanced Econometric Studio Charting & Interoperability Engine
 * Implements:
 * 1. Event-Study Coefficient Plot with 95% CIs and t0 reference benchmark
 * 2. Counterfactual Trajectory Overlay with Standard Error Shading
 * 3. Distance Decay Gradient Curves and Binscatter
 * 4. Lifecycle Phase Distributional Box Plots
 * 5. Journal / Monochrome Theme Switcher (IEEE / Elsevier publication format)
 * 6. Vector/Image Chart Exporter (SVG / PNG) and Stata / R Code Copy
 */

let esChartInstance = null;
let cfChartInstance = null;
let decayChartInstance = null;
let lifecycleChartInstance = null;
let isJournalTheme = false;

// Color Palettes
const DIGITAL_COLORS = {
    primary: '#0284c7',
    navy: '#0f172a',
    treat: '#8b5cf6',
    drag: '#ef4444',
    ctrl: '#64748b',
    synth: '#f59e0b',
    grid: '#f1f5f9',
    text: '#334155'
};

const JOURNAL_COLORS = {
    primary: '#000000',
    navy: '#000000',
    treat: '#222222',
    drag: '#555555',
    ctrl: '#777777',
    synth: '#333333',
    grid: '#e5e7eb',
    text: '#111827'
};

function getActiveColors() {
    return isJournalTheme ? JOURNAL_COLORS : DIGITAL_COLORS;
}

// ----------------------------------------------------------------------------
// 1. Event-Study Coefficient Plot with 95% CIs and T0 Benchmark Line
// ----------------------------------------------------------------------------
function initEventStudyPlot(canvasId, esData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !esData || !esData.points_sweet_spot) return;

    if (esChartInstance) esChartInstance.destroy();

    const colors = getActiveColors();
    const sweetPoints = esData.points_sweet_spot;
    const labels = sweetPoints.map(p => p.tau_label);
    const coefs = sweetPoints.map(p => p.coef);
    const ciLows = sweetPoints.map(p => p.ci_lower);
    const ciHighs = sweetPoints.map(p => p.ci_upper);

    // Custom plugin to draw vertical line at t0 (launch of policy/development)
    const t0LinePlugin = {
        id: 't0BenchmarkLine',
        afterDraw: (chart) => {
            const { ctx, chartArea: { top, bottom }, scales: { x } } = chart;
            // t-1 is index 4, t0 is index 5
            const t0Index = sweetPoints.findIndex(p => p.tau === 0);
            if (t0Index === -1) return;
            
            const xPos = (x.getPixelForTick(t0Index - 1) + x.getPixelForTick(t0Index)) / 2;
            
            ctx.save();
            ctx.strokeStyle = isJournalTheme ? '#000000' : '#dc2626';
            ctx.lineWidth = 2;
            ctx.setLineDash([6, 4]);
            ctx.beginPath();
            ctx.moveTo(xPos, top);
            ctx.lineTo(xPos, bottom);
            ctx.stroke();

            // Label text
            ctx.fillStyle = isJournalTheme ? '#000000' : '#dc2626';
            ctx.font = isJournalTheme ? 'bold 11px "Times New Roman"' : 'bold 11px sans-serif';
            ctx.fillText('Policy Launch (T0)', xPos + 6, top + 15);
            ctx.restore();
        }
    };

    esChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Point Estimate (β)',
                    data: coefs,
                    borderColor: colors.treat,
                    backgroundColor: colors.treat,
                    borderWidth: 2.5,
                    pointRadius: 5,
                    pointHoverRadius: 7,
                    tension: 0.1,
                    order: 1
                },
                {
                    label: '95% CI Upper Bound',
                    data: ciHighs,
                    borderColor: 'rgba(139, 92, 246, 0.3)',
                    backgroundColor: 'rgba(139, 92, 246, 0.15)',
                    borderWidth: 1,
                    borderDash: [3, 3],
                    pointRadius: 0,
                    fill: '+1',
                    order: 2
                },
                {
                    label: '95% CI Lower Bound',
                    data: ciLows,
                    borderColor: 'rgba(139, 92, 246, 0.3)',
                    backgroundColor: 'transparent',
                    borderWidth: 1,
                    borderDash: [3, 3],
                    pointRadius: 0,
                    fill: false,
                    order: 3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: isJournalTheme 
                        ? 'FIGURE 1. Event-Study Estimates of Industrial Development on Land Values (95% Clustered CI)' 
                        : 'Dynamic Event-Study Coefficients (Sweet Spot 3–8km vs Control Baseline)',
                    font: {
                        family: isJournalTheme ? 'Times New Roman' : 'inherit',
                        size: 13,
                        weight: 'bold'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const p = sweetPoints[context.dataIndex];
                            if (p.is_ref) return 't-1: Reference Period (Normalized to 0.00)';
                            return [
                                `Coefficient (β): ${p.coef >= 0 ? '+' : ''}${p.coef}`,
                                `95% CI: [${p.ci_lower}, ${p.ci_upper}]`,
                                `Std Error: ${p.std_err}`,
                                `p-Value: ${p.p_val} (${p.is_sig ? 'p < 0.05 *' : 'Not Sig.'})`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Event Time (Years relative to Policy / Commissioning Launch T0)',
                        font: { family: isJournalTheme ? 'Times New Roman' : 'inherit' }
                    },
                    grid: { color: colors.grid }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Impact on ln(Price/m²)',
                        font: { family: isJournalTheme ? 'Times New Roman' : 'inherit' }
                    },
                    grid: { color: colors.grid }
                }
            }
        },
        plugins: [t0LinePlugin]
    });
}

// ----------------------------------------------------------------------------
// 2. Counterfactual Trend Overlay with Shaded SE Bands
// ----------------------------------------------------------------------------
function initCounterfactualPlot(canvasId, cfData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !cfData || !cfData.years) return;

    if (cfChartInstance) cfChartInstance.destroy();

    const colors = getActiveColors();
    const years = cfData.years;

    cfChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: years,
            datasets: [
                {
                    label: 'Observed Treatment (3–8km)',
                    data: cfData.treat_observed,
                    borderColor: colors.treat,
                    backgroundColor: colors.treat,
                    borderWidth: 2.5,
                    pointRadius: 4,
                    fill: false,
                    tension: 0.2
                },
                {
                    label: 'Synthetic Counterfactual (Parallel Trends)',
                    data: cfData.counterfactual,
                    borderColor: colors.synth,
                    borderWidth: 2.5,
                    borderDash: [6, 4],
                    pointRadius: 4,
                    pointStyle: 'rectRot',
                    fill: false,
                    tension: 0.2
                },
                {
                    label: 'Observed Control (>10km)',
                    data: cfData.ctrl_observed,
                    borderColor: colors.ctrl,
                    backgroundColor: colors.ctrl,
                    borderWidth: 2,
                    pointRadius: 3,
                    fill: false,
                    tension: 0.2
                },
                {
                    label: 'Treatment Upper 95% SE',
                    data: cfData.treat_se_high,
                    borderColor: 'transparent',
                    backgroundColor: 'rgba(139, 92, 246, 0.12)',
                    pointRadius: 0,
                    fill: '+1'
                },
                {
                    label: 'Treatment Lower 95% SE',
                    data: cfData.treat_se_low,
                    borderColor: 'transparent',
                    backgroundColor: 'transparent',
                    pointRadius: 0,
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: isJournalTheme 
                        ? 'FIGURE 2. Observed Trajectories vs Synthetic Parallel-Trends Counterfactual' 
                        : 'Observed Trajectory vs Counterfactual Baseline Overlay (with 95% SE Bands)',
                    font: { family: isJournalTheme ? 'Times New Roman' : 'inherit', size: 13, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ₹${Number(context.raw).toLocaleString('en-IN')}/sqm`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Sale Year', font: { family: isJournalTheme ? 'Times New Roman' : 'inherit' } },
                    grid: { color: colors.grid }
                },
                y: {
                    title: { display: true, text: 'Land Price (INR / sqm)', font: { family: isJournalTheme ? 'Times New Roman' : 'inherit' } },
                    ticks: {
                        callback: val => '₹' + Number(val).toLocaleString('en-IN')
                    },
                    grid: { color: colors.grid }
                }
            }
        }
    });
}

// ----------------------------------------------------------------------------
// 3. Distance Decay Gradient Curves & Binscatter
// ----------------------------------------------------------------------------
function initDistanceDecayPlot(canvasId, decayData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !decayData) return;

    if (decayChartInstance) decayChartInstance.destroy();

    const colors = getActiveColors();
    const bins = decayData.binscatter || [];
    const curve = decayData.decay_curve || [];

    // Binscatter points: {x: dist, y: price}
    const scatterPoints = bins.map(b => ({
        x: b.mean_distance_km,
        y: b.mean_price_sqm,
        n: b.n_obs,
        ci_l: b.ci_lower,
        ci_u: b.ci_upper
    }));

    // Non-parametric curve points
    const curvePoints = curve.map(c => ({
        x: c.distance_km,
        y: c.fitted_price_sqm
    }));

    decayChartInstance = new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                {
                    type: 'scatter',
                    label: 'Binned Averages (Binscatter N=25)',
                    data: scatterPoints,
                    backgroundColor: colors.primary,
                    borderColor: colors.navy,
                    borderWidth: 1.5,
                    pointRadius: 5,
                    pointHoverRadius: 8
                },
                {
                    type: 'line',
                    label: 'Non-Parametric LOESS / Polynomial Decay Fit',
                    data: curvePoints,
                    borderColor: colors.drag,
                    borderWidth: 2.5,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: isJournalTheme 
                        ? 'FIGURE 3. Distance Decay Gradient: Land Price per m² vs Distance from GIDC Boundary' 
                        : 'Spatial Distance Decay Gradient & Binscatter (0 to 10 km Buffer)',
                    font: { family: isJournalTheme ? 'Times New Roman' : 'inherit', size: 13, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const raw = context.raw;
                            if (raw.n) {
                                return [
                                    `Distance: ${raw.x} km`,
                                    `Mean Price: ₹${Number(raw.y).toLocaleString('en-IN')}/sqm`,
                                    `95% CI: [₹${Number(raw.ci_l).toLocaleString('en-IN')}, ₹${Number(raw.ci_u).toLocaleString('en-IN')}]`,
                                    `Observations in Bin: ${raw.n}`
                                ];
                            }
                            return `Fitted Price: ₹${Number(raw.y).toLocaleString('en-IN')}/sqm at ${raw.x} km`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    type: 'linear',
                    position: 'bottom',
                    title: { display: true, text: 'Distance from GIDC Estate Boundary (km)', font: { family: isJournalTheme ? 'Times New Roman' : 'inherit' } },
                    min: 0,
                    max: 10,
                    grid: { color: colors.grid }
                },
                y: {
                    title: { display: true, text: 'Land Price (INR / sqm)', font: { family: isJournalTheme ? 'Times New Roman' : 'inherit' } },
                    ticks: {
                        callback: val => '₹' + Number(val).toLocaleString('en-IN')
                    },
                    grid: { color: colors.grid }
                }
            }
        }
    });
}

// ----------------------------------------------------------------------------
// 4. Lifecycle Phase Distributional Box Plots
// ----------------------------------------------------------------------------
function initLifecycleDistributionPlot(canvasId, lifecycleData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !lifecycleData || !lifecycleData.length) return;

    if (lifecycleChartInstance) lifecycleChartInstance.destroy();

    const colors = getActiveColors();
    const labels = lifecycleData.map(d => d.phase_name.split(':')[0]);
    
    // We represent box plot stats using floating bar datasets for IQR [Q1, Q3]
    // and line points for Median and Mean
    const iqrBars = lifecycleData.map(d => [d.q1, d.q3]);
    const medians = lifecycleData.map(d => d.median);
    const means = lifecycleData.map(d => d.mean);

    lifecycleChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Interquartile Range [Q1 – Q3]',
                    data: iqrBars,
                    backgroundColor: isJournalTheme ? '#d1d5db' : 'rgba(59, 130, 246, 0.45)',
                    borderColor: isJournalTheme ? '#111827' : '#2563eb',
                    borderWidth: 1.5,
                    borderRadius: 4
                },
                {
                    type: 'line',
                    label: 'Median Price (50th %ile)',
                    data: medians,
                    borderColor: isJournalTheme ? '#000000' : '#10b981',
                    backgroundColor: isJournalTheme ? '#000000' : '#10b981',
                    borderWidth: 2.5,
                    pointRadius: 6,
                    pointStyle: 'rect',
                    fill: false
                },
                {
                    type: 'line',
                    label: 'Parametric Mean (μ)',
                    data: means,
                    borderColor: isJournalTheme ? '#444444' : '#f59e0b',
                    backgroundColor: isJournalTheme ? '#444444' : '#f59e0b',
                    borderWidth: 2,
                    borderDash: [4, 4],
                    pointRadius: 5,
                    pointStyle: 'circle',
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: isJournalTheme 
                        ? 'FIGURE 4. Price Dispersion & Market Outliers across Estate Lifecycle Phases' 
                        : 'Price Dispersion & Skewness across Industrial Lifecycle Phases 1–4',
                    font: { family: isJournalTheme ? 'Times New Roman' : 'inherit', size: 13, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const d = lifecycleData[context.dataIndex];
                            return [
                                `Phase: ${d.phase_name}`,
                                `Median: ₹${Number(d.median).toLocaleString('en-IN')}/sqm`,
                                `Mean: ₹${Number(d.mean).toLocaleString('en-IN')}/sqm`,
                                `IQR: [₹${Number(d.q1).toLocaleString('en-IN')}, ₹${Number(d.q3).toLocaleString('en-IN')}]`,
                                `Whiskers: [₹${Number(d.whisker_low).toLocaleString('en-IN')}, ₹${Number(d.whisker_high).toLocaleString('en-IN')}]`,
                                `Skewness: ${d.skewness} | Outliers: ${d.outliers_count}`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Industrial Estate Lifecycle Phase', font: { family: isJournalTheme ? 'Times New Roman' : 'inherit' } },
                    grid: { color: colors.grid }
                },
                y: {
                    title: { display: true, text: 'Land Price (INR / sqm)', font: { family: isJournalTheme ? 'Times New Roman' : 'inherit' } },
                    ticks: {
                        callback: val => '₹' + Number(val).toLocaleString('en-IN')
                    },
                    grid: { color: colors.grid }
                }
            }
        }
    });
}

// ----------------------------------------------------------------------------
// 5. Journal / Monochrome Theme Switcher (IEEE / Elsevier Format)
// ----------------------------------------------------------------------------
function toggleJournalTheme(esData, cfData, decayData, lifecycleData) {
    isJournalTheme = !isJournalTheme;
    const bodyEl = document.body;
    const btnText = document.getElementById('journalToggleBtnText');
    const badgeEl = document.getElementById('journalThemeBadge');

    if (isJournalTheme) {
        bodyEl.classList.add('journal-print-mode');
        if (btnText) btnText.innerText = 'Switch to Standard Theme';
        if (badgeEl) {
            badgeEl.className = 'badge bg-dark text-white border';
            badgeEl.innerText = 'Journal High-Contrast Mode ACTIVE';
        }
    } else {
        bodyEl.classList.remove('journal-print-mode');
        if (btnText) btnText.innerText = 'Journal / Print Theme (IEEE/Elsevier)';
        if (badgeEl) {
            badgeEl.className = 'badge bg-secondary-subtle text-secondary border';
            badgeEl.innerText = 'Standard Interactive Mode';
        }
    }

    // Re-initialize charts with updated color palette
    initEventStudyPlot('eventStudyCanvas', esData);
    initCounterfactualPlot('counterfactualCanvas', cfData);
    initDistanceDecayPlot('distanceDecayCanvas', decayData);
    initLifecycleDistributionPlot('lifecycleCanvas', lifecycleData);
}

// ----------------------------------------------------------------------------
// 6. Vector / High-Resolution Image Export (SVG / PNG / Print)
// ----------------------------------------------------------------------------
function exportChartImage(canvasId, filename, format = 'png') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    if (format === 'svg') {
        // Build simple SVG image container embedding raster data for high-res vector wrapper
        const dataUrl = canvas.toDataURL('image/png', 1.0);
        const svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}">
  <image href="${dataUrl}" width="${canvas.width}" height="${canvas.height}" />
</svg>`;
        const blob = new Blob([svgContent], { type: 'image/svg+xml;charset=utf-8' });
        const link = document.createElement('a');
        link.download = `${filename}.svg`;
        link.href = URL.createObjectURL(blob);
        link.click();
    } else {
        const link = document.createElement('a');
        link.download = `${filename}.png`;
        link.href = canvas.toDataURL('image/png', 1.0);
        link.click();
    }
}

// ----------------------------------------------------------------------------
// 7. Clipboard Copy Helper for Replication Codes
// ----------------------------------------------------------------------------
function copyToClipboard(elementId, successMsg) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const text = el.innerText || el.textContent;
    navigator.clipboard.writeText(text).then(() => {
        alert(successMsg || 'Code copied to clipboard successfully!');
    }).catch(err => {
        console.error('Failed to copy', err);
    });
}
