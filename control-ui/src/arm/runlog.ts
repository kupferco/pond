// Logging of runs to Firebase (project pond-grow): trajectory in Storage, summary in Firestore.
// Nothing is written to disk or the repo. The Firebase web config comes from Hosting's reserved
// /__/firebase/init.json, so no keys live in the code; off Hosting (vite dev) logging reports itself as unavailable.
import { attemptSummary, type RunSummary } from './summary.ts';
import { gzipJson, trajectoryJson, type RunMeta } from './trajectory.ts';
import type { Attempt } from './attempt.ts';

export type { RunSummary };

interface Backend {
  db: import('firebase/firestore/lite').Firestore;
  storage: import('firebase/storage').FirebaseStorage;
  fs: typeof import('firebase/firestore/lite');
  st: typeof import('firebase/storage');
}

export class RunLog {
  private backend: Promise<Backend> | null = null;
  private chain: Promise<unknown> = Promise.resolve();
  logged = 0;
  failed = 0;
  lastError = '';
  pending = 0;

  private async load(): Promise<Backend> {
    const res = await fetch('/__/firebase/init.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('Firebase config not found (open the page on the Hosting site, and a web app must be registered in project pond-grow)');
    const config = await res.json();
    const [app, fs, st] = await Promise.all([import('firebase/app'), import('firebase/firestore/lite'), import('firebase/storage')]);
    const a = app.initializeApp(config, 'pond-runs');
    return { db: fs.getFirestore(a), storage: st.getStorage(a), fs, st };
  }

  private get(): Promise<Backend> {
    this.backend ??= this.load();
    this.backend.catch(() => { this.backend = null; }); // allow a retry on the next run
    return this.backend;
  }

  /** Queue a finished attempt for upload. Never throws; failures are counted in `failed` / `lastError`. */
  enqueue(a: Attempt, meta: RunMeta): void {
    this.pending++;
    this.chain = this.chain.then(async () => {
      try { await this.write(a, meta); this.logged++; }
      catch (e) { this.failed++; this.lastError = e instanceof Error ? e.message : String(e); }
      finally { this.pending--; }
    });
  }

  idle(): Promise<unknown> { return this.chain; }

  private async write(a: Attempt, meta: RunMeta) {
    const { db, storage, fs, st } = await this.get();
    const storagePath = `runs/${meta.batchId}/${meta.runId}.json.gz`;
    const blob = await gzipJson(trajectoryJson(a, meta));
    await st.uploadBytes(st.ref(storage, storagePath), blob, { contentType: 'application/gzip' });
    const summary = attemptSummary(a, meta, storagePath, blob.size);
    await fs.setDoc(fs.doc(db, 'runs', meta.runId), { ...summary, ts: fs.serverTimestamp() });
  }

  /** Most recent runs, newest first. */
  async recent(max = 300): Promise<Array<RunSummary & { tsMs: number }>> {
    const { db, fs } = await this.get();
    const snap = await fs.getDocs(fs.query(fs.collection(db, 'runs'), fs.orderBy('ts', 'desc'), fs.limit(max)));
    return snap.docs.map((d) => {
      const v = d.data() as RunSummary & { ts?: { toMillis(): number } };
      return { ...v, tsMs: v.ts?.toMillis?.() ?? 0 };
    });
  }
}

export function newRunId(): string {
  const b = new Uint8Array(10);
  crypto.getRandomValues(b);
  return Array.from(b, (x) => x.toString(36).padStart(2, '0')).join('').slice(0, 20);
}
