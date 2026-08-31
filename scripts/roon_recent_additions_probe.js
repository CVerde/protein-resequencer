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

async function inspectHierarchy(core, hierarchy) {
  const service = core.services.RoonApiBrowse;
  const opened = await browse(service, { hierarchy, pop_all: true });
  const level = opened && opened.list ? opened.list.level : 0;
  const count = opened && opened.list ? Math.min(opened.list.count || 100, 300) : 100;
  const result = await load(service, { hierarchy, level, offset: 0, count });
  log(`Hiérarchie Roon ${hierarchy}`, {
    list: result.list,
    items: (result.items || []).map(item => ({
      title: item.title, subtitle: item.subtitle, hint: item.hint,
      item_key: item.item_key, image_key: item.image_key,
    })),
  });
}

const roon = new RoonApi({
  extension_id: "fr.cverde.protein-resequencer.daily-additions",
  display_name: "Protein Resequencer — Ajouts quotidiens",
  display_version: "0.1.0",
  publisher: "CVerde",
  website: "https://github.com/CVerde/protein-resequencer",
  log_level: "none",
  core_paired: core => {
    log(`Core Roon autorisé : ${core.display_name}`);
    Promise.all([inspectHierarchy(core, "browse"), inspectHierarchy(core, "albums")])
      .catch(error => log(`Exploration Roon impossible : ${error.message}`));
  },
  core_unpaired: core => log(`Core Roon déconnecté : ${core.display_name}`),
});

roon.init_services({ required_services: [RoonApiBrowse, RoonApiImage] });
log("Extension démarrée ; autorisez-la dans Roon > Réglages > Extensions");
roon.start_discovery();

module.exports = { inspectHierarchy };
