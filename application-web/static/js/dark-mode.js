/* ============================================================
   DARK MODE TOGGLE — persistance + détection système
   ============================================================ */
(function () {
    const STORAGE_KEY = 'traffic-theme';

    // 1. Appliquer le thème AVANT le rendu (évite le flash)
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const btn = document.getElementById('darkModeToggle');
        if (btn) {
            btn.innerHTML = theme === 'dark'
                ? '<i class="fas fa-sun"></i>'
                : '<i class="fas fa-moon"></i>';
            btn.title = theme === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre';
        }
    }

    // 2. Déterminer le thème initial
    function getInitialTheme() {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) return saved;
        // Respecte la préférence système
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    // 3. Initialiser dès que possible
    applyTheme(getInitialTheme());

    // 4. Brancher le bouton une fois le DOM prêt
    document.addEventListener('DOMContentLoaded', () => {
        const btn = document.getElementById('darkModeToggle');
        if (btn) {
            btn.addEventListener('click', () => {
                const current = document.documentElement.getAttribute('data-theme') || 'light';
                const next = current === 'dark' ? 'light' : 'dark';
                applyTheme(next);
                localStorage.setItem(STORAGE_KEY, next);
            });
        }
        // Synchroniser avec les changements système (si pas de préférence sauvegardée)
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            if (!localStorage.getItem(STORAGE_KEY)) {
                applyTheme(e.matches ? 'dark' : 'light');
            }
        });
    });
})();