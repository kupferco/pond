import { CommandLayer, type Mode } from '../commands.ts';
import { SimDriver } from '../drivers/simDriver.ts';
import { RealDriver } from '../drivers/realDriver.ts';
import { MOTORS } from '../model.ts';
import { Viewer } from '../viewer.ts';
import { Attempt, POS_TOL_MM, TILT_TOL_DEG, type AttemptResult } from '../arm/attempt.ts';
import { POD_REST_Z, REACH } from '../arm/dims.ts';
import { clampToReach, farEnough, randomPlacement, type XY } from '../arm/placement.ts';
import { RunLog, newRunId, type RunSummary } from '../arm/runlog.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'arm')!;

const esc = (v: unknown) => String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
const unitOf = (m: (typeof MOTORS)[number]) => (m.linear ? 'mm' : '°');
const mm = (m: number) => Math.round(m * 1000);
const seedNow = () => Math.floor(Math.random() * 0x7fffffff);

interface Row { n: number; result: AttemptResult; seed: number; pod: XY; slot: XY }

export const armScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const sim = new SimDriver(mujoco);
    const cmd = new CommandLayer(sim, new RealDriver());
    const viewer = new Viewer(view, sim);
    const runLog = new RunLog();
    status.textContent = '';

    panel.innerHTML = `
    <h1>Pond arm control</h1>
    <div class="mode" role="group" aria-label="Driver">
      <button data-mode="sim" class="on">Sim</button>
      <button data-mode="real">Real</button>
    </div>
    <p id="msg" class="msg"></p>

    <section class="card">
      <h2>Scene</h2>
      <div class="xy">
        <span>Pod</span><label>x <input class="lock" id="pod-x" type="number" step="5" aria-label="Pod x mm"></label><label>y <input class="lock" id="pod-y" type="number" step="5" aria-label="Pod y mm"></label>
        <span>Slot</span><label>x <input class="lock" id="slot-x" type="number" step="5" aria-label="Slot x mm"></label><label>y <input class="lock" id="slot-y" type="number" step="5" aria-label="Slot y mm"></label>
      </div>
      <div class="row"><button class="lock" id="randomize">Randomize</button></div>
      <p class="hint">mm from the arm base (x forward, y left). Reach: ${REACH.rMin * 1000}–${REACH.rMax * 1000} mm from the base, within ±${REACH.angMax}° of forward; pod and slot at least 65 mm apart. Pod: 25 × 40 mm cylinder (assumed, as in cad/pod_store.py). Slot: one 29 mm square socket.</p>
    </section>

    <div class="tabs" role="tablist">
      <button role="tab" data-tab="step" aria-selected="true">Step</button>
      <button role="tab" data-tab="task" aria-selected="false">Task</button>
      <button role="tab" data-tab="direct" aria-selected="false">Direct</button>
    </div>

    <div class="tabpane" data-pane="step">
      <div class="xy stepbar">
        <label>Joint <select class="lock" id="step-joint">${MOTORS.map((m) => `<option value="${m.id}">${m.id} · ${m.label}</option>`).join('')}</select></label>
        <label>Step <input class="lock" id="step-size" type="number" min="0.1" step="1" value="10"> <span id="step-unit">°</span></label>
      </div>
      <div class="row"><button class="lock big" id="step-minus">− step</button><button class="lock big" id="step-plus">+ step</button><button class="lock" id="step-home">Home</button></div>
      <table>
        <thead><tr><th>Motor</th><th>Joint</th><th>Target</th><th>Now</th></tr></thead>
        <tbody>${MOTORS.map((m) => `<tr><td class="id">${m.id}</td><td>${m.label}<small>${m.min} to ${m.max}${unitOf(m)}</small></td><td class="now" data-target="${m.id}">0.0</td><td class="now" data-now="${m.id}">0.0</td></tr>`).join('')}</tbody>
      </table>
    </div>

    <div class="tabpane" data-pane="task" hidden>
      <p><strong>Pick up the pod and place it in the slot.</strong> Scripted controller: inverse kinematics, then approach, descend, grasp, lift, move, lower, release, retreat.</p>
      <p class="hint">Success = pod seated in the socket within ${POS_TOL_MM} mm and ${TILT_TOL_DEG}° of the seat pose. The controller sees pod and slot with 1.2 mm of simulated perception noise. Grasp and release are kinematic (no contact physics yet).</p>
      <div class="row wrap">
        <button class="lock big" id="run-one">Run task</button>
        <label>Speed <select class="lock" id="speed"><option value="1">1×</option><option value="4" selected>4×</option><option value="0">Max</option></select></label>
      </div>
      <div id="one" class="result" hidden></div>

      <h3>Auto-run</h3>
      <div class="row wrap">
        <label>Attempts <input class="lock" id="auto-n" type="number" min="1" max="500" step="1" value="50"></label>
        <button class="lock big" id="auto-go">Run randomized</button><button id="auto-stop" hidden>Stop</button>
      </div>
      <div id="auto" class="auto" hidden>
        <progress id="auto-bar" max="1" value="0"></progress>
        <p id="auto-text" class="stat"></p>
        <div class="scroll"><table class="runs"><thead><tr><th>#</th><th>Result</th><th>Pos mm</th><th>Tilt °</th><th>Time s</th><th>Seed</th></tr></thead><tbody id="auto-rows"></tbody></table></div>
      </div>

      <h3>Logging</h3>
      <label class="chk"><input type="checkbox" id="log-on" checked> Log runs to Firebase (pond-grow)</label>
      <p id="log-status" class="hint"></p>
      <details id="runs-box"><summary>Logged runs</summary>
        <div class="row"><button id="runs-refresh">Refresh</button></div>
        <div id="runs-list" class="hint">Open to load.</div>
      </details>
    </div>

    <div class="tabpane" data-pane="direct" hidden>
    <table>
      <thead><tr><th>Motor</th><th>Joint</th><th>Target °</th><th></th><th>Now °</th></tr></thead>
      <tbody id="direct-rows">${MOTORS.map((m) => `
        <tr data-id="${m.id}">
          <td class="id">${m.id}</td>
          <td>${m.label}<small>${m.min}° to ${m.max}°</small></td>
          <td><input class="lock" type="number" step="1" min="${m.min}" max="${m.max}" value="${m.home}" aria-label="Motor ${m.id} target degrees"></td>
          <td><button class="go lock">Go</button></td>
          <td class="now" data-now="${m.id}">0.0</td>
        </tr>`).join('')}
      </tbody>
    </table>
    <div class="row"><button class="lock" id="goall">Go all</button><button class="lock" id="home">Home</button></div>
    </div>`;

    const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
    const msg = $('msg');
    const say = (t: string, err = false) => { msg.textContent = t; msg.className = err ? 'msg err' : 'msg'; };
    const guard = (fn: () => void) => { try { fn(); } catch (e) { say((e as Error).message, true); } };

    // --- scene placement ---------------------------------------------------
    let pod: XY = [0.16, -0.06], slot: XY = [0.16, 0.08];
    const inputs = { podX: $<HTMLInputElement>('pod-x'), podY: $<HTMLInputElement>('pod-y'), slotX: $<HTMLInputElement>('slot-x'), slotY: $<HTMLInputElement>('slot-y') };
    const showPlacement = () => {
      inputs.podX.value = String(mm(pod[0])); inputs.podY.value = String(mm(pod[1]));
      inputs.slotX.value = String(mm(slot[0])); inputs.slotY.value = String(mm(slot[1]));
    };
    const placeIdle = () => {
      sim.setMocap('pod', [pod[0], pod[1], POD_REST_Z]);
      sim.setMocap('slot', [slot[0], slot[1], 0]);
      mujoco.mj_forward(sim.model, sim.data);
    };
    const readPlacement = () => {
      const p: XY = [parseFloat(inputs.podX.value) / 1000, parseFloat(inputs.podY.value) / 1000];
      const s: XY = [parseFloat(inputs.slotX.value) / 1000, parseFloat(inputs.slotY.value) / 1000];
      if ([...p, ...s].some(Number.isNaN)) { say('Pod and slot positions must be numbers', true); showPlacement(); return; }
      const pc = clampToReach(p), sc = clampToReach(s);
      if (!farEnough(pc, sc)) { say('Pod and slot are too close together (min 65 mm); position not changed', true); showPlacement(); return; }
      const moved = Math.hypot(pc[0] - p[0], pc[1] - p[1]) > 1e-4 || Math.hypot(sc[0] - s[0], sc[1] - s[1]) > 1e-4;
      pod = pc; slot = sc;
      showPlacement(); placeIdle();
      say(moved ? 'Moved to the nearest reachable position' : '');
    };
    Object.values(inputs).forEach((i) => i.addEventListener('change', readPlacement));
    $('randomize').addEventListener('click', () => { const p = randomPlacement(seedNow()); pod = p.pod; slot = p.slot; showPlacement(); placeIdle(); say(''); });
    showPlacement(); placeIdle();

    // --- tabs --------------------------------------------------------------
    const selectTab = (name: string) => {
      panel.querySelectorAll<HTMLElement>('.tabs [data-tab]').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.tab === name)));
      panel.querySelectorAll<HTMLElement>('.tabpane').forEach((p) => { p.hidden = p.dataset.pane !== name; });
    };
    panel.querySelectorAll<HTMLElement>('.tabs [data-tab]').forEach((b) => b.addEventListener('click', () => selectTab(b.dataset.tab!)));

    // --- direct tab (unchanged behaviour) -----------------------------------
    const rows = [...panel.querySelectorAll('#direct-rows tr')];
    const rowInput = (tr: Element) => tr.querySelector('input') as HTMLInputElement;
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
    $('goall').addEventListener('click', () => guard(() => {
      const pose: Record<string, number> = {};
      for (const tr of rows) {
        const v = parseFloat(rowInput(tr).value);
        if (!Number.isNaN(v)) pose[(tr as HTMLElement).dataset.id!] = v;
      }
      cmd.setAllTargets(pose);
      say('');
    }));
    const goHome = () => guard(() => {
      cmd.home();
      MOTORS.forEach((m, i) => { rowInput(rows[i]).value = String(m.home); });
      say('');
    });
    $('home').addEventListener('click', goHome);
    $('step-home').addEventListener('click', goHome);

    // --- step tab ------------------------------------------------------------
    const jointSel = $<HTMLSelectElement>('step-joint'), stepSize = $<HTMLInputElement>('step-size');
    const syncUnit = () => {
      const m = MOTORS.find((x) => x.id === jointSel.value)!;
      $('step-unit').textContent = unitOf(m);
    };
    jointSel.addEventListener('change', syncUnit);
    const nudge = (dir: 1 | -1) => guard(() => {
      const step = parseFloat(stepSize.value);
      if (!(step > 0)) return say('Step size must be a positive number', true);
      const id = jointSel.value;
      const now = cmd.driver.targets()[id] ?? 0;
      const applied = cmd.setJointTarget(id, now + dir * step);
      const row = rows.find((r) => (r as HTMLElement).dataset.id === id);
      if (row) rowInput(row).value = String(Math.round(applied * 100) / 100);
      say(Math.abs(applied - (now + dir * step)) > 1e-9 ? `Motor ${id} limited to ${applied}°` : '');
    });
    $('step-plus').addEventListener('click', () => nudge(1));
    $('step-minus').addEventListener('click', () => nudge(-1));

    panel.querySelectorAll<HTMLButtonElement>('.mode button').forEach((b) => b.addEventListener('click', async () => {
      try {
        await cmd.setMode(b.dataset.mode as Mode);
        say('');
      } catch (e) { say((e as Error).message, true); }
      panel.querySelectorAll('.mode button').forEach((x) => x.classList.toggle('on', (x as HTMLElement).dataset.mode === cmd.mode));
    }));

    // --- task tab: runs ----------------------------------------------------
    const oneBox = $('one'), autoBox = $('auto'), autoRows = $('auto-rows'), autoText = $('auto-text');
    const autoBar = $<HTMLProgressElement>('auto-bar'), autoStop = $('auto-stop'), logStatus = $('log-status');
    const logOn = $<HTMLInputElement>('log-on');
    let attempt: Attempt | null = null;
    let batch: { id: string; n: number; i: number; seed: number; rows: Row[]; stop: boolean } | null = null;
    let single = false;

    const setBusy = (busy: boolean) => {
      panel.querySelectorAll<HTMLInputElement | HTMLButtonElement | HTMLSelectElement>('.lock').forEach((el) => { el.disabled = busy; });
      panel.classList.toggle('busy', busy);
    };
    const showLogStatus = () => {
      if (!logOn.checked) { logStatus.textContent = 'Logging is off: runs are not saved.'; return; }
      const bits = [`${runLog.logged} saved`];
      if (runLog.pending) bits.push(`${runLog.pending} uploading`);
      if (runLog.failed) bits.push(`${runLog.failed} failed`);
      logStatus.textContent = `Logging on: ${bits.join(', ')}.${runLog.lastError ? ` Last error: ${runLog.lastError}` : ''}`;
      logStatus.className = runLog.failed ? 'hint err' : 'hint';
    };
    logOn.addEventListener('change', showLogStatus);
    showLogStatus();

    const startAttempt = (p: XY, s: XY, seed: number) => {
      pod = p; slot = s; showPlacement();
      attempt = new Attempt(sim, cmd, { pod: p, slot: s, seed });
    };

    const resultHtml = (r: AttemptResult, live = '') => `
      <div class="verdict ${r.success ? 'ok' : 'bad'}">${r.success ? '✓ Success' : '✗ Failed'}: ${esc(r.reason)}</div>
      <dl><dt>Position error</dt><dd>${r.posErrMm.toFixed(1)} mm</dd><dt>Orientation error</dt><dd>${r.tiltErrDeg.toFixed(1)}°</dd><dt>Time</dt><dd>${r.durationS.toFixed(1)} s</dd></dl>${live}`;

    const renderAuto = (finished: boolean) => {
      if (!batch) return;
      const done = batch.rows.length, ok = batch.rows.filter((r) => r.result.success).length;
      autoBar.value = done / batch.n;
      autoText.innerHTML = `${done} / ${batch.n} done · success rate <strong>${done ? Math.round(100 * ok / done) : 0}%</strong> (${ok} ok, ${done - ok} failed)${finished ? (batch.stop ? ' · stopped' : ' · finished') : ''}`;
    };
    const addAutoRow = (r: Row) => {
      const tr = document.createElement('tr');
      tr.className = r.result.success ? '' : 'fail';
      tr.innerHTML = `<td>${r.n}</td><td>${r.result.success ? '✓ seated' : `✗ ${esc(r.result.reason)}`}</td><td>${r.result.posErrMm.toFixed(1)}</td><td>${r.result.tiltErrDeg.toFixed(1)}</td><td>${r.result.durationS.toFixed(1)}</td><td>${r.seed}</td>`;
      autoRows.prepend(tr);
    };

    const finishAttempt = () => {
      const a = attempt!;
      const r = a.result!;
      const runId = newRunId();
      if (batch) {
        const row: Row = { n: batch.i + 1, result: r, seed: a.cfg.seed, pod: a.cfg.pod, slot: a.cfg.slot };
        batch.rows.push(row);
        addAutoRow(row);
        if (logOn.checked) runLog.enqueue(a, { runId, batchId: batch.id, batchIndex: batch.i, batchSize: batch.n, startedAt: new Date().toISOString() });
        batch.i++;
        renderAuto(false);
        attempt = null;
        if (batch.i >= batch.n || batch.stop) endBatch();
      } else {
        oneBox.hidden = false; oneBox.innerHTML = resultHtml(r);
        if (logOn.checked) runLog.enqueue(a, { runId, batchId: runId, batchIndex: 0, batchSize: 1, startedAt: new Date().toISOString() });
        attempt = null; single = false; setBusy(false);
      }
      showLogStatus();
    };
    const endBatch = () => {
      renderAuto(true);
      batch = null; attempt = null; setBusy(false); autoStop.hidden = true;
      void runLog.idle().then(showLogStatus);
    };

    $('run-one').addEventListener('click', () => {
      if (cmd.mode !== 'sim') return say('The task runs in the sim only', true);
      say(''); single = true; setBusy(true);
      oneBox.hidden = false; oneBox.textContent = 'Running…';
      startAttempt(pod, slot, seedNow());
    });
    $('auto-go').addEventListener('click', () => {
      if (cmd.mode !== 'sim') return say('The task runs in the sim only', true);
      const n = Math.max(1, Math.min(500, Math.floor(parseFloat($<HTMLInputElement>('auto-n').value) || 0)));
      if (!n) return say('Attempts must be a number between 1 and 500', true);
      say('');
      batch = { id: newRunId(), n, i: 0, seed: seedNow(), rows: [], stop: false };
      autoRows.innerHTML = ''; autoBox.hidden = false; autoStop.hidden = false; oneBox.hidden = true;
      setBusy(true); renderAuto(false);
    });
    autoStop.addEventListener('click', () => { if (batch) batch.stop = true; });

    // --- runs list ---------------------------------------------------------
    const runsList = $('runs-list');
    const loadRuns = async () => {
      runsList.textContent = 'Loading…';
      try {
        const runs = await runLog.recent();
        if (!runs.length) { runsList.textContent = 'No logged runs yet.'; return; }
        const groups = new Map<string, Array<RunSummary & { tsMs: number }>>();
        for (const r of runs) {
          const key = r.batchSize > 1 ? r.batchId : 'single';
          (groups.get(key) ?? groups.set(key, []).get(key)!).push(r);
        }
        runsList.innerHTML = [...groups.entries()].map(([key, rs]) => {
          const ok = rs.filter((r) => r.success).length;
          const when = new Date(Math.max(...rs.map((r) => r.tsMs))).toLocaleString();
          const title = key === 'single' ? 'Single runs' : `Batch ${esc(key.slice(0, 6))}`;
          const sorted = [...rs].sort((a, b) => a.batchIndex - b.batchIndex || a.tsMs - b.tsMs);
          return `<details class="batch"><summary>${title} · ${esc(when)} · ${rs.length}${key !== 'single' ? ` / ${esc(rs[0].batchSize)}` : ''} runs · <strong>${Math.round(100 * ok / rs.length)}%</strong> success</summary>
            <table class="runs"><thead><tr><th>#</th><th>Result</th><th>Pos mm</th><th>Tilt °</th><th>Time s</th><th>Pod → slot (mm)</th></tr></thead><tbody>${sorted.map((r) => `
              <tr class="${r.success ? '' : 'fail'}"><td>${esc(r.batchIndex + 1)}</td><td>${r.success ? '✓' : `✗ ${esc(r.reason)}`}</td><td>${esc(r.posErrMm)}</td><td>${esc(r.tiltErrDeg)}</td><td>${esc(r.durationS)}</td><td>${esc(Math.round(r.podXmm))},${esc(Math.round(r.podYmm))} → ${esc(Math.round(r.slotXmm))},${esc(Math.round(r.slotYmm))}</td></tr>`).join('')}</tbody></table></details>`;
        }).join('');
      } catch (e) { runsList.textContent = `Could not load runs: ${e instanceof Error ? e.message : e}`; }
    };
    $('runs-refresh').addEventListener('click', () => { void loadRuns(); });
    $('runs-box').addEventListener('toggle', () => { if (($('runs-box') as HTMLDetailsElement).open) void loadRuns(); });

    // --- frame loop ----------------------------------------------------------
    const text = (sel: string, f: (id: string) => string) => panel.querySelectorAll<HTMLElement>(sel).forEach((el) => {
      el.textContent = f(el.dataset.now ?? el.dataset.target!);
    });
    let sinceUi = 1;
    return {
      frame(dt: number) {
        if (batch && !attempt) {
          const p = randomPlacement(batch.seed + batch.i);
          startAttempt(p.pod, p.slot, batch.seed + batch.i);
        }
        if (attempt) {
          const t0 = performance.now();
          const speed = batch ? 0 : parseFloat($<HTMLSelectElement>('speed').value);
          if (speed > 0) attempt.advance(Math.min(dt, 0.1) * speed);
          else while (!attempt.done && performance.now() - t0 < 14) attempt.advance(0.05);
          if (single && attempt) oneBox.textContent = `Running… ${attempt.phaseName} (${attempt.time.toFixed(1)} s)`;
          if (attempt?.done) finishAttempt();
        } else {
          sim.advance(dt);
        }
        sinceUi += dt;
        if (sinceUi > 0.1) {
          sinceUi = 0;
          const j = cmd.readJoints(), t = cmd.driver.targets();
          if (j) text('[data-now]', (id) => (j[id] ?? 0).toFixed(1));
          text('[data-target]', (id) => (t[id] ?? 0).toFixed(1));
          if (batch || logOn.checked) showLogStatus();
        }
        viewer.render();
      },
      dispose() {
        viewer.dispose();
        sim.dispose();
        panel.innerHTML = '';
      },
    };
  },
};
