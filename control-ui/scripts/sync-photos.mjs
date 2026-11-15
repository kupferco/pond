// Copies new or changed images and videos from the Drive "Online Gallery" folder into Cloud Storage.
// Every subfolder of it is a category (name as written in Drive); anything deeper belongs to its top-level subfolder's
// category, files directly in Online Gallery go to "Other". Nothing outside Online Gallery is read.
// Storage: photos/web/<id>.jpg + photos/thumb/<id>.jpg (images), photos/video/<id>.mp4 + photos/thumb/<id>.jpg (poster,
// videos, transcoded to H.264/AAC mp4 with ffmpeg so iPhone .mov plays everywhere), photos/index.json.
// Idempotent: a file is skipped when its Drive id is in the index with the same modifiedTime. Files removed from Drive
// are removed from the bucket; moved/renamed files and folders update without re-copying.
// Videos over MAX_VIDEO_MB are skipped with a log line. Other file types are ignored.
// Run:  node scripts/sync-photos.mjs   (see docs/notes/2026-11-14-photos.md)
//
// Env: GOOGLE_APPLICATION_CREDENTIALS (service account key file), PHOTOS_BUCKET (default pond-grow.firebasestorage.app),
//      POND_GALLERY_FOLDER_ID (preferred: Drive id of the Online Gallery folder, from its URL),
//      POND_GALLERY_FOLDER_PATH (fallback when no id is set; "/"-separated names, the first one being a shared drive
//      or a top-level folder; default "Pond 2.0/Images and Videos/Online Gallery"),
//      MAX_VIDEO_MB (default 200),
//      DRY_RUN=1 to only print what would happen.
import { google } from 'googleapis';
import { Storage } from '@google-cloud/storage';
import sharp from 'sharp';
import { spawn } from 'node:child_process';
import { mkdtemp, rm, readFile } from 'node:fs/promises';
import { createWriteStream } from 'node:fs';
import { pipeline } from 'node:stream/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const BUCKET = process.env.PHOTOS_BUCKET || 'pond-grow.firebasestorage.app';
const DRY = !!process.env.DRY_RUN;
const MAX_VIDEO = (Number(process.env.MAX_VIDEO_MB) || 200) * 1024 * 1024;
const VIDEO_PX = 1280;
const WEB_PX = 1600, THUMB_PX = 400;
const FOLDER_PATH = (process.env.POND_GALLERY_FOLDER_PATH || 'Pond 2.0/Images and Videos/Online Gallery').split('/').map(x => x.trim()).filter(Boolean);

// Works for shared drives and My Drive: every list/get passes supportsAllDrives; lists also include shared drive items.
const ALL_DRIVES = { supportsAllDrives: true, includeItemsFromAllDrives: true };
const q = v => v.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
const FOLDER = "mimeType='application/vnd.google-apps.folder' and trashed=false";

const auth = new google.auth.GoogleAuth({ scopes: ['https://www.googleapis.com/auth/drive.readonly'] });
const drive = google.drive({ version: 'v3', auth });
const bucket = new Storage().bucket(BUCKET);

async function findFolder() {
  const id = (process.env.POND_GALLERY_FOLDER_ID || '').trim();
  if (id) return id;
  const label = FOLDER_PATH.join(' / ');
  // First segment: a shared drive by that name, otherwise a top-level folder visible to the service account.
  const [first, ...rest] = FOLDER_PATH;
  const drives = (await drive.drives.list({ q: `name='${q(first)}'`, fields: 'drives(id)', pageSize: 10 })).data.drives || [];
  let parent, corpus;
  if (drives.length) {
    parent = drives[0].id; corpus = { corpora: 'drive', driveId: parent };
  } else {
    const r = await drive.files.list({ q: `${FOLDER} and name='${q(first)}'`, fields: 'files(id)', corpora: 'allDrives', ...ALL_DRIVES });
    if (!r.data.files?.length) throw new Error(`"${first}" (start of ${label}) is not visible to the service account. Share it (Viewer) or set POND_GALLERY_FOLDER_ID.`);
    parent = r.data.files[0].id; corpus = { corpora: 'allDrives' };
  }
  for (const name of rest) {
    const r = await drive.files.list({ q: `'${parent}' in parents and ${FOLDER} and name='${q(name)}'`, fields: 'files(id)', ...corpus, ...ALL_DRIVES });
    if (!r.data.files?.length) throw new Error(`Folder "${name}" not found on the path ${label}. Check the names or set POND_GALLERY_FOLDER_ID.`);
    if (r.data.files.length > 1) console.warn(`${r.data.files.length} folders named "${name}" on the path; using the first. Set POND_GALLERY_FOLDER_ID to be exact.`);
    parent = r.data.files[0].id;
  }
  return parent;
}

const MEDIA = "(mimeType contains 'image/' or mimeType contains 'video/')";
const FOLDER_MIME = 'application/vnd.google-apps.folder';

async function listChildren(folderId, extra) {
  const out = [];
  let pageToken;
  do {
    const r = await drive.files.list({
      q: `'${folderId}' in parents and trashed=false and ${extra}`,
      fields: 'nextPageToken,files(id,name,description,mimeType,size,modifiedTime,createdTime,imageMediaMetadata(time),videoMediaMetadata(durationMillis))',
      pageSize: 200, pageToken, ...ALL_DRIVES,
    });
    out.push(...(r.data.files || []));
    pageToken = r.data.nextPageToken;
  } while (pageToken);
  return out;
}

// Walks Online Gallery: each direct subfolder is a category; deeper folders fold into it.
async function listGallery(rootId) {
  const items = [], categories = [];
  for (const f of await listChildren(rootId, MEDIA)) items.push({ ...f, category: 'Other' });
  for (const c of await listChildren(rootId, `mimeType='${FOLDER_MIME}'`)) {
    categories.push(c.name);
    const stack = [c.id];
    while (stack.length) {
      const dir = stack.pop();
      for (const f of await listChildren(dir, MEDIA)) items.push({ ...f, category: c.name });
      for (const d of await listChildren(dir, `mimeType='${FOLDER_MIME}'`)) stack.push(d.id);
    }
  }
  if (items.some(f => f.category === 'Other') && !categories.includes('Other')) categories.push('Other');
  // Alphabetical (numeric-aware, so "Pond 2.0" < "Pond 10.0"); "Other" always last.
  categories.sort((a, b) => (a === 'Other') - (b === 'Other') || a.localeCompare(b, undefined, { numeric: true, sensitivity: 'base' }));
  return { items, categories };
}

function run(cmd, args) {
  return new Promise((res, rej) => {
    const p = spawn(cmd, args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let err = '';
    p.stderr.on('data', d => { err = (err + d).slice(-2000); });
    p.on('error', rej);
    p.on('close', c => c === 0 ? res() : rej(new Error(`${cmd} exited ${c}: ${err.trim().split('\n').pop()}`)));
  });
}

// Download to a temp file, transcode to H.264 mp4 (max 1280 px, faststart for seeking), grab a poster frame.
async function processVideo(f) {
  const dir = await mkdtemp(join(tmpdir(), 'pond-video-'));
  try {
    const src = join(dir, 'src'), mp4 = join(dir, 'out.mp4'), jpg = join(dir, 'poster.jpg');
    const res = await drive.files.get({ fileId: f.id, alt: 'media', supportsAllDrives: true }, { responseType: 'stream' });
    await pipeline(res.data, createWriteStream(src));
    const scale = `scale='min(${VIDEO_PX},iw)':'min(${VIDEO_PX},ih)':force_original_aspect_ratio=decrease:force_divisible_by=2`;
    await run('ffmpeg', ['-y', '-i', src, '-vf', scale, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '26', '-pix_fmt', 'yuv420p',
      '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', mp4]);
    await run('ffmpeg', ['-y', '-ss', '1', '-i', mp4, '-frames:v', '1', jpg]).catch(() => run('ffmpeg', ['-y', '-i', mp4, '-frames:v', '1', jpg]));
    const poster = sharp(await readFile(jpg));
    const info = await poster.metadata();
    const thumb = await poster.resize({ width: THUMB_PX, height: THUMB_PX, fit: 'inside', withoutEnlargement: true }).jpeg({ quality: 75 }).toBuffer();
    await bucket.upload(mp4, { destination: `photos/video/${f.id}.mp4`, metadata: { contentType: 'video/mp4', cacheControl: 'public, max-age=3600' } });
    await put(`photos/thumb/${f.id}.jpg`, thumb, 'image/jpeg');
    return { w: info.width, h: info.height };
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

// EXIF time looks like "2024:05:17 14:03:22"; fall back to the Drive creation time.
function takenDate(f) {
  const t = f.imageMediaMetadata?.time;
  const m = t && /^(\d{4}):(\d\d):(\d\d) (\d\d):(\d\d):(\d\d)$/.exec(t);
  return m ? `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}` : f.createdTime;
}

async function readIndex() {
  const file = bucket.file('photos/index.json');
  if ((await file.exists())[0]) return JSON.parse((await file.download())[0].toString('utf8'));
  return { photos: [] };
}

async function put(path, buf, contentType) {
  await bucket.file(path).save(buf, { contentType, metadata: { cacheControl: 'public, max-age=3600' } });
}

const old = await readIndex();
const known = new Map(old.photos.map(p => [p.id, p]));
const { items: files, categories } = await listGallery(await findFolder());
const photos = [];
let added = 0, updated = 0, skipped = 0, failed = 0, tooBig = 0;

for (const f of files) {
  const isVideo = f.mimeType.startsWith('video/');
  if (isVideo && Number(f.size || 0) > MAX_VIDEO) {
    console.log(`skip (over ${MAX_VIDEO / 1024 / 1024} MB): ${f.name}`);
    tooBig++;
    continue; // a previous copy, if any, is removed below
  }
  const prev = known.get(f.id);
  const meta = { id: f.id, type: isVideo ? 'video' : 'image', name: f.name, caption: f.description || '', category: f.category, taken: takenDate(f), modified: f.modifiedTime };
  if (prev && prev.modified === f.modifiedTime && prev.type === meta.type) {
    photos.push({ ...prev, name: meta.name, caption: meta.caption, category: meta.category }); // edits and moves don't need a re-copy
    skipped++;
    continue;
  }
  console.log(`${prev ? 'update' : 'add'} ${meta.type}: ${f.category} / ${f.name}`);
  if (DRY) { photos.push(meta); prev ? updated++ : added++; continue; }
  try {
    if (isVideo) {
      photos.push({ ...meta, ...(await processVideo(f)) });
    } else {
      const res = await drive.files.get({ fileId: f.id, alt: 'media', supportsAllDrives: true }, { responseType: 'arraybuffer' });
      const src = sharp(Buffer.from(res.data)).rotate(); // apply EXIF orientation
      const web = await src.clone().resize({ width: WEB_PX, height: WEB_PX, fit: 'inside', withoutEnlargement: true }).jpeg({ quality: 82, mozjpeg: true }).toBuffer({ resolveWithObject: true });
      const thumb = await src.clone().resize({ width: THUMB_PX, height: THUMB_PX, fit: 'inside', withoutEnlargement: true }).jpeg({ quality: 75 }).toBuffer();
      await put(`photos/web/${f.id}.jpg`, web.data, 'image/jpeg');
      await put(`photos/thumb/${f.id}.jpg`, thumb, 'image/jpeg');
      photos.push({ ...meta, w: web.info.width, h: web.info.height });
    }
    prev ? updated++ : added++;
  } catch (e) {
    console.error(`failed: ${f.name}: ${e.message}`);
    failed++;
    if (prev) photos.push(prev); // keep the old copy
  }
}

let removed = 0;
for (const p of old.photos) {
  if (photos.some(x => x.id === p.id)) continue;
  console.log(`remove: ${p.name}`);
  removed++;
  if (!DRY) await Promise.all([`photos/web/${p.id}.jpg`, `photos/thumb/${p.id}.jpg`, `photos/video/${p.id}.mp4`].map(n => bucket.file(n).delete({ ignoreNotFound: true })));
}

photos.sort((a, b) => (b.taken || '').localeCompare(a.taken || ''));
if (!DRY) await put('photos/index.json', Buffer.from(JSON.stringify({ updated: new Date().toISOString(), categories, photos })), 'application/json');
console.log(`${DRY ? '[dry run] ' : ''}added ${added}, updated ${updated}, unchanged ${skipped}, removed ${removed}, too big ${tooBig}, failed ${failed}; ${photos.length} items in ${categories.length} categories`);
if (failed) process.exitCode = 1;
