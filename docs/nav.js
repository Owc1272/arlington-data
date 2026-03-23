/* Arlington Data Explorer — Shared Navigation */
(function () {
    var page = document.body.dataset.page || '';

    var links = [
        { label: 'Home',           href: 'index.html',      key: 'home' },
        { label: 'Override Cycle', href: 'override.html',   key: 'override' },
        { label: 'Spending',       href: 'spending.html',   key: 'spending' },
        { label: 'Revenue',        href: 'revenue.html',    key: 'revenue' },
        { label: 'Schools',        href: 'schools.html',    key: 'schools' },
        { label: 'Forecasts',      href: 'forecasts.html',  key: 'forecasts' },
        { label: 'Statewide',      href: 'statewide.html',  key: 'statewide' }
    ];

    function makeLink(item) {
        var active = item.key === page ? ' class="nav-active"' : '';
        return '<a href="' + item.href + '"' + active + '>' + item.label + '</a>';
    }

    var mainItems = links.map(function (item) {
        return '<li>' + makeLink(item) + '</li>';
    }).join('');

    var html =
        '<a href="index.html" class="nav-brand">Arlington Data Explorer</a>' +
        '<ul class="nav-links">' + mainItems + '</ul>';

    var nav = document.getElementById('main-nav');
    if (nav) {
        nav.innerHTML = html;
    }
})();
