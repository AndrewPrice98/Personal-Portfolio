// Filter buttons for the project queue. Without JS the buttons stay hidden and every row shows.
(function () {
    'use strict';
    var bar = document.querySelector('.queue-filters');
    var rows = document.querySelectorAll('.alert-queue .alert-row');
    if (!bar || !rows.length) return;
    var buttons = bar.querySelectorAll('button[data-filter]');
    function apply(kind) {
        for (var i = 0; i < rows.length; i++) {
            rows[i].hidden = !(kind === 'all' || rows[i].getAttribute('data-category') === kind);
        }
        for (var j = 0; j < buttons.length; j++) {
            buttons[j].setAttribute('aria-pressed', buttons[j].getAttribute('data-filter') === kind ? 'true' : 'false');
        }
    }
    for (var k = 0; k < buttons.length; k++) {
        buttons[k].addEventListener('click', function (e) { apply(e.currentTarget.getAttribute('data-filter')); });
    }
    bar.hidden = false;
})();
