/* Arlington Data Explorer — Shared Navigation + Mobile Helpers */
(function () {
    var page = document.body.dataset.page || '';

    var links = [
        { label: 'Home',           href: 'index.html',      key: 'home',      icon: '&#x1F504;', title: 'The Override Cycle',   desc: 'The sawtooth pattern: override passes, fund builds, costs outpace revenue, fund drains.' },
        { label: 'Override Cycle', href: 'override.html',   key: 'override',  icon: '&#x1F4CA;', title: 'Where the Money Goes', desc: 'School budget doubled in 20 years. Health insurance, pensions, and special education grow 5\u201312% annually.' },
        { label: 'Spending',       href: 'spending.html',   key: 'spending',  icon: '&#x1F4C9;', title: 'Why Revenue Can\u2019t Keep Up', desc: 'Last among 13 peers in new growth. 95% residential tax base. State aid lags cost growth.' },
        { label: 'Revenue',        href: 'revenue.html',    key: 'revenue',   icon: '&#x1F3EB;', title: 'Arlington Schools',    desc: 'Below-average spending, above-average outcomes. 25+ charts comparing Arlington to 12 peer districts.' },
        { label: 'Schools',        href: 'schools.html',    key: 'schools',   icon: '&#x1F4D0;', title: 'Historical Forecasts', desc: 'When estimates miss by 100%+. AHS from $100M to $291M. DPW Yard from $20M to $47M.' },
        { label: 'Forecasts',      href: 'forecasts.html',  key: 'forecasts', icon: '&#x1F3DB;', title: 'Statewide Forces',    desc: 'MSBA reimbursement cuts, GIC rate spikes, pension mandates \u2014 forces beyond Arlington\u2019s control.' },
        { label: 'Statewide',      href: 'statewide.html',  key: 'statewide', icon: '', title: '', desc: '' }
    ];

    /* === Build nav === */
    function makeLink(item) {
        var active = item.key === page ? ' class="nav-active"' : '';
        return '<a href="' + item.href + '"' + active + '>' + item.label + '</a>';
    }

    var mainItems = links.map(function (item) {
        return '<li>' + makeLink(item) + '</li>';
    }).join('');

    var html =
        '<a href="index.html" class="nav-brand">Arlington Data Explorer</a>' +
        '<button class="nav-toggle" aria-label="Menu">&#9776;</button>' +
        '<ul class="nav-links">' + mainItems + '</ul>';

    var nav = document.getElementById('main-nav');
    if (nav) {
        nav.innerHTML = html;

        /* Hamburger toggle */
        var toggle = nav.querySelector('.nav-toggle');
        var ul = nav.querySelector('.nav-links');
        toggle.addEventListener('click', function () {
            ul.classList.toggle('nav-open');
            toggle.classList.toggle('nav-open');
            toggle.innerHTML = ul.classList.contains('nav-open') ? '&#10005;' : '&#9776;';
        });

        /* Close menu when a link is tapped */
        ul.addEventListener('click', function (e) {
            if (e.target.tagName === 'A') {
                ul.classList.remove('nav-open');
                toggle.classList.remove('nav-open');
                toggle.innerHTML = '&#9776;';
            }
        });
    }

    /* === "Next page" card at bottom of inner pages === */
    function injectNextPage() {
        var currentIdx = -1;
        for (var i = 0; i < links.length; i++) {
            if (links[i].key === page) { currentIdx = i; break; }
        }

        if (currentIdx >= 0 && currentIdx < links.length - 1) {
            var next = links[currentIdx];
            var nextPage = links[currentIdx + 1];
            if (next.title && next.desc) {
                var footer = document.querySelector('footer');
                if (footer && !document.querySelector('.next-page-wrap')) {
                    var card = document.createElement('div');
                    card.className = 'next-page-wrap';
                    card.innerHTML =
                        '<a href="' + nextPage.href + '" class="section-card next-page-card">' +
                            '<div class="section-icon">' + next.icon + '</div>' +
                            '<h2>' + next.title + '</h2>' +
                            '<p>' + next.desc + '</p>' +
                            '<span class="section-link">Continue Reading &#x2192;</span>' +
                        '</a>';
                    footer.parentNode.insertBefore(card, footer);
                }
            }
        }
    }
    /* Try now (if footer already parsed), and also on DOMContentLoaded */
    injectNextPage();
    document.addEventListener('DOMContentLoaded', injectNextPage);

    /* === Chart.js tooltip dismiss on mobile === */
    if ('ontouchstart' in window) {
        /* Tap outside any canvas → dismiss all tooltips */
        document.addEventListener('touchstart', function (e) {
            if (e.target.tagName !== 'CANVAS' && typeof Chart !== 'undefined') {
                Chart.helpers.each(Chart.instances, function (chart) {
                    if (chart.tooltip) {
                        chart.tooltip.setActiveElements([], { x: 0, y: 0 });
                        chart.setActiveElements([]);
                        chart.update('none');
                    }
                });
            }
        });

        /* Double-tap a canvas → dismiss its tooltip */
        var lastTap = 0;
        document.addEventListener('touchend', function (e) {
            if (e.target.tagName !== 'CANVAS' || typeof Chart === 'undefined') return;
            var now = Date.now();
            if (now - lastTap < 400) {
                // Double-tap detected — clear tooltip on this chart
                var chart = Chart.getChart(e.target);
                if (chart && chart.tooltip) {
                    chart.tooltip.setActiveElements([], { x: 0, y: 0 });
                    chart.setActiveElements([]);
                    chart.update('none');
                }
                e.preventDefault();
            }
            lastTap = now;
        });
    }
})();
