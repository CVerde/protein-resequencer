#!/usr/bin/env node
"use strict";

const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const MODULE_ROOT = process.env.ROON_NODE_MODULES || "/home/pi/songr/node_modules";
const STATE_FILE = process.env.ROON_DAILY_ADDITIONS_STATE ||
  "/home/pi/.local/state/protein-resequencer/roon-daily-additions.json";
const PYTHON = process.env.PYTHON || "python3";
const PRINT_SCRIPT = path.join(__dirname, "print_daily_roon_additions.py");
const SCAN_INTERVAL_MS = Number(process.env.ROON_ADDITIONS_SCAN_INTERVAL_MS || 300_000);

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

function normalizeText(value) {
  return String(value || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim().toLocaleLowerCase("fr-FR");
}

function albumKey(album) {
  return `${normalizeText(album.artist)}|${normalizeText(album.title)}|${album.image_key || ""}`;
}

function emptyState() {
  return { initialized: false, known: {}, additions: [], printedDates: [] };
}

function readState() {
  try {
    const state = JSON.parse(fs.readFileSync(STATE_FILE, "utf8"));
    if (state && state.known && Array.isArray(state.additions) &&
        Array.isArray(state.printedDates)) return state;
  } catch (_) {}
  return emptyState();
}

function writeState(state) {
  fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
  const temporary = `${STATE_FILE}.${process.pid}.tmp`;
  fs.writeFileSync(temporary, JSON.stringify(state, null, 2) + "\n", "utf8");
  fs.renameSync(temporary, STATE_FILE);
}

function browse(service, options) {
  return new Promise((resolve, reject) => service.browse(options,
    (error, body) => error ? reject(new Error(String(error))) : resolve(body)));
}

function load(service, options) {
  return new Promise((resolve, reject) => service.load(options,
    (error, body) => error ? reject(new Error(String(error))) : resolve(body)));
}

function getImage(service, imageKey) {
  return new Promise((resolve, reject) => service.get_image(imageKey, {
    scale: "fit", width: 372, height: 372, format: "image/png",
  }, (error, contentType, image) => error ? reject(new Error(String(error))) :
    resolve({ contentType, image })));
}

async function listAlbums(core) {
  const service = core.services.RoonApiBrowse;
  const opened = await browse(service, { hierarchy: "albums", pop_all: true,
    multi_session_key: "protein-resequencer-additions" });
  const list = opened && opened.list;
  if (!list) throw new Error("Roon n'a pas renvoyé la liste Albums");
  const albums = [];
  for (let offset = 0; offset < list.count; offset += 100) {
    const page = await load(service, { hierarchy: "albums", level: list.level,
      offset, count: Math.min(100, list.count - offset),
      multi_session_key: "protein-resequencer-additions" });
    for (const item of page.items || []) {
      if (!item.title || !item.subtitle) continue;
      albums.push({ title: item.title, artist: item.subtitle,
        image_key: item.image_key || null, year: null });
    }
  }
  return albums;
}

function updateLibrary(state, albums, now = new Date()) {
  const current = {};
  const added = [];
  for (const album of albums) {
    const key = albumKey(album);
    if (!key || key === "|") continue;
    current[key] = album;
    if (state.initialized && !state.known[key]) {
      const entry = { ...album, detectedDate: parisDate(now),
        detectedAt: now.toISOString() };
      state.additions.push(entry);
      added.push(entry);
    }
  }
  state.known = current;
  state.initialized = true;
  return added;
}

function datesDue(state, now = new Date()) {
  const parts = parisParts(now);
  if (`${parts.hour}:${parts.minute}` < "00:05") return [];
  const today = parisDate(now);
  return state.printedDates.includes(today) ? [] : [today];
}

function runPrinter(reportPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(PYTHON, [PRINT_SCRIPT, reportPath], { stdio: "inherit" });
    child.once("error", reject);
    child.once("exit", code => code === 0 ? resolve() :
      reject(new Error(`impression terminée avec le code ${code}`)));
  });
}

async function printDate(core, state, date, printImpl = runPrinter) {
  const albums = state.additions.filter(item => !item.printedAt);
  if (!albums.length) return false;
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "roon-additions-"));
  try {
    const payload = { date, albums: [] };
    for (let index = 0; index < albums.length; index += 1) {
      const album = { ...albums[index] };
      if (album.image_key) {
        try {
          const result = await getImage(core.services.RoonApiImage, album.image_key);
          album.cover = path.join(directory, `cover-${index}.png`);
          fs.writeFileSync(album.cover, result.image);
        } catch (error) {
          log(`Pochette indisponible pour ${album.artist} — ${album.title} : ${error.message}`);
        }
      }
      payload.albums.push(album);
    }
    const reportPath = path.join(directory, "report.json");
    fs.writeFileSync(reportPath, JSON.stringify(payload), "utf8");
    await printImpl(reportPath, payload);
    return true;
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}

async function printDue(core, state, now = new Date(), printImpl = runPrinter) {
  for (const date of datesDue(state, now)) {
    const printed = await printDate(core, state, date, printImpl);
    if (printed) {
      const printedAt = now.toISOString();
      for (const album of state.additions) {
        if (!album.printedAt) album.printedAt = printedAt;
      }
    }
    state.printedDates.push(date);
    writeState(state);
    if (printed) log(`Ticket des ajouts du ${date} imprimé`);
    else log(`Aucun ajout à imprimer pour le ${date}`);
  }
}

async function cycle(core, now = new Date(), printImpl = runPrinter) {
  const state = readState();
  const albums = await listAlbums(core);
  const added = updateLibrary(state, albums, now);
  writeState(state);
  if (added.length) log(`${added.length} nouvel album détecté` + (added.length > 1 ? "s" : ""));
  else log(`Bibliothèque vérifiée : ${albums.length} albums`);
  await printDue(core, state, now, printImpl);
}

function main() {
  const RoonApi = require(`${MODULE_ROOT}/node-roon-api`);
  const RoonApiBrowse = require(`${MODULE_ROOT}/node-roon-api-browse`);
  const RoonApiImage = require(`${MODULE_ROOT}/node-roon-api-image`);
  let scanTimer = null;
  let printTimer = null;
  let queue = Promise.resolve();
  const enqueueScan = (core) => {
    queue = queue.then(() => cycle(core)).catch(error => log(`Erreur : ${error.message}`));
  };
  const enqueuePrint = (core) => {
    queue = queue.then(async () => {
      const state = readState();
      await printDue(core, state);
    }).catch(error => log(`Erreur : ${error.message}`));
  };
  const roon = new RoonApi({
    extension_id: "fr.cverde.protein-resequencer.daily-additions",
    display_name: "Protein Resequencer — Ajouts quotidiens",
    display_version: "1.0.0", publisher: "CVerde",
    email: "cverde@users.noreply.github.com",
    website: "https://github.com/CVerde/protein-resequencer", log_level: "none",
    core_paired: core => {
      log(`Core Roon autorisé : ${core.display_name}`);
      if (scanTimer) clearInterval(scanTimer);
      if (printTimer) clearInterval(printTimer);
      enqueueScan(core);
      scanTimer = setInterval(() => enqueueScan(core), SCAN_INTERVAL_MS);
      printTimer = setInterval(() => enqueuePrint(core), 10_000);
    },
    core_unpaired: core => {
      log(`Core Roon déconnecté : ${core.display_name}`);
      if (scanTimer) clearInterval(scanTimer);
      if (printTimer) clearInterval(printTimer);
      scanTimer = null;
      printTimer = null;
    },
  });
  roon.init_services({ required_services: [RoonApiBrowse, RoonApiImage] });
  log("Service démarré ; surveillance des ajouts Roon active");
  roon.start_discovery();
}

if (require.main === module) main();

module.exports = { albumKey, cycle, datesDue, emptyState, listAlbums, normalizeText,
  parisDate, parisParts, printDue, readState, updateLibrary, writeState };
