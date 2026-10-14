// DiD Econometric Charts Engine using Chart.js

let trajectoryChart = null;
let barImpactChart = null;
let ratioChart = null;

const BUFFER_COLORS = {
    'Control (>10km)': '#64748b',
    'Clean Commercial (<0.3km)': '#3b82f6',
    '<0.5km': '#ef4444',
    '0.5-1.5km': '#10b981',
    '3-8km': '#8b5cf6'
};

function initTrajectoryChart(canvasId, trajectoryData, postYear = 2018) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    if (trajectoryChart) {
        trajectoryChart.destroy();
    }
    
    const datasets = [];
    for (const [groupName, values] of Object.entries(trajectoryData.series)) {
        datasets.push({
            label: groupName,
            data: values,
            borderColor: BUFFER_COLORS[groupName] || '#0284c7',
            backgroundColor: BUFFER_COLORS[groupName] || '#0284c7',
            borderWidth: groupName === '3-8km' || groupName === '<0.5km' ? 3 : 2,
            borderDash: groupName.includes('Control') ? [5, 5] : [],
            pointRadius: 4,
            pointHoverRadius: 6,
            tension: 0.25,
            fill: false
        });
    }
    
    trajectoryChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: trajectoryData.years,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Mean Property Price per Sqm by Spatial Buffer (2012–2025)',
                    font: { size: 14, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ₹${context.raw?.toLocaleString('en-IN') || 'N/A'}/sqm`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: { display: true, text: 'Sale Year' },
                    grid: { color: '#f1f5f9' }
                },
                y: {
                    title: { display: true, text: 'Price (INR / sqm)' },
                    ticks: {
                        callback: function(val) {
                            return '₹' + val.toLocaleString('en-IN');
                        }
                    },
                    grid: { color: '#f1f5f9' }
                }
            }
        }
    });
}

function initBarImpactChart(canvasId, barData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    if (barImpactChart) {
        barImpactChart.destroy();
    }
    
    barImpactChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: barData.labels,
            datasets: [{
                label: 'Net DiD Impact (%)',
                data: barData.values,
                backgroundColor: barData.colors,
                borderRadius: 6,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: 'Post-Event Net DiD Impact vs Control Baseline (%)',
                    font: { size: 14, weight: 'bold' }
                },
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const val = context.raw;
                            return `Impact: ${val >= 0 ? '+' : ''}${val.toFixed(2)}%`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    title: { display: true, text: 'Net Price Impact (%)' },
                    ticks: {
                        callback: function(val) {
                            return (val >= 0 ? '+' : '') + val + '%';
                        }
                    },
                    grid: {
                        color: function(context) {
                            return context.tick.value === 0 ? '#1e293b' : '#f1f5f9';
                        },
                        lineWidth: function(context) {
                            return context.tick.value === 0 ? 2 : 1;
                        }
                    }
                }
            }
        }
    });
}

function initRatioChart(canvasId, ratioData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    
    if (ratioChart) {
        ratioChart.destroy();
    }
    
    const datasets = [];
    for (const [groupName, values] of Object.entries(ratioData.series)) {
        datasets.push({
            label: groupName,
            data: values,
            borderColor: BUFFER_COLORS[groupName] || '#0284c7',
            borderWidth: 2,
            pointRadius: 3,
            tension: 0.2,
            fill: false
        });
    }
    
    ratioChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ratioData.years,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Circle Rate to Market Price Ratio (Statutory Sticky Lag)',
                    font: { size: 14, weight: 'bold' }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: ${context.raw} (${(context.raw * 100).toFixed(1)}%)`;
                        }
                    }
                }
            },
            scales: {
                x: { title: { display: true, text: 'Year' } },
                y: {
                    title: { display: true, text: 'Ratio (Circle Rate / Market Rate)' },
                    min: 0.5,
                    max: 1.0,
                    ticks: {
                        callback: function(val) {
                            return (val * 100).toFixed(0) + '%';
                        }
                    }
                }
            }
        }
    });
}
