/* Arlington Data Explorer — Shared Navigation */
(function () {
    var page = document.body.dataset.page || '';

    var links = [
        { label: 'Home',           href: 'index.html',      key: 'home' },
        { label: 'Revenue',        href: 'revenue.html',    key: 'revenue' },
        { label: 'Spending',       href: 'spending.html',   key: 'spending' },
        { label: 'Schools',        href: 'schools.html',    key: 'schools' },
        { label: 'Property',       href: 'gis.html',        key: 'property' },
        { label: 'Override Cycle', href: 'override.html',   key: 'override' }
    ];

    var dropdownLinks = [
        { label: 'Population', href: 'population.html', key: 'population' },
        { label: 'Crime',      href: 'crime.html',      key: 'crime' }
    ];

    var dropdownKeys = dropdownLinks.map(function (d) { return d.key; });
    var moreActive = dropdownKeys.indexOf(page) !== -1;

    function makeLink(item) {
        var active = item.key === page ? ' class="nav-active"' : '';
        return '<a href="' + item.href + '"' + active + '>' + item.label + '</a>';
    }

    var mainItems = links.map(function (item) {
        return '<li>' + makeLink(item) + '</li>';
    }).join('');

    var dropItems = dropdownLinks.map(function (item) {
        return makeLink(item);
    }).join('');

    var moreClass = moreActive ? ' class="nav-active"' : '';

    var html =
        '<a href="index.html" class="nav-brand">Arlington Data Explorer</a>' +
        '<ul class="nav-links">' +
            mainItems +
            '<li class="nav-dropdown">' +
                '<a href="#"' + moreClass + '>More &#9662;</a>' +
                '<div class="nav-dropdown-menu">' + dropItems + '</div>' +
            '</li>' +
        '</ul>';

    var nav = document.getElementById('main-nav');
    if (nav) {
        nav.innerHTML = html;
    }
})();
