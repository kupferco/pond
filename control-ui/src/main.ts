import loadMujoco from '@mujoco/mujoco';
import wasmUrl from '@mujoco/mujoco/mujoco.wasm?url';
import './style.css';
import { SCENES } from './scenes/index.ts';
import { GROUPS, STORAGE_KEY, resolveSceneId } from './scenes/list.ts';
import type { Scene, SceneInstance } from './scenes/scene.ts';

const status = document.getElementById('status')!;
const panel = document.getElementById('panel')!;
const view = document.getElementById('view')!;
const picker = document.getElementById('picker')!;

const readStored = () => { try { return localStorage.getItem(STORAGE_KEY); } catch { return null; } };
const writeStored = (id: string) => { try { localStorage.setItem(STORAGE_KEY, id); } catch { /* private mode: URL still works */ } };

async function main() {
  const mujoco = await loadMujoco({ locateFile: (p: string) => (p.endsWith('.wasm') ? wasmUrl : p) });
  const byId = (id: string) => SCENES.find((s) => s.id === id)!;

  let current: SceneInstance | null = null;
  let currentId = '';
  let token = 0; // guards against overlapping loads when switching quickly

  // --- picker -------------------------------------------------------------
  picker.innerHTML = `
    <button id="picker-btn" aria-haspopup="listbox" aria-expanded="false"><span class="label"></span><span class="caret" aria-hidden="true">▾</span></button>
    <div id="picker-list" role="listbox" aria-label="Scene" hidden>${GROUPS.map((g) => `
      <div class="grp" role="presentation">${g}</div>
      ${SCENES.filter((s) => s.group === g).map((s) => `<button role="option" data-id="${s.id}">${s.name}</button>`).join('')}`).join('')}
    </div>`;
  const btn = document.getElementById('picker-btn')!;
  const list = document.getElementById('picker-list')!;
  const setOpen = (open: boolean) => { list.hidden = !open; btn.setAttribute('aria-expanded', String(open)); };
  btn.addEventListener('click', () => setOpen(list.hasAttribute('hidden')));
  document.addEventListener('pointerdown', (e) => { if (!picker.contains(e.target as Node)) setOpen(false); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { setOpen(false); btn.focus(); } });
  list.addEventListener('click', (e) => {
    const o = (e.target as HTMLElement).closest<HTMLElement>('[data-id]');
    if (!o) return;
    setOpen(false);
    void select(o.dataset.id!, true);
  });

  const reflect = (s: Scene) => {
    btn.querySelector('.label')!.textContent = s.name;
    list.querySelectorAll<HTMLElement>('[data-id]').forEach((o) => o.setAttribute('aria-selected', String(o.dataset.id === s.id)));
    document.title = `Pond — Sim: ${s.name}`;
  };

  // --- scene switching ----------------------------------------------------
  async function select(id: string, push: boolean) {
    if (id === currentId) return;
    const scene = byId(id);
    const mine = ++token;
    currentId = id;
    reflect(scene);
    writeStored(id);
    if (push) {
      const url = new URL(location.href);
      url.searchParams.set('scene', id);
      history.pushState(null, '', url);
    }
    current?.dispose();
    current = null;
    status.textContent = 'Loading…';
    try {
      const inst = await scene.load({ mujoco, view, panel, status });
      if (mine !== token) { inst.dispose(); return; }
      current = inst;
    } catch (e) {
      if (mine === token) status.textContent = `Failed to load ${scene.name}: ${e instanceof Error ? e.message : e}`;
    }
  }

  window.addEventListener('popstate', () => { void select(resolveSceneId(location.search, readStored()), false); });

  const first = resolveSceneId(location.search, readStored());
  // Make the URL carry the scene without adding a history entry.
  const u = new URL(location.href);
  if (u.searchParams.get('scene') !== first) { u.searchParams.set('scene', first); history.replaceState(null, '', u); }
  await select(first, false);

  let last = performance.now();
  const frame = (now: number) => {
    const dt = (now - last) / 1000;
    last = now;
    current?.frame(dt);
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

main().catch((e) => { status.textContent = `Failed to start: ${e instanceof Error ? e.message : e}`; });
