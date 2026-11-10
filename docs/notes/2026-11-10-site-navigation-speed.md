# Why switching tabs on the site felt slow (10 Nov 2026)

## Summary

The slowness was in the site, not in GitHub Pages. The service worker (`sw.js`) went to the network on
every request and only used its saved copy if the network took longer than 1.5 s. So on a phone with a
weak signal each tab switch waited up to 1.5 s for the page, then again for its JSON file. The service
worker also fetched with `cache: 'no-store'`, which skips the browser cache, so the saved copy never helped
when the network was merely slow rather than down.

## What was slow

| Cause | Effect |
|---|---|
| Service worker was network-first with a 1.5 s wait and `no-store` | Every navigation, script, stylesheet and JSON file paid a full network round trip, up to 1.5 s each, in sequence (page, then JSON) |
| Gallery fetched `renders.json` with `cache: 'no-store'` | Never reused a saved copy |
| Decisions page loaded `marked` from a CDN as a blocking script in the body | The page could not build until a third-party host answered, even for the list, which doesn't need it |
| Decisions fetched `docs.json` only after that script finished | Requests ran one after another |
| Gallery thumbnails come from the Cloud Run render server | Slow on a cold start, and nothing saved them, so each visit re-downloaded them |

## What changed

- `sw.js` is now stale-while-revalidate: it answers from the saved copy at once and refreshes it in the
  background. It saves all pages, scripts and JSON files on install, and saves gallery thumbnails as they are
  seen. Cache name bumped to `pond-v3` so old copies are dropped.
- Cost of that: a content update shows on the second visit after it is published, not the first.
- Pages hint their JSON file in `<head>` (`preload`), so the request starts before the page script runs.
  The gallery also opens its connection to the render server early.
- Gallery no longer uses `no-store`.
- Decisions loads `marked` only when a document is opened, in parallel with the document itself.

Left alone: `site.js` stays a normal blocking script. It is 4.6 KB, same origin and saved by the service
worker, and it has to build the menu before the page content.

## Numbers

I could not run a browser or a phone in this environment, so these are not measured. They follow from
the code and need checking on a real device (Chrome DevTools, Network tab, throttled to "Fast 3G", on a
second visit):

| | Before | After (expected) |
|---|---|---|
| Tab switch, repeat visit, slow network | page up to 1.5 s, then JSON up to 1.5 s: up to about 3 s | served from the saved copy: tens of milliseconds |
| Tab switch, repeat visit, good network | page and JSON round trips, about 2 x the network latency | same as above |
| Decisions list | waits for the CDN script, then `docs.json` | `docs.json` only |

## Would moving host help?

No. GitHub Pages already serves from a CDN with HTTP caching, and the files are tiny (all five JSON files
together are about 26 KB). Firebase Hosting or Cloud Run would give similar latency, and Cloud Run adds
cold starts, which is already what makes the gallery thumbnails slow. After the first visit the service
worker answers locally, so the host is out of the path for navigation anyway.

## Still open

- Thumbnails are full `iso.png` renders from the render server. A smaller thumbnail size would help the
  first gallery visit; that needs a change in `render-server`, not on this site.
