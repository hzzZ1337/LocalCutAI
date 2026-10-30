(() => {
  'use strict';
  const repo = document.querySelector('meta[name="github-repo"]')?.content.trim() || '';
  const entries = [
    { key: 'app', name: 'LocalCutAI-App-Windows.zip', path: 'downloads/LocalCutAI-App-Windows.zip', link: document.getElementById('app-download'), status: document.getElementById('app-status') },
    { key: 'ffmpeg', name: 'LocalCutAI-FFmpeg-Windows.zip', path: 'downloads/LocalCutAI-FFmpeg-Windows.zip', link: document.getElementById('ffmpeg-download'), status: document.getElementById('ffmpeg-status') }
  ];
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();

  function setAvailable(entry, url, external = false) {
    entry.link.href = url;
    entry.link.removeAttribute('aria-disabled');
    entry.link.classList.remove('download-unavailable');
    if (external) entry.link.removeAttribute('download');
    else entry.link.setAttribute('download', entry.name);
    entry.status.textContent = 'Plik gotowy do pobrania.';
    entry.status.style.color = '#6ee7b7';
  }
  function setMissing(entry) {
    entry.link.href = '#';
    entry.link.setAttribute('aria-disabled', 'true');
    entry.link.classList.add('download-unavailable');
    entry.link.removeAttribute('download');
    entry.status.textContent = 'Plik nie został jeszcze dodany do folderu downloads ani do GitHub Release.';
  }
  async function checkLocal(entry) {
    try {
      const response = await fetch(entry.path, { method: 'HEAD', cache: 'no-store' });
      if (response.ok) { setAvailable(entry, entry.path); return true; }
    } catch { /* local file:// preview is not supported; use HTTP/HTTPS */ }
    setMissing(entry);
    return false;
  }
  async function load() {
    const validRepo = /^[-\w.]+\/[-\w.]+$/.test(repo) && !/owner|repository|twojlogin/i.test(repo);
    if (validRepo) {
      try {
        const response = await fetch(`https://api.github.com/repos/${repo}/releases?per_page=100`, { headers: { 'Accept': 'application/vnd.github+json' } });
        if (!response.ok) throw new Error(`GitHub API: HTTP ${response.status}`);
        const releases = await response.json();
        const latest = new Map();
        for (const release of releases) {
          for (const asset of (Array.isArray(release.assets) ? release.assets : [])) {
            if (entries.some(entry => entry.name === asset.name) && !latest.has(asset.name)) latest.set(asset.name, asset);
          }
        }
        for (const entry of entries) {
          const asset = latest.get(entry.name);
          if (asset?.browser_download_url) setAvailable(entry, asset.browser_download_url, true);
          else await checkLocal(entry);
        }
        return;
      } catch (error) {
        console.warn('Could not load LocalCut AI GitHub release assets:', error);
      }
    }
    for (const entry of entries) await checkLocal(entry);
  }
  entries.forEach(entry => entry.link.addEventListener('click', event => {
    if (entry.link.getAttribute('aria-disabled') === 'true') {
      event.preventDefault();
      entry.status.textContent = 'Autor nie dodał jeszcze tego archiwum. Sprawdź później.';
    }
  }));
  load();
})();
