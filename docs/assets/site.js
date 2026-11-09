// Shared site header for the Pond hub.
// Usage, first thing inside <body>:
//   <script src="ROOT/assets/site.js" data-root="ROOT/" data-page="home|gallery|roadmap|decisions|shopping|history"></script>
(function () {
  var me = document.currentScript;
  var root = me.getAttribute('data-root') || './';
  var page = me.getAttribute('data-page') || '';
  var links = [
    ['home', 'Home', ''],
    ['gallery', 'Drawings', 'gallery/'],
    ['roadmap', 'Roadmap', 'roadmap/'],
    ['decisions', 'Decisions', 'decisions/'],
    ['shopping', 'Shopping', 'shopping/'],
    ['history', 'History', 'history/']
  ];

  var css = document.createElement('style');
  css.textContent =
    '*{box-sizing:border-box}html,body{overflow-x:hidden;max-width:100%}' +
    '.pd-bar{position:sticky;top:0;z-index:50;display:flex;align-items:center;justify-content:space-between;' +
      'padding:12px 16px;background:#fff;border-bottom:1px solid #e6e8e3}' +
    '.pd-logo{font-family:Georgia,"Times New Roman",serif;font-size:24px;font-weight:700;letter-spacing:-.02em;' +
      'color:#1f3b2d;text-decoration:none;line-height:1}' +
    '.pd-burger{width:44px;height:44px;border:0;background:none;display:flex;flex-direction:column;justify-content:center;' +
      'align-items:center;gap:5px;cursor:pointer;padding:0}' +
    '.pd-burger span{display:block;width:24px;height:2px;background:#1f3b2d;border-radius:2px}' +
    '.pd-shade{position:fixed;inset:0;background:rgba(0,0,0,.35);opacity:0;pointer-events:none;transition:opacity .2s;z-index:60}' +
    '.pd-drawer{position:fixed;top:0;right:0;height:100%;width:min(280px,80vw);background:#fff;z-index:70;' +
      'transform:translateX(100%);transition:transform .25s ease;box-shadow:-4px 0 16px rgba(0,0,0,.12);' +
      'display:flex;flex-direction:column;padding:12px 0}' +
    '.pd-open .pd-shade{opacity:1;pointer-events:auto}.pd-open .pd-drawer{transform:none}' +
    '.pd-close{align-self:flex-end;width:44px;height:44px;margin-right:8px;border:0;background:none;font-size:28px;' +
      'line-height:1;color:#1f3b2d;cursor:pointer}' +
    '.pd-drawer a{display:block;padding:14px 24px;font-size:18px;font-weight:600;color:#1f3b2d;text-decoration:none}' +
    '.pd-drawer a.on{background:#e3efe5;color:#2f6b3a}' +
    '.pd-drawer a:active{background:#f0f3ee}';
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
