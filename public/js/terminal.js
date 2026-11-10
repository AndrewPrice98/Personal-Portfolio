// Turns the static terminal block into a working prompt.
// Without JS the block still shows the whoami result and the chips are plain links.
(function () {
    'use strict';
    var root = document.querySelector('.terminal');
    if (!root) return;

    var body = root.querySelector('.term-body');
    var staticLine = root.querySelector('.term-line');
    var staticOut = root.querySelector('.term-output');
    var history = root.querySelector('.term-history');
    var live = root.querySelector('.term-live');
    var chips = root.querySelectorAll('.term-chips a[data-cmd]');
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var PROMPT = 'andrew@portfolio:~$';

    var EMAILS = ['PriceDev505@outlook.com', 'Aprice226@outlook.com'];
    var LINKEDIN = 'https://www.linkedin.com/in/andrew-price98';
    var GITHUB = 'https://github.com/AndrewPrice98';

    var PROJECTS = [
        ['netguard', 'network intrusion detection and SOC console for small networks (Python)'],
        ['logingestllm', 'local AI agent that summarizes logs and flags security events'],
        ['ccna-study', 'CCNA 200-301 study platform with a Cisco IOS simulator'],
        ['cysa-study', 'CySA+ (CS0-004) trainer with a pure-JavaScript Linux shell'],
        ['job-tracker', 'job-search organizer that reads your inbox'],
        ['flight-tracker', 'live map of military aircraft from ADS-B data'],
        ['tempered', 'iPhone calorie and training tracker with AI meal logging'],
        ['sudo-snake', 'Snake rebuilt as a retro terminal arcade game for iPhone']
    ];
    var SLUGS = PROJECTS.map(function (p) { return p[0]; });

    function pad(s, n) { while (s.length < n) s += ' '; return s; }
    function link(text, href) { return { t: text, href: href }; }
    function contactLines() {
        return [
            [link(EMAILS[0], 'mailto:' + EMAILS[0])],
            [link(EMAILS[1], 'mailto:' + EMAILS[1])],
            [link('linkedin.com/in/andrew-price98', LINKEDIN)],
            [link('github.com/AndrewPrice98', GITHUB)]
        ];
    }

    // Each command returns an array of lines; a line is a string or an array of
    // strings and {t, href} links.
    var COMMANDS = {
        help: function () {
            return [
                'help              list commands',
                'whoami            who I am',
                'projects          the case files',
                'open <slug>       open a case file',
                'resume            experience and education',
                'contact           email, LinkedIn, GitHub',
                'mission           what I am looking for',
                'certs             clearance and certifications',
                'clear             clear the screen'
            ];
        },
        whoami: function () {
            return ['Andrew T. Price II', 'security analyst · full-stack developer · avionics technician'];
        },
        projects: function () {
            var lines = PROJECTS.map(function (p) {
                return [link(p[0], 'projects/' + p[0] + '.html'), pad('', 15 - p[0].length) + p[1]];
            });
            lines.push('type: open <slug>');
            return lines;
        },
        resume: function () {
            return [
                'Heavy Integrated Avionics Technician, Kirtland AFB (2023-present)',
                '  led a 12-member team, 98% mission-capable rate',
                'Instrument and Flight Control System Technician, Hurlburt Field (2021-2023)',
                'Full Stack Development Apprentice, Creating Coding Careers (Aug 2026-present)',
                'BAS Cybersecurity, American Public University System (2020)',
                'AAS Aviation Maintenance, CCAF (2020)',
                [link('Full resume', 'resume.html')]
            ];
        },
        contact: contactLines,
        mission: function () {
            return ['Open to work, aiming at SOC analyst and security engineering roles.'];
        },
        certs: function () {
            return [
                'Active DoD Secret clearance',
                'CompTIA Security+ (DoD 8570 IAT Level II / 8140 baseline)',
                '5+ years USAF avionics (AC-130 / C-130)',
                [link('More on the resume', 'resume.html#highlights')]
            ];
        }
    };

    function plain(lines) {
        return lines.map(function (l) {
            if (typeof l === 'string') return l;
            return l.map(function (seg) { return typeof seg === 'string' ? seg : seg.t; }).join('');
        }).join('\n');
    }

    function renderLines(lines) {
        var pre = document.createElement('pre');
        pre.className = 'term-output';
        lines.forEach(function (l, i) {
            if (i) pre.appendChild(document.createTextNode('\n'));
            if (typeof l === 'string') { pre.appendChild(document.createTextNode(l)); return; }
            l.forEach(function (seg) {
                if (typeof seg === 'string') { pre.appendChild(document.createTextNode(seg)); return; }
                var a = document.createElement('a');
                a.href = seg.href;
                a.textContent = seg.t;
                if (/^https?:/.test(seg.href)) { a.target = '_blank'; a.rel = 'noopener'; }
                pre.appendChild(a);
            });
        });
        return pre;
    }

    // The complete result goes to the live region once.
    function announce(text) {
        live.textContent = '';
        live.textContent = text;
    }

    function echo(cmd) {
        var p = document.createElement('p');
        p.className = 'term-line';
        p.setAttribute('aria-hidden', 'true');
        var pr = document.createElement('span');
        pr.className = 'term-prompt';
        pr.textContent = PROMPT;
        var c = document.createElement('span');
        c.className = 'term-cmd';
        c.textContent = ' ' + cmd;
        p.appendChild(pr);
        p.appendChild(c);
        history.appendChild(p);
    }

    function hasLinks(lines) {
        return lines.some(function (l) { return typeof l !== 'string' && l.some(function (seg) { return typeof seg !== 'string'; }); });
    }

    // The visible output is real, reachable text (links included), so it is never
    // aria-hidden. The live region carries the complete text when there are no links;
    // for results with links it announces a short summary so each link is reached once, in place.
    function output(lines) {
        history.appendChild(renderLines(lines));
        announce(hasLinks(lines) ? 'Output printed below the prompt, with links.' : plain(lines));
    }

    var past = [];
    var pos = 0;
    var draft = '';
    var input;

    function run(raw) {
        var line = raw.trim().replace(/\s+/g, ' ');
        if (!line) return;
        echo(line);
        past.push(line);
        pos = past.length;
        var lower = line.toLowerCase();
        var parts = lower.split(' ');
        var name = parts[0];

        if (lower === 'clear') {
            history.textContent = '';
            staticLine.hidden = true;
            staticOut.hidden = true;
            announce('');
            return;
        }
        if (lower === 'sudo hire andrew') {
            output(['Great choice. Let’s talk.'].concat(contactLines()));
            return;
        }
        if (name === 'open') {
            var slug = parts[1];
            if (!slug) { output(['usage: open <slug> — try projects']); return; }
            if (SLUGS.indexOf(slug) === -1) { output(['no such project: ' + slug + ' — try projects']); return; }
            output(['opening projects/' + slug + '.html']);
            window.location.href = 'projects/' + slug + '.html';
            return;
        }
        if (parts.length === 1 && Object.prototype.hasOwnProperty.call(COMMANDS, name)) {
            output(COMMANDS[name]());
            return;
        }
        output(['command not found: ' + line + ' — try help']);
    }

    // Completes command and slug names. Returns false when there is nothing to complete.
    function complete() {
        var v = input.value.replace(/^\s+/, '').toLowerCase();
        if (!v) return false;
        var head = '';
        var prefix = v;
        var pool;
        if (/^open\s/.test(v)) {
            head = 'open ';
            prefix = v.replace(/^open\s+/, '');
            pool = SLUGS;
        } else {
            pool = Object.keys(COMMANDS).concat(['open', 'sudo hire andrew']);
        }
        var hits = pool.filter(function (c) { return c.indexOf(prefix) === 0; });
        if (!hits.length) return false;
        var common = hits[0];
        hits.forEach(function (h) { while (h.indexOf(common) !== 0) common = common.slice(0, -1); });
        if (hits.length === 1 && common === 'open') common = 'open ';
        if (head + common === input.value.replace(/^\s+/, '') && hits.length === 1) return false;
        input.value = head + common;
        if (hits.length > 1 && common === prefix) {
            echo(head + prefix);
            output([hits.join('  ')]);
        }
        return true;
    }

    function buildPrompt() {
        var form = document.createElement('form');
        form.className = 'term-line term-input-line';
        form.setAttribute('autocomplete', 'off');
        var pr = document.createElement('span');
        pr.className = 'term-prompt';
        pr.setAttribute('aria-hidden', 'true');
        pr.textContent = PROMPT;
        input = document.createElement('input');
        input.type = 'text';
        input.className = 'term-input';
        input.setAttribute('aria-label', 'Terminal command. Try help.');
        input.autocomplete = 'off';
        input.spellcheck = false;
        input.setAttribute('autocapitalize', 'off');
        form.appendChild(pr);
        form.appendChild(input);
        body.insertBefore(form, live);

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var v = input.value;
            input.value = '';
            run(v);
        });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (pos > 0) { if (pos === past.length) draft = input.value; input.value = past[--pos]; }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (pos < past.length - 1) input.value = past[++pos];
                else if (pos < past.length) { pos = past.length; input.value = draft; }
            } else if (e.key === 'Tab' && !e.shiftKey && input.value.trim()) {
                if (complete()) e.preventDefault();
            }
        });
        root.addEventListener('click', function (e) {
            if (e.target.closest('a, button, input, .term-chips')) return;
            if (window.getSelection && String(window.getSelection())) return;
            // On touch screens only the prompt line focuses the input, so a stray tap does not raise the keyboard.
            if (window.matchMedia('(pointer: coarse)').matches && !e.target.closest('.term-input-line')) return;
            input.focus();
        });
    }

    function init() {
        buildPrompt();
        // The static result stays readable in place; only the echoed prompt line is decorative.
        staticLine.setAttribute('aria-hidden', 'true');

        chips.forEach(function (chip) {
            chip.addEventListener('click', function (e) {
                if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button) return;
                e.preventDefault();
                run(chip.getAttribute('data-cmd'));
            });
        });

        if (reduceMotion) return;
        // Type "whoami" once, then reveal the result.
        var cmdEl = staticLine.querySelector('.term-cmd');
        var word = cmdEl.textContent;
        cmdEl.textContent = '';
        staticOut.style.visibility = 'hidden';
        var i = 0;
        (function tick() {
            cmdEl.textContent = word.slice(0, ++i);
            if (i < word.length) { setTimeout(tick, 70 + Math.random() * 60); return; }
            setTimeout(function () {
                staticOut.style.visibility = '';
            }, 250);
        })();
    }

    init();
})();
