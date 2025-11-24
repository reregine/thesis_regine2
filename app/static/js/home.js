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
        this.slideWidth = 320; // Fixed width including margin
        this.visibleSlides = this.calculateVisibleSlides();
        
        this.init();
    }
    
    init() {
        console.log('Initializing carousel with', this.slides.length, 'slides');
        this.setupEventListeners();
        this.updateCarousel();
        this.startAutoPlay();
        this.updateIndicators();
        this.setupResizeHandler();
    }
    
    calculateVisibleSlides() {
        if (!this.carousel || !this.carousel.parentElement) return 3;
        
        const containerWidth = this.carousel.parentElement.offsetWidth;
        const calculatedSlides = Math.floor(containerWidth / this.slideWidth);
        return Math.max(1, Math.min(calculatedSlides, 4)); // Between 1 and 4 slides visible
    }
    
    setupEventListeners() {
        // Navigation buttons
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => this.prevSlide());
        }
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => this.nextSlide());
        }
        
        // Auto-play controls
        if (this.pauseBtn) {
            this.pauseBtn.addEventListener('click', () => this.pauseAutoPlay());
        }
        if (this.playBtn) {
            this.playBtn.addEventListener('click', () => this.startAutoPlay());
        }
        
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
    }
    
    setupTouchEvents() {
        let startX = 0;
        let isDragging = false;
        
        if (!this.carousel) return;
        
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
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            this.prevSlide();
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            this.nextSlide();
        } else if (e.key === ' ') {
            e.preventDefault();
            this.toggleAutoPlay();
        }
    }
    
    nextSlide() {
        if (this.slides.length <= this.visibleSlides) return;
        
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
        if (!this.carousel || this.slides.length === 0) return;
        
        const scrollPosition = this.currentIndex * this.slideWidth;
        this.carousel.style.transform = `translateX(-${scrollPosition}px)`;
        this.updateIndicators();
        this.updateNavigationButtons();
    }
    
    updateIndicators() {
        this.indicators.forEach((indicator, index) => {
            indicator.classList.toggle('active', index === this.currentIndex);
        });
    }
    
    updateNavigationButtons() {
        if (this.prevBtn) {
            this.prevBtn.disabled = this.currentIndex === 0;
            this.prevBtn.style.opacity = this.currentIndex === 0 ? '0.5' : '1';
        }
        if (this.nextBtn) {
            const maxIndex = Math.max(0, this.slides.length - this.visibleSlides);
            this.nextBtn.disabled = this.currentIndex >= maxIndex;
            this.nextBtn.style.opacity = this.currentIndex >= maxIndex ? '0.5' : '1';
        }
    }
    
    filterByPeriod(period) {
        console.log('Filtering by period:', period);
        
        // Update active period badge
        this.periodBadges.forEach(badge => {
            badge.classList.toggle('active', badge.dataset.period === period);
        });
        
        // Show/hide slides based on period
        let visibleCount = 0;
        this.slides.forEach(slide => {
            const slidePeriod = slide.dataset.period;
            let shouldShow = false;
            
            switch(period) {
                case 'all':
                    shouldShow = true;
                    break;
                case 'weekly':
                    // Show best sellers (weekly)
                    shouldShow = slidePeriod === 'weekly';
                    break;
                case 'monthly':
                    // Show customer favorites (monthly)  
                    shouldShow = slidePeriod === 'monthly';
                    break;
                default:
                    shouldShow = true;
            }
            
            slide.style.display = shouldShow ? 'block' : 'none';
            if (shouldShow) visibleCount++;
        });
        
        // Reset to first slide and update visible slides
        this.currentIndex = 0;
        this.slides = document.querySelectorAll('.carousel-slide[style="display: block"], .carousel-slide:not([style])');
        
        // Update indicators visibility
        this.updateIndicatorsVisibility(visibleCount);
        this.updateCarousel();
        
        console.log(`Visible slides: ${visibleCount} for period: ${period}`);
    }
    
    updateIndicatorsVisibility(visibleCount) {
        const indicatorsContainer = document.querySelector('.carousel-indicators');
        if (indicatorsContainer) {
            indicatorsContainer.style.display = visibleCount > this.visibleSlides ? 'flex' : 'none';
        }
    }
    
    startAutoPlay() {
        if (this.autoPlayInterval || this.slides.length <= this.visibleSlides) return;
        
        this.isAutoPlaying = true;
        if (this.pauseBtn) this.pauseBtn.style.display = 'block';
        if (this.playBtn) this.playBtn.style.display = 'none';
        
        this.autoPlayInterval = setInterval(() => {
            if (this.currentIndex >= this.slides.length - this.visibleSlides) {
                this.currentIndex = 0;
            } else {
                this.currentIndex++;
            }
            this.updateCarousel();
        }, 5000);
    }
    
    pauseAutoPlay() {
        this.isAutoPlaying = false;
        clearInterval(this.autoPlayInterval);
        this.autoPlayInterval = null;
        if (this.pauseBtn) this.pauseBtn.style.display = 'none';
        if (this.playBtn) this.playBtn.style.display = 'block';
    }
    
    toggleAutoPlay() {
        if (this.isAutoPlaying) {
            this.pauseAutoPlay();
        } else {
            this.startAutoPlay();
        }
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

// Add to your home.js
function flipCard(cardElement) {
    // Close any other flipped cards first
    document.querySelectorAll('.featured-product-card.flipped').forEach(flippedCard => {
        if (flippedCard !== cardElement) {
            flippedCard.classList.remove('flipped');
        }
    });
    
    // Flip the clicked card
    cardElement.classList.toggle('flipped');
}

function unflipCard(cardElement) {
    cardElement.classList.remove('flipped');
}

// Close card when clicking outside
document.addEventListener('click', function(event) {
    if (!event.target.closest('.featured-product-card')) {
        document.querySelectorAll('.featured-product-card.flipped').forEach(card => {
            card.classList.remove('flipped');
        });
    }
});

// Close card with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        document.querySelectorAll('.featured-product-card.flipped').forEach(card => {
            card.classList.remove('flipped');
        });
    }
});

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        FeaturedProductsCarousel,
        ProductInteractions,
        FeaturedProductsManager
    };
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing carousel...');
    
    // Initialize carousel if on home page
    const carouselElement = document.querySelector('.featured-products-carousel');
    if (carouselElement) {
        console.log('Carousel element found, initializing...');
        window.featuredCarousel = new FeaturedProductsCarousel();
        console.log('Carousel initialized successfully');
    } else {
        console.log('No carousel element found on this page');
    }
    
    // Initialize product interactions
    window.productInteractions = new ProductInteractions();
    
    // Initialize featured products manager
    window.featuredProductsManager = new FeaturedProductsManager();
    
    // Add loading state management
    manageLoadingStates();
});
