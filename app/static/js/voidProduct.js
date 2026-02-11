// voidProduct.js - Complete Void/Return Management System

// ===== VOID PRODUCT MANAGEMENT =====
const VoidProductSystem = {
    // Initialize void product system
    init: function() {
        this.loadVoidRequests();
        this.attachEventListeners();
    },

    // Attach event listeners
    attachEventListeners: function() {
        // Void filter in orders modal
        const statusFilter = document.getElementById('orderStatusFilter');
        if (statusFilter) {
            // Add void option to filter if not exists
            if (!statusFilter.querySelector('option[value="void"]')) {
                const voidOption = document.createElement('option');
                voidOption.value = 'void';
                voidOption.textContent = '🔄 Returns/Void';
                statusFilter.appendChild(voidOption);
            }
            
            statusFilter.addEventListener('change', () => {
                if (statusFilter.value === 'void') {
                    this.loadVoidRequests();
                }
            });
        }

        // View void details buttons (delegation)
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('view-void-btn') || 
                e.target.closest('.view-void-btn')) {
                const btn = e.target.classList.contains('view-void-btn') ? 
                    e.target : e.target.closest('.view-void-btn');
                const voidId = btn.dataset.voidId;
                this.showVoidDetails(voidId);
            }
            
            if (e.target.classList.contains('process-void-btn') ||
                e.target.closest('.process-void-btn')) {
                const btn = e.target.classList.contains('process-void-btn') ? 
                    e.target : e.target.closest('.process-void-btn');
                const voidId = btn.dataset.voidId;
                this.showProcessVoidModal(voidId);
            }
        });
    },

    // Load void requests for admin
    loadVoidRequests: async function(status = 'all', page = 1) {
        const ordersList = document.getElementById('orders-list');
        if (!ordersList) return;

        try {
            ordersList.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 40px;">
                        <div style="display: flex; flex-direction: column; align-items: center; gap: 12px;">
                            <div style="font-size: 32px;">🔄</div>
                            <div style="color: #6b7280;">Loading void/return requests...</div>
                        </div>
                    </td>
                </tr>
            `;

            const response = await fetch(`/void/admin/all?status=${status}&page=${page}`);
            const data = await response.json();

            if (data.success) {
                this.renderVoidRequests(data.requests, data.pagination);
            } else {
                throw new Error(data.message || 'Failed to load void requests');
            }
        } catch (error) {
            console.error('Error loading void requests:', error);
            ordersList.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 40px;">
                        <div style="display: flex; flex-direction: column; align-items: center; gap: 12px; color: #dc2626;">
                            <div style="font-size: 32px;">❌</div>
                            <div>Error loading void requests. Please try again.</div>
                            <button onclick="VoidProductSystem.loadVoidRequests()" 
                                    style="padding: 8px 16px; background: #10b981; color: white; border: none; border-radius: 6px; cursor: pointer;">
                                Retry
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }
    },

    // Render void requests in table
    renderVoidRequests: function(requests, pagination) {
        const ordersList = document.getElementById('orders-list');
        if (!ordersList) return;

        if (!requests || requests.length === 0) {
            ordersList.innerHTML = `
                <tr>
                    <td colspan="9" style="text-align: center; padding: 60px 20px;">
                        <div style="display: flex; flex-direction: column; align-items: center; gap: 16px;">
                            <div style="font-size: 48px; opacity: 0.5;">🔄</div>
                            <div style="font-size: 16px; font-weight: 600; color: #374151;">
                                No void/return requests found
                            </div>
                            <div style="font-size: 14px; color: #6b7280;">
                                When customers request returns, they will appear here.
                            </div>
                        </div>
                    </td>
                </tr>
            `;
            return;
        }

        let html = '';
        requests.forEach(request => {
            // Status badge styling
            let statusBadge = '';
            let statusColor = '';
            let statusBg = '';
            
            switch(request.void_status) {
                case 'pending':
                    statusColor = '#d97706';
                    statusBg = '#fef3c7';
                    statusBadge = '⏳ Pending Review';
                    break;
                case 'approved':
                    statusColor = '#059669';
                    statusBg = '#d1fae5';
                    statusBadge = '✅ Approved';
                    break;
                case 'rejected':
                    statusColor = '#dc2626';
                    statusBg = '#fee2e2';
                    statusBadge = '❌ Rejected';
                    break;
                case 'refunded':
                    statusColor = '#2563eb';
                    statusBg = '#dbeafe';
                    statusBadge = '💰 Refunded';
                    break;
                default:
                    statusColor = '#6b7280';
                    statusBg = '#f3f4f6';
                    statusBadge = request.void_status;
            }

            // Return type display
            const returnTypeMap = {
                'defective': 'Defective Product',
                'wrong_item': 'Wrong Item',
                'damaged': 'Damaged',
                'not_as_described': 'Not as Described',
                'other': 'Other'
            };

            html += `
                <tr class="void-request-row" data-void-id="${request.void_id}">
                    <td><span style="font-weight: 600;">#VOID-${request.void_id}</span></td>
                    <td>#${request.user_id}</td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <img src="${request.product_image || 'https://cdn-icons-png.flaticon.com/512/4076/4076505.png'}" 
                                 alt="${request.product_name}"
                                 style="width: 40px; height: 40px; border-radius: 6px; object-fit: cover; border: 1px solid #e5e7eb;">
                            <div>
                                <div style="font-weight: 500; color: #1f2937;">${request.product_name}</div>
                                <div style="font-size: 11px; color: #6b7280;">Order #${request.reservation_id}</div>
                            </div>
                        </div>
                    </td>
                    <td>${request.quantity}</td>
                    <td>₱${parseFloat(request.price || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td>₱${parseFloat(request.total || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                    <td>
                        <span style="
                            display: inline-block;
                            padding: 4px 12px;
                            border-radius: 20px;
                            font-size: 11px;
                            font-weight: 600;
                            background: ${statusBg};
                            color: ${statusColor};
                            border: 1px solid ${statusColor}20;
                        ">
                            ${statusBadge}
                        </span>
                    </td>
                    <td>${request.requested_at_display || ''}</td>
                    <td>
                        <div style="display: flex; gap: 8px;">
                            <button class="view-void-btn" data-void-id="${request.void_id}"
                                    style="padding: 6px 12px; background: #f3f4f6; border: 1px solid #d1d5db; 
                                           border-radius: 6px; color: #4b5563; font-size: 12px; font-weight: 500; 
                                           cursor: pointer; transition: all 0.2s;">
                                👁️ View
                            </button>
                            ${request.void_status === 'pending' ? `
                            <button class="process-void-btn" data-void-id="${request.void_id}"
                                    style="padding: 6px 12px; background: linear-gradient(135deg, #10b981, #059669); 
                                           border: none; border-radius: 6px; color: white; font-size: 12px; 
                                           font-weight: 600; cursor: pointer; transition: all 0.2s;">
                                ⚙️ Process
                            </button>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `;
        });

        // Add pagination
        if (pagination && pagination.pages > 1) {
            html += `
                <tr class="pagination-row">
                    <td colspan="9" style="padding: 20px;">
                        <div style="display: flex; justify-content: center; align-items: center; gap: 12px;">
                            ${pagination.has_prev ? `
                                <button onclick="VoidProductSystem.loadVoidRequests('all', ${pagination.page - 1})"
                                        style="padding: 6px 14px; background: #f8fafc; border: 1px solid #e5e7eb; 
                                               border-radius: 6px; cursor: pointer;">
                                    ← Previous
                                </button>
                            ` : ''}
                            <span style="font-size: 13px; color: #6b7280;">
                                Page ${pagination.page} of ${pagination.pages}
                            </span>
                            ${pagination.has_next ? `
                                <button onclick="VoidProductSystem.loadVoidRequests('all', ${pagination.page + 1})"
                                        style="padding: 6px 14px; background: #f8fafc; border: 1px solid #e5e7eb; 
                                               border-radius: 6px; cursor: pointer;">
                                    Next →
                                </button>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `;
        }

        ordersList.innerHTML = html;
    },

    // Show void request details modal
    showVoidDetails: async function(voidId) {
        try {
            const response = await fetch(`/void/admin/${voidId}`);
            const data = await response.json();

            if (data.success) {
                this.renderVoidDetailsModal(data.request);
            } else {
                alert('Failed to load void request details');
            }
        } catch (error) {
            console.error('Error loading void details:', error);
            alert('Error loading void request details');
        }
    },

    // Render void details modal
    renderVoidDetailsModal: function(request) {
        // Remove existing modal if any
        const existingModal = document.getElementById('voidDetailsModal');
        if (existingModal) existingModal.remove();

        // Create modal
        const modal = document.createElement('div');
        modal.id = 'voidDetailsModal';
        modal.className = 'void-modal-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10002;
            padding: 20px;
            animation: fadeIn 0.3s ease;
        `;

        // Status color mapping
        const statusColors = {
            pending: { bg: '#fef3c7', color: '#d97706', text: 'Pending Review' },
            approved: { bg: '#d1fae5', color: '#059669', text: 'Approved' },
            rejected: { bg: '#fee2e2', color: '#dc2626', text: 'Rejected' },
            refunded: { bg: '#dbeafe', color: '#2563eb', text: 'Refunded' }
        };

        const status = statusColors[request.void_status] || statusColors.pending;

        modal.innerHTML = `
            <div class="void-modal" style="
                background: white;
                border-radius: 16px;
                width: 100%;
                max-width: 700px;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: slideUp 0.3s ease;
            ">
                <!-- Header -->
                <div style="padding: 24px; border-bottom: 1px solid #e5e7eb; 
                           background: linear-gradient(to right, #f8fafc, white);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="font-size: 32px;">🔄</div>
                            <div>
                                <h2 style="margin: 0; color: #1f2937; font-size: 20px; font-weight: 700;">
                                    Void/Return Request #VOID-${request.void_id}
                                </h2>
                                <p style="margin: 4px 0 0; color: #6b7280; font-size: 14px;">
                                    Requested on ${request.requested_at_display}
                                </p>
                            </div>
                        </div>
                        <button class="close-void-modal" style="
                            background: none;
                            border: none;
                            font-size: 28px;
                            cursor: pointer;
                            color: #6b7280;
                            padding: 4px 12px;
                            border-radius: 8px;
                            transition: all 0.2s;
                        ">×</button>
                    </div>
                </div>

                <!-- Content -->
                <div style="padding: 24px;">
                    <!-- Status Badge -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
                        <div>
                            <span style="
                                display: inline-block;
                                padding: 6px 16px;
                                border-radius: 30px;
                                font-size: 13px;
                                font-weight: 700;
                                background: ${status.bg};
                                color: ${status.color};
                                border: 1px solid ${status.color}30;
                            ">
                                ${status.text}
                            </span>
                        </div>
                        ${request.refund_amount ? `
                            <div style="
                                padding: 8px 16px;
                                background: #ecfdf5;
                                border-radius: 8px;
                                border-left: 4px solid #10b981;
                            ">
                                <span style="font-size: 12px; color: #065f46;">Refund Amount:</span>
                                <span style="font-size: 18px; font-weight: 700; color: #059669; margin-left: 8px;">
                                    ₱${parseFloat(request.refund_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                </span>
                            </div>
                        ` : ''}
                    </div>

                    <!-- Product Info -->
                    <div style="display: flex; gap: 20px; padding: 20px; background: #f8fafc; border-radius: 12px; margin-bottom: 24px;">
                        <img src="${request.product_image || 'https://cdn-icons-png.flaticon.com/512/4076/4076505.png'}" 
                             alt="${request.product_name}"
                             style="width: 80px; height: 80px; border-radius: 10px; object-fit: cover; border: 2px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <div style="flex: 1;">
                            <div style="font-weight: 700; color: #1f2937; font-size: 16px; margin-bottom: 8px;">
                                ${request.product_name}
                            </div>
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px;">
                                <div>
                                    <span style="font-size: 12px; color: #6b7280;">Order ID:</span>
                                    <span style="font-size: 13px; font-weight: 600; color: #374151; margin-left: 4px;">
                                        #${request.reservation_id}
                                    </span>
                                </div>
                                <div>
                                    <span style="font-size: 12px; color: #6b7280;">Customer ID:</span>
                                    <span style="font-size: 13px; font-weight: 600; color: #374151; margin-left: 4px;">
                                        #${request.user_id}
                                    </span>
                                </div>
                                <div>
                                    <span style="font-size: 12px; color: #6b7280;">Quantity:</span>
                                    <span style="font-size: 13px; font-weight: 600; color: #374151; margin-left: 4px;">
                                        ${request.quantity}
                                    </span>
                                </div>
                                <div>
                                    <span style="font-size: 12px; color: #6b7280;">Price:</span>
                                    <span style="font-size: 13px; font-weight: 600; color: #374151; margin-left: 4px;">
                                        ₱${parseFloat(request.price || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Return Details -->
                    <div style="margin-bottom: 24px;">
                        <h3 style="margin: 0 0 16px; color: #1f2937; font-size: 16px; font-weight: 700;">
                            📋 Return Details
                        </h3>
                        
                        <div style="background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px;">
                            <!-- Reason -->
                            <div style="margin-bottom: 20px;">
                                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                    <span style="font-weight: 600; color: #374151; font-size: 14px;">Reason Type:</span>
                                    <span style="
                                        padding: 2px 10px;
                                        background: #e0f2fe;
                                        color: #0369a1;
                                        border-radius: 16px;
                                        font-size: 12px;
                                        font-weight: 600;
                                    ">
                                        ${request.return_type_display || request.return_type}
                                    </span>
                                </div>
                                
                                <div style="
                                    padding: 16px;
                                    background: #f8fafc;
                                    border-radius: 8px;
                                    border-left: 4px solid #ef4444;
                                ">
                                    <div style="font-size: 13px; color: #4b5563; margin-bottom: 4px;">
                                        <strong>Customer's Explanation:</strong>
                                    </div>
                                    <div style="font-size: 14px; color: #1f2937; line-height: 1.6;">
                                        ${request.reason || 'No reason provided'}
                                    </div>
                                </div>
                            </div>

                            <!-- Problem Description -->
                            ${request.problem_description ? `
                            <div style="margin-bottom: 20px;">
                                <div style="font-size: 13px; color: #4b5563; margin-bottom: 8px;">
                                    <strong>Detailed Problem Description:</strong>
                                </div>
                                <div style="
                                    padding: 16px;
                                    background: #f8fafc;
                                    border-radius: 8px;
                                    font-size: 14px;
                                    color: #1f2937;
                                    line-height: 1.6;
                                ">
                                    ${request.problem_description}
                                </div>
                            </div>
                            ` : ''}

                            <!-- Uploaded Image -->
                            ${request.image_path ? `
                            <div>
                                <div style="font-size: 13px; color: #4b5563; margin-bottom: 8px;">
                                    <strong>Uploaded Evidence:</strong>
                                </div>
                                <div style="
                                    padding: 16px;
                                    background: #f8fafc;
                                    border-radius: 8px;
                                ">
                                    <img src="/${request.image_path}" 
                                         alt="Evidence"
                                         style="max-width: 100%; max-height: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
                                         onclick="window.open('/${request.image_path}', '_blank')"
                                         title="Click to view full size">
                                </div>
                            </div>
                            ` : ''}
                        </div>
                    </div>

                    <!-- Admin Notes (if any) -->
                    ${request.admin_notes ? `
                    <div style="margin-bottom: 24px;">
                        <h3 style="margin: 0 0 16px; color: #1f2937; font-size: 16px; font-weight: 700;">
                            📝 Admin Notes
                        </h3>
                        <div style="
                            padding: 16px;
                            background: #fffbeb;
                            border-radius: 8px;
                            border-left: 4px solid #f59e0b;
                            font-size: 14px;
                            color: #92400e;
                            line-height: 1.6;
                        ">
                            ${request.admin_notes}
                        </div>
                    </div>
                    ` : ''}

                    <!-- Processed Info -->
                    ${request.processed_at ? `
                    <div style="
                        padding: 16px;
                        background: #f8fafc;
                        border-radius: 8px;
                        border-top: 1px solid #e5e7eb;
                    ">
                        <div style="display: flex; justify-content: space-between; color: #6b7280; font-size: 13px;">
                            <span>Processed on: ${request.processed_at_display || request.processed_at}</span>
                            ${request.processed_by ? `<span>Processed by: Admin #${request.processed_by}</span>` : ''}
                        </div>
                    </div>
                    ` : ''}
                </div>

                <!-- Footer Actions -->
                <div style="padding: 20px 24px; border-top: 1px solid #e5e7eb; 
                           display: flex; justify-content: flex-end; gap: 12px;">
                    <button class="close-void-modal-btn" style="
                        padding: 10px 20px;
                        background: #f3f4f6;
                        border: 1px solid #d1d5db;
                        border-radius: 8px;
                        color: #4b5563;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.2s;
                    ">Close</button>
                    
                    ${request.void_status === 'pending' ? `
                        <button onclick="VoidProductSystem.showProcessVoidModal(${request.void_id})" 
                                style="
                            padding: 10px 24px;
                            background: linear-gradient(135deg, #10b981, #059669);
                            border: none;
                            border-radius: 8px;
                            color: white;
                            font-weight: 700;
                            cursor: pointer;
                            transition: all 0.2s;
                        ">Process Request</button>
                    ` : ''}
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // Add animation styles
        const style = document.createElement('style');
        style.textContent = `
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        `;
        document.head.appendChild(style);

        // Close handlers
        const closeModal = () => modal.remove();
        modal.querySelector('.close-void-modal').addEventListener('click', closeModal);
        modal.querySelector('.close-void-modal-btn').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    },

    // Show process void modal
    showProcessVoidModal: async function(voidId) {
        try {
            const response = await fetch(`/void/admin/${voidId}`);
            const data = await response.json();

            if (data.success) {
                this.renderProcessVoidModal(data.request);
            }
        } catch (error) {
            console.error('Error loading void request:', error);
            alert('Error loading void request details');
        }
    },

    // Render process void modal
    renderProcessVoidModal: function(request) {
        // Remove existing modal
        const existingModal = document.getElementById('processVoidModal');
        if (existingModal) existingModal.remove();

        const modal = document.createElement('div');
        modal.id = 'processVoidModal';
        modal.className = 'void-modal-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10003;
            padding: 20px;
        `;

        modal.innerHTML = `
            <div class="void-modal" style="
                background: white;
                border-radius: 16px;
                width: 100%;
                max-width: 600px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            ">
                <!-- Header -->
                <div style="padding: 24px; border-bottom: 1px solid #e5e7eb;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="display: flex; align-items: center; gap: 12px;">
                            <div style="font-size: 28px;">⚙️</div>
                            <div>
                                <h2 style="margin: 0; color: #1f2937; font-size: 20px; font-weight: 700;">
                                    Process Void Request
                                </h2>
                                <p style="margin: 4px 0 0; color: #6b7280; font-size: 14px;">
                                    #VOID-${request.void_id} - ${request.product_name}
                                </p>
                            </div>
                        </div>
                        <button class="close-process-modal" style="
                            background: none;
                            border: none;
                            font-size: 28px;
                            cursor: pointer;
                            color: #6b7280;
                        ">×</button>
                    </div>
                </div>

                <!-- Form -->
                <form id="processVoidForm" style="padding: 24px;">
                    <input type="hidden" name="void_id" value="${request.void_id}">
                    
                    <!-- Action Selection -->
                    <div style="margin-bottom: 24px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #374151;">
                            Action *
                        </label>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                            <label style="
                                display: flex;
                                align-items: center;
                                padding: 16px;
                                border: 2px solid #e5e7eb;
                                border-radius: 12px;
                                cursor: pointer;
                                transition: all 0.2s;
                            ">
                                <input type="radio" name="action" value="approve" required
                                       style="margin-right: 8px; accent-color: #10b981;">
                                <div>
                                    <div style="font-weight: 700; color: #059669;">✅ Approve</div>
                                    <div style="font-size: 11px; color: #6b7280;">Process refund</div>
                                </div>
                            </label>
                            <label style="
                                display: flex;
                                align-items: center;
                                padding: 16px;
                                border: 2px solid #e5e7eb;
                                border-radius: 12px;
                                cursor: pointer;
                                transition: all 0.2s;
                            ">
                                <input type="radio" name="action" value="reject" required
                                       style="margin-right: 8px; accent-color: #dc2626;">
                                <div>
                                    <div style="font-weight: 700; color: #dc2626;">❌ Reject</div>
                                    <div style="font-size: 11px; color: #6b7280;">Deny request</div>
                                </div>
                            </label>
                        </div>
                    </div>

                    <!-- Refund Details (shown when approve is selected) -->
                    <div id="refundDetails" style="display: none; margin-bottom: 24px; padding: 20px; background: #f8fafc; border-radius: 12px;">
                        <h3 style="margin: 0 0 16px; color: #1f2937; font-size: 16px; font-weight: 700;">
                            💰 Refund Details
                        </h3>
                        
                        <div style="margin-bottom: 16px;">
                            <label style="display: block; margin-bottom: 6px; font-weight: 600; color: #374151; font-size: 13px;">
                                Refund Amount *
                            </label>
                            <div style="display: flex; align-items: center;">
                                <span style="margin-right: 8px; font-weight: 600; color: #6b7280;">₱</span>
                                <input type="number" name="refund_amount" step="0.01" min="0"
                                       value="${request.total || ''}"
                                       style="
                                    flex: 1;
                                    padding: 10px;
                                    border: 1px solid #d1d5db;
                                    border-radius: 8px;
                                    font-size: 14px;
                                ">
                            </div>
                        </div>

                        <div>
                            <label style="display: block; margin-bottom: 6px; font-weight: 600; color: #374151; font-size: 13px;">
                                Refund Method *
                            </label>
                            <select name="refund_method" style="
                                width: 100%;
                                padding: 10px;
                                border: 1px solid #d1d5db;
                                border-radius: 8px;
                                font-size: 14px;
                            ">
                                <option value="">Select method</option>
                                <option value="wallet">Wallet Credit</option>
                                <option value="bank_transfer">Bank Transfer</option>
                                <option value="cash">Cash (On-site)</option>
                            </select>
                        </div>
                    </div>

                    <!-- Admin Notes -->
                    <div style="margin-bottom: 24px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #374151;">
                            Admin Notes
                        </label>
                        <textarea name="admin_notes" rows="4"
                                  placeholder="Add notes about this decision (will be visible to customer)..."
                                  style="
                            width: 100%;
                            padding: 12px;
                            border: 1px solid #d1d5db;
                            border-radius: 8px;
                            font-size: 14px;
                            resize: vertical;
                        "></textarea>
                    </div>

                    <!-- Buttons -->
                    <div style="display: flex; gap: 12px;">
                        <button type="button" class="cancel-process-btn" style="
                            flex: 1;
                            padding: 12px;
                            background: #f3f4f6;
                            border: 1px solid #d1d5db;
                            border-radius: 8px;
                            color: #4b5563;
                            font-weight: 600;
                            cursor: pointer;
                        ">Cancel</button>
                        <button type="submit" style="
                            flex: 1;
                            padding: 12px;
                            background: linear-gradient(135deg, #10b981, #059669);
                            border: none;
                            border-radius: 8px;
                            color: white;
                            font-weight: 700;
                            cursor: pointer;
                        ">Submit Decision</button>
                    </div>
                </form>
            </div>
        `;

        document.body.appendChild(modal);

        // Toggle refund details based on action
        const actionRadios = modal.querySelectorAll('input[name="action"]');
        const refundDetails = modal.querySelector('#refundDetails');

        actionRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.value === 'approve' && radio.checked) {
                    refundDetails.style.display = 'block';
                } else {
                    refundDetails.style.display = 'none';
                }
            });
        });

        // Form submission
        const form = modal.querySelector('#processVoidForm');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const action = formData.get('action');
            const data = {
                void_id: parseInt(formData.get('void_id')),
                action: action,
                admin_notes: formData.get('admin_notes')
            };

            if (action === 'approve') {
                data.refund_amount = parseFloat(formData.get('refund_amount')) || 0;
                data.refund_method = formData.get('refund_method');
                
                if (!data.refund_amount || data.refund_amount <= 0) {
                    alert('Please enter a valid refund amount');
                    return;
                }
                if (!data.refund_method) {
                    alert('Please select a refund method');
                    return;
                }
            }

            try {
                const response = await fetch('/void/admin/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    alert(`Void request ${action}ed successfully!`);
                    modal.remove();
                    
                    // Refresh both orders and void requests
                    if (window.ordersSystem) {
                        window.ordersSystem.loadOrders();
                    }
                    this.loadVoidRequests();
                    
                    // Refresh cart status section if open
                    if (window.refreshStatusSection) {
                        window.refreshStatusSection();
                    }
                } else {
                    alert(result.message || 'Failed to process void request');
                }
            } catch (error) {
                console.error('Error processing void request:', error);
                alert('Error processing void request');
            }
        });

        // Close handlers
        const closeModal = () => modal.remove();
        modal.querySelector('.close-process-modal').addEventListener('click', closeModal);
        modal.querySelector('.cancel-process-btn').addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeModal();
        });
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.VoidProductSystem = VoidProductSystem;
    
    // Check if orders modal exists and add void filter
    const ordersModal = document.getElementById('ordersModal');
    if (ordersModal) {
        // Add void filter option if not exists
        const statusFilter = document.getElementById('orderStatusFilter');
        if (statusFilter && !statusFilter.querySelector('option[value="void"]')) {
            const voidOption = document.createElement('option');
            voidOption.value = 'void';
            voidOption.textContent = '🔄 Returns/Void';
            statusFilter.appendChild(voidOption);
        }
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VoidProductSystem;
}