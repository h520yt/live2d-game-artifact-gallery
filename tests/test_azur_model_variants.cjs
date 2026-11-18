"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { test } = require("node:test");

const root = path.resolve(__dirname, "..");
const manifest = JSON.parse(fs.readFileSync(
  path.join(root, "azur_lane/viewer/manifest.json"), "utf8"
));
const variants = require(path.join(root, "azur_lane/viewer/model_variants.js"));

test("Azur Lane 60 model files form 54 unique skin cards", () => {
  const grouped = variants.groupModels(manifest.models);
  assert.equal(manifest.models.length, 60);
  assert.equal(grouped.length, 54);
  const pairs = grouped.filter((group) => group.variants.length === 2);
  assert.equal(pairs.length, 6);
  assert.deepEqual(pairs.map((group) => group.name).sort(), [
    "chaijun_4",
    "jialisuoniye_3",
    "ougen_6",
    "qiye_7",
    "shengluyisi_2",
    "sitelasibao_2",
  ]);
  assert.equal(grouped.reduce((sum, group) => sum + group.variants.length, 0), 60);
  for (const group of pairs) {
    assert.deepEqual(group.variants.map((model) => model.name), [
      group.name,
      group.name + "_hx",
    ]);
  }
});

test("version filtering can open a matching secondary model", () => {
  const grouped = variants.groupModels(manifest.models);
  const skin = grouped.find((entry) => entry.name === "shengluyisi_2");
  assert.ok(skin);
  assert.equal(variants.preferredModel(skin).name, "shengluyisi_2");
  assert.equal(variants.preferredModel(skin, "1").name, "shengluyisi_2_hx");
  assert.equal(variants.preferredModel(skin, "2").name, "shengluyisi_2");
  assert.ok(skin.variants.some((model) => String(model.ver) === "1"));
});

test("direct links to _hx remain addressable after grouping", () => {
  const grouped = variants.groupModels(manifest.models);
  const base = variants.groupForModel(grouped, "qiye_7");
  const hx = variants.groupForModel(grouped, "qiye_7_hx");
  assert.strictEqual(base, hx);
  assert.equal(hx.variants.length, 2);
  assert.equal(variants.preferredModel(hx).name, "qiye_7");
});

test("stray or mismatched HX models are never silently merged", () => {
  const testModels = [
    { name: "sample_1", id: 1, en: "Same Skin", ver: 2 },
    { name: "sample_1_hx", id: 2, en: "Other Skin", ver: 2 },
    { name: "orphan_1_hx", id: 3, en: "Orphan", ver: 2 },
  ];
  const groups = variants.groupModels(testModels);
  assert.equal(groups.length, 3);
  assert.ok(groups.every((group) => group.variants.length === 1));
});

test("native viewer grid uses grouped records and exposes variant selector", () => {
  const page = fs.readFileSync(
    path.join(root, "azur_lane/viewer/index.html"), "utf8"
  );
  assert.ok(page.includes('<script src="model_variants.js"></script>'));
  assert.match(page, /modelGroups\s*=\s*AzurModelVariants\.groupModels\(manifest\.models\)/);
  assert.match(page, /const models = modelGroups/);
  assert.ok(page.includes("l2d-variant-select"));
  assert.ok(page.includes("renderVariantSelector(i)"));
  assert.ok(page.includes("selectRole: (name) =>"));
  assert.ok(page.includes("selectedModelIndex = -1"));
});
