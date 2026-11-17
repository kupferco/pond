// Sag of the track pipe under the cart (OpenPocket #282, owner answers Q1 and Q6). Pure maths.
// Q1: the thinnest standard PVC pipe that will not bend; 32 mm OD is the choice, flag whether the standard 25 mm would do.
// Q6: the pipe runs are held in the middle (spine brackets at x = 0), so the middle is the stiffest and the sag is at the run ends, towards the corners.
// Model: from the bracket the run is a CANTILEVER to the point where the cart stands; the cart's weight acts on the pipe it rides (one pipe, worst case).
// Wall thicknesses are ASSUMED standard sizes (check the datasheet of the pipe that is bought): 32 x 1.8 (UK solvent weld waste / 3 bar metric), 25 x 1.5.
export const E_SHORT_MPA = 3000;      // PVC-U short term modulus, about 3 GPa
export const E_CREEP_MPA = 1000;      // after a year or more under load PVC-U creeps to about a third (design value 1 GPa for long loads)
export const G = 9.81;
export interface Pipe { name: string; od: number; wall: number }
export const PIPES: Pipe[] = [{ name: '32 mm PVC (1.8 wall)', od: 32, wall: 1.8 }, { name: '32 mm PVC (3.0 wall, pressure)', od: 32, wall: 3 }, { name: '25 mm PVC (1.5 wall)', od: 25, wall: 1.5 }, { name: '25 mm PVC (2.5 wall, pressure)', od: 25, wall: 2.5 }];
export const I_MM4 = (p: Pipe) => (Math.PI / 64) * (p.od ** 4 - (p.od - 2 * p.wall) ** 4);
/** Tip deflection (mm) of a cantilever of length L (mm) with a load F (N) at the end: F L^3 / (3 E I). */
export const cantileverSag = (p: Pipe, lMm: number, fN: number, eMpa: number) => (fN * lMm ** 3) / (3 * eMpa * I_MM4(p));
/** Deflection (mm) of a beam fixed at one end and guided (no rotation) at the other, load F at the free end of a span L: F L^3 / (12 E I): the leg end held square by its joint ring. */
export const guidedSag = (p: Pipe, lMm: number, fN: number, eMpa: number) => (fN * lMm ** 3) / (12 * eMpa * I_MM4(p));
/** Cart weight (kg, plan section 3) carried by the pipe it rides on, with the arm's pull in use adding to it: weightN = mass x g x dynamic factor. */
export const CART_KG = 3, DYNAMIC = 1.5;
export const LOAD_N = CART_KG * G * DYNAMIC;
/** Allowed sag at the cart (mm): the wheel rows (76 mm apart) and the bore clearance (4 mm) must still follow the pipe: stay within 2 mm. */
export const SAG_LIMIT_MM = 2;
/** The track in the Transplant layout: legs 580 apart, corner radius 150, bracket at the middle of each run. */
export const LEGS_MM = 580, CORNER_R_MM = 150;
export const RUN_HALF_STRAIGHT_MM = LEGS_MM / 2 - CORNER_R_MM;   // 140: from the bracket to where the straight run ends and the bend starts
export const RUN_HALF_TO_LEG_MM = LEGS_MM / 2;                    // 290: from the bracket to the leg, the pessimistic reach (the bend stiffness is ignored)
export interface SagRow { pipe: string; spanMm: number; case: string; shortMm: number; creepMm: number; ok: boolean }
export function sagTable(loadN = LOAD_N): SagRow[] {
  const rows: SagRow[] = [];
  for (const p of PIPES) for (const [span, label] of [[RUN_HALF_STRAIGHT_MM, 'cart at the end of the straight run'], [RUN_HALF_TO_LEG_MM, 'cart at the corner, whole run as a cantilever']] as const) {
    const shortMm = cantileverSag(p, span, loadN, E_SHORT_MPA), creepMm = cantileverSag(p, span, loadN, E_CREEP_MPA);
    rows.push({ pipe: p.name, spanMm: span, case: label, shortMm, creepMm, ok: creepMm <= SAG_LIMIT_MM });
  }
  return rows;
}
/** Longest cantilever (mm) that keeps the sag at the cart within the limit for this pipe and load (long term modulus by default). */
export const maxCantileverMm = (p: Pipe, fN = LOAD_N, eMpa = E_CREEP_MPA, limitMm = SAG_LIMIT_MM) => Math.cbrt((3 * eMpa * I_MM4(p) * limitMm) / fN);
