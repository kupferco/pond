// Water sample scene: the daily sampling job of the cart (OpenPocket #357). The cart stops at a unit, the arm takes the nozzle from the cart's parking socket, plugs it into the unit's lid socket,
// the cart's peristaltic pump draws the sample into the coiled tube, the arm parks the nozzle; at the station the arm plugs the nozzle into the roof socket above the test cup and the pump runs in reverse.
import { CommandLayer } from '../commands.ts';
import { SimDriver } from '../drivers/simDriver.ts';
import { RealDriver } from '../drivers/realDriver.ts';
import { Viewer } from '../viewer.ts';
import { DEFAULT_CONFIG, formatCommand, parseCommand, samplePlan, runDue, nextRunMs, type SampleCommand } from '../sample/language.ts';
import { HEEL_ML, POSE_NAMES, SAMPLE_ML, TUBE_ML } from '../sample/layout.ts';
import { SampleRun, SampleWorld, sampleMjcf } from '../sample/world.ts';
import { SCENE_INFOS } from './list.ts';
import type { Scene } from './scene.ts';

const info = SCENE_INFOS.find((s) => s.id === 'water-sample')!;
const esc = (v: unknown) => String(v).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]!));
const VIEWS: Record<string, { target: [number, number, number]; dist: number; az: number; el: number }> = {
  overview: { target: [0.1, 0.5, -0.05], dist: 2.4, az: 0.9, el: 0.35 },
  unit: { target: [0.12, 0.03, -0.02], dist: 0.7, az: 0.7, el: 0.35 },
  station: { target: [0.15, 1.0, 0.0], dist: 0.7, az: 0.7, el: 0.35 },
};

export const waterSampleScene: Scene = {
  ...info,
  async load({ mujoco, view, panel, status }) {
    const sim = new SimDriver(mujoco, sampleMjcf());
    const cmd = new CommandLayer(sim, new RealDriver());
    const world = new SampleWorld(sim);
    const viewer = new Viewer(view, sim, { ...VIEWS.unit, maxDist: 5, far: 30 });
    status.textContent = '';
    let cfg = { ...DEFAULT_CONFIG };
    let lastRun: number | null = null;

    panel.innerHTML = `
    <h1>Pond water sample</h1>
    <section class="card cartstat" aria-live="off">
      <dl>
        <dt>Now</dt><dd id="w-now">Ready</dd>
        <dt>Cart</dt><dd id="w-cart"></dd>
        <dt>Nozzle</dt><dd id="w-noz"></dd>
        <dt>Pump</dt><dd id="w-pump"></dd>
        <dt>Tube</dt><dd id="w-tube"></dd>
        <dt>Station cup</dt><dd id="w-cup"></dd>
        <dt>Next run</dt><dd id="w-next"></dd>
      </dl>
      <p class="hint">The cart on its track with the arm, the pump and the coiled tube; on the left the unit to sample (blue tank, flush socket in its lid), further along the unit with the water testing station (box with the sample cup and a socket in its roof). Run one full cycle, or type a single command.</p>
    </section>
    <p id="w-msg" class="msg"></p>
    <div class="row wrap">
      <button class="lock big grow" id="w-run">Run the sample cycle</button>
      <button class="lock big grow" id="w-reset">Reset</button>
    </div>
    <div class="xy stepbar">
      <label>Speed <select class="lock tall" id="w-speed" aria-label="Speed"><option value="1">1×</option><option value="5" selected>5×</option><option value="20">20×</option><option value="0">Max</option></select></label>
      <label>Every <input class="lock" id="w-days" type="number" min="0.1" step="any" value="${cfg.intervalDays}" aria-label="Days between samples" style="width:4.5em"> days</label>
    </div>
    <p class="hint">Daily by default; change the number of days to change how often the robot samples.</p>
    <p><strong>One command</strong></p>
    <div class="row wrap">
      <input class="lock grow" id="w-line" list="w-lines" placeholder="pose unit_above" aria-label="Command" autocomplete="off">
      <datalist id="w-lines">${[...POSE_NAMES.map((n) => `pose ${n}`), 'gripper open', 'gripper close', 'cart to unit', 'cart to station', 'pump in 10', 'pump out 10', 'wait 5'].map((l) => `<option value="${l}">`).join('')}</datalist>
      <button class="lock big" id="w-one">Do it</button>
    </div>
    <div class="row">
      <button class="big grow" data-view="overview">Overview</button>
      <button class="big grow" data-view="unit">Unit</button>
      <button class="big grow" data-view="station">Station</button>
    </div>
    <div id="w-result" class="result" hidden></div>
    <details class="card"><summary>The cycle, as commands</summary><pre class="hint" id="w-plan" style="white-space:pre-wrap"></pre></details>
    <details class="card"><summary>About this scene</summary>
      <p class="hint">Scripted and kinematic, like the Transplant scene: the arm is put on each pose in turn and every step is checked (the arm touches nothing, the nozzle is plugged in straight before the pump runs, the pump draws only from the unit and pushes only into the station, the cart only drives with the nozzle parked, the tube never holds more than ${TUBE_ML} ml). Assumed and still to measure on the bench: ${DEFAULT_CONFIG.mlPerTurn} ml per pump turn, a ${SAMPLE_ML} ml sample, a ${HEEL_ML} ml cup that always keeps its heel over the standpipe and mixes perfectly (so about 46 percent of the old sample stays). The arm stands 40 mm higher over the lid than in the CAD so the SO-101 stand-in reaches the station roof with the nozzle pointing straight down. Design: docs/water-station/README.md; commands and real-hardware run sheet: docs/water-station/arm-sample-run.md.</p>
    </details>`;

    const $ = <T extends HTMLElement>(id: string) => panel.querySelector<T>('#' + id)!;
    const msg = $('w-msg'), result = $('w-result');
    const say = (t: string, err = false) => { msg.textContent = t; msg.className = err ? 'msg err' : 'msg'; };
    const plan = () => samplePlan(cfg);
    const showPlan = () => { $('w-plan').textContent = plan().map((c, i) => `${String(i + 1).padStart(2)}  ${formatCommand(c)}`).join('\n'); };
    showPlan();
    const setBusy = (busy: boolean) => {
      panel.querySelectorAll<HTMLInputElement | HTMLButtonElement | HTMLSelectElement>('.lock').forEach((el) => { el.disabled = busy; });
      panel.classList.toggle('busy', busy);
    };
    let run: SampleRun | null = null;
    let fullCycle = false;
    const start = (cmds: SampleCommand[], full: boolean) => { if (world.violation) return say('The last run stopped with a fault. Press Reset first.', true); result.hidden = true; say(''); setBusy(true); fullCycle = full; run = new SampleRun(world, cmd, cmds, cfg.mlPerTurn); };
    $('w-run').addEventListener('click', () => start(plan(), true));
    $('w-reset').addEventListener('click', () => { world.reset(); cmd.home(); run = null; result.hidden = true; lastRun = null; say(''); });
    $('w-one').addEventListener('click', () => { try { start([parseCommand($<HTMLInputElement>('w-line').value)], false); } catch (e) { say((e as Error).message, true); } });
    $('w-days').addEventListener('change', () => { const v = parseFloat($<HTMLInputElement>('w-days').value); if (v > 0) cfg = { ...cfg, intervalDays: v }; else say('Days must be above 0', true); });
    panel.querySelectorAll<HTMLButtonElement>('[data-view]').forEach((b) => b.addEventListener('click', () => viewer.setView(VIEWS[b.dataset.view!])));

    const resultHtml = (r: SampleRun) => {
      const x = r.result();
      const rows = x.ok ? `<dt>Drawn at the unit</dt><dd>${x.drawnMl.toFixed(0)} ml</dd><dt>Over the standpipe</dt><dd>${x.drainedMl.toFixed(0)} ml</dd><dt>New sample in the cup</dt><dd>${x.newInCupMl.toFixed(0)} of ${x.cupMl.toFixed(0)} ml (${x.oldPct.toFixed(0)} percent old)</dd>` : '';
      return `<div class="verdict ${x.ok ? 'ok' : 'bad'}">${x.ok ? '✓ Success' : `✗ Failed: ${esc(x.reason)}`}</div><dl>${rows}<dt>Time</dt><dd>${x.time.toFixed(0)} s</dd></dl>`;
    };
    const show = () => {
      $('w-now').textContent = run ? `${run.label} (${Math.round(run.progress * 100)} percent)` : (world.violation ? 'Stopped' : 'Ready');
      $('w-cart').textContent = world.stop ? `at the ${world.stop === 'unit' ? 'unit to sample' : 'station'}` : 'driving';
      const p = world.plug();
      $('w-noz').textContent = world.where === 'parked' ? 'parked on the cart' : p.socket ? `in the ${p.socket} socket` : 'in the hand';
      $('w-pump').textContent = `${world.rotorTurns.toFixed(1)} turns net (positive = drawing)`;
      $('w-tube').textContent = `${world.tubeMl.toFixed(0)} of ${TUBE_ML} ml`;
      $('w-cup').textContent = `${world.cupMl.toFixed(0)} ml, ${world.newInCup.toFixed(0)} ml new, ${world.drainedMl.toFixed(0)} ml run to the drain`;
      $('w-next').textContent = lastRun === null ? `due now (every ${cfg.intervalDays} day${cfg.intervalDays === 1 ? '' : 's'})` : (runDue(lastRun, Date.now(), cfg.intervalDays) ? 'due now' : new Date(nextRunMs(lastRun, cfg.intervalDays)).toLocaleString());
    };
    show();

    let sinceUi = 1;
    return {
      frame(dt: number) {
        if (run) {
          const speed = parseFloat($<HTMLSelectElement>('w-speed').value), t0 = performance.now();
          if (speed > 0) run.advance(Math.min(dt, 0.1) * speed);
          else while (!run.done && performance.now() - t0 < 14) run.advance(0.5);
          if (run.done) {
            result.hidden = false; result.innerHTML = resultHtml(run);
            if (run.failReason === '' && fullCycle) lastRun = Date.now();
            if (run.failReason !== '') say(run.failReason, true);
            run = null; setBusy(false); show();
          }
        }
        sinceUi += dt;
        if (sinceUi > 0.1) { sinceUi = 0; show(); }
        viewer.render();
      },
      dispose() { viewer.dispose(); sim.dispose(); panel.innerHTML = ''; },
    };
  },
};
