// reports.js - Dedicated JavaScript for Incubatee Reports
let currentView = 'table';
let currentReportData = null;
let charts = {};
let currentFilterType = 'all';
let currentFilterValue = '';
let previewData = null;


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
    // Load filter options
    loadFilterOptions();
    
    // Initialize filter display
    toggleFilterOptions();
});

// New functions for filters and preview
async function loadFilterOptions() {
    try {
        // Load incubatees
        const incubateeResponse = await fetch('/admin/reports/get-incubatees');
        const incubateeData = await incubateeResponse.json();
        
        if (incubateeData.success) {
            const incubateeSelect = document.getElementById('incubateeFilter');
            incubateeSelect.innerHTML = '<option value="">Select incubatee...</option>';
            incubateeData.incubatees.forEach(inc => {
                incubateeSelect.innerHTML += `<option value="${inc.id}">${inc.name}</option>`;
            });
        }
        
        // Load categories
        const categoryResponse = await fetch('/admin/reports/get-categories');
        const categoryData = await categoryResponse.json();
        
        if (categoryData.success) {
            const categorySelect = document.getElementById('categoryFilter');
            categorySelect.innerHTML = '<option value="">Select category...</option>';
            categoryData.categories.forEach(cat => {
                categorySelect.innerHTML += `<option value="${cat}">${cat}</option>`;
            });
        }
    } catch (error) {
        console.error('Error loading filter options:', error);
    }
}

function toggleFilterOptions() {
    currentFilterType = document.getElementById('filterType').value;
    
    // Show/hide filter inputs
    document.getElementById('incubateeFilterGroup').style.display = 
        currentFilterType === 'incubatee' ? 'block' : 'none';
    document.getElementById('categoryFilterGroup').style.display = 
        currentFilterType === 'category' ? 'block' : 'none';
    
    // Reset filter values when switching types
    if (currentFilterType !== 'incubatee') {
        document.getElementById('incubateeFilter').value = '';
    }
    if (currentFilterType !== 'category') {
        document.getElementById('categoryFilter').value = '';
    }
}

async function previewReport() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const filterType = document.getElementById('filterType').value;
    
    // Get filter value
    let filterValue = '';
    if (filterType === 'incubatee') {
        filterValue = document.getElementById('incubateeFilter').value;
    } else if (filterType === 'category') {
        filterValue = document.getElementById('categoryFilter').value;
    }
    
    if (!startDate || !endDate) {
        showNotification('Please select both start and end dates', 'error');
        return;
    }
    
    if ((filterType === 'incubatee' || filterType === 'category') && !filterValue) {
        showNotification(`Please select a ${filterType}`, 'error');
        return;
    }
    
    showLoadingState();
    
    try {
        // Build query parameters
        let url = `/admin/reports/preview?start_date=${startDate}&end_date=${endDate}&filter=${filterType}`;
        if (filterType === 'incubatee' && filterValue) {
            url += `&incubatee_id=${filterValue}`;
        } else if (filterType === 'category' && filterValue) {
            url += `&category=${encodeURIComponent(filterValue)}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            previewData = data;
            displayPreview(data);
            showNotification('✅ Preview generated successfully!', 'success');
        } else {
            throw new Error(data.error || 'Failed to generate preview');
        }
    } catch (error) {
        console.error('Error generating preview:', error);
        showNotification('Failed to generate preview: ' + error.message, 'error');
    }
}

function displayPreview(data) {
    // Update preview summary
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const filterType = document.getElementById('filterType').value;
    let filterText = 'All Data';
    
    if (filterType === 'incubatee') {
        const incubateeSelect = document.getElementById('incubateeFilter');
        const selectedOption = incubateeSelect.options[incubateeSelect.selectedIndex];
        filterText = `Incubatee: ${selectedOption.text}`;
    } else if (filterType === 'category') {
        const categorySelect = document.getElementById('categoryFilter');
        const selectedOption = categorySelect.options[categorySelect.selectedIndex];
        filterText = `Category: ${selectedOption.text}`;
    }
    
    document.getElementById('preview-date-range').textContent = 
        `${startDate} to ${endDate}`;
    document.getElementById('preview-filter').textContent = filterText;
    document.getElementById('preview-revenue').textContent = 
        `₱${data.total_revenue.toFixed(2)}`;
    document.getElementById('preview-rows').textContent = 
        `${data.total_rows} rows${data.has_more_data ? ' (first 20 shown)' : ''}`;
    
    // Update preview table
    const tbody = document.getElementById('preview-table-body');
    if (data.preview_data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="no-data">No data found for the selected filters</td></tr>';
    } else {
        tbody.innerHTML = data.preview_data.map(row => `
            <tr>
                <td>${formatDateOnly(row.date)}</td>
                <td>#${row.order_id}</td>
                <td>${escapeHtml(row.incubatee)}</td>
                <td>${escapeHtml(row.product)}</td>
                <td>${escapeHtml(row.customer)}</td>
                <td>${row.quantity}</td>
                <td>₱${row.unit_price.toFixed(2)}</td>
                <td><strong>₱${row.total.toFixed(2)}</strong></td>
            </tr>
        `).join('');
    }
    
    // Show modal
    document.getElementById('preview-modal').classList.remove('hidden');
}

function closePreview() {
    document.getElementById('preview-modal').classList.add('hidden');
    previewData = null;
}

function generateFromPreview() {
    closePreview();
    generateReport();
}

function exportFromPreview() {
    closePreview();
    exportReport();
}

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

// Update generateReport function to include filters
async function generateReport() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const filterType = document.getElementById('filterType').value;
    
    // Get filter value
    let filterValue = '';
    if (filterType === 'incubatee') {
        filterValue = document.getElementById('incubateeFilter').value;
    } else if (filterType === 'category') {
        filterValue = document.getElementById('categoryFilter').value;
    }
    
    if (!startDate || !endDate) {
        showNotification('Please select both start and end dates', 'error');
        return;
    }
    
    if ((filterType === 'incubatee' || filterType === 'category') && !filterValue) {
        showNotification(`Please select a ${filterType}`, 'error');
        return;
    }
    
    showLoadingState();
    
    try {
        // Build query parameters
        let url = `/admin/reports/sales-summary?start_date=${startDate}&end_date=${endDate}&filter=${filterType}`;
        if (filterType === 'incubatee' && filterValue) {
            url += `&incubatee_id=${filterValue}`;
        } else if (filterType === 'category' && filterValue) {
            url += `&category=${encodeURIComponent(filterValue)}`;
        }
        
        const response = await fetch(url);
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
    // Only update elements that exist
    const tableBody = document.getElementById('reportTableBody');
    if (tableBody) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="9" class="loading-state">Generating report...</td>
            </tr>
        `;
    }
    
    const reportCards = document.getElementById('reportCards');
    if (reportCards) {
        reportCards.innerHTML = '<div class="loading-state">Generating report...</div>';
    }
    
    const incubateePerformance = document.getElementById('incubateePerformance');
    if (incubateePerformance) {
        incubateePerformance.innerHTML = '<div class="loading-state">Generating report...</div>';
    }
    
    // Update metrics to show loading state - FIXED: Use totalRevenue ID
    const totalRevenueElement = document.getElementById('totalRevenue');
    if (totalRevenueElement) {
        totalRevenueElement.textContent = '₱0.00';
    }
    
    const totalOrdersElement = document.getElementById('totalOrders');
    if (totalOrdersElement) {
        totalOrdersElement.textContent = '0';
    }
}

function displayReportData(data) {
    displayTableData(data);
    displayCardData(data);
    displayIncubateePerformance(data);
}

function displayTableData(data) {
    const tbody = document.getElementById('reportTableBody');
    if (!tbody) return;
    
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
    if (!container) return;
    
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
    if (!container) return;
    
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
                    <span class="stat-label">Total Sales</span>
                </div>
                <div class="performance-stat">
                    <span class="stat-value">${incubatee.order_count}</span>
                    <span class="stat-label">Orders</span>
                </div>
                <div class="performance-stat">
                    <span class="stat-value">${incubatee.product_count}</span>
                    <span class="stat-label">Products</span>
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
    // Update Total Revenue (keep ID as totalRevenue but label says Total Sales)
    const totalRevenueElement = document.getElementById('totalRevenue');
    if (totalRevenueElement) {
        totalRevenueElement.textContent = '₱' + (data.summary?.total_revenue || 0).toFixed(2);
    }
    
    // Update Total Orders
    const totalOrdersElement = document.getElementById('totalOrders');
    if (totalOrdersElement) {
        totalOrdersElement.textContent = data.summary?.total_orders || 0;
    }
    
    // The other metrics have been removed from HTML
}

function updateCharts(data) {
    destroyCharts();
    
    // Remove chart containers that don't exist anymore
    const chartsToRemove = ['revenueChart', 'statusChart'];
    chartsToRemove.forEach(id => {
        const chartElement = document.getElementById(id);
        if (chartElement && chartElement.parentElement) {
            chartElement.parentElement.remove();
        }
    });
    
    // Sales by Incubatee Chart (doughnut)
    const incubateeSalesCtx = document.getElementById('categoryChart');
    if (incubateeSalesCtx) {
        charts.incubateeSales = new Chart(incubateeSalesCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: data.charts?.incubatee_sales?.labels || [],
                datasets: [{
                    data: data.charts?.incubatee_sales?.data || [],
                    backgroundColor: [
                        '#3b82f6', '#ef4444', '#10b981', '#f59e0b',
                        '#8b5cf6', '#06b6d4', '#84cc16', '#f97316',
                        '#ec4899', '#6366f1'
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

    // Top Incubatees Chart
    const topIncubateeCtx = document.getElementById('incubateeChart');
    if (topIncubateeCtx) {
        charts.topIncubatees = new Chart(topIncubateeCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.charts?.top_incubatees?.labels || [],
                datasets: [{
                    label: 'Sales',
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
    }
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

// Update exportReport function to include filters
async function exportReport() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const filterType = document.getElementById('filterType').value;
    
    // Get filter value
    let filterValue = '';
    if (filterType === 'incubatee') {
        filterValue = document.getElementById('incubateeFilter').value;
    } else if (filterType === 'category') {
        filterValue = document.getElementById('categoryFilter').value;
    }
    
    if (!startDate || !endDate) {
        showNotification('Please select both start and end dates', 'error');
        return;
    }
    
    if ((filterType === 'incubatee' || filterType === 'category') && !filterValue) {
        showNotification(`Please select a ${filterType}`, 'error');
        return;
    }
    
    try {
        // Build query parameters
        let url = `/admin/reports/export?start_date=${startDate}&end_date=${endDate}&filter=${filterType}`;
        if (filterType === 'incubatee' && filterValue) {
            url += `&incubatee_id=${filterValue}`;
        } else if (filterType === 'category' && filterValue) {
            url += `&category=${encodeURIComponent(filterValue)}`;
        }
        
        const response = await fetch(url);
        const blob = await response.blob();
        
        const urlObject = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = urlObject;
        a.download = `report-${startDate}-to-${endDate}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(urlObject);
        
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