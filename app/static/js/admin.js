// Global variables
let allProducts = [];
const today = new Date();
const formattedDate = today.toISOString().split('T')[0]; 
// Auto-cancellation timeout in milliseconds (1 minute for testing)
//const AUTO_CANCEL_TIMEOUT = 60 * 1000; // 1 minute
// For production, use: 
const AUTO_CANCEL_TIMEOUT = 3 * 24 * 60 * 60 * 1000; // 3 days

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeAdmin();
});

function initializeAdmin() {
    // Auto display today's date
    document.getElementById("current-date").innerText = formattedDate;

    loadProducts(); // Load products when page loads

    initializeEventListeners(); // Initialize event listeners
    
    initializeIncubateeSearch(); // Initialize incubatee search

    startAutoCancellationChecker();  // Start auto-cancellation checker
}

function initializeEventListeners() {
    // Category filter event
    document.getElementById("categoryFilter").addEventListener("change", handleCategoryFilter);

    // Validation: Stock Number → Only numbers and dash
    document.getElementById("stock_no").addEventListener("input", function() {
        this.value = this.value.replace(/[^0-9-]/g, "");
    });

    // Validation: Offered Services → Only letters and spaces
    document.getElementById("products").addEventListener("input", function() {
        this.value = this.value.replace(/[^a-zA-Z\s]/g, "");
    });

    // Preview uploaded image
    document.getElementById("product_image").addEventListener("change", handleImagePreview);

    // Handle form submission
    document.getElementById("incubateeForm").addEventListener("submit", handleProductFormSubmit);

    // Logout functionality
    document.getElementById("confirm-logout").addEventListener("click", handleLogout);
    document.getElementById("cancel-logout").addEventListener("click", function() {
        document.getElementById("logout-modal").classList.add("hidden");
    });

    // Modal open/close logic
    initializeModalHandlers();
    
    // Incubatee add form submission
    initializeIncubateeAddForm();
    
    // Initialize orders modal
    initializeOrdersModal();
    // Initialize sales report modal
    initializeSalesReportModal();
}

function initializeModalHandlers() {
    const incubateeModal = document.getElementById("incubateeModal");
    const openIncubateeModal = document.getElementById("openIncubateeModal");
    const closeIncubateeModalTop = document.getElementById("closeIncubateeModalTop");
    const closeIncubateeModalBottom = document.getElementById("closeIncubateeModalBottom");

    // Open modal
    if (openIncubateeModal) {
        openIncubateeModal.addEventListener("click", () => {
            incubateeModal.classList.add("active");
        });
    }

    // Close modal from both buttons
    [closeIncubateeModalTop, closeIncubateeModalBottom].forEach(btn => {
        if (btn) {
            btn.addEventListener("click", () => {
                incubateeModal.classList.remove("active");
            });
        }
    });

    // Close modal when clicking outside
    if (incubateeModal) {
        incubateeModal.addEventListener("click", (e) => {
            if (e.target === incubateeModal) {
                incubateeModal.classList.remove("active");
            }
        });
    }
}

function initializeIncubateeAddForm() {
    const form = document.getElementById("incubateeAddForm");
    const modal = document.getElementById("incubateeModal");

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            const formData = {
                first_name: document.getElementById("first_name").value.trim(),
                middle_name: document.getElementById("middle_name").value.trim(),
                last_name: document.getElementById("last_name").value.trim(),
                company_name: document.getElementById("company_name").value.trim(),
                email: document.getElementById("email").value.trim(),
                phone_number: document.getElementById("phone_number").value.trim(),
                contact_info: document.getElementById("contact_info").value.trim(),
                batch: document.getElementById("batch").value.trim()
            };

            try {
                const res = await fetch("/admin/add-incubatee", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(formData)
                });

                const data = await res.json();

                if (data.success) {
                    showToast("✅ Incubatee added successfully!", "success");
                    form.reset();
                    modal.classList.remove("active");

                    // Refresh dropdown instantly
                    await refreshIncubateeDropdown();
                } else {
                    showToast("❌ " + (data.error || "Failed to add incubatee."), "error");
                }
            } catch (err) {
                console.error("Error:", err);
                showToast("⚠️ Error adding incubatee. Please try again.", "error");
            }
        });
    }
}

async function initializeIncubateeSearch() {
    const searchContainer = document.querySelector(".incubatee-search-container");
    const searchInput = document.getElementById("incubateeSearch");
    const dropdown = document.getElementById("incubateeDropdown");
    const hiddenInput = document.getElementById("incubatee_id");

    if (!searchInput || !dropdown || !hiddenInput) return;

    let incubatees = [];

    // Fetch incubatees from backend
    try {
        const res = await fetch("/admin/get-incubatees");
        const data = await res.json();
        if (data.success) incubatees = data.incubatees;
    } catch (err) {
        console.error("❌ Failed to load incubatees", err);
    }

    // Show filtered list as user types
    searchInput.addEventListener("input", () => {
        const query = searchInput.value.toLowerCase().trim();
        dropdown.innerHTML = "";

        if (!query) {
            dropdown.classList.add("hidden");
            return;
        }

        const filtered = incubatees.filter(i =>
            `${i.first_name} ${i.last_name} ${i.company_name || ""}`
                .toLowerCase()
                .includes(query)
        );

        if (filtered.length === 0) {
            dropdown.innerHTML = `<div class="dropdown-item empty">No matches found</div>`;
        } else {
            filtered.forEach(i => {
                const item = document.createElement("div");
                item.classList.add("dropdown-item");
                item.textContent = `${i.first_name} ${i.last_name} (${i.company_name || "No Company"})`;
                item.dataset.id = i.incubatee_id;
                item.addEventListener("click", () => {
                    searchInput.value = item.textContent;
                    hiddenInput.value = item.dataset.id;
                    dropdown.classList.add("hidden");
                });
                dropdown.appendChild(item);
            });
        }

        dropdown.classList.remove("hidden");
    });

    // Hide dropdown when clicking outside
    document.addEventListener("click", (e) => {
        if (!searchContainer.contains(e.target)) {
            dropdown.classList.add("hidden");
        }
    });
}

// Function to load all products from database
function loadProducts() {
    fetch("/admin/get-products")
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                allProducts = data.products; // store all
                displayProducts(allProducts);
            } else {
                console.error("Error loading products:", data.error);
                showEmptyState();
            }
        })
        .catch(error => {
            console.error("Error fetching products:", error);
            showEmptyState();
        });
}

function handleCategoryFilter(e) {
    const selectedCategory = e.target.value;
    if (selectedCategory === "all") {
        displayProducts(allProducts);
    } else {
        const filtered = allProducts.filter(p => p.category === selectedCategory);
        displayProducts(filtered);
    }
}

// Function to display products in the table
function displayProducts(products) {
    const tableBody = document.getElementById("product-list");
    
    if (products.length === 0) {
        showEmptyState();
        return;
    }

    tableBody.innerHTML = products.map(product => `
        <tr>
            <td>${escapeHtml(product.name)}</td>
            <td>${escapeHtml(product.stock_no)}</td>
            <td>${escapeHtml(product.products)}</td>
            <td>${product.stock_amount}</td>
            <td>₱${product.price_per_stocks.toFixed(2)}</td>
            <td>${product.pricing_unit}</td>
            <td>
                ${product.image_path ? 
                `<img src="/${product.image_path}" width="60" style="border-radius:6px;" alt="${escapeHtml(product.name)}">` : 
                'No Image'
                }
            </td>
            <td>${product.expiration_date}</td>
            <td>${product.warranty ? product.warranty : "—"}</td>
            <td>${product.added_on}</td>
            <td>
                <button class="btn-delete" onclick="deleteProduct(${product.incubatee_id})" title="Delete product">
                <span class="btn-delete-icon">🗑️</span>
                <span class="btn-delete-text">Delete</span>
                </button>
            </td>
        </tr>
    `).join('');
}

// Function to show empty state
function showEmptyState() {
    const tableBody = document.getElementById("product-list");
    tableBody.innerHTML = `
        <tr>
            <td colspan="9" style="text-align:center; color:#777; padding:20px;">
                No products added yet. Add your first product using the form on the left.
            </td>
        </tr>
    `;
}

function handleImagePreview(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById("preview-img");
            preview.src = e.target.result;
            preview.style.display = "block";
        };
        reader.readAsDataURL(file);
    }
}

function handleProductFormSubmit(event) {
    event.preventDefault();

    if (!this.checkValidity()) {
        this.reportValidity();
        return;
    }

    const saveBtn = this.querySelector(".btn");
    saveBtn.classList.add("btn-loading");
    saveBtn.textContent = "Saving...";
    
    const formData = new FormData();
    formData.append("incubatee_id", document.getElementById("incubatee_id").value);
    formData.append("name", document.getElementById("name").value);
    formData.append("stock_no", document.getElementById("stock_no").value);
    formData.append("products", document.getElementById("products").value);
    formData.append("stock_amount", document.getElementById("stock_amount").value);
    formData.append("price_per_stocks", document.getElementById("price_per_stocks").value);
    formData.append("details", document.getElementById("details").value);
    formData.append("category", document.getElementById("category").value);
    formData.append("warranty", document.getElementById("warranty").value);
    formData.append("expiration_date", document.getElementById("expiration_date").value);
    formData.append("added_on", formattedDate);

    // Append the image file
    const imageFile = document.getElementById("product_image").files[0];
    if (imageFile) {
        formData.append("product_image", imageFile);
    }

    // Send to backend
    fetch("/admin/add-product", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Reset form
            this.reset();
            document.getElementById("preview-img").style.display = "none";
            
            // Reload the product list to show the new product
            loadProducts();
            
            // Show success message
            showNotification("✅ Product saved successfully!", "success");
        } else {
            showNotification("⚠️ Error saving product: " + data.error, "error");
        }
    })
    .catch(error => {
        console.error("Error:", error);
        showNotification("⚠️ Failed to connect to server.", "error");
    })
    .finally(() => {
        saveBtn.classList.remove("btn-loading");
        saveBtn.textContent = "Save Product";
    });
}

// Enhanced delete product function with loading state
function deleteProduct(productId) {
    if (confirm("Are you sure you want to delete this product? This action cannot be undone.")) {
        const deleteBtn = event.target.closest('.btn-delete');
        
        // Add loading state
        if (deleteBtn) {
            deleteBtn.classList.add('loading');
            deleteBtn.innerHTML = '<span class="btn-delete-icon">🗑️</span><span class="btn-delete-text">Deleting...</span>';
        }
        
        fetch(`/admin/delete-product/${productId}`, {
            method: "DELETE"
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showNotification('✅ Product deleted successfully!', 'success');
                loadProducts(); // Reload the list
            } else {
                showNotification('⚠️ Error deleting product: ' + data.error, 'error');
            }
        })
        .catch(error => {
            console.error("Error:", error);
            showNotification('⚠️ Failed to delete product.', 'error');
        })
        .finally(() => {
            // Remove loading state
            if (deleteBtn) {
                deleteBtn.classList.remove('loading');
                deleteBtn.innerHTML = '<span class="btn-delete-icon">🗑️</span><span class="btn-delete-text">Delete</span>';
            }
        });
    }
}

async function refreshIncubateeDropdown() {
    const selectEl = document.getElementById("incubatee_id");
    if (!selectEl) return;

    try {
        const res = await fetch("/admin/get-incubatees");
        const data = await res.json();

        if (data.success && data.incubatees.length > 0) {
            selectEl.innerHTML = `<option value="">-- Select Incubatee --</option>`;
            data.incubatees.forEach((i) => {
                const option = document.createElement("option");
                option.value = i.incubatee_id;
                option.textContent = `${i.last_name}, ${i.first_name} (${i.company_name || "No Company"})`;
                selectEl.appendChild(option);
            });
        } else {
            selectEl.innerHTML = `<option value="">No incubatees found</option>`;
        }
    } catch (err) {
        console.error("Error refreshing dropdown:", err);
    }
}

// Logout functionality
function logout() {
    document.getElementById("logout-modal").classList.remove("hidden");
}

function handleLogout() {
    fetch('/login/logout', {
        method: 'GET',
        credentials: 'include'
    })
    .then(response => {
        window.location.href = '/login/';
    })
    .catch(error => {
        console.error('Logout error:', error);
        window.location.href = '/login/';
    });
}

// Helper function to prevent XSS
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Notification function for better UX
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        color: white;
        font-weight: 600;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        transform: translateX(100%);
        transition: transform 0.3s ease;
        ${type === 'success' ? 'background: linear-gradient(135deg, #22c55e, #16a34a);' : ''}
        ${type === 'error' ? 'background: linear-gradient(135deg, #e63946, #d90429);' : ''}
        ${type === 'info' ? 'background: linear-gradient(135deg, #3b82f6, #1d4ed8);' : ''}
    `;
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.style.transform = 'translateX(0)', 100);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Toast Notification
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.textContent = message;
    toast.className = `toast toast-${type}`;
    document.body.appendChild(toast);

    // basic styles
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === "success" ? "#16a34a" : type === "error" ? "#dc2626" : "#2563eb"};
        color: white;
        padding: 10px 18px;
        border-radius: 8px;
        font-weight: 600;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        opacity: 0;
        transform: translateY(-10px);
        transition: all 0.3s ease;
        z-index: 2000;
    `;
    setTimeout(() => {
        toast.style.opacity = "1";
        toast.style.transform = "translateY(0)";
    }, 50);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(-10px)";
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

let ordersRefreshInterval;

function startOrdersAutoRefresh() {
    // Refresh orders every 5 seconds when modal is open
    ordersRefreshInterval = setInterval(() => {
        const ordersModal = document.getElementById("ordersModal");
        if (ordersModal.classList.contains("active")) {
            const currentFilter = document.getElementById("orderStatusFilter").value;
            loadAllOrders(currentFilter);
        }
    }, 5000); // 5 seconds
}

function stopOrdersAutoRefresh() {
    if (ordersRefreshInterval) {
        clearInterval(ordersRefreshInterval);
    }
}
// Orders Modal Functions - Updated for pickup only
function initializeOrdersModal() {
    const ordersModal = document.getElementById("ordersModal");
    const openOrdersModal = document.getElementById("openOrdersModal");
    const closeOrdersModalTop = document.getElementById("closeOrdersModalTop");
    const closeOrdersModalBottom = document.getElementById("closeOrdersModalBottom");

    // Open modal
    if (openOrdersModal) {
        openOrdersModal.addEventListener("click", () => {
            ordersModal.classList.add("active");
            loadAllOrders(); // Load orders when modal opens
            startOrdersAutoRefresh(); // Start auto-refresh
        });
    }

    // Close modal from both buttons
    [closeOrdersModalTop, closeOrdersModalBottom].forEach(btn => {
        if (btn) {
            btn.addEventListener("click", () => {
                ordersModal.classList.remove("active");
                stopOrdersAutoRefresh(); // Stop auto-refresh
            });
        }
    });

    // Close modal when clicking outside
    if (ordersModal) {
        ordersModal.addEventListener("click", (e) => {
            if (e.target === ordersModal) {
                ordersModal.classList.remove("active");
                stopOrdersAutoRefresh(); // Stop auto-refresh
            }
        });
    }

    // Order status filter
    document.getElementById("orderStatusFilter").addEventListener("change", function() {
        loadAllOrders(this.value);
    });
}

//new function to start the auto-cancellation checker
function startAutoCancellationChecker() {
    // Check every 30 seconds for reservations that need to be auto-cancelled
    setInterval(() => {
        checkAndAutoCancelReservations();
    }, 30000); // Check every 30 seconds
    
    // Also check immediately when admin page loads
    checkAndAutoCancelReservations();
}

// New function to check and auto-cancel overdue reservations
async function checkAndAutoCancelReservations() {
    try {
        const response = await fetch('/reservations/check-overdue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                timeout_ms: AUTO_CANCEL_TIMEOUT
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.rejected_count > 0) {
            console.log(`Auto-rejected ${data.rejected_count} overdue reservations`);
            
            // Show notification
            showNotification(`⚠️ Auto-rejected ${data.rejected_count} overdue reservations`, "info");
            
            // If orders modal is open, refresh the orders list
            const ordersModal = document.getElementById("ordersModal");
            if (ordersModal && ordersModal.classList.contains("active")) {
                const currentFilter = document.getElementById("orderStatusFilter").value;
                loadAllOrders(currentFilter);
            }
        }
    } catch (error) {
        console.error('Error in auto-rejection check:', error);
    }
}

// Update the loadAllOrders function to include auto-cancellation check
function loadAllOrders(status = 'all') {
    const ordersList = document.getElementById("orders-list");
    ordersList.innerHTML = '<tr><td colspan="9" class="empty-orders">Loading orders...</td></tr>';

    fetch("/reservations/")
        .then(response => response.json())
        .then(reservations => {
            if (!Array.isArray(reservations)) {
                throw new Error('Invalid response format');
            }

            // 🔄 CRITICAL FIX: Process pending reservations first
            const pendingReservations = reservations.filter(r => r.status === 'pending');
            if (pendingReservations.length > 0) {
                // Trigger processing of pending reservations
                return fetch("/reservations/process-pending", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    }
                })
                .then(() => fetch("/reservations/")) // Re-fetch after processing
                .then(response => response.json());
            }
            return reservations;
        })
        .then(processedReservations => {
            // Filter by status if specified
            let filteredReservations = processedReservations;
            if (status !== 'all') {
                filteredReservations = processedReservations.filter(r => r.status === status);
            }

            displayOrders(filteredReservations);
            
            // Check for reservations that need auto-cancellation
            checkReservationsForAutoCancel(processedReservations);
        })
        .catch(error => {
            console.error("Error loading orders:", error);
            ordersList.innerHTML = '<tr><td colspan="9" class="empty-orders">Error loading orders. Please try again.</td></tr>';
        });
}

// New function to check reservations client-side and trigger auto-cancellation
function checkReservationsForAutoCancel(reservations) {
    const now = new Date().getTime();
    const overdueReservations = reservations.filter(reservation => {
        if (reservation.status !== 'approved') return false;
        
        const reservedTime = new Date(reservation.reserved_at).getTime();
        const timeDiff = now - reservedTime;
        
        return timeDiff > AUTO_CANCEL_TIMEOUT;
    });
    
    if (overdueReservations.length > 0) {
        console.log(`Found ${overdueReservations.length} overdue reservations for auto-cancellation`);
        // Trigger server-side auto-cancellation
        checkAndAutoCancelReservations();
    }
}

// Display orders in the table - Updated for automatic approval and overdue handling
function displayOrders(reservations) {
    const ordersList = document.getElementById("orders-list");
    
    if (reservations.length === 0) {
        ordersList.innerHTML = '<tr><td colspan="9" class="empty-orders">No orders found.</td></tr>';
        return;
    }

    ordersList.innerHTML = reservations.map(reservation => {
        // Calculate time remaining for auto-cancellation
        const reservedTime = new Date(reservation.reserved_at).getTime();
        const now = new Date().getTime();
        const timeDiff = now - reservedTime;
        const timeRemaining = AUTO_CANCEL_TIMEOUT - timeDiff;
        
        // Check if reservation is overdue
        const isOverdue = timeRemaining <= 0;
        
        let timeWarning = '';
        let statusDisplay = '';
        
        if (reservation.status === 'pending') {
            statusDisplay = '<span class="status-pending">Pending Auto-Approval</span>';
        } else if (reservation.status === 'approved') {
            if (isOverdue) {
                // Overdue - disable pickup button and show overdue warning
                statusDisplay = `
                    <button class="btn-pickup btn-disabled" disabled title="Overdue - Cannot pick up">
                        ⚠️ Overdue
                    </button>
                    <div class="time-warning overdue">
                        ⚠️ Will be auto-rejected soon
                    </div>
                `;
            } else {
                // Not overdue - show pickup button with countdown
                const minutesRemaining = Math.ceil(timeRemaining / (60 * 1000));
                timeWarning = `<div class="time-warning countdown">
                    ⏰ Auto-reject in ${minutesRemaining} min
                </div>`;
                
                statusDisplay = `
                    <button class="btn-pickup" onclick="completeReservation(${reservation.reservation_id})" title="Mark as Picked Up">
                        🎁 Pick Up
                    </button>
                    ${timeWarning}
                `;
            }
        } else if (reservation.status === 'completed') {
            statusDisplay = '<span class="status-completed">Completed</span>';
        } else if (reservation.status === 'rejected') {
            // Check if it's an auto-rejected reservation due to timeout
            if (reservation.rejected_reason && reservation.rejected_reason.includes('Not picked up on time')) {
                statusDisplay = '<span class="status-auto-rejected">Auto-Rejected (Not Picked Up)</span>';
            } else {
                statusDisplay = '<span class="status-rejected">Rejected: ' + (reservation.rejected_reason || 'Insufficient stock') + '</span>';
            }
        }

        return `
        <tr class="${isOverdue && reservation.status === 'approved' ? 'row-overdue' : ''} ${reservation.status === 'rejected' && reservation.rejected_reason && reservation.rejected_reason.includes('Not picked up on time') ? 'row-auto-rejected' : ''}">
            <td>#${reservation.reservation_id}</td>
            <td>${reservation.user_id}</td>
            <td><strong>${escapeHtml(reservation.product_name)}</strong></td>
            <td>${reservation.quantity}</td>
            <td>₱${(reservation.price_per_stocks || 0).toFixed(2)}</td>
            <td><strong>₱${((reservation.price_per_stocks || 0) * reservation.quantity).toFixed(2)}</strong></td>
            <td>
                <span class="status-badge status-${reservation.status}">
                    ${reservation.status}
                </span>
            </td>
            <td>${formatDateToExact(reservation.reserved_at)}</td>
            <td>
                <div class="order-actions">
                    ${statusDisplay}
                </div>
            </td>
        </tr>
        `;
    }).join('');
}

// Complete reservation (pick up)
function completeReservation(reservationId) {
    if (!confirm("Mark this order as completed/picked up?")) return;

    const button = event.target;
    button.classList.add('loading');
    button.textContent = 'Completing...';

    fetch(`/reservations/${reservationId}/status`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            status: "completed"
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            showNotification("✅ Order marked as completed/picked up!", "success");
            loadAllOrders(document.getElementById("orderStatusFilter").value);
        } else {
            showNotification(`❌ Error: ${data.error}`, "error");
            button.classList.remove('loading');
            button.textContent = '🎁 Pick Up';
        }
    })
    .catch(error => {
        console.error("Error completing reservation:", error);
        showNotification("❌ Failed to complete reservation", "error");
        button.classList.remove('loading');
        button.textContent = '🎁 Pick Up';
    });
}
// Sales Report Modal Functions
function initializeSalesReportModal() {
    const salesReportModal = document.getElementById("salesReportModal");
    const openSalesReportModal = document.getElementById("openSalesReportModal");
    const closeSalesReportModalTop = document.getElementById("closeSalesReportModalTop");
    const closeSalesReportModalBottom = document.getElementById("closeSalesReportModalBottom");

    // Open modal
    if (openSalesReportModal) {
        openSalesReportModal.addEventListener("click", () => {
            salesReportModal.classList.add("active");
            // Set today's date as default
            document.getElementById("reportDate").value = formattedDate;
            generateSalesReport();
        });
    }

    // Close modal from both buttons
    [closeSalesReportModalTop, closeSalesReportModalBottom].forEach(btn => {
        if (btn) {
            btn.addEventListener("click", () => {
                salesReportModal.classList.remove("active");
            });
        }
    });

    // Close modal when clicking outside
    if (salesReportModal) {
        salesReportModal.addEventListener("click", (e) => {
            if (e.target === salesReportModal) {
                salesReportModal.classList.remove("active");
            }
        });
    }
}

// Generate Sales Report
function generateSalesReport() {
    const reportDate = document.getElementById("reportDate").value;
    const salesReportList = document.getElementById("sales-report-list");
    
    salesReportList.innerHTML = '<tr><td colspan="9" class="empty-orders">Generating report...</td></tr>';

    fetch(`/reservations/sales-report?date=${reportDate}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                displaySalesReport(data.report);
                updateSalesSummary(data.summary);
            } else {
                throw new Error(data.error || 'Failed to generate report');
            }
        })
        .catch(error => {
            console.error("Error generating sales report:", error);
            salesReportList.innerHTML = '<tr><td colspan="9" class="empty-orders">Error generating report. Please try again.</td></tr>';
            resetSalesSummary();
        });
}

// Display Sales Report
function displaySalesReport(report) {
    const salesReportList = document.getElementById("sales-report-list");
    
    if (report.length === 0) {
        salesReportList.innerHTML = '<tr><td colspan="9" class="empty-orders">No sales data for selected date.</td></tr>';
        return;
    }

    salesReportList.innerHTML = report.map(sale => `
        <tr>
            <td>#${sale.reservation_id}</td>
            <td>${sale.user_id}</td>
            <td><strong>${escapeHtml(sale.product_name)}</strong></td>
            <td>${sale.quantity}</td>
            <td>₱${(sale.unit_price || 0).toFixed(2)}</td>
            <td><strong>₱${((sale.unit_price || 0) * sale.quantity).toFixed(2)}</strong></td>
            <td>
                <span class="status-badge status-${sale.status}">
                    ${sale.status}
                </span>
            </td>
            <td>${formatDateToExact(sale.reserved_at)}</td>
            <td>${sale.completed_at ? formatDateToExact(sale.completed_at) : '—'}</td>
        </tr>
    `).join('');
}

// Update Sales Summary
function updateSalesSummary(summary) {
    document.getElementById("totalSales").textContent = `₱${summary.total_sales.toFixed(2)}`;
    document.getElementById("totalOrders").textContent = summary.total_orders;
    document.getElementById("completedOrders").textContent = summary.completed_orders;
    document.getElementById("totalProducts").textContent = summary.total_products;
}

// Reset Sales Summary
function resetSalesSummary() {
    document.getElementById("totalSales").textContent = "₱0.00";
    document.getElementById("totalOrders").textContent = "0";
    document.getElementById("completedOrders").textContent = "0";
    document.getElementById("totalProducts").textContent = "0";
}

// Export Sales Report to CSV
function exportSalesReport() {
    const reportDate = document.getElementById("reportDate").value;
    
    fetch(`/reservations/sales-report/export?date=${reportDate}`)
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `sales-report-${reportDate}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            showNotification("✅ Sales report exported successfully!", "success");
        })
        .catch(error => {
            console.error("Error exporting sales report:", error);
            showNotification("❌ Failed to export sales report", "error");
        });
}

// Date formatting utility function with time
function formatDateToReadable(dateString) {
    if (!dateString) return '—';
    
    try {
        const date = new Date(dateString);
        
        // Check if date is valid
        if (isNaN(date.getTime())) {
            return 'Invalid Date';
        }
        
        const options = { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        };
        
        return date.toLocaleDateString('en-US', options);
    } catch (error) {
        console.error('Error formatting date:', error, dateString);
        return 'Invalid Date';
    }
}

// Alternative: More specific format if you want exactly "Oct 10, 2025 10:00 AM"
function formatDateToExact(dateString) {
    if (!dateString) return '—';
    
    try {
        const date = new Date(dateString);
        
        if (isNaN(date.getTime())) {
            return 'Invalid Date';
        }
        
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        
        const month = months[date.getMonth()];
        const day = date.getDate();
        const year = date.getFullYear();
        
        // Format time in 12-hour format
        let hours = date.getHours();
        let minutes = date.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        
        hours = hours % 12;
        hours = hours ? hours : 12; // the hour '0' should be '12'
        minutes = minutes < 10 ? '0' + minutes : minutes;
        
        const timeString = `${hours}:${minutes} ${ampm}`;
        
        return `${month} ${day}, ${year} ${timeString}`;
    } catch (error) {
        console.error('Error formatting date:', error, dateString);
        return 'Invalid Date';
    }
}

// Function for date only (without time)
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

// Function for time only in 12-hour format
function formatTimeOnly(dateString) {
    if (!dateString) return '—';
    
    try {
        const date = new Date(dateString);
        
        if (isNaN(date.getTime())) {
            return 'Invalid Date';
        }
        
        let hours = date.getHours();
        let minutes = date.getMinutes();
        const ampm = hours >= 12 ? 'PM' : 'AM';
        
        hours = hours % 12;
        hours = hours ? hours : 12; // the hour '0' should be '12'
        minutes = minutes < 10 ? '0' + minutes : minutes;
        
        return `${hours}:${minutes} ${ampm}`;
    } catch (error) {
        console.error('Error formatting time:', error, dateString);
        return 'Invalid Time';
    }
}

// Load pricing units when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadPricingUnits();
});

// Function to load pricing units
async function loadPricingUnits() {
    try {
        const response = await fetch('/admin/get-pricing-units');
        const data = await response.json();
        
        if (data.success) {
            const pricingUnitSelect = document.getElementById('pricing_unit');
            pricingUnitSelect.innerHTML = '<option value="" disabled selected>Select Pricing Unit</option>';
            
            data.pricing_units.forEach(unit => {
                const option = document.createElement('option');
                option.value = unit.unit_id;
                option.textContent = unit.unit_name;
                pricingUnitSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading pricing units:', error);
    }
}

// Add Pricing Unit Modal functionality
document.getElementById('addPricingUnitBtn').addEventListener('click', function() {
    document.getElementById('pricingUnitModal').style.display = 'block';
});

// Close Pricing Unit Modal
document.getElementById('closePricingUnitModal').addEventListener('click', function() {
    document.getElementById('pricingUnitModal').style.display = 'none';
});

document.getElementById('closePricingUnitModalBottom').addEventListener('click', function() {
    document.getElementById('pricingUnitModal').style.display = 'none';
});

// Handle Pricing Unit Form Submission
document.getElementById('pricingUnitForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const formData = {
        unit_name: document.getElementById('unit_name').value,
        unit_description: document.getElementById('unit_description').value
    };
    
    try {
        const response = await fetch('/admin/add-pricing-unit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✅ Pricing unit added successfully!');
            document.getElementById('pricingUnitForm').reset();
            document.getElementById('pricingUnitModal').style.display = 'none';
            loadPricingUnits(); // Reload the pricing units dropdown
        } else {
            alert('❌ Error: ' + data.error);
        }
    } catch (error) {
        console.error('Error adding pricing unit:', error);
        alert('❌ Error adding pricing unit');
    }
});

// User Management Functions
async function loadUsers() {
    try {
        const response = await fetch('/admin/get-users');
        const data = await response.json();
        
        if (data.success) {
            displayUsers(data.users);
        } else {
            console.error('Error loading users:', data.error);
        }
    } catch (error) {
        console.error('Error fetching users:', error);
    }
}

function displayUsers(users) {
    const container = document.getElementById('users-container');
    if (!container) return;
    
    if (users.length === 0) {
        container.innerHTML = '<p class="no-data">No users found.</p>';
        return;
    }
    
    container.innerHTML = users.map(user => `
        <div class="user-card">
            <div class="user-info">
                <h3>${escapeHtml(user.username)}</h3>
                <p>User ID: ${user.user_id}</p>
                <p>Joined: ${formatDateToReadable(user.created_at)}</p>
            </div>
            <div class="user-stats">
                <div class="stat">
                    <span class="stat-value">${user.total_reservations}</span>
                    <span class="stat-label">Total Reservations</span>
                </div>
                <div class="stat">
                    <span class="stat-value pending">${user.pending_reservations}</span>
                    <span class="stat-label">Pending</span>
                </div>
                <div class="stat">
                    <span class="stat-value approved">${user.approved_reservations}</span>
                    <span class="stat-label">Approved</span>
                </div>
                <div class="stat">
                    <span class="stat-value completed">${user.completed_reservations}</span>
                    <span class="stat-label">Completed</span>
                </div>
            </div>
        </div>
    `).join('');
}

// Incubatee Management Functions
async function loadIncubatees() {
    try {
        const response = await fetch('/admin/get-incubatees-list');
        const data = await response.json();
        
        if (data.success) {
            displayIncubatees(data.incubatees);
        } else {
            console.error('Error loading incubatees:', data.error);
        }
    } catch (error) {
        console.error('Error fetching incubatees:', error);
    }
}

function displayIncubatees(incubatees) {
    const container = document.getElementById('incubatees-container');
    if (!container) return;
    
    if (incubatees.length === 0) {
        container.innerHTML = '<p class="no-data">No incubatees found.</p>';
        return;
    }
    
    container.innerHTML = incubatees.map(incubatee => `
        <div class="incubatee-card ${incubatee.is_approved ? 'approved' : 'pending'}">
            <div class="incubatee-header">
                <h3>${escapeHtml(incubatee.full_name)}</h3>
                <button class="btn-toggle-approval ${incubatee.is_approved ? 'btn-approved' : 'btn-pending'}" 
                        onclick="toggleIncubateeApproval(${incubatee.incubatee_id})">
                    ${incubatee.is_approved ? '✅ Approved' : '⏳ Pending'}
                </button>
            </div>
            <div class="incubatee-info">
                <p><strong>Company:</strong> ${escapeHtml(incubatee.company_name || 'N/A')}</p>
                <p><strong>Email:</strong> ${escapeHtml(incubatee.email || 'N/A')}</p>
                <p><strong>Phone:</strong> ${escapeHtml(incubatee.phone || 'N/A')}</p>
                <p><strong>Batch:</strong> ${incubatee.batch || 'N/A'}</p>
            </div>
            <div class="incubatee-stats">
                <div class="stat">
                    <span class="stat-value">${incubatee.product_count}</span>
                    <span class="stat-label">Products</span>
                </div>
                <div class="stat">
                    <span class="stat-value">₱${incubatee.total_sales.toFixed(2)}</span>
                    <span class="stat-label">Total Sales</span>
                </div>
            </div>
            <div class="incubatee-footer">
                <small>Joined: ${formatDateOnly(incubatee.created_at)}</small>
            </div>
        </div>
    `).join('');
}

async function toggleIncubateeApproval(incubateeId) {
    if (!confirm('Are you sure you want to change the approval status?')) return;
    
    try {
        const response = await fetch(`/admin/toggle-incubatee-approval/${incubateeId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(data.message, 'success');
            loadIncubatees(); // Refresh the list
        } else {
            showNotification('Error: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error toggling approval:', error);
        showNotification('Failed to update approval status', 'error');
    }
}

// Sales Summary Functions
async function loadSalesSummary() {
    try {
        const response = await fetch('/admin/sales-summary');
        const data = await response.json();
        
        if (data.success) {
            displaySalesSummary(data.summary);
        } else {
            console.error('Error loading sales summary:', data.error);
        }
    } catch (error) {
        console.error('Error fetching sales summary:', error);
    }
}

function displaySalesSummary(summary) {
    // Update summary cards
    document.getElementById('total-revenue').textContent = `₱${summary.total_revenue.toFixed(2)}`;
    document.getElementById('total-orders').textContent = summary.total_orders;
    document.getElementById('completed-orders').textContent = summary.completed_orders;
    document.getElementById('completion-rate').textContent = `${summary.completion_rate.toFixed(1)}%`;
    
    // Display sales by incubatee
    const container = document.getElementById('sales-by-incubatee');
    if (container) {
        container.innerHTML = summary.sales_by_incubatee.map(sale => `
            <div class="sales-item">
                <div class="sales-info">
                    <h4>${escapeHtml(sale.name)}</h4>
                    <p>${escapeHtml(sale.company)}</p>
                </div>
                <div class="sales-stats">
                    <span class="sales-count">${sale.sales_count} sales</span>
                    <span class="sales-revenue">₱${sale.revenue.toFixed(2)}</span>
                </div>
            </div>
        `).join('');
    }
}

// Initialize all management sections
function initializeAdminManagement() {
    // Load users if on users page
    if (document.getElementById('users-container')) {
        loadUsers();
    }
    
    // Load incubatees if on incubatees page
    if (document.getElementById('incubatees-container')) {
        loadIncubatees();
    }
    
    // Load sales summary if on dashboard
    if (document.getElementById('total-revenue')) {
        loadSalesSummary();
    }
}

// Call this when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeAdminManagement();
});