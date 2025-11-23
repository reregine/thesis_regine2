// home.js - Featured Products Carousel and Interactions
class FeaturedProductsCarousel {
    constructor() {
        this.carousel = document.querySelector('.carousel-track');
        this.slides = document.querySelectorAll('.carousel-slide');
        this.indicators = document.querySelectorAll('.indicator');
        this.prevBtn = document.querySelector('.carousel-prev');
        this.nextBtn = document.querySelector('.carousel-next');
        this.pauseBtn = document.getElementById('pauseCarousel');
        this.playBtn = document.getElementById('playCarousel');
        this.periodBadges = document.querySelectorAll('.period-badge');
        
        this.currentIndex = 0;
        this.isAutoPlaying = true;
        this.autoPlayInterval = null;
        this.slideWidth = 300 + 24; // slide width + gap
        this.visibleSlides = this.calculateVisibleSlides();
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.startAutoPlay();
        this.updateIndicators();
        this.setupResizeHandler();
    }
    
    calculateVisibleSlides() {
        const containerWidth = this.carousel.parentElement.offsetWidth;
        return Math.floor(containerWidth / this.slideWidth);
    }
    
    setupEventListeners() {
        // Navigation buttons
        this.prevBtn.addEventListener('click', () => this.prevSlide());
        this.nextBtn.addEventListener('click', () => this.nextSlide());
        
        // Auto-play controls
        this.pauseBtn.addEventListener('click', () => this.pauseAutoPlay());
        this.playBtn.addEventListener('click', () => this.startAutoPlay());
        
        // Indicators
        this.indicators.forEach((indicator, index) => {
            indicator.addEventListener('click', () => this.goToSlide(index));
        });
        
        // Period filtering
        this.periodBadges.forEach(badge => {
            badge.addEventListener('click', (e) => this.filterByPeriod(e.target.dataset.period));
        });
        
        // Touch/swipe support
        this.setupTouchEvents();
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => this.handleKeyboard(e));
        
        // Intersection Observer for auto-play when visible
        this.setupIntersectionObserver();
    }
    
    setupTouchEvents() {
        let startX = 0;
        let isDragging = false;
        
        this.carousel.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            isDragging = true;
            this.pauseAutoPlay();
        });
        
        this.carousel.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            e.preventDefault();
        });
        
        this.carousel.addEventListener('touchend', (e) => {
            if (!isDragging) return;
            
            const endX = e.changedTouches[0].clientX;
            const diff = startX - endX;
            const minSwipeDistance = 50;
            
            if (Math.abs(diff) > minSwipeDistance) {
                if (diff > 0) {
                    this.nextSlide();
                } else {
                    this.prevSlide();
                }
            }
            
            isDragging = false;
            setTimeout(() => this.startAutoPlay(), 3000);
        });
        
        // Mouse drag support
        this.carousel.addEventListener('mousedown', (e) => {
            startX = e.clientX;
            isDragging = true;
            this.pauseAutoPlay();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            e.preventDefault();
        });
        
        document.addEventListener('mouseup', (e) => {
            if (!isDragging) return;
            
            const endX = e.clientX;
            const diff = startX - endX;
            const minDragDistance = 50;
            
            if (Math.abs(diff) > minDragDistance) {
                if (diff > 0) {
                    this.nextSlide();
                } else {
                    this.prevSlide();
                }
            }
            
            isDragging = false;
            setTimeout(() => this.startAutoPlay(), 3000);
        });
    }
    
    setupIntersectionObserver() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    this.startAutoPlay();
                } else {
                    this.pauseAutoPlay();
                }
            });
        }, { threshold: 0.5 });
        
        if (this.carousel) {
            observer.observe(this.carousel);
        }
    }
    
    setupResizeHandler() {
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                this.visibleSlides = this.calculateVisibleSlides();
                this.updateCarousel();
            }, 250);
        });
    }
    
    handleKeyboard(e) {
        if (!this.carousel.parentElement.contains(document.activeElement)) return;
        
        switch(e.key) {
            case 'ArrowLeft':
                e.preventDefault();
                this.prevSlide();
                break;
            case 'ArrowRight':
                e.preventDefault();
                this.nextSlide();
                break;
            case ' ':
                e.preventDefault();
                this.toggleAutoPlay();
                break;
        }
    }
    
    nextSlide() {
        this.currentIndex = Math.min(this.currentIndex + 1, this.slides.length - this.visibleSlides);
        this.updateCarousel();
    }
    
    prevSlide() {
        this.currentIndex = Math.max(this.currentIndex - 1, 0);
        this.updateCarousel();
    }
    
    goToSlide(index) {
        this.currentIndex = Math.min(index, this.slides.length - this.visibleSlides);
        this.updateCarousel();
    }
    
    updateCarousel() {
        const scrollPosition = this.currentIndex * this.slideWidth;
        this.carousel.scrollTo({
            left: scrollPosition,
            behavior: 'smooth'
        });
        this.updateIndicators();
        this.updateNavigationButtons();
    }
    
    updateIndicators() {
        this.indicators.forEach((indicator, index) => {
            indicator.classList.toggle('active', index === this.currentIndex);
        });
    }
    
    updateNavigationButtons() {
        this.prevBtn.disabled = this.currentIndex === 0;
        this.nextBtn.disabled = this.currentIndex >= this.slides.length - this.visibleSlides;
    }
    
    filterByPeriod(period) {
        // Update active period badge
        this.periodBadges.forEach(badge => {
            badge.classList.toggle('active', badge.dataset.period === period);
        });
        
        // Show/hide slides based on period
        this.slides.forEach(slide => {
            const shouldShow = period === 'all' || slide.dataset.period === period;
            slide.style.display = shouldShow ? 'block' : 'none';
        });
        
        // Reset to first slide
        this.currentIndex = 0;
        this.updateCarousel();
        
        // Refresh carousel after filter
        setTimeout(() => {
            this.slides = document.querySelectorAll('.carousel-slide[style="display: block"], .carousel-slide:not([style])');
            this.updateIndicators();
        }, 300);
    }
    
    startAutoPlay() {
        if (this.autoPlayInterval) return;
        
        this.isAutoPlaying = true;
        this.pauseBtn.style.display = 'block';
        this.playBtn.style.display = 'none';
        
        this.autoPlayInterval = setInterval(() => {
            if (this.currentIndex >= this.slides.length - this.visibleSlides) {
                this.currentIndex = 0;
            } else {
                this.currentIndex++;
            }
            this.updateCarousel();
        }, 5000); // Change slide every 5 seconds
    }
    
    pauseAutoPlay() {
        this.isAutoPlaying = false;
        clearInterval(this.autoPlayInterval);
        this.autoPlayInterval = null;
        this.pauseBtn.style.display = 'none';
        this.playBtn.style.display = 'block';
    }
    
    toggleAutoPlay() {
        if (this.isAutoPlaying) {
            this.pauseAutoPlay();
        } else {
            this.startAutoPlay();
        }
    }
    
    destroy() {
        this.pauseAutoPlay();
        // Remove event listeners if needed
    }
}

// Product Interaction Functions
class ProductInteractions {
    constructor() {
        this.init();
    }
    
    init() {
        this.setupProductEventListeners();
    }
    
    setupProductEventListeners() {
        // Add to cart buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('.btn-add-cart')) {
                const productId = e.target.closest('.btn-add-cart').getAttribute('onclick').match(/\d+/)[0];
                this.addToCart(parseInt(productId));
            }
            
            if (e.target.closest('.btn-view-details')) {
                const productId = e.target.closest('.btn-view-details').getAttribute('onclick').match(/\d+/)[0];
                this.viewProductDetails(parseInt(productId));
            }
        });
    }
    
    async addToCart(productId) {
        try {
            const response = await fetch('/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    product_id: productId,
                    quantity: 1
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Product added to cart!', 'success');
                this.updateCartCount();
            } else {
                this.showNotification(data.message || 'Failed to add product to cart', 'error');
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            this.showNotification('Error adding product to cart', 'error');
        }
    }
    
    viewProductDetails(productId) {
        // Redirect to product details page or show modal
        window.location.href = `/shop/product/${productId}`;
        
        // Alternative: Show modal with product details
        // this.showProductModal(productId);
    }
    
    showProductModal(productId) {
        // Implement modal display for product details
        console.log('Show product modal for:', productId);
        // You can fetch product details and display in a modal
    }
    
    async updateCartCount() {
        try {
            const response = await fetch('/cart/count');
            const data = await response.json();
            
            if (data.success) {
                const badge = document.getElementById('cartCountBadge');
                if (badge) {
                    badge.textContent = data.count;
                    badge.style.display = data.count > 0 ? 'inline-block' : 'none';
                }
            }
        } catch (error) {
            console.error('Error updating cart count:', error);
        }
    }
    
    showNotification(message, type = 'info') {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `home-toast home-toast-${type}`;
        toast.innerHTML = `
            <div class="home-toast-content">
                <span class="home-toast-message">${message}</span>
                <button class="home-toast-close">&times;</button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Add styles if not already added
        this.addToastStyles();
        
        // Animate in
        setTimeout(() => toast.classList.add('home-toast-show'), 100);
        
        // Auto remove
        setTimeout(() => {
            toast.classList.remove('home-toast-show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
        
        // Close on click
        toast.querySelector('.home-toast-close').addEventListener('click', () => {
            toast.classList.remove('home-toast-show');
            setTimeout(() => toast.remove(), 300);
        });
    }
    
    addToastStyles() {
        if (document.getElementById('home-toast-styles')) return;
        
        const styles = `
            .home-toast {
                position: fixed;
                top: 20px;
                right: 20px;
                background: white;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 10000;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                max-width: 300px;
            }
            
            .home-toast-show {
                transform: translateX(0);
            }
            
            .home-toast-content {
                padding: 1rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
            }
            
            .home-toast-message {
                flex: 1;
                font-weight: 500;
            }
            
            .home-toast-close {
                background: none;
                border: none;
                font-size: 1.2rem;
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .home-toast-success {
                border-left: 4px solid #22c55e;
            }
            
            .home-toast-error {
                border-left: 4px solid #ef4444;
            }
            
            .home-toast-info {
                border-left: 4px solid #3b82f6;
            }
        `;
        
        const styleSheet = document.createElement('style');
        styleSheet.id = 'home-toast-styles';
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }
}

// Featured Products Data Management
class FeaturedProductsManager {
    constructor() {
        this.autoRefreshInterval = null;
        this.init();
    }
    
    init() {
        this.startAutoRefresh();
        this.setupRefreshButton();
    }
    
    async refreshFeaturedProducts() {
        try {
            const response = await fetch('/api/featured-products');
            const data = await response.json();
            
            if (data.success) {
                this.updateCarousel(data.featured_products);
            }
        } catch (error) {
            console.error('Error refreshing featured products:', error);
        }
    }
    
    updateCarousel(products) {
        // This would require more complex DOM updates
        // For now, we'll just log the refresh
        console.log('Featured products refreshed:', products.length, 'products');
    }
    
    startAutoRefresh() {
        // Refresh every 10 minutes
        this.autoRefreshInterval = setInterval(() => {
            this.refreshFeaturedProducts();
        }, 10 * 60 * 1000);
    }
    
    setupRefreshButton() {
        // You can add a manual refresh button if needed
    }
    
    destroy() {
        clearInterval(this.autoRefreshInterval);
    }
}

// Global functions for HTML onclick attributes
function viewProductDetails(productId) {
    window.productInteractions.viewProductDetails(productId);
}

function addToCart(productId) {
    window.productInteractions.addToCart(productId);
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize carousel if on home page
    if (document.querySelector('.featured-products-carousel')) {
        window.featuredCarousel = new FeaturedProductsCarousel();
    }
    
    // Initialize product interactions
    window.productInteractions = new ProductInteractions();
    
    // Initialize featured products manager
    window.featuredProductsManager = new FeaturedProductsManager();
    
    // Add loading state management
    manageLoadingStates();
});

// Loading state management
function manageLoadingStates() {
    // Add loading states to buttons
    document.addEventListener('click', function(e) {
        if (e.target.matches('.btn-add-cart, .btn-view-details')) {
            const button = e.target.closest('button');
            const originalText = button.innerHTML;
            
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            button.disabled = true;
            
            // Revert after 3 seconds max (in case of error)
            setTimeout(() => {
                button.innerHTML = originalText;
                button.disabled = false;
            }, 3000);
        }
    });
}

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        FeaturedProductsCarousel,
        ProductInteractions,
        FeaturedProductsManager
    };
}