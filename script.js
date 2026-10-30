(() => {
  'use strict';
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const nav = $('#nav');
  const menuButton = $('.menu-toggle');
  const toast = $('#toast');
  const statusNodes = [$('#download-status'), $('#download-status-bottom')].filter(Boolean);
  const year = $('#year');
  if (year) year.textContent = new Date().getFullYear();

  let toastTimer;
  function notify(message) {
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('show'), 4200);
  }

  menuButton?.addEventListener('click', () => {
    const isOpen = nav?.classList.toggle('open') ?? false;
    menuButton.setAttribute('aria-expanded', String(isOpen));
    menuButton.textContent = isOpen ? '×' : '☰';
  });
  $$('#nav a').forEach(link => link.addEventListener('click', () => {
    nav?.classList.remove('open');
    menuButton?.setAttribute('aria-expanded', 'false');
    if (menuButton) menuButton.textContent = '☰';
  }));

  // Scroll progress bar and gentle reveal animations.
  const progress = $('#scroll-progress');
  const updateProgress = () => {
    if (!progress) return;
    const scrollable = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.width = `${scrollable > 0 ? (window.scrollY / scrollable) * 100 : 0}%`;
  };
  window.addEventListener('scroll', updateProgress, { passive: true });
  updateProgress();

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const revealNodes = $$('.reveal');
  if ('IntersectionObserver' in window && !reduceMotion) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -35px 0px' });
    revealNodes.forEach(node => observer.observe(node));
  } else {
    revealNodes.forEach(node => node.classList.add('is-visible'));
  }

  // Global download counter from a public GitHub Release (no fabricated counts).
  const githubRepo = document.querySelector('meta[name="github-repo"]')?.content.trim() || '';
  const countNode = $('#download-count');
  const countNote = $('#download-count-note');

  async function loadGitHubReleaseStats() {
    if (!/^[-\w.]+\/[-\w.]+$/.test(githubRepo) || /owner|repository|twojlogin/i.test(githubRepo)) {
      if (countNote) countNote.textContent = 'Licznik pobrań aplikacji włączy się po ustawieniu owner/repo i dodaniu publicznego GitHub Release.';
      return;
    }
    try {
      let page = 1;
      let total = 0;
      while (page <= 10) {
        const response = await fetch(`https://api.github.com/repos/${githubRepo}/releases?per_page=100&page=${page}`, {
          headers: { 'Accept': 'application/vnd.github+json' }
        });
        if (!response.ok) throw new Error(`GitHub API: HTTP ${response.status}`);
        const releases = await response.json();
        if (!Array.isArray(releases)) throw new Error('Nieprawidłowa odpowiedź GitHub API.');
        for (const release of releases) {
          for (const asset of (Array.isArray(release.assets) ? release.assets : [])) {
            if (asset.name === 'LocalCutAI-App-Windows.zip') total += Number(asset.download_count || 0);
          }
        }
        if (releases.length < 100) break;
        page += 1;
      }
      if (countNode) countNode.textContent = total.toLocaleString('pl-PL');
      if (countNote) countNote.textContent = 'Łączna liczba pobrań pliku LocalCutAI-App-Windows.zip z publicznych wydań GitHub Releases.';
    } catch (error) {
      if (countNote) countNote.textContent = 'Nie udało się odczytać statystyk GitHub Releases. Licznik będzie dostępny po sprawdzeniu połączenia.';
      console.warn('LocalCut AI download count unavailable:', error);
    }
  }
  loadGitHubReleaseStats();

  // Browse the full app source and website source one text file at a time.
  const sourceSelect = $('#source-file');
  const sourceCode = $('#source-code code');
  const sourceStatus = $('#source-status');
  const sourcePath = $('#source-filepath');
  const copySource = $('#copy-source');
  let activeSourceText = '';

  async function loadSourceFile(filePath) {
    if (!sourceCode || !filePath) return;
    sourceCode.textContent = `Wczytywanie ${filePath}…`;
    if (sourcePath) sourcePath.textContent = filePath;
    if (sourceStatus) sourceStatus.textContent = 'Ładowanie pliku…';
    try {
      const response = await fetch(filePath, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      activeSourceText = await response.text();
      sourceCode.textContent = activeSourceText;
      const lines = activeSourceText.split('\n').length;
      if (sourceStatus) sourceStatus.textContent = `Plik wczytany: ${lines.toLocaleString('pl-PL')} linii. Skopiuj go albo pobierz ZIP z pełnym projektem.`;
    } catch (error) {
      activeSourceText = '';
      sourceCode.textContent = 'Nie udało się wczytać pliku źródłowego. Otwórz stronę przez HTTP/HTTPS (np. lokalny serwer) i upewnij się, że katalog source/ został opublikowany.\n\nSzczegóły: ' + error.message;
      if (sourceStatus) sourceStatus.textContent = 'Przeglądarka kodu wymaga dostępu do plików przez HTTP/HTTPS.';
    }
  }

  if (sourceSelect && sourceCode) {
    fetch('source_manifest.json', { cache: 'no-store' })
      .then(response => { if (!response.ok) throw new Error(`HTTP ${response.status}`); return response.json(); })
      .then(data => {
        const files = Array.isArray(data.files) ? data.files : [];
        sourceSelect.replaceChildren();
        files.forEach(file => {
          const option = document.createElement('option');
          option.value = file.path;
          option.textContent = file.label;
          sourceSelect.appendChild(option);
        });
        const preferred = files.find(file => file.path === 'source/LocalCutAI/app/main_window.py') || files[0];
        if (preferred) {
          sourceSelect.value = preferred.path;
          loadSourceFile(preferred.path);
        } else {
          sourceCode.textContent = 'Brak plików w manifeście źródeł.';
        }
      })
      .catch(error => {
        sourceCode.textContent = 'Nie udało się odczytać listy plików. Upewnij się, że na hostingu znajduje się source_manifest.json oraz katalog source/.\n\nSzczegóły: ' + error.message;
        if (sourceStatus) sourceStatus.textContent = 'Brak manifestu lub katalogu source/.';
      });
    sourceSelect.addEventListener('change', () => loadSourceFile(sourceSelect.value));
  }

  copySource?.addEventListener('click', async () => {
    if (!activeSourceText) { notify('Najpierw wczytaj plik źródłowy.'); return; }
    try {
      await navigator.clipboard.writeText(activeSourceText);
      copySource.textContent = 'Skopiowano ✓';
      notify('Zawartość bieżącego pliku została skopiowana.');
      setTimeout(() => { copySource.textContent = 'Kopiuj plik'; }, 1800);
    } catch {
      notify('Schowek jest niedostępny. Zaznacz kod w polu i skopiuj go ręcznie.');
    }
  });

  // Click-to-zoom presentation previews.
  const lightbox = $('#lightbox');
  const lightboxImage = $('#lightbox-image');
  const lightboxClose = $('#lightbox-close');
  let previousFocus = null;
  function closeLightbox() {
    lightbox?.classList.remove('open');
    lightbox?.setAttribute('aria-hidden', 'true');
    if (lightboxImage) lightboxImage.src = '';
    previousFocus?.focus?.();
  }
  $$('[data-lightbox]').forEach(button => button.addEventListener('click', () => {
    if (!lightbox || !lightboxImage) return;
    previousFocus = button;
    lightboxImage.src = button.dataset.lightbox;
    lightboxImage.alt = $('img', button)?.alt || 'Poglądowy interfejs LocalCut AI';
    lightbox.classList.add('open');
    lightbox.setAttribute('aria-hidden', 'false');
    lightboxClose?.focus();
  }));
  lightboxClose?.addEventListener('click', closeLightbox);
  lightbox?.addEventListener('click', event => { if (event.target === lightbox) closeLightbox(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && lightbox?.classList.contains('open')) closeLightbox(); });
})();
