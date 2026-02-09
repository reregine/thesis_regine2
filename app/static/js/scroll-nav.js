// Hide Header on Scroll for Mobile
document.addEventListener('DOMContentLoaded', function() {
    const header = document.querySelector('.header');
    const body = document.body;
    let lastScrollTop = 0;
    let scrollTimeout;
    const mobileBreakpoint = 768;
    const scrollThreshold = 100; // Pixels to scroll before hiding
    
    // Create scroll-to-top button
    const scrollToTopBtn = document.createElement('button');
    scrollToTopBtn.className = 'scroll-to-top';
    scrollToTopBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
    scrollToTopBtn.setAttribute('aria-label', 'Scroll to top');
    document.body.appendChild(scrollToTopBtn);
    
    // Function to handle scroll events
    function handleScroll() {
        if (window.innerWidth > mobileBreakpoint) {
            // Don't hide header on desktop
            header.classList.remove('hidden');
            header.classList.remove('scrolling-up');
            body.classList.remove('header-hidden');
            return;
        }
        
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollingDown = scrollTop > lastScrollTop;
        const atTop = scrollTop === 0;
        
        // Clear any existing timeout
        clearTimeout(scrollTimeout);
        
        if (atTop) {
            // At top of page - show header
            header.classList.remove('hidden');
            header.classList.remove('scrolling-up');
            body.classList.remove('header-hidden');
            scrollToTopBtn.classList.remove('visible');
        } else if (scrollingDown && scrollTop > scrollThreshold) {
            // Scrolling down past threshold - hide header
            header.classList.add('hidden');
            header.classList.remove('scrolling-up');
            body.classList.add('header-hidden');
            
            // Show scroll-to-top button
            if (scrollTop > 500) {
                scrollToTopBtn.classList.add('visible');
            }
        } else {
            // Scrolling up - show header
            header.classList.remove('hidden');
            header.classList.add('scrolling-up');
            body.classList.remove('header-hidden');
            
            // Hide scroll-to-top button when near top
            if (scrollTop < 500) {
                scrollToTopBtn.classList.remove('visible');
            }
        }
        
        lastScrollTop = scrollTop;
        
        // Set timeout to remove scrolling-up class after animation
        if (!scrollingDown && !atTop) {
            scrollTimeout = setTimeout(() => {
                header.classList.remove('scrolling-up');
            }, 300);
        }
    }
    
    // Function to scroll to top
    function scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
    
    // Add event listeners
    window.addEventListener('scroll', handleScroll, { passive: true });
    scrollToTopBtn.addEventListener('click', scrollToTop);
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > mobileBreakpoint) {
            // Reset on desktop
            header.classList.remove('hidden', 'scrolling-up');
            body.classList.remove('header-hidden');
            scrollToTopBtn.classList.remove('visible');
        }
    });
    
    // Initial check
    handleScroll();
    
    // Optional: Add touch/swipe detection for mobile
    let touchStartY = 0;
    let touchEndY = 0;
    
    document.addEventListener('touchstart', function(e) {
        touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });
    
    document.addEventListener('touchend', function(e) {
        touchEndY = e.changedTouches[0].screenY;
        handleSwipe();
    }, { passive: true });
    
    function handleSwipe() {
        const swipeDistance = touchEndY - touchStartY;
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // If swiping down near top, show header immediately
        if (swipeDistance > 50 && scrollTop < 100) {
            header.classList.remove('hidden');
            header.classList.add('scrolling-up');
            body.classList.remove('header-hidden');
            
            setTimeout(() => {
                header.classList.remove('scrolling-up');
            }, 300);
        }
    }
});