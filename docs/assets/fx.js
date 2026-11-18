// Live USD→BRL conversion for the business model page.
// Every amount is stored once, in US dollars, in a data-usd attribute (a number or "low-high").
// The reais are computed from the current rate. Without JavaScript the page shows the same
// numbers worked out at the default rate (DEFAULT_RATE), written into the HTML.
(function (root) {
  var DEFAULT_RATE = 5.5; // reais per US$1
  var DEFAULT_DATE = 'a stored default';
  var KEY = 'pond-fx-usd-brl';
  var DAY = 24 * 60 * 60 * 1000;
  var API = 'https://api.frankfurter.app/latest?from=USD&to=BRL';

  function group(n, dec) {
    var s = n.toFixed(dec), p = s.split('.'), i = p[0];
    i = i.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return p[1] ? i + '.' + p[1] : i;
  }
  // Reais: cents under 10 (whole in ranges), nearest 10 from 100 up, whole reais in between.
  function brl(n, range) {
    if (n < 10) return range ? group(Math.round(n), 0) : group(n, 2);
    if (n >= 100) return group(Math.round(n / 10) * 10, 0);
    return group(Math.round(n), 0);
  }
  // Dollars: under 1 in cents, under 10 with cents, else whole.
  function usd(n) {
    if (n < 1) return null;
    return n < 10 ? group(n, 2) : group(Math.round(n), 0);
  }
  function parts(spec) { return String(spec).split('-').map(Number); }
  function fmtUsd(spec) {
    var p = parts(spec);
    if (p[p.length - 1] < 1) return p.map(function (v) { return Math.round(v * 100); }).join('–') + '¢';
    return '$' + p.map(function (v) { return usd(v) || group(v, 2); }).join('–');
  }
  function fmtBrl(spec, rate) {
    var p = parts(spec);
    return 'R$' + p.map(function (v) { return brl(v * rate, p.length > 1); }).join('–');
  }
  function text(el, rate) {
    var spec = el.getAttribute('data-usd');
    var u = fmtUsd(spec), b = fmtBrl(spec, rate);
    return el.getAttribute('data-first') === 'brl' ? b + ' (about ' + u + ')' : u + ' (' + b + ')';
  }
  function note(rate, date) {
    return 'US$1 ≈ R$' + rate.toFixed(2) + ', rate from ' + date;
  }
  function apply(doc, rate, date) {
    var els = doc.querySelectorAll('[data-usd]');
    for (var i = 0; i < els.length; i++) els[i].textContent = text(els[i], rate);
    var n = doc.querySelectorAll('.fx-note');
    for (var j = 0; j < n.length; j++) n[j].textContent = note(rate, date);
  }
  var api = { DEFAULT_RATE: DEFAULT_RATE, DEFAULT_DATE: DEFAULT_DATE, text: text, note: note };
  if (typeof module !== 'undefined') module.exports = api;
  if (!root.document) return;

  function start() {
    var doc = root.document, store = null;
    try { store = root.localStorage; } catch (e) {}
    var cached = null;
    try { cached = JSON.parse(store.getItem(KEY)); } catch (e) {}
    var good = cached && cached.rate > 0 && cached.rate < 100;
    if (good) apply(doc, cached.rate, cached.date);
    if (good && Date.now() - cached.at < DAY) return;
    if (!root.fetch) return;
    root.fetch(API, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw new Error('rate ' + r.status);
      return r.json();
    }).then(function (d) {
      var rate = d && d.rates && d.rates.BRL;
      if (!(rate > 0 && rate < 100)) throw new Error('bad rate');
      var date = d.date || 'today';
      apply(doc, rate, date);
      try { store.setItem(KEY, JSON.stringify({ rate: rate, date: date, at: Date.now() })); } catch (e) {}
    }).catch(function () { /* keep the cached or default numbers */ });
  }
  if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', start);
  else start();
})(typeof window !== 'undefined' ? window : {});
