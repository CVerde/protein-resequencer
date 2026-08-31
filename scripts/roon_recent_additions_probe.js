#!/usr/bin/env node
"use strict";

const MODULE_ROOT = process.env.ROON_NODE_MODULES || "/home/pi/songr/node_modules";
const RoonApi = require(`${MODULE_ROOT}/node-roon-api`);
const RoonApiBrowse = require(`${MODULE_ROOT}/node-roon-api-browse`);
const RoonApiImage = require(`${MODULE_ROOT}/node-roon-api-image`);

function log(message, value) {
  const suffix = value === undefined ? "" : ` ${JSON.stringify(value)}`;
  process.stdout.write(`[${new Date().toISOString()}] ${message}${suffix}\n`);
}

function browse(service, options) {
  return new Promise((resolve, reject) => service.browse(options,
    (error, body) => error ? reject(new Error(String(error))) : resolve(body)));
}

function load(service, options) {
  return new Promise((resolve, reject) => service.load(options,
    (error, body) => error ? reject(new Error(String(error))) : resolve(body)));
}

function summarize(result) {
  return {
    list: result.list,
    items: (result.items || []).map(item => ({
      title: item.title, subtitle: item.subtitle, hint: item.hint,
      item_key: item.item_key, image_key: item.image_key,
    })),
  };
}

async function openLevel(service, hierarchy, itemKey, maxItems = 30) {
  const options = itemKey
    ? { hierarchy, item_key: itemKey }
    : { hierarchy, pop_all: true };
  const opened = await browse(service, options);
  const level = opened && opened.list ? opened.list.level : 0;
  const count = opened && opened.list
    ? Math.min(opened.list.count || maxItems, maxItems)
    : maxItems;
  return load(service, { hierarchy, level, offset: 0, count });
}

async function inspectLibrary(core) {
  const service = core.services.RoonApiBrowse;
  const root = await openLevel(service, "browse");
  log("Racine Roon", summarize(root));

  const library = (root.items || []).find(item =>
    String(item.title || "").toLocaleLowerCase().includes("library"));
  if (!library) throw new Error("entrée Library introuvable");

  const contents = await openLevel(service, "browse", library.item_key);
  log("Contenu de Library", summarize(contents));

  const albums = (contents.items || []).find(item =>
    String(item.title || "").toLocaleLowerCase().includes("albums"));
  if (!albums) throw new Error("entrée Albums introuvable");

  const albumContents = await openLevel(service, "browse", albums.item_key);
  log("Contenu de Library / Albums", summarize(albumContents));
}

const roon = new RoonApi({
  extension_id: "fr.cverde.protein-resequencer.daily-additions",
  display_name: "Protein Resequencer — Ajouts quotidiens",
  display_version: "0.1.0",
  publisher: "CVerde",
  email: "cverde@users.noreply.github.com",
  website: "https://github.com/CVerde/protein-resequencer",
  log_level: "none",
  core_paired: core => {
    log(`Core Roon autorisé : ${core.display_name}`);
    inspectLibrary(core)
      .catch(error => log(`Exploration Roon impossible : ${error.message}`));
  },
  core_unpaired: core => log(`Core Roon déconnecté : ${core.display_name}`),
});

roon.init_services({ required_services: [RoonApiBrowse, RoonApiImage] });
log("Extension démarrée ; autorisez-la dans Roon > Réglages > Extensions");
roon.start_discovery();

module.exports = { inspectLibrary, openLevel, summarize };
