#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const SONGR_URL = process.env.SONGR_URL || "http://127.0.0.1:3333";
const SOCKET_CLIENT_PATH = process.env.SONGR_SOCKET_IO_CLIENT ||
  "/home/pi/songr/node_modules/socket.io-client";
const STATE_FILE = process.env.ROON_DAILY_REPORT_STATE ||
  "/home/pi/.local/state/protein-resequencer/roon-daily-report.json";
const PYTHON = process.env.PYTHON || "python3";
const PRINT_SCRIPT = path.join(__dirname, "print_daily_roon_report.py");
const ZONE_IDS = new Set((process.env.ROON_PRINT_ZONE_IDS || "")
  .split(",").map(value => value.trim()).filter(Boolean));
const CATALOG_CACHE_MS = 5 * 60 * 1000;
let catalogCache = null;
let catalogCachedAt = 0;
const musicBrainzCache = new Map();
let lastMusicBrainzRequestAt = 0;

function log(message) {
  process.stdout.write(`[${new Date().toISOString()}] ${message}\n`);
}

function parisParts(now = new Date()) {
  const parts = new Intl.DateTimeFormat("fr-FR", {
    timeZone: "Europe/Paris", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(now);
  return Object.fromEntries(parts.map(part => [part.type, part.value]));
}

function parisDate(now = new Date()) {
  const value = parisParts(now);
  return `${value.year}-${value.month}-${value.day}`;
}

function parisTime(now = new Date()) {
  const value = parisParts(now);
  return `${value.hour}h${value.minute}`;
}

function normalizeText(value) {
  return String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim().toLocaleLowerCase("fr-FR");
}

function artistParts(value) {
  return String(value || "").split(/\s*(?:\/|&|\bfeat(?:uring)?\.?\b|\bwith\b|\bavec\b)\s*/iu)
    .map(normalizeText).filter(Boolean);
}

function artistMatches(left, right) {
  const leftParts = artistParts(left);
  const rightParts = artistParts(right);
  return leftParts.some(part => rightParts.includes(part));
}

function trackKey(nowPlaying) {
  return [nowPlaying.artist, nowPlaying.album, nowPlaying.title].map(normalizeText).join("|");
}

function emptyState(date = parisDate()) {
  return { date, tracks: [], lastByZone: {} };
}

function readState() {
  try {
    const state = JSON.parse(fs.readFileSync(STATE_FILE, "utf8"));
    if (state.date && Array.isArray(state.tracks) && state.lastByZone) return state;
  } catch (_) {}
  return emptyState();
}

function writeState(state) {
  fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
  const temporary = `${STATE_FILE}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, JSON.stringify(state, null, 2) + "\n", "utf8");
  fs.renameSync(temporary, STATE_FILE);
}

function allowedEvent(data) {
  const item = data && data.now_playing;
  if (!item || item.state !== "playing") return false;
  if (!item.title || !item.album || !item.artist) return false;
  return !ZONE_IDS.size || ZONE_IDS.has(data.zone_id);
}

function findCatalogYear(index, nowPlaying) {
  if (Number.isInteger(nowPlaying.year)) return nowPlaying.year;
  const album = normalizeText(nowPlaying.album);
  const albums = index && Array.isArray(index.albums) ? index.albums : [];
  const match = albums.find(item => artistMatches(item.artist, nowPlaying.artist) &&
    normalizeText(item.title) === album);
  if (!match) return "";
  return match.originalReleaseYear || match.editionReleaseYear ||
    (match.originalReleaseDate && match.originalReleaseDate.year) ||
    (match.releaseDate && match.releaseDate.year) || "";
}

function findMusicBrainzYear(result, nowPlaying) {
  const wantedAlbum = normalizeText(nowPlaying.album);
  const groups = result && Array.isArray(result["release-groups"])
    ? result["release-groups"] : [];
  const match = groups.find(group => {
    const artists = Array.isArray(group["artist-credit"])
      ? group["artist-credit"].map(credit => credit.name || (credit.artist && credit.artist.name))
      : [];
    return Number(group.score || 0) >= 90 && normalizeText(group.title) === wantedAlbum &&
      artists.some(artist => artistMatches(artist, nowPlaying.artist));
  });
  const year = match && String(match["first-release-date"] || "").match(/^(\d{4})/);
  return year ? Number(year[1]) : "";
}

async function resolveMusicBrainzYear(nowPlaying, fetchImpl = fetch) {
  const key = `${normalizeText(nowPlaying.artist)}|${normalizeText(nowPlaying.album)}`;
  if (musicBrainzCache.has(key)) return musicBrainzCache.get(key);
  try {
    const searchArtist = String(nowPlaying.artist).split("/")[0].trim();
    const query = `releasegroup:"${String(nowPlaying.album).replaceAll('"', '\\"')}" AND ` +
      `artist:"${searchArtist.replaceAll('"', '\\"')}"`;
    const parameters = new URLSearchParams({ query, fmt: "json", limit: "5" });
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const throttle = Math.max(0, 1100 - (Date.now() - lastMusicBrainzRequestAt));
      if (throttle) await new Promise(resolve => setTimeout(resolve, throttle));
      lastMusicBrainzRequestAt = Date.now();
      const response = await fetchImpl(`https://musicbrainz.org/ws/2/release-group/?${parameters}`, {
        headers: { "User-Agent": "ProteinResequencer/1.0 (https://github.com/CVerde/protein-resequencer)" },
        signal: AbortSignal.timeout(8000),
      });
      if (response.ok) {
        const year = findMusicBrainzYear(await response.json(), nowPlaying);
        musicBrainzCache.set(key, year);
        return year;
      }
      if (![429, 503].includes(response.status) || attempt === 2) {
        throw new Error(`MusicBrainz HTTP ${response.status}`);
      }
      const retryAfter = Number(response.headers && response.headers.get("retry-after"));
      const delay = Number.isFinite(retryAfter) && retryAfter > 0
        ? retryAfter * 1000 : [2000, 5000][attempt];
      log(`MusicBrainz HTTP ${response.status}, nouvelle tentative dans ${delay / 1000}s`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  } catch (error) {
    log(`Année MusicBrainz indisponible : ${error.message}`);
    return "";
  }
}

async function resolveYear(nowPlaying, fetchImpl = fetch) {
  if (Number.isInteger(nowPlaying.year)) return nowPlaying.year;
  try {
    const now = Date.now();
    if (!catalogCache || now - catalogCachedAt >= CATALOG_CACHE_MS) {
      const response = await fetchImpl(`${SONGR_URL}/api/catalog/index`, {
        signal: AbortSignal.timeout(4000),
      });
      if (!response.ok) throw new Error(`catalogue HTTP ${response.status}`);
      catalogCache = await response.json();
      catalogCachedAt = now;
    }
    const songrYear = findCatalogYear(catalogCache, nowPlaying);
    return songrYear || await resolveMusicBrainzYear(nowPlaying, fetchImpl);
  } catch (error) {
    log(`Année Songr indisponible : ${error.message}`);
    return resolveMusicBrainzYear(nowPlaying, fetchImpl);
  }
}

function printReport(report) {
  return new Promise((resolve, reject) => {
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), "roon-report-"));
    const reportPath = path.join(directory, "report.json");
    fs.writeFileSync(reportPath, JSON.stringify(report), "utf8");
    const child = spawn(PYTHON, [PRINT_SCRIPT, reportPath], { stdio: "inherit" });
    child.once("error", error => { fs.rmSync(directory, { recursive: true, force: true }); reject(error); });
    child.once("exit", code => {
      fs.rmSync(directory, { recursive: true, force: true });
      code === 0 ? resolve() : reject(new Error(`impression terminée avec le code ${code}`));
    });
  });
}

async function rolloverIfNeeded(printImpl = printReport, now = new Date()) {
  const state = readState();
  const today = parisDate(now);
  if (state.date === today) return false;
  await printImpl(state);
  writeState(emptyState(today));
  log(`Compte rendu du ${state.date} imprimé (${state.tracks.length} titres)`);
  return true;
}

async function enrichMissingYears(fetchImpl = fetch) {
  const state = readState();
  let changed = false;
  const resolved = new Map();
  for (const track of state.tracks) {
    if (track.year) continue;
    const key = `${normalizeText(track.artist)}|${normalizeText(track.album)}`;
    if (!resolved.has(key)) resolved.set(key, await resolveYear(track, fetchImpl));
    const year = resolved.get(key);
    if (year) {
      track.year = year;
      changed = true;
    }
  }
  if (changed) {
    writeState(state);
    log("Années manquantes du rapport courant mises à jour");
  }
  return changed;
}

async function recordNowPlaying(data, fetchImpl = fetch, now = new Date()) {
  if (!allowedEvent(data)) return "ignored";
  const state = readState();
  const item = data.now_playing;
  const key = trackKey(item);
  if (state.lastByZone[data.zone_id] === key) return "duplicate";
  const year = await resolveYear(item, fetchImpl);
  state.tracks.push({
    time: parisTime(now), title: item.title, album: item.album,
    year: year || null, artist: item.artist,
    duration: Number.isFinite(Number(item.duration)) ? Number(item.duration) : null,
    zoneId: data.zone_id,
  });
  state.lastByZone[data.zone_id] = key;
  writeState(state);
  log(`Mémorisé : ${item.artist} — ${item.title} (${year || "année inconnue"})`);
  return "recorded";
}

function main() {
  let io;
  try { ({ io } = require(SOCKET_CLIENT_PATH)); }
  catch (error) { log(`Socket.IO introuvable : ${error.message}`); process.exit(1); }
  const socket = io(SONGR_URL, { reconnection: true, reconnectionDelay: 2000 });
  let queue = Promise.resolve();
  const enqueue = task => { queue = queue.then(task).catch(error => log(`Erreur : ${error.message}`)); };
  socket.on("connect", () => {
    log(`Connecté à Songr (${socket.id})`);
    enqueue(async () => {
      await rolloverIfNeeded();
      await enrichMissingYears();
    });
  });
  socket.on("disconnect", reason => log(`Déconnecté de Songr : ${reason}`));
  socket.on("connect_error", error => log(`Connexion Songr impossible : ${error.message}`));
  socket.on("now-playing-updated", data => enqueue(async () => {
    await rolloverIfNeeded();
    await recordNowPlaying(data);
  }));
  setInterval(() => enqueue(() => rolloverIfNeeded()), 10_000);
  setInterval(() => enqueue(() => enrichMissingYears()), 30 * 60 * 1000);
}

if (require.main === module) main();

module.exports = { allowedEvent, artistMatches, artistParts, emptyState, enrichMissingYears, findCatalogYear,
  findMusicBrainzYear, normalizeText, parisDate, parisTime, readState, recordNowPlaying,
  resolveMusicBrainzYear, resolveYear, rolloverIfNeeded, trackKey, writeState };
