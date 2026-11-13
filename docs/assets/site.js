// Shared site header for the Pond hub.
// Usage, first thing inside <body>:
//   <script src="ROOT/assets/site.js" data-root="ROOT/" data-page="home|gallery|roadmap|decisions|part-list|history"></script>
// Page styles live in ROOT/assets/style.css (linked in each page's <head>).
(function () {
  var me = document.currentScript;
  var root = me.getAttribute('data-root') || './';
  var page = me.getAttribute('data-page') || '';
  var links = [
    ['home', 'Home', ''],
    ['gallery', 'Drawings', 'gallery/'],
    ['roadmap', 'Roadmap', 'roadmap/'],
    ['decisions', 'Decisions', 'decisions/'],
    ['part-list', 'Part list', 'part-list/'],
    ['history', 'History', 'history/'],
    ['sim', 'Sim control', 'sim/']
  ];

  // App manifest + theme colour, so "Add to home screen" behaves like an app (portrait only).
  var mf = document.createElement('link'); mf.rel = 'manifest'; mf.href = root + 'manifest.webmanifest';
  document.head.appendChild(mf);
  var tc = document.createElement('meta'); tc.name = 'theme-color'; tc.content = '#ffffff';
  document.head.appendChild(tc);

  // Service worker: fresh copy when the network is quick, saved copy if it's slow or offline.
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register(root + 'sw.js', { scope: root }).catch(function () {});
  }

  var css = document.createElement('style');
  css.textContent =
    '.pd-bar{position:sticky;top:0;z-index:50;display:flex;align-items:center;justify-content:space-between;' +
      'height:60px;padding:0 20px;background:rgba(255,255,255,.88);-webkit-backdrop-filter:saturate(180%) blur(12px);' +
      'backdrop-filter:saturate(180%) blur(12px);border-bottom:1px solid rgba(10,37,64,.06)}' +
    '.pd-logo{font-family:var(--serif,Georgia,serif);font-size:24px;font-weight:700;letter-spacing:-.02em;color:#0a2540;text-decoration:none;line-height:1}' +
    '.pd-logo:after{content:".";color:#2fa36b}' +
    '.pd-burger{width:44px;height:44px;margin-right:-10px;border:0;background:none;display:flex;flex-direction:column;' +
      'justify-content:center;align-items:center;gap:5px;cursor:pointer;padding:0}' +
    '.pd-burger span{display:block;width:20px;height:2px;background:#0a2540;border-radius:2px}' +
    '.pd-shade{position:fixed;inset:0;background:rgba(10,37,64,.3);opacity:0;pointer-events:none;transition:opacity .2s;z-index:60}' +
    '.pd-drawer{position:fixed;top:0;right:0;height:100%;width:min(300px,82vw);background:#fff;z-index:70;' +
      'transform:translateX(100%);transition:transform .28s cubic-bezier(.2,.8,.2,1);' +
      'box-shadow:-20px 0 50px -12px rgba(50,50,93,.25);display:flex;flex-direction:column;padding:8px 0}' +
    '.pd-open .pd-shade{opacity:1;pointer-events:auto}.pd-open .pd-drawer{transform:none}' +
    '.pd-close{align-self:flex-end;width:44px;height:44px;margin:6px 10px 10px 0;border:0;background:none;font-size:26px;' +
      'line-height:1;color:#425466;cursor:pointer}' +
    '.pd-drawer a{display:block;margin:2px 12px;padding:13px 14px;border-radius:10px;font-size:17px;font-weight:600;' +
      'color:#0a2540;text-decoration:none}' +
    '.pd-drawer a.on{background:#eef7f2;color:#1d7a4f}' +
    '.pd-drawer a:active{background:#f6f9fc}';
  document.head.appendChild(css);

  var bar = document.createElement('div');
  bar.className = 'pd-bar';
  bar.innerHTML = '<a class="pd-logo" href="' + root + '">Pond</a>' +
    '<button class="pd-burger" aria-label="Open menu" aria-expanded="false"><span></span><span></span><span></span></button>';

  var shade = document.createElement('div');
  shade.className = 'pd-shade';

  var drawer = document.createElement('nav');
  drawer.className = 'pd-drawer';
  drawer.setAttribute('aria-label', 'Site menu');
  var close = document.createElement('button');
  close.className = 'pd-close'; close.setAttribute('aria-label', 'Close menu'); close.textContent = '×';
  drawer.appendChild(close);
  links.forEach(function (l) {
    var a = document.createElement('a');
    a.href = root + l[2]; a.textContent = l[1];
    if (l[0] === page) a.className = 'on';
    drawer.appendChild(a);
  });

  me.parentNode.insertBefore(bar, me);
  document.body.appendChild(shade);
  document.body.appendChild(drawer);

  var burger = bar.querySelector('.pd-burger');
  function set(open) {
    document.documentElement.classList.toggle('pd-open', open);
    burger.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  burger.onclick = function () { set(true); };
  close.onclick = function () { set(false); };
  shade.onclick = function () { set(false); };
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') set(false); });
})();
