
// Configuration
const LOW_STOCK_CONFIG = {
    LOW_STOCK_THRESHOLD: 10,      // ≤ 10 = low stock
    CRITICAL_THRESHOLD: 3,        // ≤ 3 = critical stock
    CHECK_INTERVAL: 30000,        // Check every 30 seconds
    NOTIFICATION_DURATION: 10000, // Notification shows for 10 seconds
    COOLDOWN_MINUTES: 5           // Don't show same notification within 5 minutes
};

// State
let lowStockProducts = [];
let isLowStockFilterActive = false;
let criticalStockNotified = false;


// Main initialization function
function initializeLowStockWarnings() {
    console.log('🔍 Initializing low stock warnings...');
    
    // Add low stock filter button to the filter bar
    addLowStockFilterButton();
    
    // Check for low stock products on page load
    checkLowStockProducts();
    
    // Set up periodic checking
    setInterval(checkLowStockProducts, LOW_STOCK_CONFIG.CHECK_INTERVAL);
    
    // Add CSS styles if not already added
    addLowStockStyles();
    updateLowStockCountBadge();
    console.log('✅ Low stock warnings initialized');
}

// Add low stock filter button to UI
function addLowStockFilterButton() {
    const filterBar = document.querySelector('.filter-bar');
    if (!filterBar || document.querySelector('.low-stock-filter-btn')) return;
    
    const lowStockBtn = document.createElement('button');
    lowStockBtn.className = 'low-stock-filter-btn';
    lowStockBtn.id = 'lowStockFilterBtn';
    lowStockBtn.innerHTML = `
        <span class="icon">⚠️</span>
        Low Stock
        <span class="low-stock-badge-count" id="lowStockCount">0</span>
    `;
    lowStockBtn.title = 'Show low stock items only';
    lowStockBtn.addEventListener('click', toggleLowStockFilter);
    
    // Insert after the category filter
    const categoryFilter = document.getElementById('categoryFilter');
    if (categoryFilter && categoryFilter.parentNode) {
        categoryFilter.parentNode.insertBefore(lowStockBtn, categoryFilter.nextSibling);
    } else {
        filterBar.appendChild(lowStockBtn);
    }
}

// Check low stock (handle HTML errors)
function checkLowStockProducts() {
    console.log('🔍 Checking low stock...');
    
    fetch('/admin/check-low-stock')
        .then(response => {
            // First check if response is OK
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Check content type to ensure it's JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error(`Expected JSON but got: ${contentType}`);
            }
            
            return response.json();
        })
        .then(data => {
            if (data.success) {
                lowStockProducts = data.products || [];
                updateLowStockCountBadge();
                
                // Update visual indicators
                updateLowStockIndicators();
                
                // Check for critical notifications
                const criticalProducts = lowStockProducts.filter(product => 
                    product.current_stock <= LOW_STOCK_CONFIG.CRITICAL_THRESHOLD
                );
                
                if (criticalProducts.length > 0 && !criticalStockNotified) {
                    showCriticalStockNotification(criticalProducts);
                    criticalStockNotified = true;
                    
                    setTimeout(() => {
                        criticalStockNotified = false;
                    }, LOW_STOCK_CONFIG.COOLDOWN_MINUTES * 60 * 1000);
                }
            } else {
                console.error('Error checking low stock:', data.error);
                showNotification('❌ Error checking low stock: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error('Error fetching low stock:', error);
            
            // Try to get text response to see what's being returned
            fetch('/admin/check-low-stock')
                .then(res => res.text())
                .then(text => {
                    console.error('Response text (first 200 chars):', text.substring(0, 200));
                    
                    // Check if it's an HTML error page
                    if (text.includes('<html>') || text.includes('<!DOCTYPE')) {
                        showNotification('⚠️ Session expired. Please refresh the page.', 'warning');
                        // Optionally redirect to login
                        // setTimeout(() => { window.location.reload(); }, 3000);
                    }
                })
                .catch(e => {
                    console.error('Could not get response text:', e);
                });
        });
}

function updateLowStockDisplay(data) {
    if (!data) return;
    
    // Update the low stock count badge
    const lowStockCount = data.total_low_stock || 0;
    const lowStockCountElement = document.getElementById('lowStockCount');
    if (lowStockCountElement) {
        lowStockCountElement.textContent = lowStockCount;
    }
    
    // Update the filter button state
    const lowStockBtn = document.getElementById('lowStockFilterBtn');
    if (lowStockBtn) {
        lowStockBtn.style.display = 'flex';
        if (lowStockCount === 0) {
            lowStockBtn.disabled = true;
            lowStockBtn.title = 'No low stock items';
        } else {
            lowStockBtn.disabled = false;
            lowStockBtn.title = isLowStockFilterActive 
                ? 'Showing low stock items only (click to show all)' 
                : 'Show low stock items only';
        }
    }
    
    // If low stock filter is active, refresh the display
    if (isLowStockFilterActive) {
        applyLowStockFilter();
    }
    
    // Update visual indicators
    updateLowStockIndicators();
    
    // Check for critical stock notifications
    const criticalProducts = lowStockProducts.filter(product => 
        product.current_stock <= LOW_STOCK_CONFIG.CRITICAL_THRESHOLD
    );
    
    if (criticalProducts.length > 0 && !criticalStockNotified) {
        showCriticalStockNotification(criticalProducts);
        criticalStockNotified = true;
        
        // Reset after cooldown period
        setTimeout(() => {
            criticalStockNotified = false;
        }, LOW_STOCK_CONFIG.COOLDOWN_MINUTES * 60 * 1000);
    }
}

// Update low stock indicators on displayed products
function updateLowStockIndicators() {
    const productRows = document.querySelectorAll('#product-list tr[data-product-id]');
    
    productRows.forEach(row => {
        const productId = parseInt(row.getAttribute('data-product-id'));
        // Try to find product in server data first, then fall back to window.allProducts
        let product = lowStockProducts.find(p => p.product_id == productId);
        
        if (!product && window.allProducts) {
            product = window.allProducts.find(p => p.product_id == productId);
        }
        
        if (product) {
            updateProductRowWarning(row, product);
        } else {
            // Clear warning for products that are not low stock
            clearStockCellWarning(row);
        }
    });
}

// Update individual product row with warning indicators
function updateProductRowWarning(row, product) {
    // Remove existing badges
    const existingBadge = row.querySelector('.low-stock-badge');
    if (existingBadge) {
        existingBadge.remove();
    }
    
    // Remove existing classes
    row.classList.remove('low-stock-row', 'critical-stock-row');
    
    // Determine stock amount (handle both data formats)
    const stockAmount = product.current_stock || product.stock_amount;
    
    // Check stock level
    if (stockAmount <= LOW_STOCK_CONFIG.CRITICAL_THRESHOLD) {
        // Critical stock (≤ 3)
        row.classList.add('critical-stock-row');
        addLowStockBadge(row, stockAmount, 'critical');
        updateStockCellWarning(row, product, 'critical');
    } else if (stockAmount <= LOW_STOCK_CONFIG.LOW_STOCK_THRESHOLD) {
        // Low stock (4-10)
        row.classList.add('low-stock-row');
        addLowStockBadge(row, stockAmount, 'low');
        updateStockCellWarning(row, product, 'low');
    } else {
        // Normal stock - remove any warnings
        clearStockCellWarning(row);
    }
}

// Add low stock badge to a row
function addLowStockBadge(row, stockAmount, severity = 'low') {
    const badge = document.createElement('div');
    badge.className = `low-stock-badge ${severity === 'critical' ? 'critical-stock-badge' : ''}`;
    
    if (severity === 'critical') {
        badge.textContent = `CRITICAL: ${stockAmount}`;
        badge.title = `CRITICAL STOCK! Only ${stockAmount} units left. Restock immediately!`;
    } else {
        badge.textContent = `LOW: ${stockAmount}`;
        badge.title = `Low stock: ${stockAmount} units remaining. Consider restocking.`;
    }
    
    // Position the badge on the right side of the row
    const lastCell = row.querySelector('td:last-child');
    if (lastCell) {
        lastCell.style.position = 'relative';
        lastCell.appendChild(badge);
    }
}

// Update stock cell with warning
function updateStockCellWarning(row, product, severity) {
    const stockCell = row.querySelector('td:nth-child(4)');
    if (!stockCell) return;
    
    stockCell.classList.add(severity === 'critical' ? 'stock-count-critical' : 'stock-count-low');
    
    // Get stock amount from either format
    const stockAmount = product.current_stock || product.stock_amount;
    
    const tooltipText = severity === 'critical' 
        ? `🔥 CRITICAL STOCK!<br>Only ${stockAmount} units remaining.<br>Please restock immediately!`
        : `⚠️ LOW STOCK!<br>Only ${stockAmount} units remaining.<br>Consider restocking soon.`;
    
    // Preserve any existing content or use stock amount
    const currentContent = stockCell.textContent.trim();
    const stockNumber = currentContent.split(' ')[0] || stockAmount;
    
    stockCell.innerHTML = `
        ${stockNumber}
        <div class="stock-warning-tooltip" style="display: inline-block; margin-left: 5px;">
            ${severity === 'critical' ? '🔥' : '⚠️'}
            <span class="tooltip-text">
                ${tooltipText}
            </span>
        </div>
    `;
}

// Clear stock cell warning
function clearStockCellWarning(row) {
    const stockCell = row.querySelector('td:nth-child(4)');
    if (stockCell) {
        stockCell.classList.remove('stock-count-low', 'stock-count-critical');
        if (stockCell.querySelector('.stock-warning-tooltip')) {
            const productId = row.getAttribute('data-product-id');
            const product = window.allProducts.find(p => p.product_id == productId);
            if (product) {
                stockCell.innerHTML = product.stock_amount;
            }
        }
    }
}

// Update low stock count badge
function updateLowStockCountBadge() {
    const lowStockCount = document.getElementById('lowStockCount');
    if (lowStockCount) {
        lowStockCount.textContent = lowStockProducts.length;
        
        // Add animation if there are low stock items
        if (lowStockProducts.length > 0) {
            lowStockCount.classList.add('pulse');
            setTimeout(() => lowStockCount.classList.remove('pulse'), 1000);
        }
    }
    
    // Update the filter button state
    const lowStockBtn = document.getElementById('lowStockFilterBtn');
    if (lowStockBtn) {
        lowStockBtn.style.display = 'flex';
        if (lowStockProducts.length === 0) {
            lowStockBtn.disabled = true;
            lowStockBtn.title = 'No low stock items';
        } else {
            lowStockBtn.disabled = false;
            lowStockBtn.title = isLowStockFilterActive 
                ? 'Showing low stock items only (click to show all)' 
                : 'Show low stock items only';
        }
    }
}

// Toggle low stock filter
function toggleLowStockFilter() {
    const lowStockBtn = document.getElementById('lowStockFilterBtn');
    isLowStockFilterActive = !isLowStockFilterActive;
    
    if (lowStockBtn) {
        if (isLowStockFilterActive) {
            lowStockBtn.classList.add('active');
            lowStockBtn.title = 'Showing low stock items only (click to show all)';
            applyLowStockFilter();
        } else {
            lowStockBtn.classList.remove('active');
            lowStockBtn.title = 'Show low stock items only';
            // Use the displayProducts function from admin.js
            if (typeof window.displayProducts === 'function') {
                window.displayProducts(window.allProducts);
            }
        }
    }
}

// Apply low stock filter
function applyLowStockFilter() {
    if (lowStockProducts.length > 0) {
        // Use the displayProducts function from admin.js
        if (typeof window.displayProducts === 'function') {
            window.displayProducts(lowStockProducts);
        }
    } else {
        // If no low stock products, show message
        const tableBody = document.getElementById("product-list");
        if (tableBody) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="11" style="text-align:center; color:#777; padding:20px;">
                        🎉 No low stock products! All items have sufficient inventory.
                    </td>
                </tr>
            `;
        }
    }
}

// Check for critical stock notifications
function checkCriticalStockNotifications() {
    const criticalProducts = lowStockProducts.filter(product => 
        product.stock_amount <= LOW_STOCK_CONFIG.CRITICAL_THRESHOLD
    );
    
    // Only show notification for new critical items (to avoid spamming)
    if (criticalProducts.length > 0 && !criticalStockNotified) {
        showCriticalStockNotification(criticalProducts);
        criticalStockNotified = true;
        
        // Reset after cooldown period
        setTimeout(() => {
            criticalStockNotified = false;
        }, LOW_STOCK_CONFIG.COOLDOWN_MINUTES * 60 * 1000);
    }
}

// Show critical stock notification
function showCriticalStockNotification(criticalProducts) {
    // Create floating notification
    const notification = document.createElement('div');
    notification.id = 'criticalStockNotification';
    notification.className = 'critical-stock-notification';
    
    let notificationHTML = `
        <div class="critical-notification-header">
            <span class="critical-icon">🔥</span>
            <strong>CRITICAL STOCK ALERT!</strong>
            <button class="close-critical-notification" onclick="this.parentElement.parentElement.remove()">&times;</button>
        </div>
        <div class="critical-notification-body">
            <p>${criticalProducts.length} product(s) have critically low stock:</p>
            <ul>
    `;
    
    criticalProducts.slice(0, 3).forEach(product => {
        // Handle both data formats
        const productName = product.product_name || product.name;
        const incubateeName = product.incubatee_name || (window.allProducts?.find(p => p.product_id == product.product_id)?.incubatee_name) || 'Unknown';
        const stockAmount = product.current_stock || product.stock_amount;
        
        notificationHTML += `
            <li>
                <strong>${escapeHtml(productName)}</strong> 
                (${escapeHtml(incubateeName)}): 
                <span class="critical-count">${stockAmount} units left</span>
            </li>
        `;
    });
    
    if (criticalProducts.length > 3) {
        notificationHTML += `<li>...and ${criticalProducts.length - 3} more</li>`;
    }
    
    notificationHTML += `
            </ul>
            <p>Please contact incubatees for immediate restocking.</p>
        </div>
        <div class="critical-notification-actions">
            <button class="btn-view-low-stock" onclick="window.toggleLowStockFilter(); this.parentElement.parentElement.remove();">
                🔍 View All Low Stock
            </button>
        </div>
    `;
    
    notification.innerHTML = notificationHTML;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }
    }, LOW_STOCK_CONFIG.NOTIFICATION_DURATION);
}

// Add CSS styles for low stock warnings
function addLowStockStyles() {
    if (document.querySelector('#low-stock-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'low-stock-styles';
    style.textContent = `
        /* Low Stock Warning Styles */
        .low-stock-badge {
            position: absolute;
            top: -8px;
            right: -8px;
            background: linear-gradient(135deg, #f59e0b, #dc2626);
            color: white;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 10px;
            font-weight: bold;
            z-index: 10;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            animation: pulse 2s infinite;
            white-space: nowrap;
        }
        
        .low-stock-badge::before {
            content: "⚠️ ";
        }
        
        .low-stock-row {
            position: relative;
            background-color: #fff7ed !important;
            border-left: 4px solid #f59e0b;
        }
        
        .low-stock-row:hover {
            background-color: #fed7aa !important;
        }
        
        .critical-stock-row {
            background-color: #fef2f2 !important;
            border-left: 4px solid #dc2626;
        }
        
        .critical-stock-row:hover {
            background-color: #fecaca !important;
        }
        
        .critical-stock-badge {
            background: linear-gradient(135deg, #dc2626, #991b1b);
            animation: pulse 1s infinite;
        }
        
        .critical-stock-badge::before {
            content: "🔥 ";
        }
        
        .stock-count-low {
            color: #dc2626;
            font-weight: bold;
            animation: blink 1.5s infinite;
        }
        
        .stock-count-critical {
            color: #dc2626;
            font-weight: bold;
            animation: blink 1s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Low stock filter button */
        .low-stock-filter-btn {
            background: #f59e0b;
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 5px;
            transition: all 0.3s;
            margin-left: 10px;
        }
        
        .low-stock-filter-btn:hover:not(:disabled) {
            background: #d97706;
        }
        
        .low-stock-filter-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .low-stock-filter-btn.active {
            background: #dc2626;
            box-shadow: 0 2px 4px rgba(220, 38, 38, 0.3);
        }
        
        .low-stock-badge-count {
            background: white;
            color: #dc2626;
            border-radius: 50%;
            width: 18px;
            height: 18px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            font-weight: bold;
            margin-left: 5px;
        }
        
        /* Tooltip for stock warning */
        .stock-warning-tooltip {
            position: relative;
            display: inline-block;
        }
        
        .stock-warning-tooltip .tooltip-text {
            visibility: hidden;
            width: 200px;
            background-color: #333;
            color: #fff;
            text-align: center;
            border-radius: 6px;
            padding: 8px;
            position: absolute;
            z-index: 1000;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 12px;
            font-weight: normal;
        }
        
        .stock-warning-tooltip:hover .tooltip-text {
            visibility: visible;
            opacity: 1;
        }
        
        /* Critical stock notification */
        .critical-stock-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            width: 350px;
            background: linear-gradient(135deg, #dc2626, #991b1b);
            color: white;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(220, 38, 38, 0.3);
            z-index: 9999;
            animation: slideIn 0.5s ease;
            overflow: hidden;
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .critical-notification-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 15px;
            background: rgba(0, 0, 0, 0.2);
            font-size: 14px;
        }
        
        .critical-icon {
            font-size: 18px;
            margin-right: 8px;
        }
        
        .close-critical-notification {
            background: none;
            border: none;
            color: white;
            font-size: 20px;
            cursor: pointer;
            padding: 0;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .close-critical-notification:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        .critical-notification-body {
            padding: 15px;
            font-size: 13px;
            background: white;
            color: #333;
        }
        
        .critical-notification-body ul {
            margin: 10px 0;
            padding-left: 20px;
        }
        
        .critical-notification-body li {
            margin: 5px 0;
        }
        
        .critical-count {
            color: #dc2626;
            font-weight: bold;
        }
        
        .critical-notification-actions {
            padding: 12px 15px;
            background: rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        
        .btn-view-low-stock {
            background: white;
            color: #dc2626;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }
        
        .btn-view-low-stock:hover {
            background: #f0f0f0;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
    `;
    
    document.head.appendChild(style);
}
// Send email notifications to incubatees
function sendLowStockEmails() {
    if (!confirm('Send low stock email notifications to incubatees?')) {
        return;
    }
    
    const emailBtn = document.querySelector('.btn-email-notify');
    const originalText = emailBtn.textContent;
    emailBtn.textContent = 'Sending...';
    emailBtn.disabled = true;
    emailBtn.classList.add('sending');
    
    // SIMPLE: Just call the server endpoint
    fetch('/admin/send-low-stock-notifications', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`✅ Sent ${data.notifications_sent} email notifications`, 'success');
            
            // Show success details
            if (data.sent_emails && data.sent_emails.length > 0) {
                showEmailSuccessModal(data);
            }
            
            // Refresh the low stock list
            checkLowStockProducts();
        } else {
            showNotification('❌ Error sending emails: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Error sending emails:', error);
        showNotification('❌ Failed to send emails', 'error');
    })
    .finally(() => {
        emailBtn.textContent = originalText;
        emailBtn.disabled = false;
        emailBtn.classList.remove('sending');
    });
}

// Export functions for use in admin.js
window.lowStockModule = {
    initializeLowStockWarnings,
    checkLowStockProducts,
    toggleLowStockFilter,
    updateLowStockIndicators,
    showLowStockWarning: function(productName, stockAmount) {
        const severity = stockAmount <= 3 ? 'critical' : 'low';
        const icon = severity === 'critical' ? '🔥' : '⚠️';
        const message = `${icon} ${severity.toUpperCase()} STOCK: "${productName}" has ${stockAmount} units left`;
        
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, severity === 'critical' ? 'error' : 'warning');
        }
    }
};

// Helper function (redefined here for standalone use)
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}