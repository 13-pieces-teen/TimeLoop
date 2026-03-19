function() {
    function animateScene() {
        var current = document.querySelector('.nf-current');
        if (!current) return;
        var scene = current.querySelector('.nf-scene');
        if (!scene || scene.dataset.animated) return;
        if (scene.classList.contains('loop-reset')) return;
        scene.dataset.animated = '1';

        var els = [];
        var title = scene.querySelector('.scene-event-title');
        if (title) els.push(title);
        var paras = scene.querySelectorAll('.scene-narration p');
        for (var j = 0; j < paras.length; j++) els.push(paras[j]);
        var dlg = scene.querySelector('.scene-dialogue');
        if (dlg) els.push(dlg);
        var san = scene.querySelector('.scene-san-flavor');
        if (san) els.push(san);
        var ending = scene.querySelector('.scene-ending');
        if (ending) els.push(ending);

        els.forEach(function(el, i) {
            el.style.opacity = '0';
            el.style.transform = 'translateY(8px)';
            setTimeout(function() {
                el.style.transition = 'opacity 0.55s ease-out, transform 0.55s ease-out';
                el.style.opacity = '1';
                el.style.transform = 'translateY(0)';
            }, 100 + i * 400);
        });
    }

    document.addEventListener('click', function(e) {
        var toggle = e.target.closest('.nf-history-toggle');
        if (!toggle) return;
        toggle.classList.toggle('open');
        var hist = toggle.nextElementSibling;
        if (hist && hist.classList.contains('nf-history')) {
            hist.classList.toggle('open');
            if (hist.classList.contains('open')) {
                setTimeout(function() { hist.scrollTop = hist.scrollHeight; }, 120);
            }
        }
    });

    var timer;
    var obs = new MutationObserver(function() {
        clearTimeout(timer);
        timer = setTimeout(animateScene, 60);
    });
    obs.observe(document.body, { childList: true, subtree: true });

    // --- Instant echo: show player input + thinking indicator immediately on click ---
    function showThinking(inputText) {
        var focus = document.querySelector('.narrative-focus');
        if (!focus) return;
        var current = focus.querySelector('.nf-current');
        if (!current) return;
        var echo = '<div class="nf-player-echo" style="opacity:1">&gt; ' + inputText + '</div>';
        var dots = '<div class="nf-thinking"><span></span><span></span><span></span></div>';
        current.innerHTML = echo + dots;
    }

    document.addEventListener('click', function(e) {
        var actBtn = e.target.closest('.act-btn');
        if (actBtn) {
            var ta = document.querySelector('.input-area textarea');
            if (ta && ta.value.trim()) showThinking(ta.value.trim());
            return;
        }
        var choiceBtn = e.target.closest('.choice-btn');
        if (choiceBtn && !choiceBtn.classList.contains('choice-btn--disabled')) {
            var label = choiceBtn.textContent || choiceBtn.innerText || '';
            if (label && label !== '---') showThinking(label.trim().substring(0, 60));
        }
    });
}
