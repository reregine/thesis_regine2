// incubatees.js - Incubatee Management JavaScript
let allIncubatees = [];
let currentFilter = 'all';
let editingIncubateeId = null;

// API Service Functions
class IncubateeAPI {
    static async getIncubateeLogo(incubateeId) {
        try {
            const response = await fetch(`/admin/get-incubatee-logo/${incubateeId}`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching incubatee logo:', error);
            return { success: false, error: 'Failed to load logo' };
        }
    }

    static async getIncubateeDetails(incubateeId) {
        try {
            const response = await fetch(`/admin/get-incubatee-details/${incubateeId}`);
            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Error fetching incubatee details:', error);
            return { success: false, error: 'Failed to load incubatee details' };
        }
    }

    static async loadAllIncubateeLogos() {
        const logoContainers = document.querySelectorAll('.incubatee-avatar');
        
        logoContainers.forEach(async (container) => {
            const incubateeId = container.getAttribute('data-incubatee-id');
            if (!incubateeId) return;

            try {
                const result = await this.getIncubateeLogo(incubateeId);
                
                if (result.success && result.logo_url) {
                    const img = container.querySelector('img.avatar-logo');
                    if (img) {
                        img.src = result.logo_url;
                        img.style.display = 'block';
                        const placeholder = container.querySelector('.avatar-placeholder');
                        if (placeholder) placeholder.style.display = 'none';
                    }
                }
            } catch (error) {
                console.error(`Error loading logo for incubatee ${incubateeId}:`, error);
            }
        });
    }
}

// Load incubatees when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeIncubateesPage();
    initializeFileUpload();

});

function initializeIncubateesPage() {
    loadIncubatees();
    initializeIncubateesEventListeners();
    initializeIncubateeModalHandlers();
    // Load logos after a short delay to ensure DOM is ready
    setTimeout(() => {
        IncubateeAPI.loadAllIncubateeLogos();
    }, 500);
}

function initializeIncubateesEventListeners() {
    // Handle add incubatee form submission
    const addForm = document.getElementById('addIncubateeForm');
    if (addForm) {
        addForm.addEventListener('submit', handleAddIncubatee);
    }

    // Handle edit incubatee form submission
    const editForm = document.getElementById('editIncubateeForm');
    if (editForm) {
        editForm.addEventListener('submit', handleEditIncubatee);
    }

    // Close modals when clicking outside
    const addModal = document.getElementById('addIncubateeModal');
    const editModal = document.getElementById('editIncubateeModal');
    const detailsModal = document.getElementById('incubateeDetailsModal');
    const incubateeModal = document.getElementById('incubateeModal');

    if (addModal) {
        addModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeAddIncubateeModal();
            }
        });
    }

    if (editModal) {
        editModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeEditIncubateeModal();
            }
        });
    }

    if (detailsModal) {
        detailsModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeIncubateeModal();
            }
        });
    }

    if (incubateeModal) {
        incubateeModal.addEventListener('click', function(e) {
            if (e.target === this) {
                closeIncubateeAddModal();
            }
        });
    }

    // Initialize logo preview for edit modal
    const editLogoInput = document.getElementById('edit_company_logo');
    if (editLogoInput) {
        editLogoInput.addEventListener('change', handleEditLogoPreview);
    }

    // Initialize logo preview for add modal
    const addLogoInput = document.getElementById('company_logo');
    if (addLogoInput) {
        addLogoInput.addEventListener('change', handleLogoPreview);
    }
}

function initializeIncubateeModalHandlers() {
    const incubateeModal = document.getElementById("incubateeModal");
    const openIncubateeModalBtn = document.querySelector(".btn-add");
    const closeIncubateeModalTop = document.getElementById("closeIncubateeModalTop");
    const closeIncubateeModalBottom = document.getElementById("closeIncubateeModalBottom");

    // Open modal
    if (openIncubateeModalBtn) {
        openIncubateeModalBtn.addEventListener("click", () => {
            incubateeModal.classList.add("active");
        });
    }

    // Close modal from both buttons
    [closeIncubateeModalTop, closeIncubateeModalBottom].forEach(btn => {
        if (btn) {
            btn.addEventListener("click", () => {
                closeIncubateeAddModal();
            });
        }
    });

    // Initialize incubatee add form submission
    initializeIncubateeAddForm();
}

function initializeIncubateeAddForm() {
    const form = document.getElementById("incubateeAddForm");
    const modal = document.getElementById("incubateeModal");

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();

            // Create FormData object to handle both form fields and file uploads
            const formData = new FormData(form);

            try {
                const res = await fetch("/admin/add-incubatee", {
                    method: "POST",
                    body: formData // No Content-Type header needed for FormData
                });

                const data = await res.json();

                if (data.success) {
                    showToast("✅ Incubatee added successfully!", "success");
                    form.reset();
                    // Reset logo preview
                    document.getElementById("preview-logo").style.display = "none";
                    modal.classList.remove("active");

                    // Refresh the incubatees list
                    loadIncubatees();
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

// Enhanced file upload handling
function initializeFileUpload() {
    const fileInput = document.getElementById('company_logo');
    const fileLabel = document.querySelector('.file-upload-label');
    const previewImage = document.getElementById('preview-logo');
    const previewContainer = document.getElementById('logo-preview');

    if (!fileInput || !fileLabel) return;

    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        
        if (file) {
            // Validate file type
            const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/svg+xml'];
            if (!allowedTypes.includes(file.type)) {
                showNotification('❌ Please select a valid image file (JPEG, PNG, GIF, SVG)', 'error');
                resetFileInput();
                return;
            }
            
            // Validate file size (max 5MB)
            if (file.size > 5 * 1024 * 1024) {
                showNotification('❌ File size too large. Maximum size is 5MB.', 'error');
                resetFileInput();
                return;
            }
            
            // Update UI to show file is selected
            fileLabel.classList.add('has-file');
            updateFileLabelText(file.name);
            
            // Show preview
            const reader = new FileReader();
            reader.onload = function(e) {
                previewImage.src = e.target.result;
                previewContainer.style.display = 'block';
                previewImage.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else {
            resetFileInput();
        }
    });

    // Drag and drop functionality
    fileLabel.addEventListener('dragover', function(e) {
        e.preventDefault();
        fileLabel.classList.add('drag-over');
    });

    fileLabel.addEventListener('dragleave', function(e) {
        e.preventDefault();
        fileLabel.classList.remove('drag-over');
    });

    fileLabel.addEventListener('drop', function(e) {
        e.preventDefault();
        fileLabel.classList.remove('drag-over');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            fileInput.dispatchEvent(new Event('change'));
        }
    });
}

function updateFileLabelText(fileName) {
    const title = document.querySelector('.file-upload-title');
    const subtitle = document.querySelector('.file-upload-subtitle');
    
    if (title && subtitle) {
        title.textContent = fileName;
        subtitle.textContent = 'Click to change file';
    }
}

function resetFileInput() {
    const fileInput = document.getElementById('company_logo');
    const fileLabel = document.querySelector('.file-upload-label');
    const previewContainer = document.getElementById('logo-preview');
    
    if (fileInput) fileInput.value = '';
    if (fileLabel) fileLabel.classList.remove('has-file');
    if (previewContainer) previewContainer.style.display = 'none';
    
    // Reset label text
    const title = document.querySelector('.file-upload-title');
    const subtitle = document.querySelector('.file-upload-subtitle');
    if (title && subtitle) {
        title.textContent = 'Choose Company Logo';
        subtitle.textContent = 'PNG, JPG, GIF, SVG up to 5MB';
    }
}

// Preview uploaded logo for incubatee form
function handleLogoPreview(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            const preview = document.getElementById("preview-logo");
            preview.src = e.target.result;
            preview.style.display = "block";
            
            // Update the modern file upload UI
            const fileLabel = document.querySelector('.file-upload-label');
            if (fileLabel) {
                fileLabel.classList.add('has-file');
                updateFileLabelText(file.name);
            }
        };
        reader.readAsDataURL(file);
    }
}

function closeIncubateeAddModal() {
    const modal = document.getElementById("incubateeModal");
    const form = document.getElementById("incubateeAddForm");
    
    if (modal) {
        modal.classList.remove("active");
    }
    if (form) {
        form.reset();
    }
    // Reset logo preview
    const preview = document.getElementById("preview-logo");
    if (preview) {
        preview.style.display = "none";
    }
}

async function loadIncubatees() {
    try {
        showLoadingState();
        const response = await fetch('/admin/get-incubatees-list');
        const data = await response.json();
        
        if (data.success) {
            allIncubatees = data.incubatees;
            filterAndDisplayIncubatees();
            updateIncubateeStats(allIncubatees);
        } else {
            showErrorState('Error loading incubatees: ' + data.error);
        }
    } catch (error) {
        console.error('Error fetching incubatees:', error);
        showErrorState('Failed to load incubatees. Please check your connection.');
    }
}

function showLoadingState() {
    const container = document.getElementById('incubatees-container');
    if (container) {
        container.innerHTML = '<div class="loading-state">Loading incubatees...</div>';
    }
}

function showErrorState(message) {
    const container = document.getElementById('incubatees-container');
    if (container) {
        container.innerHTML = `<div class="error-state">${message}</div>`;
    }
    showNotification(message, 'error');
}

function filterAndDisplayIncubatees() {
    let filteredIncubatees = allIncubatees;
    
    // Apply status filter
    if (currentFilter === 'approved') {
        filteredIncubatees = filteredIncubatees.filter(i => i.is_approved);
    } else if (currentFilter === 'pending') {
        filteredIncubatees = filteredIncubatees.filter(i => !i.is_approved);
    }
    
    // Apply search filter
    const searchInput = document.getElementById('incubateeSearch');
    if (searchInput) {
        const searchTerm = searchInput.value.toLowerCase();
        if (searchTerm) {
            filteredIncubatees = filteredIncubatees.filter(i => 
                i.full_name.toLowerCase().includes(searchTerm) ||
                (i.company_name && i.company_name.toLowerCase().includes(searchTerm)) ||
                (i.email && i.email.toLowerCase().includes(searchTerm))
            );
        }
    }
    
    displayIncubatees(filteredIncubatees);
}

function displayIncubatees(incubatees) {
    const container = document.getElementById('incubatees-container');
    if (!container) return;
    
    if (incubatees.length === 0) {
        container.innerHTML = '<div class="no-data">No incubatees found.</div>';
        return;
    }

    container.innerHTML = incubatees.map(incubatee => `
        <div class="incubatee-card ${incubatee.is_approved ? 'approved' : 'pending'}">
            <div class="incubatee-header">
                <div class="incubatee-avatar" data-incubatee-id="${incubatee.incubatee_id}">
                    ${incubatee.logo_path ? 
                        `<img src="/admin/get-incubatee-logo/${incubatee.incubatee_id}" 
                              alt="${escapeHtml(incubatee.full_name)}" 
                              class="avatar-logo"
                              onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">` :
                        ''
                    }
                    <div class="avatar-placeholder" style="${incubatee.logo_path ? 'display: none;' : ''}">
                        ${incubatee.full_name.charAt(0).toUpperCase()}
                    </div>
                </div>
                <div class="incubatee-basic-info">
                    <h3>${escapeHtml(incubatee.full_name)}</h3>
                    <p class="company-name">${escapeHtml(incubatee.company_name || 'No Company')}</p>
                    <p class="incubatee-id">ID: ${incubatee.incubatee_id} • Batch: ${incubatee.batch || 'N/A'}</p>
                </div>
                <div class="incubatee-actions">
                    <button class="btn-toggle-approval ${incubatee.is_approved ? 'btn-approved' : 'btn-pending'}" 
                            onclick="toggleIncubateeApproval(${incubatee.incubatee_id})">
                        ${incubatee.is_approved ? '✅ Approved' : '⏳ Pending'}
                    </button>
                    <button class="btn-edit" onclick="openEditIncubateeModal(${incubatee.incubatee_id})">
                        ✏️ Edit
                    </button>
                    <button class="btn-view" onclick="showIncubateeDetails(${incubatee.incubatee_id})">
                        👁️ View
                    </button>
                </div>
            </div>
            
            <div class="incubatee-contact">
                <div class="contact-item">
                    <span class="contact-icon">📧</span>
                    <span>${escapeHtml(incubatee.email || 'No email')}</span>
                </div>
                <div class="contact-item">
                    <span class="contact-icon">📞</span>
                    <span>${escapeHtml(incubatee.phone || 'No phone')}</span>
                </div>
                ${incubatee.website ? `
                <div class="contact-item">
                    <span class="contact-icon">🌐</span>
                    <span><a href="${incubatee.website}" target="_blank">Website</a></span>
                </div>
                ` : ''}
            </div>
            
            <div class="incubatee-stats">
                <div class="stat">
                    <span class="stat-value">${incubatee.product_count}</span>
                    <span class="stat-label">Products</span>
                </div>
                <div class="stat">
                    <span class="stat-value revenue">₱${incubatee.total_sales.toFixed(2)}</span>
                    <span class="stat-label">Total Sales</span>
                </div>
                <div class="stat">
                    <span class="stat-value">${formatDateOnly(incubatee.created_at)}</span>
                    <span class="stat-label">Joined</span>
                </div>
            </div>
        </div>
    `).join('');

    // Load logos via API after DOM is updated
    setTimeout(() => {
        IncubateeAPI.loadAllIncubateeLogos();
    }, 100);
}

function updateIncubateeStats(incubatees) {
    const totalIncubateesEl = document.getElementById('totalIncubatees');
    const approvedIncubateesEl = document.getElementById('approvedIncubatees');
    const pendingIncubateesEl = document.getElementById('pendingIncubatees');
    const totalProductsEl = document.getElementById('totalProducts');
    const totalRevenueEl = document.querySelector('.revenue');

    if (totalIncubateesEl) {
        totalIncubateesEl.textContent = incubatees.length;
    }
    if (approvedIncubateesEl) {
        const approvedIncubatees = incubatees.filter(i => i.is_approved).length;
        approvedIncubateesEl.textContent = approvedIncubatees;
    }
    if (pendingIncubateesEl) {
        const pendingIncubatees = incubatees.filter(i => !i.is_approved).length;
        pendingIncubateesEl.textContent = pendingIncubatees;
    }
    if (totalProductsEl) {
        const totalProducts = incubatees.reduce((sum, i) => sum + i.product_count, 0);
        totalProductsEl.textContent = totalProducts;
    }
    if (totalRevenueEl) {
        const totalRevenue = incubatees.reduce((sum, i) => sum + i.total_sales, 0);
        totalRevenueEl.textContent = '₱' + totalRevenue.toFixed(2);
    }
}

function setIncubateeFilter(filter) {
    currentFilter = filter;
    
    // Update active tab
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');
    
    filterAndDisplayIncubatees();
}

function filterIncubatees() {
    filterAndDisplayIncubatees();
}

// Modern dialog function (no additional HTML required)
function showModernConfirm(message, title = 'Confirmation') {
    return new Promise((resolve) => {
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(8px);
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        `;

        // Create modal content
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            max-width: 400px;
            width: 100%;
            text-align: center;
            border: 1px solid #e2e8f0;
        `;

        modal.innerHTML = `
            <div style="font-size: 48px; margin-bottom: 20px;">⚠️</div>
            <h3 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 10px; color: #1e293b;">${title}</h3>
            <p style="color: #64748b; margin-bottom: 30px; line-height: 1.5;">${message}</p>
            <div style="display: flex; gap: 12px; justify-content: center;">
                <button id="modalCancel" style="padding: 12px 24px; border: 1px solid #e2e8f0; background: white; border-radius: 8px; font-weight: 600; color: #64748b; cursor: pointer; transition: all 0.2s;">Cancel</button>
                <button id="modalConfirm" style="padding: 12px 24px; border: none; background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border-radius: 8px; font-weight: 600; cursor: pointer; transition: all 0.2s;">Yes, Continue</button>
            </div>
        `;

        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Add event listeners
        const cancelBtn = modal.querySelector('#modalCancel');
        const confirmBtn = modal.querySelector('#modalConfirm');

        const cleanup = () => {
            document.body.removeChild(overlay);
        };

        cancelBtn.onclick = () => {
            cleanup();
            resolve(false);
        };

        confirmBtn.onclick = () => {
            cleanup();
            resolve(true);
        };

        // Close on overlay click
        overlay.onclick = (e) => {
            if (e.target === overlay) {
                cleanup();
                resolve(false);
            }
        };
    });
}

// Updated toggle function using modern confirm
async function toggleIncubateeApproval(incubateeId) {
    const incubatee = allIncubatees.find(i => i.incubatee_id === incubateeId);
    if (!incubatee) return;

    const isCurrentlyApproved = incubatee.is_approved;
    const action = isCurrentlyApproved ? 'revoke approval from' : 'approve';
    
    const confirmed = await showModernConfirm(
        `Are you sure you want to ${action} "${incubatee.full_name}"?`,
        `${isCurrentlyApproved ? 'Revoke Approval' : 'Approve Incubatee'}`
    );

    if (!confirmed) return;
    
    try {
        // Show loading state on the button
        const button = event.target;
        const originalText = button.innerHTML;
        button.innerHTML = '⏳ Updating...';
        button.disabled = true;

        const response = await fetch(`/admin/toggle-incubatee-approval/${incubateeId}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification(`✅ ${data.message}`, 'success');
            loadIncubatees(); // Refresh the list
        } else {
            showNotification(`❌ Error: ${data.error}`, 'error');
            // Reset button on error
            button.innerHTML = originalText;
            button.disabled = false;
        }
    } catch (error) {
        console.error('Error toggling approval:', error);
        showNotification('❌ Failed to update approval status', 'error');
        // Reset button on error
        const button = event.target;
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Add Incubatee Modal Functions
function openAddIncubateeModal() {
    document.getElementById('addIncubateeModal').classList.add('active');
}

function closeAddIncubateeModal() {
    document.getElementById('addIncubateeModal').classList.remove('active');
    const form = document.getElementById('addIncubateeForm');
    if (form) form.reset();
}

async function handleAddIncubatee(e) {
    e.preventDefault();
    
    const formData = {
        first_name: document.getElementById('add_first_name').value,
        last_name: document.getElementById('add_last_name').value,
        middle_name: document.getElementById('add_middle_name').value,
        company_name: document.getElementById('add_company_name').value,
        email: document.getElementById('add_email').value,
        phone_number: document.getElementById('add_phone_number').value,
        contact_info: document.getElementById('add_contact_info').value,
        batch: document.getElementById('add_batch').value,
        is_approved: document.getElementById('add_is_approved').checked
    };

    try {
        const response = await fetch('/admin/add-incubatee', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (data.success) {
            showNotification('✅ Incubatee added successfully!', 'success');
            closeAddIncubateeModal();
            loadIncubatees(); // Refresh the list
        } else {
            showNotification('❌ Error: ' + data.error, 'error');
        }
    } catch (error) {
        console.error('Error adding incubatee:', error);
        showNotification('❌ Failed to add incubatee', 'error');
    }
}


// Edit Incubatee Modal Functions
function openEditIncubateeModal(incubateeId) {
    const incubatee = allIncubatees.find(i => i.incubatee_id === incubateeId);
    if (!incubatee) return;

    editingIncubateeId = incubateeId;
    
    // Store original data for comparison
    window.originalIncubateeData = {
        first_name: incubatee.first_name || '',
        last_name: incubatee.last_name || '',
        middle_name: incubatee.middle_name || '',
        company_name: incubatee.company_name || '',
        email: incubatee.email || '',
        phone: incubatee.phone || '',
        contact_info: incubatee.contact_info || '',
        batch: incubatee.batch || '',
        website: incubatee.website || '',
        is_approved: incubatee.is_approved
    };
    
    // Populate form with current data
    document.getElementById('edit_first_name').value = window.originalIncubateeData.first_name;
    document.getElementById('edit_last_name').value = window.originalIncubateeData.last_name;
    document.getElementById('edit_middle_name').value = window.originalIncubateeData.middle_name;
    document.getElementById('edit_company_name').value = window.originalIncubateeData.company_name;
    document.getElementById('edit_email').value = window.originalIncubateeData.email;
    document.getElementById('edit_phone_number').value = window.originalIncubateeData.phone;
    document.getElementById('edit_contact_info').value = window.originalIncubateeData.contact_info;
    document.getElementById('edit_batch').value = window.originalIncubateeData.batch;
    document.getElementById('edit_website').value = window.originalIncubateeData.website;
    document.getElementById('edit_is_approved').checked = window.originalIncubateeData.is_approved;

    // Handle logo preview using API
    const logoPreview = document.getElementById('edit_logo_preview');
    const currentLogo = document.getElementById('edit_current_logo');
    
    if (incubatee.logo_path) {
        // Use API endpoint for logo
        currentLogo.src = `/admin/get-incubatee-logo/${incubateeId}`;
        currentLogo.style.display = 'block';
        currentLogo.onerror = () => {
            currentLogo.style.display = 'none';
            logoPreview.innerHTML = '<p style="color: var(--text-tertiary);">No logo available</p>';
        };
        logoPreview.innerHTML = `<p style="margin-bottom: 10px; font-weight: 600; color: var(--text-secondary);">Current Logo:</p>`;
        logoPreview.appendChild(currentLogo);
    } else {
        currentLogo.style.display = 'none';
        logoPreview.innerHTML = '<p style="color: var(--text-tertiary);">No logo uploaded</p>';
    }

    // Reset file input and new logo preview
    document.getElementById('edit_company_logo').value = '';
    document.getElementById('edit_new_logo_preview').style.display = 'none';

    document.getElementById('editIncubateeModal').classList.add('active');
}

// Helper function to check if form data has changed
function hasFormDataChanged() {
    if (!window.originalIncubateeData) return true;
    
    const currentData = {
        first_name: document.getElementById('edit_first_name').value,
        last_name: document.getElementById('edit_last_name').value,
        middle_name: document.getElementById('edit_middle_name').value,
        company_name: document.getElementById('edit_company_name').value,
        email: document.getElementById('edit_email').value,
        phone_number: document.getElementById('edit_phone_number').value,
        contact_info: document.getElementById('edit_contact_info').value,
        batch: document.getElementById('edit_batch').value,
        website: document.getElementById('edit_website').value,
        is_approved: document.getElementById('edit_is_approved').checked
    };

    // Check if any field has changed
    for (let key in currentData) {
        if (currentData[key] !== window.originalIncubateeData[key]) {
            return true;
        }
    }

    // Check if a new logo was selected
    const logoFile = document.getElementById('edit_company_logo').files[0];
    if (logoFile) {
        return true;
    }

    return false;
}

// Updated handleEditIncubatee function
async function handleEditIncubatee(e) {
    e.preventDefault();
    
    if (!editingIncubateeId) return;

    // Check if anything has actually changed
    if (!hasFormDataChanged()) {
        showNotification('ℹ️ No changes detected.', 'info');
        closeEditIncubateeModal();
        return;
    }

    const formData = new FormData();
    
    // Only append fields that have changed
    const currentData = {
        first_name: document.getElementById('edit_first_name').value,
        last_name: document.getElementById('edit_last_name').value,
        middle_name: document.getElementById('edit_middle_name').value,
        company_name: document.getElementById('edit_company_name').value,
        email: document.getElementById('edit_email').value,
        phone_number: document.getElementById('edit_phone_number').value,
        contact_info: document.getElementById('edit_contact_info').value,
        batch: document.getElementById('edit_batch').value,
        website: document.getElementById('edit_website').value,
        is_approved: document.getElementById('edit_is_approved').checked
    };

    // Add changed fields to FormData
    for (let key in currentData) {
        if (currentData[key] !== window.originalIncubateeData[key]) {
            formData.append(key, currentData[key]);
        }
    }

    // Append logo file if selected
    const logoFile = document.getElementById('edit_company_logo').files[0];
    if (logoFile) {
        formData.append('company_logo', logoFile);
    }

    // Show loading state
    const submitBtn = e.target.querySelector('.btn-save');
    const originalBtnText = submitBtn.textContent;
    submitBtn.innerHTML = '⏳ Updating...';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`/admin/update-incubatee/${editingIncubateeId}`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            showNotification('✅ Incubatee updated successfully!', 'success');
            closeEditIncubateeModal();
            loadIncubatees(); // Refresh the list
        } else {
            showNotification('❌ Error: ' + data.error, 'error');
            // Reset button state
            submitBtn.textContent = originalBtnText;
            submitBtn.disabled = false;
        }
    } catch (error) {
        console.error('Error updating incubatee:', error);
        showNotification('❌ Failed to update incubatee', 'error');
        // Reset button state
        submitBtn.textContent = originalBtnText;
        submitBtn.disabled = false;
    }
}

function closeEditIncubateeModal() {
    document.getElementById('editIncubateeModal').classList.remove('active');
    editingIncubateeId = null;
    window.originalIncubateeData = null;
    
    const form = document.getElementById('editIncubateeForm');
    if (form) form.reset();
    
    // Reset logo preview
    document.getElementById('edit_current_logo').style.display = 'none';
    document.getElementById('edit_logo_preview').innerHTML = '';
    document.getElementById('edit_new_logo_preview').style.display = 'none';
}

// Handle logo preview for edit modal
function handleEditLogoPreview(event) {
    const file = event.target.files[0];
    const preview = document.getElementById('edit_new_logo_preview');
    
    if (file) {
        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/svg+xml'];
        if (!allowedTypes.includes(file.type)) {
            showNotification('❌ Please select a valid image file (JPEG, PNG, GIF, SVG)', 'error');
            event.target.value = '';
            preview.style.display = 'none';
            return;
        }
        
        // Validate file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
            showNotification('❌ File size too large. Maximum size is 5MB.', 'error');
            event.target.value = '';
            preview.style.display = 'none';
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    } else {
        preview.style.display = 'none';
    }
}

// View Incubatee Details Functions
async function showIncubateeDetails(incubateeId) {
    try {
        const result = await IncubateeAPI.getIncubateeDetails(incubateeId);
        
        if (!result.success) {
            showNotification('Failed to load incubatee details: ' + result.error, 'error');
            return;
        }

        const incubatee = result.incubatee;
        const modal = document.getElementById('incubateeDetailsModal');
        const content = document.getElementById('incubateeDetailsContent');

        content.innerHTML = `
            <div class="incubatee-detail-section">
                <h3>Basic Information</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <label>Incubatee ID:</label>
                        <span>${incubatee.id}</span>
                    </div>
                    <div class="detail-item">
                        <label>Full Name:</label>
                        <span>${escapeHtml(incubatee.full_name)}</span>
                    </div>
                    <div class="detail-item">
                        <label>Company:</label>
                        <span>${escapeHtml(incubatee.company_name || 'N/A')}</span>
                    </div>
                    <div class="detail-item">
                        <label>Batch:</label>
                        <span>${incubatee.batch || 'N/A'}</span>
                    </div>
                    <div class="detail-item">
                        <label>Email:</label>
                        <span>${escapeHtml(incubatee.email || 'N/A')}</span>
                    </div>
                    <div class="detail-item">
                        <label>Phone:</label>
                        <span>${escapeHtml(incubatee.phone || 'N/A')}</span>
                    </div>
                    <div class="detail-item">
                        <label>Status:</label>
                        <span class="status-badge ${incubatee.is_approved ? 'status-approved' : 'status-pending'}">
                            ${incubatee.is_approved ? 'Approved' : 'Pending Approval'}
                        </span>
                    </div>
                    <div class="detail-item">
                        <label>Join Date:</label>
                        <span>${formatDateToReadable(incubatee.created_at)}</span>
                    </div>
                </div>
            </div>

            <div class="incubatee-detail-section">
                <h3>Business Statistics</h3>
                <div class="stats-grid">
                    <div class="stat-card mini">
                        <div class="stat-value">${incubatee.product_count}</div>
                        <div class="stat-label">Total Products</div>
                    </div>
                    <div class="stat-card mini">
                        <div class="stat-value revenue">₱${incubatee.total_sales.toFixed(2)}</div>
                        <div class="stat-label">Total Revenue</div>
                    </div>
                    <div class="stat-card mini">
                        <div class="stat-value">${incubatee.products.filter(p => p.stock > 0).length}</div>
                        <div class="stat-label">In Stock</div>
                    </div>
                    <div class="stat-card mini">
                        <div class="stat-value">${incubatee.products.filter(p => p.stock === 0).length}</div>
                        <div class="stat-label">Out of Stock</div>
                    </div>
                </div>
            </div>

            <div class="incubatee-detail-section">
                <h3>Products (${incubatee.products.length})</h3>
                ${incubatee.products.length === 0 ? 
                    '<p class="no-data">No products added yet.</p>' :
                    `<div class="products-list">
                        ${incubatee.products.map(product => `
                            <div class="product-item">
                                <div class="product-image">
                                    ${product.image_url 
                                        ? `<img src="${product.image_url}" alt="${escapeHtml(product.name)}"
                                             onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">` :
                                        ''
                                    }
                                    <div class="no-image" style="${product.image_url ? 'display: none;' : ''}">📷</div>
                                </div>
                                <div class="product-info">
                                    <h4>${escapeHtml(product.name)}</h4>
                                    <p class="product-category">${product.category || 'Uncategorized'}</p>
                                    <p class="product-stock">Stock: ${product.stock} • Price: ₱${product.price.toFixed(2)}</p>
                                </div>
                                <div class="product-status ${product.stock > 0 ? 'in-stock' : 'out-of-stock'}">
                                    ${product.stock > 0 ? 'In Stock' : 'Out of Stock'}
                                </div>
                            </div>
                        `).join('')}
                    </div>`
                }
            </div>
        `;

        modal.classList.add('active');
    } catch (error) {
        console.error('Error showing incubatee details:', error);
        showNotification('Failed to load incubatee details', 'error');
    }
}

function closeIncubateeModal() {
    document.getElementById('incubateeDetailsModal').classList.remove('active');
}

// Utility Functions
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
        if (isNaN(date.getTime())) return 'Invalid Date';
        
        const options = { year: 'numeric', month: 'short', day: 'numeric'};
        return date.toLocaleDateString('en-US', options);
    } catch (error) {
        console.error('Error formatting date:', error, dateString);
        return 'Invalid Date';
    }
}

function formatDateToReadable(dateString) {
    if (!dateString) return '—';
    
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return 'Invalid Date';
        
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

function showNotification(message, type = 'info') {
    // Create a simple notification without recursion
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
        background: ${type === 'success' ? '#10b981' : 
                     type === 'error' ? '#ef4444' : 
                     type === 'warning' ? '#f59e0b' : '#3b82f6'};
    `;
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Also update the showToast function to avoid potential recursion:
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === "success" ? "#10b981" : 
                     type === "error" ? "#ef4444" : 
                     type === "warning" ? "#f59e0b" : "#3b82f6"};
        color: white;
        padding: 12px 18px;
        border-radius: 8px;
        font-weight: 600;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        opacity: 0;
        transform: translateY(-10px);
        transition: all 0.3s ease;
        z-index: 2000;
    `;
    
    document.body.appendChild(toast);

    // Animate in
    setTimeout(() => {
        toast.style.opacity = "1";
        toast.style.transform = "translateY(0)";
    }, 50);

    // Auto remove
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(-10px)";
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 2500);
}

// Logout functionality
function logout() {
    if (confirm('Are you sure you want to logout?')) {
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
}