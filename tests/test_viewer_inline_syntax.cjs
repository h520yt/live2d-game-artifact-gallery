"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

const root = path.resolve(__dirname, "..");

test("all four viewer inline scripts parse after bridge integration", () => {
  for (const game of ["azur_lane", "nikke", "reverse1999", "brown_dust2"]) {
    const file = path.join(root, game, "viewer", "index.html");
    const markup = fs.readFileSync(file, "utf8");
    const inlineScripts = [...markup.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)];
    assert.ok(inlineScripts.length >= 1, game + ": expected inline viewer script");
    for (const [index, match] of inlineScripts.entries()) {
      assert.doesNotThrow(() => new vm.Script(match[1], {
        filename: game + "/viewer/index.html#script" + index,
      }), game + ": malformed JavaScript");
    }
  }
});
