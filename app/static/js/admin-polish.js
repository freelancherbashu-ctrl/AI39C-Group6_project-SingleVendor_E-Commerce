/* MeroPasal Admin — Polish JS */
(function () {
    var targets = document.querySelectorAll('.stat-card, .card');
    targets.forEach(function (el) { el.classList.add('mp-reveal'); });

    if ('IntersectionObserver' in window) {
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('mp-in');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' });
        targets.forEach(function (el) { io.observe(el); });
    } else {
        targets.forEach(function (el) { el.classList.add('mp-in'); });
    }

    var header = document.querySelector('.topbar');
    if (header) {
        var onScroll = function () {
            header.classList.toggle('mp-scrolled', window.scrollY > 4);
        };
        document.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }
})();
