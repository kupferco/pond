import type { SceneInfo } from './list.ts';
import type { Scene } from './scene.ts';

const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]!);

/** A scene that has no model yet: shows its name, group, description and "Coming soon". */
export function placeholderScene(info: SceneInfo): Scene {
  return {
    ...info,
    async load({ panel, view, status }) {
      status.textContent = '';
      panel.innerHTML = `
        <div class="placeholder">
          <p class="group">${esc(info.group)}</p>
          <h1>${esc(info.name)}</h1>
          <p>${esc(info.description)}</p>
          <p class="soon">Coming soon</p>
        </div>`;
      view.classList.add('empty');
      return {
        frame() {},
        dispose() { panel.innerHTML = ''; view.classList.remove('empty'); },
      };
    },
  };
}
