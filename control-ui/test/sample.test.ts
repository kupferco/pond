// Headless check of the water sampling job (OpenPocket #357): command language, named poses, the pump commands, the simulated cycle and what it must refuse.
import loadMujoco from '@mujoco/mujoco';
import { SimDriver } from '../src/drivers/simDriver.ts';
import { RealDriver } from '../src/drivers/realDriver.ts';
import { CommandLayer } from '../src/commands.ts';
import { DEFAULT_CONFIG, formatCommand, nextRunMs, parseCommand, parseScript, runDue, samplePlan, turnsFor, type SampleCommand } from '../src/sample/language.ts';
import { HEEL_ML, PARK_REL, POSES, POSE_NAMES, POSE_TARGETS, STATION_REL, STOPS, TOOL_TX, TOOL_TZ, TUBE_ML, UNIT_REL } from '../src/sample/layout.ts';
import { SampleRun, SampleWorld, sampleMjcf } from '../src/sample/world.ts';
import { toolPoint } from '../src/arm/kinematics.ts';
import { worstContact } from '../src/transplant/apply.ts';
import { SCENE_INFOS } from '../src/scenes/list.ts';

let fail = 0;
const check = (name: string, ok: boolean, info = '') => { console.log(ok ? 'ok  ' : 'FAIL', name, info); if (!ok) fail++; };
const mj = await loadMujoco();
const fresh = () => {
  const sim = new SimDriver(mj, sampleMjcf());
  const cmd = new CommandLayer(sim, new RealDriver());
  return { sim, cmd, world: new SampleWorld(sim) };
};
const go = (cmds: string | SampleCommand[], env = fresh(), mlPerTurn = DEFAULT_CONFIG.mlPerTurn) => {
  const list = typeof cmds === 'string' ? parseScript(cmds) : cmds;
  const run = new SampleRun(env.world, env.cmd, list, mlPerTurn);
  let n = 0;
  while (!run.done && n++ < 100000) run.advance(1);
  return { run, ...env, res: run.result() };
};
const TAKE = 'gripper open\npose park_above\npose park_in\ngripper close\npose park_above';
const PARK = 'pose park_above\npose park_in\ngripper open\npose park_above\npose rest\ngripper close';

// --- the language
check('every command formats and parses back', samplePlan().every((c) => JSON.stringify(parseCommand(formatCommand(c))) === JSON.stringify(c)));
check('script ignores comments and blank lines', parseScript('# take it\n\npose rest  # fold\npump in 5').length === 2);
for (const bad of ['pose nowhere', 'pump sideways 3', 'pump in 0', 'pump in', 'cart to moon', 'gripper half', 'dance']) {
  let msg = ''; try { parseCommand(bad); } catch (e) { msg = (e as Error).message; }
  check(`rejects "${bad}" with a readable message`, msg.includes(bad));
}
const plan = samplePlan();
const pumps = plan.filter((c) => c.op === 'pump') as Extract<SampleCommand, { op: 'pump' }>[];
check('plan: one draw then one reverse, same turns, 70 ml at 1 ml per turn', pumps.length === 2 && pumps[0].dir === 'in' && pumps[1].dir === 'out' && pumps[0].turns === 70 && pumps[1].turns === 70);
check('plan: turns follow ml per turn', (samplePlan({ ...DEFAULT_CONFIG, mlPerTurn: 0.5 }).find((c) => c.op === 'pump') as { turns: number }).turns === 140 && turnsFor(70, 0.35) === 200);
check('plan: the arm is folded and the gripper closed before every cart move after the first', plan.every((c, k) => c.op !== 'cart' || k === 0 || (plan[k - 1].op === 'gripper' && (plan[k - 1] as { state: string }).state === 'close' && (plan[k - 2] as { name?: string }).name === 'rest')));
const day = 86_400_000;
check('daily by default, adjustable', DEFAULT_CONFIG.intervalDays === 1 && runDue(null, 0, 1) && !runDue(0, day - 1, 1) && runDue(0, day, 1) && !runDue(0, day, 2) && runDue(0, 2 * day, 2) && nextRunMs(5, 2) === 5 + 2 * day);
let e1 = ''; try { runDue(0, 1, 0); } catch (e) { e1 = (e as Error).message; }
check('interval of 0 days is refused', e1 !== '');

// --- poses
check('seven named poses', POSE_NAMES.length === 7 && POSE_NAMES.every((n) => n in POSES));
{
  const { sim, world } = fresh();
  for (const n of POSE_NAMES) {
    const t = POSE_TARGETS[n];
    if (!t) continue;
    sim.setJointsKinematic({ ...POSES[n], F: 13 });
    const h = world.heldNozzle();
    const want = [t.mouth[0], t.mouth[1], t.mouth[2] + t.dz];
    const err = Math.hypot(h.tip[0] - want[0], h.tip[1] - want[1], h.tip[2] - want[2]) * 1000;
    check(`pose ${n}: nozzle tip within 1 mm of the plan, pointing straight down`, err < 1 && h.axis[2] < -0.9995, `${err.toFixed(2)} mm`);
  }
  const j = POSES.station_in;
  const tp = toolPoint(j, TOOL_TX, TOOL_TZ);
  check('pose maths agrees with the arm model', Math.abs(tp[0] - STATION_REL[0]) < 1e-3 && Math.abs(tp[2] - (STATION_REL[2] - 0.014)) < 1e-3);
  const reach = (p: number[]) => Math.hypot(p[0], p[1], p[2] - 0.095) * 1000;
  console.log(`     shoulder to mouth: parking ${reach(PARK_REL).toFixed(0)} mm, unit ${reach(UNIT_REL).toFixed(0)} mm, station ${reach(STATION_REL).toFixed(0)} mm`);
}

// --- the full cycle
{
  const { run, res, world, cmd, sim } = go(plan);
  check('full cycle succeeds', res.ok, res.reason);
  check('drew 70 ml, tube empty again', Math.abs(res.drawnMl - 70) < 1e-6 && world.tubeMl < 1e-6, `${res.drawnMl}`);
  check('cup is back at its heel, old sample about 46 percent (README: 46)', Math.abs(world.cupMl - HEEL_ML) < 1e-6 && Math.abs(res.oldPct - 46.4) < 0.5, `${res.oldPct.toFixed(1)}`);
  check('water is conserved: what went in came out over the standpipe or stayed', Math.abs(res.drawnMl - res.drainedMl - (world.cupMl - HEEL_ML)) < 1e-6);
  check('ends with the nozzle parked, the cart at the station, the arm at rest, the gripper closed', world.where === 'parked' && world.stop === 'station' && world.plug().socket === 'park' && !world.gripOpen);
  check('the pump turned in and out the same amount', Math.abs(cmd.driver.pumpTurns()) < 1e-6 && Math.abs(world.rotorTurns) < 1e-6);
  check('whole cycle takes a couple of minutes of sim time (incl. the 60 s read)', res.time > 120 && res.time < 400, `${res.time.toFixed(0)} s`);
  void run; void sim;
}
{
  // daily: two cycles in a row keep working, the old share falls again
  const env = fresh();
  const a = go(plan, env), b = go(plan.slice(plan.findIndex((c) => c.op === 'cart')), env);
  check('a second cycle (nozzle parked, cart at the station) works and mixes further', a.res.ok && b.res.ok && b.res.oldPct < a.res.oldPct * 0.5 + 1, `${a.res.oldPct.toFixed(1)} -> ${b.res.oldPct.toFixed(1)}`);
}

// --- what the simulator must refuse
const refused = (name: string, script: string, part: string) => { const r = go(script).res; check(`refuses: ${name}`, !r.ok && r.reason.includes(part), r.reason); };
refused('pump with the nozzle parked', 'pump in 5', 'parked');
refused('pump in the air (hand at rest holding nothing)', `${TAKE}\npump in 5`, 'not plugged');
refused('draw from the parking socket', `${TAKE}\npose park_in\npump in 5`, 'parking');
refused('push into the unit socket', `cart to unit\n${TAKE}\npose unit_above\npose unit_in\npump out 5`, 'unit socket');
refused('draw at the station socket', `cart to station\n${TAKE}\npose station_above\npose station_in\npump in 5`, 'station socket');
refused('push more than the tube holds (empty tube)', `cart to station\n${TAKE}\npose station_above\npose station_in\npump out 5`, 'ran dry');
refused('draw more than the tube holds', `cart to unit\n${TAKE}\npose unit_above\npose unit_in\npump in ${TUBE_ML + 5}`, 'tube is full');
refused('plug one step short (above the socket)', `cart to unit\n${TAKE}\npose unit_above\npump in 5`, 'not plugged');
refused('let go of the nozzle away from the parking socket', `${TAKE}\npose unit_above\ngripper open`, 'fall');
refused('drive with the nozzle in the hand', `${TAKE}\ncart to station`, 'nozzle');
refused('drive with the arm out of rest', `${TAKE}\npose park_above\n${PARK.split('\n').slice(0, 4).join('\n')}\ncart to station`, 'rest');
{
  // reach: poses that cannot be reached are caught at load time; a hand at the wrong place plugs nothing
  const env = fresh();
  const r = go(`${TAKE}\npose station_above\npose station_in\npump out 1`, env).res;   // cart still at the unit: the station is 1 m away
  check('refuses: station poses with the cart at the unit', !r.ok && r.reason.includes('not plugged'), r.reason);
}
{
  // the contact check really sees the arm hitting the cart: swing the hand down into the cart deck
  const { sim } = fresh();
  sim.setJointsKinematic({ A: 90, B: 60, C: 60, D: 0, E: 0, F: 13 });
  const w = worstContact(sim.model, sim.data);
  check('contact check sees the arm in the cart deck', w.depth < -0.001, `${w.names} ${(w.depth * 1000).toFixed(1)} mm`);
  const s2 = fresh(); const r = go('pose rest\npose park_above\npose unit_above\npose station_above', s2);
  check('moving between all the poses (cart at the unit) touches nothing', r.res.reason === '' || !r.res.reason.includes('touched'), r.res.reason);
}

// --- drivers and scene list
{
  const { sim } = fresh();
  sim.pump(5); sim.pump(-2);
  check('sim driver counts pump turns, reset clears them', sim.pumpTurns() === 3 && (sim.reset(), sim.pumpTurns() === 0));
  let msg = ''; try { new RealDriver().pump(); } catch (e) { msg = (e as Error).message; }
  check('real driver says it is not connected', msg.includes('not connected'));
}
check('water-sample scene is listed', SCENE_INFOS.some((s) => s.id === 'water-sample' && s.group === 'Tests'));
void STOPS;
if (fail) { console.error(`${fail} FAILED`); process.exit(1); }
console.log('all ok');
