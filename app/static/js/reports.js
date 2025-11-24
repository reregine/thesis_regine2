// reports.js - Dedicated JavaScript for Incubatee Reports
let currentView = 'table';
let currentReportData = null;
let charts = {};

// Use different variable names to avoid conflict with admin.js
const currentDate = new Date().toISOString().split('T')[0];
const thirtyDaysAgo = new Date();
thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
const thirtyDaysAgoStr = thirtyDaysAgo.toISOString().split('T')[0];

document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('startDate').value = thirtyDaysAgoStr;
    document.getElementById('endDate').value = currentDate;
    
    // Generate initial report
    generateReport();
});


function setView(view) {
    currentView = view;
    
    // Update active button
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Show/hide views
    document.getElementById('tableView').classList.toggle('active', view === 'table');
    document.getElementById('cardsView').classList.toggle('active', view === 'cards');
    
    // Refresh display if we have data
    if (currentReportData) {
        displayReportData(currentReportData);
    }
}

async function generateReport() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const reportType = document.getElementById('reportType').value;

    if (!startDate || !endDate) {
        showNotification('Please select both start and end dates', 'error');
        return;
    }

    showLoadingState();

    try {
        const response = await fetch(`/admin/sales-summary?start_date=${startDate}&end_date=${endDate}&type=${reportType}`);
        const data = await response.json();
        
        if (data.success) {
            currentReportData = data;
            displayReportData(data);
            updateCharts(data);
            updateMetrics(data);
            showNotification('✅ Report generated successfully!', 'success');
        } else {
            throw new Error(data.error || 'Failed to generate report');
        }
    } catch (error) {
        console.error('Error generating report:', error);
        showNotification('Failed to generate report: ' + error.message, 'error');
        resetCharts();
    }
}

function showLoadingState() {
    document.getElementById('reportTableBody').innerHTML = `
        <tr>
            <td colspan="9" class="loading-state">Generating report...</td>
        </tr>
    `;
    document.getElementById('reportCards').innerHTML = '<div class="loading-state">Generating report...</div>';
    document.getElementById('incubateePerformance').innerHTML = '<div class="loading-state">Generating report...</div>';
}

function displayReportData(data) {
    displayTableData(data);
    displayCardData(data);
    displayIncubateePerformance(data);
}

function displayTableData(data) {
    const tbody = document.getElementById('reportTableBody');
    
    if (!data.sales_data || data.sales_data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="no-data">No sales data for the selected period</td></tr>';
        return;
    }

    tbody.innerHTML = data.sales_data.map(sale => `
        <tr>
            <td>${formatDateOnly(sale.sale_date)}</td>
            <td>#${sale.reservation_id}</td>
            <td>${escapeHtml(sale.incubatee_name)}</td>
            <td>${escapeHtml(sale.product_name)}</td>
            <td>${escapeHtml(sale.customer_name)}</td>
            <td>${sale.quantity}</td>
            <td>₱${sale.unit_price.toFixed(2)}</td>
            <td><strong>₱${sale.total_price.toFixed(2)}</strong></td>
            <td>
                <span class="status-badge status-${sale.status}">
                    ${sale.status}
                </span>
            </td>
        </tr>
    `).join('');
}

function displayCardData(data) {
    const container = document.getElementById('reportCards');
    
    if (!data.sales_data || data.sales_data.length === 0) {
        container.innerHTML = '<div class="no-data">No sales data for the selected period</div>';
        return;
    }

    container.innerHTML = data.sales_data.map(sale => `
        <div class="sale-card">
            <div class="sale-header">
                <div class="sale-id">Order #${sale.reservation_id}</div>
                <div class="sale-date">${formatDateOnly(sale.sale_date)}</div>
            </div>
            <div class="sale-info">
                <div class="sale-incubatee">
                    <strong>Incubatee:</strong> ${escapeHtml(sale.incubatee_name)}
                </div>
                <div class="sale-product">
                    <strong>Product:</strong> ${escapeHtml(sale.product_name)}
                </div>
                <div class="sale-customer">
                    <strong>Customer:</strong> ${escapeHtml(sale.customer_name)}
                </div>
            </div>
            <div class="sale-details">
                <div class="sale-quantity">Qty: ${sale.quantity}</div>
                <div class="sale-price">₱${sale.unit_price.toFixed(2)} each</div>
                <div class="sale-total"><strong>₱${sale.total_price.toFixed(2)}</strong></div>
            </div>
            <div class="sale-status">
                <span class="status-badge status-${sale.status}">
                    ${sale.status}
                </span>
            </div>
        </div>
    `).join('');
}

function displayIncubateePerformance(data) {
    const container = document.getElementById('incubateePerformance');
    
    if (!data.incubatee_performance || data.incubatee_performance.length === 0) {
        container.innerHTML = '<div class="no-data">No incubatee performance data</div>';
        return;
    }

    container.innerHTML = data.incubatee_performance.map(incubatee => `
        <div class="performance-card">
            <div class="performance-header">
                <h4>${escapeHtml(incubatee.name)}</h4>
                <span class="performance-rating ${getPerformanceRating(incubatee.revenue)}">
                    ${getPerformanceRating(incubatee.revenue)}
                </span>
            </div>
            <div class="performance-stats">
                <div class="performance-stat">
                    <span class="stat-value revenue">₱${incubatee.revenue.toFixed(2)}</span>
                    <span class="stat-label">Revenue</span>
                </div>
                <div class="performance-stat">
                    <span class="stat-value">${incubatee.order_count}</span>
                    <span class="stat-label">Orders</span>
                </div>
                <div class="performance-stat">
                    <span class="stat-value">${incubatee.product_count}</span>
                    <span class="stat-label">Products</span>
                </div>
                <div class="performance-stat">
                    <span class="stat-value">${incubatee.completion_rate}%</span>
                    <span class="stat-label">Completion</span>
                </div>
            </div>
            <div class="performance-trend">
                <div class="trend-label">Top Product:</div>
                <div class="trend-value">${escapeHtml(incubatee.top_product || 'N/A')}</div>
            </div>
        </div>
    `).join('');
}

function getPerformanceRating(revenue) {
    if (revenue > 10000) return 'Excellent';
    if (revenue > 5000) return 'Good';
    if (revenue > 1000) return 'Average';
    return 'Needs Improvement';
}

function updateMetrics(data) {
    document.getElementById('totalRevenue').textContent = '₱' + (data.summary?.total_revenue || 0).toFixed(2);
    document.getElementById('totalOrders').textContent = data.summary?.total_orders || 0;
    document.getElementById('completedOrders').textContent = data.summary?.completed_orders || 0;
    document.getElementById('completionRate').textContent = (data.summary?.completion_rate || 0) + '%';
    document.getElementById('activeIncubatees').textContent = data.summary?.active_incubatees || 0;
}

function updateCharts(data) {
    destroyCharts();
    
    // Revenue Trend Chart
    const revenueCtx = document.getElementById('revenueChart').getContext('2d');
    charts.revenue = new Chart(revenueCtx, {
        type: 'line',
        data: {
            labels: data.charts?.revenue_trend?.labels || [],
            datasets: [{
                label: 'Revenue',
                data: data.charts?.revenue_trend?.data || [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₱' + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });

    // Category Sales Chart
    const categoryCtx = document.getElementById('categoryChart').getContext('2d');
    charts.category = new Chart(categoryCtx, {
        type: 'doughnut',
        data: {
            labels: data.charts?.category_sales?.labels || [],
            datasets: [{
                data: data.charts?.category_sales?.data || [],
                backgroundColor: [
                    '#3b82f6', '#ef4444', '#10b981', '#f59e0b',
                    '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });

    // Top Incubatees Chart
    const incubateeCtx = document.getElementById('incubateeChart').getContext('2d');
    charts.incubatee = new Chart(incubateeCtx, {
        type: 'bar',
        data: {
            labels: data.charts?.top_incubatees?.labels || [],
            datasets: [{
                label: 'Revenue',
                data: data.charts?.top_incubatees?.data || [],
                backgroundColor: '#10b981'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '₱' + value.toFixed(2);
                        }
                    }
                }
            }
        }
    });

    // Status Distribution Chart
    const statusCtx = document.getElementById('statusChart').getContext('2d');
    charts.status = new Chart(statusCtx, {
        type: 'pie',
        data: {
            labels: data.charts?.status_distribution?.labels || [],
            datasets: [{
                data: data.charts?.status_distribution?.data || [],
                backgroundColor: [
                    '#f59e0b', // pending
                    '#3b82f6', // approved
                    '#10b981', // completed
                    '#ef4444'  // rejected
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function destroyCharts() {
    Object.values(charts).forEach(chart => {
        if (chart) {
            chart.destroy();
        }
    });
    charts = {};
}

function resetCharts() {
    destroyCharts();
    // Create empty charts
    updateCharts({ charts: {} });
}

async function exportReport() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const reportType = document.getElementById('reportType').value;

    if (!startDate || !endDate) {
        showNotification('Please select both start and end dates', 'error');
        return;
    }

    try {
        const response = await fetch(`/admin/export-report?start_date=${startDate}&end_date=${endDate}&type=${reportType}`);
        const blob = await response.blob();
        
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `incubatee-report-${startDate}-to-${endDate}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        
        showNotification('✅ Report exported successfully!', 'success');
    } catch (error) {
        console.error('Error exporting report:', error);
        showNotification('❌ Failed to export report', 'error');
    }
}

// Utility functions for reports
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function formatDateOnly(dateString) {
    if (!dateString) return '—';
    
    try {
        const date = new Date(dateString);
        
        if (isNaN(date.getTime())) {
            return 'Invalid Date';
        }
        
        const options = { year: 'numeric', month: 'short', day: 'numeric'};
        
        return date.toLocaleDateString('en-US', options);
    } catch (error) {
        console.error('Error formatting date:', error, dateString);
        return 'Invalid Date';
    }
}

// Notification function for reports page
function showNotification(message, type = 'info') {
    // Remove any existing notifications
    const existingNotifications = document.querySelectorAll('.custom-notification');
    existingNotifications.forEach(notification => notification.remove());
    
    const notification = document.createElement('div');
    notification.className = 'custom-notification';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateX(100%);
        transition: transform 0.3s ease;
        ${type === 'success' ? 'background: linear-gradient(135deg, #22c55e, #16a34a);' : ''}
        ${type === 'error' ? 'background: linear-gradient(135deg, #e63946, #d90429);' : ''}
        ${type === 'info' ? 'background: linear-gradient(135deg, #3b82f6, #1d4ed8);' : ''}
        ${type === 'warning' ? 'background: linear-gradient(135deg, #f59e0b, #d97706);' : ''}
    `;
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.style.transform = 'translateX(0)', 100);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }, 3000);
}

// Auto-refresh every 5 minutes
setInterval(() => {
    if (currentReportData) {
        generateReport();
    }
}, 300000); // 5 minutes

// Logout function for reports page
function logout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = '/admin/logout';
    }
}