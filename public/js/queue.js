// Filter buttons for the project queue. Without JS the buttons stay hidden and every row shows.
(function () {
    'use strict';
    var bar = document.querySelector('.queue-filters');
    var rows = document.querySelectorAll('.alert-queue .alert-row');
    var status = document.getElementById('queue-status');
    if (!bar || !rows.length) return;
    var buttons = bar.querySelectorAll('button[data-filter]');
    function apply(kind) {
        var shown = 0;
        for (var i = 0; i < rows.length; i++) {
            var show = kind === 'all' || rows[i].getAttribute('data-category') === kind;
            rows[i].hidden = !show;
            if (show) shown++;
        }
        for (var j = 0; j < buttons.length; j++) {
            buttons[j].setAttribute('aria-pressed', buttons[j].getAttribute('data-filter') === kind ? 'true' : 'false');
        }
        if (status) status.textContent = 'Showing ' + shown + (shown === 1 ? ' project' : ' projects');
    }
    for (var k = 0; k < buttons.length; k++) {
        buttons[k].addEventListener('click', function (e) { apply(e.currentTarget.getAttribute('data-filter')); });
    }
    bar.hidden = false;
})();
