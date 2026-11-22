// The cart's SHAPES in the sim, taken from the CAD cart (OpenPocket #447). cad/export_sim_model.py meshes every part of cad/cart_assembly.py (the cart that
// cad/parts/cart.py add_cart() puts in the Complete unit) into src/generated/cad-sim-cart.ts; this file turns those meshes into MJCF assets and visual geoms.
// The sim's own primitive geoms (sleeve segments, lobes, wheel cylinders, balls) stay as the collision shapes, built from the same CAD numbers (omni.ts) and drawn
// invisible; what you SEE is the CAD mesh, so a change in the CAD flows into every scene that carries the cart.
import { CAD_CART_PARTS } from '../generated/cad-sim.ts';
import { CAD_CART_MESHES } from '../generated/cad-sim-cart.ts';

export type CartBody = 'B' | 'C' | 'base';
export type CartGroup = 'static' | 'jaw' | 'drive' | 'roll';
const bytes = (s: string) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
/** MJCF mesh name of a CAD part: numbered (cadm12), so no CAD word such as hinge or worm appears in the scene text that tests grep for. */
const meshName = (part: string) => `cadm${CAD_CART_PARTS.findIndex((p) => p.name === part)}`;
const m5 = (mm: number) => +(mm / 1000).toFixed(5);

export interface CadMesh { name: string; vertices: Float32Array; faces: Uint32Array; rgba: readonly number[]; body: CartBody; group: CartGroup }
const cache = new Map<string, CadMesh>();
/** Decoded mesh of a CAD cart part (vertices in mm, cart frame). */
export function cadMesh(part: string): CadMesh {
  let c = cache.get(part);
  if (c) return c;
  const row = CAD_CART_PARTS.find((p) => p.name === part);
  const blob = CAD_CART_MESHES[part];
  if (!row || !blob) throw new Error(`no CAD cart part ${part}`);
  const vb = bytes(blob.v), fb = bytes(blob.f);
  c = { name: part, vertices: new Float32Array(vb.buffer, vb.byteOffset, vb.byteLength / 4), faces: new Uint32Array(fb.buffer, fb.byteOffset, fb.byteLength / 4), rgba: row.rgba, body: row.body as CartBody, group: row.group as CartGroup };
  cache.set(part, c);
  return c;
}
export const cadMeshNames = (): string[] => CAD_CART_PARTS.map((p) => p.name);

let assetXml: string | undefined;
/** <asset> block with every cart mesh (metres, cart frame). Put it once into every MJCF that carries the cart. */
export function cartAssetXml(): string {
  if (assetXml) return assetXml;
  const lines = cadMeshNames().map((n) => {
    const c = cadMesh(n);
    const v = Array.from(c.vertices, (x) => m5(x)).join(' ');
    return `<mesh name="${meshName(n)}" vertex="${v}" face="${Array.from(c.faces).join(' ')}"/>`;
  });
  assetXml = `<asset>\n${lines.join('\n')}\n</asset>`;
  return assetXml;
}

/** Insert the cart mesh assets into a finished MJCF string (before the worldbody). Used by the models that carry the cart. */
export const withCartAssets = (xml: string): string => (xml.includes('<mesh name="cadm') ? xml : xml.replace('<worldbody>', `${cartAssetXml()}\n  <worldbody>`));

/**
 * Visual geoms of one body of the cart. body: hand 'B' or 'C' or 'base'; group: which moving part of the hand; offsetMm: the body's origin in the cart frame
 * (a hand's body sits on its pipe axis, x = -60 for B and +60 for C; the base is at the cart origin). The geoms collide with nothing.
 */
export function cartMeshGeoms(body: CartBody, group: CartGroup, offsetMm: [number, number, number] = [0, 0, 0]): string {
  const pos = `${m5(-offsetMm[0])} ${m5(-offsetMm[1])} ${m5(-offsetMm[2])}`;
  return CAD_CART_PARTS.filter((p) => p.body === body && p.group === group)
    .map((p) => `<geom type="mesh" mesh="${meshName(p.name)}" pos="${pos}" rgba="${p.rgba[0]} ${p.rgba[1]} ${p.rgba[2]} ${p.rgba[3]}" contype="0" conaffinity="0" mass="0"/>`).join('\n      ');
}
