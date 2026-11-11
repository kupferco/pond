import loadMujoco from '@mujoco/mujoco';
import wasmUrl from '@mujoco/mujoco/mujoco.wasm?url';
import './style.css';
import { CommandLayer, type Mode } from './commands.ts';
import { SimDriver } from './drivers/simDriver.ts';
import { RealDriver } from './drivers/realDriver.ts';
import { MOTORS } from './model.ts';
import { Viewer } from './viewer.ts';

const status = document.getElementById('status')!;
const panel = document.getElementById('panel')!;

async function main() {
  const mujoco = await loadMujoco({ locateFile: (p: string) => (p.endsWith('.wasm') ? wasmUrl : p) });
  const sim = new SimDriver(mujoco);
  const cmd = new CommandLayer(sim, new RealDriver());
  const viewer = new Viewer(document.getElementById('view')!, sim);
  status.textContent = '';

  panel.innerHTML = `
    <h1>Pond arm control</h1>
    <div class="mode" role="group" aria-label="Driver">
      <button data-mode="sim" class="on">Sim</button>
      <button data-mode="real">Real</button>
    </div>
    <p id="msg" class="msg"></p>
    <table>
      <thead><tr><th>Motor</th><th>Joint</th><th>Target °</th><th></th><th>Now °</th></tr></thead>
      <tbody>${MOTORS.map((m) => `
        <tr data-id="${m.id}">
          <td class="id">${m.id}</td>
          <td>${m.label}<small>${m.min}° to ${m.max}°</small></td>
          <td><input type="number" step="1" min="${m.min}" max="${m.max}" value="${m.home}" aria-label="Motor ${m.id} target degrees"></td>
          <td><button class="go">Go</button></td>
          <td class="now">0.0</td>
        </tr>`).join('')}
      </tbody>
    </table>
    <div class="row"><button id="goall">Go all</button><button id="home">Home</button></div>`;

  const msg = document.getElementById('msg')!;
  const say = (t: string, err = false) => { msg.textContent = t; msg.className = err ? 'msg err' : 'msg'; };
  const rowInput = (tr: Element) => tr.querySelector('input') as HTMLInputElement;
  const rows = [...panel.querySelectorAll('tbody tr')];

  const guard = (fn: () => void) => { try { fn(); } catch (e) { say((e as Error).message, true); } };

  rows.forEach((tr) => {
    const go = () => guard(() => {
      const id = (tr as HTMLElement).dataset.id!;
      const input = rowInput(tr);
      const v = parseFloat(input.value);
      if (Number.isNaN(v)) return say(`Motor ${id}: enter a number`, true);
      const applied = cmd.setJointTarget(id, v);
      input.value = String(applied);
      say(applied !== v ? `Motor ${id} limited to ${applied}°` : '');
    });
    tr.querySelector('.go')!.addEventListener('click', go);
    rowInput(tr).addEventListener('keydown', (e) => { if ((e as KeyboardEvent).key === 'Enter') go(); });
  });
  document.getElementById('goall')!.addEventListener('click', () => guard(() => {
    const pose: Record<string, number> = {};
    for (const tr of rows) {
      const v = parseFloat(rowInput(tr).value);
      if (!Number.isNaN(v)) pose[(tr as HTMLElement).dataset.id!] = v;
    }
    cmd.setAllTargets(pose);
    say('');
  }));
  document.getElementById('home')!.addEventListener('click', () => guard(() => {
    cmd.home();
    MOTORS.forEach((m, i) => { rowInput(rows[i]).value = String(m.home); });
    say('');
  }));
  panel.querySelectorAll<HTMLButtonElement>('.mode button').forEach((b) => b.addEventListener('click', async () => {
    try {
      await cmd.setMode(b.dataset.mode as Mode);
      say('');
    } catch (e) { say((e as Error).message, true); }
    panel.querySelectorAll('.mode button').forEach((x) => x.classList.toggle('on', (x as HTMLElement).dataset.mode === cmd.mode));
  }));

  const nows = rows.map((tr) => tr.querySelector('.now')!);
  let last = performance.now();
  const frame = (now: number) => {
    sim.advance((now - last) / 1000);
    last = now;
    const j = cmd.readJoints();
    if (j) MOTORS.forEach((m, i) => { nows[i].textContent = j[m.id].toFixed(1); });
    viewer.render();
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

main().catch((e) => { status.textContent = `Failed to start: ${e instanceof Error ? e.message : e}`; });
