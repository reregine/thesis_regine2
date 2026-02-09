
// ================= MAIN CAROUSEL CLASS =================
class FeaturedProductsCarousel {
    constructor() {
        this.carousel = document.querySelector('.carousel-track');
        this.slides = document.querySelectorAll('.carousel-slide');
        this.indicators = document.querySelectorAll('.indicator');
        this.prevBtn = document.querySelector('.carousel-prev');
        this.nextBtn = document.querySelector('.carousel-next');
        this.periodBadges = document.querySelectorAll('.period-badge');
        
        this.currentIndex = 0;
        this.autoPlayInterval = null;
        this.slideWidth = 320;
        this.gap = 30;
        this.totalSlides = this.slides.length;
        
        this.init();
    }
    
    init() {
        console.log('Initializing carousel with', this.totalSlides, 'slides');
        this.slides.forEach(slide => slide.style.display = 'block');
        this.setupEventListeners();
        this.updateCarousel();
        this.updateNavigationButtons();
        this.startAutoPlay();
    }
    
    setupEventListeners() {
        if (this.prevBtn) this.prevBtn.addEventListener('click', (e) => { e.stopPropagation(); this.prevSlide(); });
        if (this.nextBtn) this.nextBtn.addEventListener('click', (e) => { e.stopPropagation(); this.nextSlide(); });
        
        this.indicators.forEach((indicator, index) => indicator.addEventListener('click', () => this.goToSlide(index)));
        this.periodBadges.forEach(badge => badge.addEventListener('click', (e) => this.filterByPeriod(e.target.dataset.period)));
        
        this.setupTouchEvents();
        if (this.carousel) {
            this.carousel.addEventListener('mouseenter', () => this.pauseAutoPlay());
            this.carousel.addEventListener('mouseleave', () => this.startAutoPlay());
        }
    }
    
    setupTouchEvents() {
        let startX = 0, isDragging = false;
        if (!this.carousel) return;
        
        this.carousel.addEventListener('touchstart', (e) => { startX = e.touches[0].clientX; isDragging = true; this.pauseAutoPlay(); });
        this.carousel.addEventListener('touchmove', (e) => { if (!isDragging) return; e.preventDefault(); });
        this.carousel.addEventListener('touchend', (e) => {
            if (!isDragging) return;
            const endX = e.changedTouches[0].clientX;
            const diffX = startX - endX;
            if (Math.abs(diffX) > 50) diffX > 0 ? this.nextSlide() : this.prevSlide();
            isDragging = false;
            setTimeout(() => this.startAutoPlay(), 3000);
        });
    }
    
    nextSlide() {
        if (this.totalSlides <= 3) return;
        const maxIndex = Math.max(0, this.totalSlides - 3);
        this.currentIndex = this.currentIndex >= maxIndex ? 0 : this.currentIndex + 1;
        this.updateCarousel();
        this.updateIndicators();
        this.updateNavigationButtons();
        this.restartAutoPlay();
    }
    
    prevSlide() {
        if (this.totalSlides <= 3) return;
        const maxIndex = Math.max(0, this.totalSlides - 3);
        this.currentIndex = this.currentIndex === 0 ? maxIndex : this.currentIndex - 1;
        this.updateCarousel();
        this.updateIndicators();
        this.updateNavigationButtons();
        this.restartAutoPlay();
    }
    
    goToSlide(index) {
        this.currentIndex = Math.min(index, Math.max(0, this.totalSlides - 3));
        this.updateCarousel();
        this.updateIndicators();
        this.updateNavigationButtons();
        this.restartAutoPlay();
    }
    
    updateCarousel() {
        if (!this.carousel || this.totalSlides === 0) return;
        const translateX = -this.currentIndex * (this.slideWidth + this.gap);
        this.carousel.style.transform = `translateX(${translateX}px)`;
        this.carousel.style.transition = 'transform 0.5s ease';
    }
    
    updateIndicators() {
        this.indicators.forEach((indicator, index) => indicator.classList.toggle('active', index === this.currentIndex));
    }
    
    updateNavigationButtons() {
        if (!this.slides.length) return;
        const maxIndex = Math.max(0, this.totalSlides - 3);
        if (this.prevBtn) {
            this.prevBtn.disabled = this.totalSlides <= 3 || this.currentIndex === 0;
            this.prevBtn.style.opacity = this.prevBtn.disabled ? '0.4' : '0.9';
        }
        if (this.nextBtn) {
            this.nextBtn.disabled = this.totalSlides <= 3 || this.currentIndex >= maxIndex;
            this.nextBtn.style.opacity = this.nextBtn.disabled ? '0.4' : '0.9';
        }
    }
    
    filterByPeriod(period) {
        console.log('Filtering by period:', period);
        this.periodBadges.forEach(badge => badge.classList.toggle('active', badge.dataset.period === period));
        this.slides.forEach(slide => {
            const slidePeriod = slide.dataset.period;
            let shouldShow = false;
            switch(period) {
                case 'all': shouldShow = true; break;
                case 'weekly': shouldShow = slidePeriod === 'weekly'; break;
                case 'monthly': shouldShow = slidePeriod === 'monthly'; break;
                default: shouldShow = true;
            }
            slide.style.display = shouldShow ? 'block' : 'none';
        });
        this.currentIndex = 0;
        setTimeout(() => {
            this.slides = document.querySelectorAll('.carousel-slide[style*="display: block"], .carousel-slide:not([style*="display: none"])');
            this.totalSlides = this.slides.length;
            this.updateCarousel();
            this.updateIndicators();
            this.updateNavigationButtons();
            const indicatorsContainer = document.querySelector('.carousel-indicators');
            if (indicatorsContainer) indicatorsContainer.style.display = this.totalSlides > 3 ? 'flex' : 'none';
        }, 10);
    }
    
    startAutoPlay() {
        if (this.autoPlayInterval || this.totalSlides <= 3) return;
        this.autoPlayInterval = setInterval(() => this.nextSlide(), 5000);
    }
    
    pauseAutoPlay() { clearInterval(this.autoPlayInterval); this.autoPlayInterval = null; }
    restartAutoPlay() { this.pauseAutoPlay(); setTimeout(() => this.startAutoPlay(), 100); }
}

// ================= ENHANCED CARD CLICK HANDLER =================
function handleCardClick(event, cardElement) {
    // Don't flip if clicking on Add to Cart button or its children
    if (event.target.closest('.btn-add-cart') || event.target.closest('.btn-add-cart-full')) {
        event.stopPropagation();
        return; // Let the button's own click handler handle it
    }
    
    // Don't flip if clicking on the close button
    if (event.target.closest('.btn-close-details')) {
        event.stopPropagation();
        return; // Let the close button handle it
    }
    
    // Otherwise, flip the card
    flipCard(cardElement);
}

// ================= UPDATED PRODUCT INTERACTIONS CLASS =================
class ProductInteractions {
    constructor() { 
        this.init(); 
    }
    
    init() {
        // Handle clicks on Add to Cart buttons using data-product-id
        document.addEventListener('click', (e) => {
            const addToCartBtn = e.target.closest('.btn-add-cart, .btn-add-cart-full');
            if (addToCartBtn) {
                e.preventDefault();
                e.stopPropagation();
                
                // Get product ID from data attribute
                const productId = addToCartBtn.getAttribute('data-product-id');
                if (productId) {
                    this.addToCart(parseInt(productId));
                    
                    // If on the back of the card, close it after adding
                    const card = addToCartBtn.closest('.featured-product-card');
                    if (card && card.classList.contains('flipped')) {
                        setTimeout(() => {
                            unflipCard(card);
                        }, 500);
                    }
                }
            }
        });
    }
    
    async addToCart(productId) {
        try {
            // Show loading state
            const buttons = document.querySelectorAll(`[data-product-id="${productId}"]`);
            buttons.forEach(btn => {
                const originalHTML = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
                btn.disabled = true;
                
                // Revert after 2 seconds
                setTimeout(() => {
                    btn.innerHTML = originalHTML;
                    btn.disabled = false;
                }, 2000);
            });
            
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
                this.showNotification('Product added to cart! 🛒', 'success');
                this.updateCartCount();
                
                // Add a quick visual feedback
                buttons.forEach(btn => {
                    btn.classList.add('added-to-cart');
                    setTimeout(() => btn.classList.remove('added-to-cart'), 1000);
                });
            } else {
                this.showNotification(data.message || 'Failed to add product to cart', 'error');
            }
        } catch (error) {
            console.error('Error adding to cart:', error);
            this.showNotification('Error adding product to cart', 'error');
        }
    }
    
    async updateCartCount() {
        try {
            const response = await fetch('/cart/count');
            
            // Handle 401 Unauthorized by hiding the badge
            if (response.status === 401) {
                const badge = document.getElementById('cartCountBadge');
                if (badge) {
                    badge.style.display = 'none';
                }
                return;
            }
            
            // Only parse JSON if response is OK
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            const badge = document.getElementById('cartCountBadge');
            
            if (badge) {
                if (data.success) {
                    badge.textContent = data.count;
                    badge.style.display = data.count > 0 ? 'inline-block' : 'none';
                } else {
                    // Hide badge if request failed
                    badge.style.display = 'none';
                }
            }
        } catch (error) { 
            console.error('Error updating cart count:', error);
            // Hide badge on any error
            const badge = document.getElementById('cartCountBadge');
            if (badge) {
                badge.style.display = 'none';
            }
        }
    }
    
    showNotification(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `home-toast home-toast-${type}`;
        toast.innerHTML = `<div class="home-toast-content"><span>${message}</span><button class="home-toast-close">&times;</button></div>`;
        document.body.appendChild(toast);
        this.addToastStyles();
        setTimeout(() => toast.classList.add('home-toast-show'), 100);
        setTimeout(() => { toast.classList.remove('home-toast-show'); setTimeout(() => toast.remove(), 300); }, 3000);
        toast.querySelector('.home-toast-close').addEventListener('click', () => { toast.classList.remove('home-toast-show'); setTimeout(() => toast.remove(), 300); });
    }
    
    addToastStyles() {
        if (document.getElementById('home-toast-styles')) return;
        const styleSheet = document.createElement('style');
        styleSheet.id = 'home-toast-styles';
        styleSheet.textContent = `
            .home-toast { position: fixed; top: 20px; right: 20px; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 10000; transform: translateX(100%); transition: transform 0.3s ease; max-width: 300px; }
            .home-toast-show { transform: translateX(0); }
            .home-toast-content { padding: 1rem; display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
            .home-toast-message { flex: 1; font-weight: 500; }
            .home-toast-close { background: none; border: none; font-size: 1.2rem; cursor: pointer; padding: 0; width: 24px; height: 24px; }
            .home-toast-success { border-left: 4px solid #22c55e; }
            .home-toast-error { border-left: 4px solid #ef4444; }
            .home-toast-info { border-left: 4px solid #3b82f6; }
        `;
        document.head.appendChild(styleSheet);
    }
}

// ================= GLOBAL FLIP CARD FUNCTIONS =================
function flipCard(cardElement) {
    document.querySelectorAll('.featured-product-card.flipped').forEach(flippedCard => {
        if (flippedCard !== cardElement) flippedCard.classList.remove('flipped');
    });
    cardElement.classList.toggle('flipped');
}

function unflipCard(cardElement) {
    cardElement.classList.remove('flipped');
}

// Close flipped cards when clicking outside or pressing Escape
document.addEventListener('click', function(event) {
    if (!event.target.closest('.featured-product-card')) {
        document.querySelectorAll('.featured-product-card.flipped').forEach(card => card.classList.remove('flipped'));
    }
});
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') document.querySelectorAll('.featured-product-card.flipped').forEach(card => card.classList.remove('flipped'));
});

// ================= GLOBAL HELPER FUNCTIONS =================
function manageLoadingStates() {
    document.addEventListener('click', function(e) {
        if (e.target.matches('.btn-add-cart, .btn-view-details')) {
            const button = e.target.closest('button');
            const originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
            button.disabled = true;
            setTimeout(() => { button.innerHTML = originalText; button.disabled = false; }, 3000);
        }
    });
}

// Global wrapper for HTML `onclick` attributes
function addToCart(productId) {
    if (window.productInteractions) window.productInteractions.addToCart(productId);
}

// ================= ADD CSS FOR VISUAL FEEDBACK =================
function addCartButtonStyles() {
    if (document.getElementById('cart-button-styles')) return;
    
    const styleSheet = document.createElement('style');
    styleSheet.id = 'cart-button-styles';
    styleSheet.textContent = `
        /* Visual feedback for added to cart */
        .btn-add-cart.added-to-cart,
        .btn-add-cart-full.added-to-cart {
            background: linear-gradient(135deg, #16a34a, #15803d) !important;
            transform: scale(0.95);
            transition: all 0.3s ease;
        }
        
        /* Prevent text selection on buttons */
        .btn-add-cart,
        .btn-add-cart-full {
            user-select: none;
        }
        
        /* Make sure buttons have proper cursor */
        .btn-add-cart:not(:disabled),
        .btn-add-cart-full:not(:disabled) {
            cursor: pointer;
        }
        
        /* Disabled state */
        .btn-add-cart:disabled,
        .btn-add-cart-full:disabled {
            opacity: 0.7;
            cursor: not-allowed;
        }
    `;
    document.head.appendChild(styleSheet);
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  console.log('DOM loaded, initializing...');
  
  // Initialize carousel
  if (document.querySelector('.featured-products-carousel')) {
    window.featuredCarousel = new FeaturedProductsCarousel();
    console.log('Carousel initialized');
  }
  
  // Initialize product interactions
  window.productInteractions = new ProductInteractions();
  
  // Initialize scroll animations
  window.scrollAnimations = new ScrollAnimations();

  // Add cart button styles
  addCartButtonStyles();
  manageLoadingStates();
  
  // Initialize hero animations
  window.heroAnimations = new HeroAnimations();
  
  // Add scroll indicator to hero section
  const heroSection = document.querySelector('.hero');
  if (heroSection) {
    const scrollIndicator = document.createElement('div');
    scrollIndicator.className = 'scroll-indicator';
    scrollIndicator.innerHTML = `
      <div class="mouse">
        <div class="wheel"></div>
      </div>
      <span>Scroll to explore</span>
    `;
    heroSection.appendChild(scrollIndicator);
  }
  setupScrollEffects();
  setupBackToTop();
});
// Additional scroll effects
function setupScrollEffects() {
  // Card hover effects on scroll
  const cards = document.querySelectorAll('.featured-product-card');
  
  window.addEventListener('scroll', () => {
    cards.forEach(card => {
      const rect = card.getBoundingClientRect();
      const isVisible = rect.top < window.innerHeight * 0.8 && rect.bottom > 0;
      
      if (isVisible) {
        card.classList.add('scroll-hover');
      } else {
        card.classList.remove('scroll-hover');
      }
    });
    
    // Hide scroll indicator when scrolling down
    const scrollIndicator = document.querySelector('.scroll-indicator');
    if (scrollIndicator && window.scrollY > 100) {
      scrollIndicator.classList.add('hidden');
    } else if (scrollIndicator) {
      scrollIndicator.classList.remove('hidden');
    }
  });
  
  // Text reveal on scroll
  const textReveals = document.querySelectorAll('.text-reveal');
  const textObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('revealed');
      }
    });
  }, { threshold: 0.5 });
  
  textReveals.forEach(reveal => textObserver.observe(reveal));
  
  // Gradient border animation
  const gradientBorders = document.querySelectorAll('.gradient-border');
  const borderObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('scroll-active');
      }
    });
  }, { threshold: 0.3 });
  
  gradientBorders.forEach(border => borderObserver.observe(border));
}
// Back to Top functionality
function setupBackToTop() {
  const backToTopBtn = document.querySelector('.back-to-top');
  if (!backToTopBtn) return;
  
  window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
      backToTopBtn.classList.add('visible');
    } else {
      backToTopBtn.classList.remove('visible');
    }
  });
  
  backToTopBtn.addEventListener('click', () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });
}

// ================= HERO ANIMATIONS =================
class HeroAnimations {
  constructor() {
    this.typewriterTexts = [
      'Agri-Aqua Mart',
      'Agri-Aqua Store',
      'Agri-Aqua Hub',
      'Agri-Aqua Market',
      'Agri-Aqua Shop'
    ];
    
    this.qualityWords = [
      'Smart', 'Fresh', 'Sustainable', 'Premium', 'Healthy'
    ];
    
    this.benefitWords = [
      'Direct from Farmers',
      'Eco-Friendly',
      '12/7 Convenience',
      'Farm-to-Table',
      'Locally Sourced'
    ];
    
    this.currentTypeIndex = 0;
    this.currentQualityIndex = 0;
    this.currentBenefitIndex = 0;
    this.isDeleting = false;
    this.typeText = '';
    this.speed = 100;
    
    this.init();
  }
  
  init() {
    this.startTypewriter();
    this.startWordChanger();
    this.setupScrollAnimations();
    this.setupFloatingElements();
  }
  
  startTypewriter() {
    const typewriterElement = document.getElementById('typewriter-text');
    const cursor = document.querySelector('.typing-cursor');
    if (!typewriterElement || !cursor) return;
    
    // Add typing class for better animation
    cursor.classList.add('modern'); // or 'block' or keep as text
    
    const type = () => {
      const currentText = this.typewriterTexts[this.currentTypeIndex];
      
      if (this.isDeleting) {
        this.typeText = currentText.substring(0, this.typeText.length - 1);
      } else {
        this.typeText = currentText.substring(0, this.typeText.length + 1);
      }
      
      typewriterElement.textContent = this.typeText;
      
      // Position cursor correctly using CSS animation
      this.positionCursor(typewriterElement, cursor);
      
      let delta = this.speed;
      
      if (!this.isDeleting && this.typeText === currentText) {
        delta = 2000; // Pause at end
        this.isDeleting = true;
        // Cursor blinks faster when paused
        cursor.style.animation = 'cursorBlink 0.6s infinite, cursorPulse 2s infinite';
      } else if (this.isDeleting && this.typeText === '') {
        this.isDeleting = false;
        this.currentTypeIndex = (this.currentTypeIndex + 1) % this.typewriterTexts.length;
        delta = 500;
        // Reset cursor animation speed
        cursor.style.animation = 'cursorBlink 1.2s infinite, cursorPulse 2s infinite';
      } else if (this.isDeleting) {
        delta = this.speed / 2;
      }
      
      setTimeout(() => type(), delta);
    };
    
    setTimeout(() => type(), 1000);
  }

positionCursor(textElement, cursorElement) {
  // Create a temporary span to measure text width
  const tempSpan = document.createElement('span');
  tempSpan.style.cssText = `
    position: absolute;
    visibility: hidden;
    white-space: nowrap;
    font-family: inherit;
    font-size: inherit;
    font-weight: inherit;
  `;
  tempSpan.textContent = this.typeText;
  document.body.appendChild(tempSpan);
  
  // Get the text width
  const textWidth = tempSpan.offsetWidth;
  
  // Remove temp span
  document.body.removeChild(tempSpan);
  
  // Position cursor at the end of text
  cursorElement.style.transform = `translateX(${textWidth}px) translateY(-1px)`;
}
  
  startWordChanger() {
    const qualityElement = document.getElementById('changing-word');
    const benefitElement = document.getElementById('benefit-word');
    const indicators = document.querySelectorAll('.word-indicator');
    
    if (!qualityElement || !benefitElement) return;
    
    setInterval(() => {
      // Change quality word
      this.currentQualityIndex = (this.currentQualityIndex + 1) % this.qualityWords.length;
      this.animateWordChange(qualityElement, this.qualityWords[this.currentQualityIndex], 'quality');
      
      // Change benefit word
      this.currentBenefitIndex = (this.currentBenefitIndex + 1) % this.benefitWords.length;
      this.animateWordChange(benefitElement, this.benefitWords[this.currentBenefitIndex], 'benefit');
      
      // Update indicators
      indicators.forEach(indicator => {
        const word = indicator.getAttribute('data-word');
        const type = indicator.getAttribute('data-type');
        
        if (type === 'quality' && word === this.qualityWords[this.currentQualityIndex]) {
          indicator.classList.add('active');
        } else if (type === 'benefit' && word === this.benefitWords[this.currentBenefitIndex]) {
          indicator.classList.add('active');
        } else {
          indicator.classList.remove('active');
        }
      });
    }, 3000);
  }
  
  animateWordChange(element, newWord, type) {
    element.classList.remove('active');
    
    setTimeout(() => {
      element.textContent = newWord;
      element.style.opacity = '0';
      element.style.transform = 'translateY(20px)';
      
      requestAnimationFrame(() => {
        element.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
        element.style.opacity = '1';
        element.style.transform = 'translateY(0)';
        
        setTimeout(() => {
          element.classList.add('active');
        }, 100);
      });
    }, 500);
  }
  
  setupScrollAnimations() {
    const video = document.querySelector('.floating-video');
    const container = document.querySelector('.video-container');
    
    if (video && container) {
      window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const rate = scrolled * -0.5;
        
        video.style.transform = `translateY(${rate}px) rotate(${rate * 0.1}deg)`;
        container.style.transform = `perspective(1000px) rotateY(${rate * 0.05}deg) rotateX(${rate * 0.02}deg)`;
      });
    }
  }
  
  setupFloatingElements() {
    const elements = document.querySelectorAll('.floating-element');
    
    elements.forEach((element, index) => {
      // Randomize animations slightly
      const duration = 6 + Math.random() * 2;
      const delay = index * 0.5;
      
      element.style.animation = `float ${duration}s ease-in-out ${delay}s infinite`;
      
      // Add hover effect
      element.addEventListener('mouseenter', () => {
        element.style.animationPlayState = 'paused';
        element.style.transform = 'scale(1.2) rotate(15deg)';
      });
      
      element.addEventListener('mouseleave', () => {
        element.style.animationPlayState = 'running';
        element.style.transform = '';
      });
    });
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
  window.heroAnimations = new HeroAnimations();
  
  // Add scroll trigger for background elements
  window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset / 1000;
    const bgElements = document.querySelectorAll('.hero-bg-element');
    
    bgElements.forEach((element, index) => {
      const rate = scrolled * (index + 1) * 0.5;
      element.style.transform = `translateY(${rate}px) rotate(${rate}deg)`;
    });
  });
});

// ================= SCROLL ANIMATIONS =================
class ScrollAnimations {
  constructor() {
    this.observer = null;
    this.scrollElements = [];
    this.lastScrollY = window.scrollY;
    this.scrollingUp = false;
    
    this.init();
  }
  
  init() {
    this.setupScrollObserver();
    this.setupScrollEvents();
    this.animateOnLoad();
  }
  
  setupScrollObserver() {
    // Create intersection observer for scroll animations
    this.observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('scroll-visible');
          entry.target.classList.add('animated');
          
          // Add staggered delay for child elements
          const children = entry.target.querySelectorAll('.stagger-child');
          children.forEach((child, index) => {
            child.style.animationDelay = `${index * 0.1}s`;
          });
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });
    
    // Observe all scrollable elements
    document.querySelectorAll('.scroll-animate').forEach(el => {
      this.observer.observe(el);
    });
  }
  
  setupScrollEvents() {
    let ticking = false;
    
    window.addEventListener('scroll', () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          this.handleScroll();
          ticking = false;
        });
        ticking = true;
      }
    });
    
    // Parallax effect for hero section
    this.setupParallaxEffect();
    
    // Progress scroll indicator
    this.setupScrollProgress();
  }
  
  handleScroll() {
    const currentScrollY = window.scrollY;
    this.scrollingUp = currentScrollY < this.lastScrollY;
    this.lastScrollY = currentScrollY;
    
    // Add/remove scroll class to body
    if (currentScrollY > 100) {
      document.body.classList.add('scrolled');
    } else {
      document.body.classList.remove('scrolled');
    }
    
    // Add scroll direction class
    if (this.scrollingUp) {
      document.body.classList.add('scrolling-up');
      document.body.classList.remove('scrolling-down');
    } else {
      document.body.classList.add('scrolling-down');
      document.body.classList.remove('scrolling-up');
    }
    
    // Update progress bar
    this.updateScrollProgress(currentScrollY);
    
    // Trigger scroll animations
    this.triggerScrollAnimations(currentScrollY);
  }
  
  setupParallaxEffect() {
    const heroImage = document.querySelector('.floating-image');
    const heroSection = document.querySelector('.hero');
    
    if (heroImage && heroSection) {
      window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const rate = scrolled * 0.3;
        
        // Parallax effect for hero image
        heroImage.style.transform = `translateY(${rate * 0.5}px) scale(${1 - rate * 0.0005})`;
        
        // Parallax for floating elements
        document.querySelectorAll('.floating-element').forEach((el, index) => {
          el.style.transform = `translateY(${rate * (0.2 + index * 0.05)}px)`;
        });
      });
    }
  }
  
  setupScrollProgress() {
    // Create progress bar if it doesn't exist
    if (!document.querySelector('.scroll-progress')) {
      const progressBar = document.createElement('div');
      progressBar.className = 'scroll-progress';
      progressBar.innerHTML = '<div class="scroll-progress-bar"></div>';
      document.body.appendChild(progressBar);
      
      // Add styles for progress bar
      this.addProgressBarStyles();
    }
  }
  
  updateScrollProgress(scrollY) {
    const progressBar = document.querySelector('.scroll-progress-bar');
    if (!progressBar) return;
    
    const windowHeight = window.innerHeight;
    const docHeight = document.documentElement.scrollHeight - windowHeight;
    const scrollPercent = (scrollY / docHeight) * 100;
    
    progressBar.style.width = `${scrollPercent}%`;
    
    // Add glow effect when scrolling
    if (scrollPercent > 0) {
      progressBar.classList.add('active');
    } else {
      progressBar.classList.remove('active');
    }
  }
  
  triggerScrollAnimations(scrollY) {
    // Animate sections based on scroll position
    const sections = document.querySelectorAll('.scroll-trigger');
    
    sections.forEach(section => {
      const rect = section.getBoundingClientRect();
      const isVisible = rect.top < window.innerHeight * 0.8 && rect.bottom > 0;
      
      if (isVisible) {
        section.classList.add('in-view');
        
        // Add direction-specific animations
        if (this.scrollingUp) {
          section.classList.add('scroll-up');
          section.classList.remove('scroll-down');
        } else {
          section.classList.add('scroll-down');
          section.classList.remove('scroll-up');
        }
      } else {
        section.classList.remove('in-view');
      }
    });
    
    // Sticky header effect
    this.handleStickyHeader(scrollY);
  }
  
  handleStickyHeader(scrollY) {
    const header = document.querySelector('.header');
    if (!header) return;
    
    if (scrollY > 100) {
      header.classList.add('sticky');
      header.classList.add('scrolled-header');
    } else {
      header.classList.remove('sticky');
      header.classList.remove('scrolled-header');
    }
  }
  
  animateOnLoad() {
    // Animate elements on page load
    setTimeout(() => {
      document.body.classList.add('page-loaded');
      
      // Animate hero section
      const hero = document.querySelector('.hero');
      if (hero) {
        hero.classList.add('loaded');
      }
    }, 100);
  }
  
  addProgressBarStyles() {
    if (document.getElementById('scroll-progress-styles')) return;
    
    const styles = `
      .scroll-progress {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: transparent;
        z-index: 9999;
        pointer-events: none;
      }
      
      .scroll-progress-bar {
        width: 0%;
        height: 100%;
        background: linear-gradient(90deg, var(--accent-color), var(--secondary-color));
        transition: width 0.2s ease;
        box-shadow: 0 0 10px rgba(34, 197, 94, 0.5);
      }
      
      .scroll-progress-bar.active {
        box-shadow: 0 0 15px rgba(34, 197, 94, 0.8);
      }
      
      /* Sticky header styles */
      .header.sticky {
        position: fixed;
        top: 0;
        width: 100%;
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        box-shadow: 0 5px 20px rgba(0, 0, 0, 0.1);
        animation: slideDown 0.3s ease-out;
        z-index: 1000;
      }
      
      .header.scrolled-header {
        padding: 0.5rem 0;
      }
      
      @keyframes slideDown {
        from { transform: translateY(-100%); }
        to { transform: translateY(0); }
      }
      
      /* Scroll animation classes */
      .scroll-animate {
        opacity: 0;
        transform: translateY(30px);
        transition: opacity 0.6s ease, transform 0.6s ease;
      }
      
      .scroll-animate.scroll-visible {
        opacity: 1;
        transform: translateY(0);
      }
      
      .scroll-trigger {
        transition: all 0.8s cubic-bezier(0.4, 0, 0.2, 1);
      }
      
      .scroll-trigger.in-view {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
      
      .scroll-trigger.scroll-up {
        animation: slideUp 0.6s ease-out;
      }
      
      .scroll-trigger.scroll-down {
        animation: slideDown 0.6s ease-out;
      }
      
      @keyframes slideUp {
        from {
          opacity: 0;
          transform: translateY(50px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
      
      .stagger-child {
        opacity: 0;
        transform: translateY(20px);
        transition: all 0.5s ease;
      }
      
      .scroll-visible .stagger-child {
        opacity: 1;
        transform: translateY(0);
      }
      
      /* Body scroll classes */
      body.scrolled {
        padding-top: 70px;
      }
      
      body.scrolling-down .header {
        transform: translateY(0);
      }
      
      body.scrolling-up .header {
        transform: translateY(0);
      }
      
      /* Parallax elements */
      .parallax-element {
        transition: transform 0.3s ease-out;
      }
    `;
    
    const styleSheet = document.createElement('style');
    styleSheet.id = 'scroll-progress-styles';
    styleSheet.textContent = styles;
    document.head.appendChild(styleSheet);
  }
}

