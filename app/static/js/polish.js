/* MeroPasal — Polish JS
   Adds scroll-reveal to product/stat cards and a scrolled-header shadow.
   No dependencies, safe no-ops if elements aren't present. */
(function () {
    // Auto-tag common repeating elements for scroll-reveal
    var targets = document.querySelectorAll(
        '.product-card, .stat-card, .card, .order-card, .category-card'
    );
    targets.forEach(function (el) { el.classList.add('mp-reveal'); });

    if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('mp-in');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' });

        targets.forEach(function (el) { io.observe(el); });
    } else {
        // Fallback: just show everything
        targets.forEach(function (el) { el.classList.add('mp-in'); });
    }

    // Header shadow on scroll
    var header = document.querySelector('.topbar');
    if (header) {
        var onScroll = function () {
            header.classList.toggle('mp-scrolled', window.scrollY > 4);
        };
        document.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }
})();
