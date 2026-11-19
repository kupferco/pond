// Shared 3D model viewer for the Pond site, driven by docs/models/models.json.
// Put <div data-models data-page="home"></div> on a page (optionally data-section="Cart" or data-id="cart-base-v2");
// every matching manifest entry is rendered as a viewer. Add a model = add one entry to models.json.
// Style: white background, soft ground shadow, orbit controls (same as drawings/viewer.html).
// Each viewer loads only when it scrolls near the screen; the viewer library itself loads once, on first need.
(function () {
  var me = document.currentScript;
  var root = (me.getAttribute('data-root') || me.src.replace(/assets\/pond-models\.js.*$/, ''));
  var LIB = 'https://cdn.jsdelivr.net/npm/@google/model-viewer@4.0.0/dist/model-viewer.min.js';
  var libP = null;
  function loadLib() {
    if (!libP) libP = customElements.get('model-viewer') ? Promise.resolve() : new Promise(function (ok, bad) {
      var s = document.createElement('script'); s.type = 'module'; s.src = LIB; s.onload = ok; s.onerror = bad; document.head.appendChild(s);
    });
    return libP;
  }
  var css = document.createElement('style');
  css.textContent =
    '.pm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(480px,100%),1fr));gap:16px;margin:0 0 28px}' +
    '.pm{margin:0;background:#fff;border:1px solid rgba(0,0,0,.12);border-radius:14px;overflow:hidden}' +
    '.pm-stage{position:relative;aspect-ratio:4/3;background:#fff;display:flex;align-items:center;justify-content:center}' +
    '.pm-stage img{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#fff}' +
    '.pm-stage model-viewer{position:absolute;inset:0;width:100%;height:100%;background:#fff;--poster-color:#fff}' +
    '.pm-note{position:relative;font:600 13px system-ui,sans-serif;color:#555;background:rgba(255,255,255,.85);padding:6px 12px;border-radius:999px}' +
    '.pm figcaption{padding:12px 16px 14px;font:14px/1.45 system-ui,sans-serif;color:#1d1f24}' +
    '.pm figcaption strong{display:block;font-size:15px}' +
    '.pm-h{margin:8px 0 12px}' +
    '@media(min-width:900px){.pm-stage{aspect-ratio:auto;height:min(62vh,560px);min-height:400px}}' +
    '.pm-fs{position:absolute;top:10px;right:10px;z-index:3;display:flex;align-items:center;gap:6px;min-height:40px;padding:0 14px;border:1px solid rgba(0,0,0,.18);border-radius:999px;background:rgba(255,255,255,.92);color:#1d1f24;font:600 14px system-ui,sans-serif;cursor:pointer;-webkit-tap-highlight-color:transparent}' +
    '.pm-fs:hover{background:#fff}' +
    '.pm-stage.pm-full{position:fixed;inset:0;z-index:2147483000;width:100vw;height:100vh;height:100dvh;min-height:0;aspect-ratio:auto;background:#fff}' +
    '.pm-stage.pm-full .pm-fs{top:max(12px,env(safe-area-inset-top));right:max(12px,env(safe-area-inset-right));min-height:44px;padding:0 18px;background:#1d1f24;color:#fff;border-color:#1d1f24}' +
    '.pm-title{display:none;position:absolute;top:max(12px,env(safe-area-inset-top));left:max(14px,env(safe-area-inset-left));z-index:3;max-width:60%;font:600 15px system-ui,sans-serif;color:#1d1f24;background:rgba(255,255,255,.85);padding:8px 12px;border-radius:999px}' +
    '.pm-stage.pm-full .pm-title{display:block}' +
    'html.pm-lock,html.pm-lock body{overflow:hidden!important}';
  document.head.appendChild(css);

  // One model at a time: three 11 MB files downloading and decoding together is more than a phone can take.
  var qBusy = false, qList = [];
  function queue(job) { qList.push(job); next(); }
  function next() { if (qBusy || !qList.length) return; qBusy = true; qList.shift()(function () { qBusy = false; next(); }); }

  function make(m) {
    var fig = document.createElement('figure'); fig.className = 'pm'; fig.id = 'model-' + m.id;
    var stage = document.createElement('div'); stage.className = 'pm-stage';
    if (m.poster) { var p = document.createElement('img'); p.src = root + m.poster; p.alt = ''; p.loading = 'lazy'; stage.appendChild(p); }
    var note = document.createElement('span'); note.className = 'pm-note'; note.textContent = 'Loading 3D…'; stage.appendChild(note);
    var ttl = document.createElement('span'); ttl.className = 'pm-title'; ttl.textContent = m.title; stage.appendChild(ttl);
    var fs = document.createElement('button'); fs.type = 'button'; fs.className = 'pm-fs';
    fs.setAttribute('aria-label', 'Full screen: ' + m.title); fs.textContent = '⛶ Full screen'; stage.appendChild(fs);
    var full = false;
    function setFull(on) {
      if (on === full) return; full = on;
      stage.classList.toggle('pm-full', on); document.documentElement.classList.toggle('pm-lock', on);
      fs.textContent = on ? '✕ Close' : '⛶ Full screen';
      fs.setAttribute('aria-label', (on ? 'Exit full screen: ' : 'Full screen: ') + m.title);
      var mv = stage.querySelector('model-viewer');
      if (mv) mv.setAttribute('touch-action', on ? 'none' : 'pan-y');
      if (on) { fs.focus({ preventScroll: true }); document.addEventListener('keydown', onKey); }
      else document.removeEventListener('keydown', onKey);
    }
    function onKey(e) { if (e.key === 'Escape') exit(); }
    function exit() {
      if (document.fullscreenElement === stage || document.webkitFullscreenElement === stage) {
        (document.exitFullscreen || document.webkitExitFullscreen).call(document);
      }
      setFull(false);
    }
    fs.addEventListener('click', function () {
      if (full) { exit(); return; }
      setFull(true); // the overlay always applies, so iOS Safari (no element fullscreen) works too
      var req = stage.requestFullscreen || stage.webkitRequestFullscreen;
      if (req) { try { var r = req.call(stage); if (r && r.catch) r.catch(function () {}); } catch (e) {} }
    });
    function onFsChange() { var el = document.fullscreenElement || document.webkitFullscreenElement; if (full && !el && stage.dataset.pmReal) { delete stage.dataset.pmReal; setFull(false); } else if (el === stage) stage.dataset.pmReal = '1'; }
    document.addEventListener('fullscreenchange', onFsChange); document.addEventListener('webkitfullscreenchange', onFsChange);
    var cap = document.createElement('figcaption');
    var t = document.createElement('strong'); t.textContent = m.title; cap.appendChild(t);
    if (m.caption) cap.appendChild(document.createTextNode(m.caption));
    fig.append(stage, cap);
    var started = false, retry = null;
    function fail(msg) {
      var old = stage.querySelector('model-viewer'); if (old) old.remove();
      note.textContent = msg + ' '; note.style.display = '';
      if (!retry) { retry = document.createElement('button'); retry.type = 'button'; retry.textContent = 'Try again';
        retry.style.cssText = 'margin-left:6px;border:0;border-radius:999px;background:#1d1f24;color:#fff;font:600 13px system-ui,sans-serif;padding:6px 12px;min-height:32px;cursor:pointer';
        retry.addEventListener('click', function () { retry.remove(); load(); }); }
      note.appendChild(retry);
    }
    function load() {
      note.style.display = ''; note.textContent = 'Loading 3D…';
      queue(function (done) {
        var finished = false, timer;
        function end() { if (finished) return false; finished = true; clearTimeout(timer); done(); return true; }
        loadLib().then(function () {
          var mv = document.createElement('model-viewer');
          mv.setAttribute('src', root + m.glb); mv.setAttribute('alt', m.title);
          mv.setAttribute('camera-controls', ''); mv.setAttribute('auto-rotate', '');
          mv.setAttribute('environment-image', 'neutral'); mv.setAttribute('shadow-intensity', '1.2');
          mv.setAttribute('shadow-softness', '1'); mv.setAttribute('exposure', '1.1');
          mv.setAttribute('touch-action', full ? 'none' : 'pan-y'); mv.setAttribute('interaction-prompt', 'none');
          var c = m.camera || {};
          if (c.orbit) mv.setAttribute('camera-orbit', c.orbit);
          if (c.target) mv.setAttribute('camera-target', c.target);
          if (c.fov) mv.setAttribute('field-of-view', c.fov);
          mv.addEventListener('progress', function (e) {
            var t = e.detail && e.detail.totalProgress;
            if (t > 0 && t < 1) { clearTimeout(timer); timer = setTimeout(function () { if (end()) fail('3D model is taking too long.'); }, 45000); note.textContent = 'Loading 3D… ' + Math.round(t * 100) + '%'; }
          });
          mv.addEventListener('load', function () { if (!end()) return; note.style.display = 'none'; var i = stage.querySelector('img'); if (i) i.remove(); });
          mv.addEventListener('error', function () { if (end()) fail('3D model could not load.'); });
          timer = setTimeout(function () { if (end()) fail('3D model is taking too long.'); }, 60000);
          stage.appendChild(mv);
        }).catch(function () { if (end()) fail('3D viewer could not load.'); });
      });
    }
    function start() { if (started) return; started = true; load(); }
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (es) { if (es.some(function (e) { return e.isIntersecting; })) { io.disconnect(); start(); } }, { rootMargin: '200px' });
      io.observe(fig);
    } else start();
    return fig;
  }

  function mount(host, models) {
    var page = host.getAttribute('data-page'), sec = host.getAttribute('data-section'), id = host.getAttribute('data-id');
    var list = models.filter(function (m) { return (!page || m.page === page || (page === 'models')) && (!sec || m.section === sec) && (!id || m.id === id); });
    var bySec = host.hasAttribute('data-group'), cur = null, grid = null;
    list.forEach(function (m) {
      if (bySec && m.section !== cur) {
        cur = m.section; var h = document.createElement('h2'); h.className = 'pm-h'; h.textContent = cur; host.appendChild(h);
        grid = document.createElement('div'); grid.className = 'pm-grid'; host.appendChild(grid);
      } else if (!grid) { grid = document.createElement('div'); grid.className = 'pm-grid'; host.appendChild(grid); }
      grid.appendChild(make(m));
    });
    if (!list.length) host.textContent = 'No models listed yet.';
  }

  fetch(root + 'models/models.json').then(function (r) { return r.json(); }).then(function (d) {
    var models = d.models.slice().sort(function (a, b) { return (a.section || '') < (b.section || '') ? -1 : (a.section || '') > (b.section || '') ? 1 : 0; });
    // keep manifest order inside a section, but keep sections together
    var order = []; d.models.forEach(function (m) { if (order.indexOf(m.section) < 0) order.push(m.section); });
    models = []; order.forEach(function (s) { d.models.forEach(function (m) { if (m.section === s) models.push(m); }); });
    document.querySelectorAll('[data-models]').forEach(function (h) { mount(h, models); });
  }).catch(function () {
    document.querySelectorAll('[data-models]').forEach(function (h) { h.textContent = 'Could not load models.json.'; });
  });
})();
