import test from "node:test";
import assert from "node:assert/strict";
import {
  hasValue, loadOne, withResource, readLimit,
  tenantAmounts, sumPositive, purchaseFee, salesCommission,
} from "./subject.mjs";

test("presence preserves zero, false, NaN and zero bigint", () => {
  for (const value of [0, false, NaN, 0n, "0", [], {}]) {
    assert.equal(hasValue(value), true);
  }
  for (const value of [null, undefined, ""]) {
    assert.equal(hasValue(value), false);
  }
});

test("a single loaded result still has an array contract", async () => {
  let calls = 0;
  assert.deepEqual(await loadOne(() => { calls++; return Promise.resolve(7); }), [7]);
  assert.equal(calls, 1);
});

test("loader errors retain identity", async () => {
  const failure = new Error("unavailable");
  await assert.rejects(loadOne(() => Promise.reject(failure)), error => error === failure);
});

test("resource release follows work on success", () => {
  const events = [];
  const resource = { release() { events.push("release"); } };
  assert.equal(withResource(resource, received => {
    assert.equal(received, resource);
    events.push("work");
    return 9;
  }), 9);
  assert.deepEqual(events, ["work", "release"]);
});

test("resource release follows work on failure and preserves the error", () => {
  const events = [];
  const failure = new Error("work failed");
  assert.throws(() => withResource({ release() { events.push("release"); } }, () => {
    events.push("work");
    throw failure;
  }), error => error === failure);
  assert.deepEqual(events, ["work", "release"]);
});

test("runtime input validation is required and zero is valid", () => {
  assert.equal(readLimit({ limit: 0 }), 0);
  assert.equal(readLimit({ limit: 12 }), 12);
  for (const payload of [null, undefined, {}, { limit: "5" }, { limit: false },
                         { limit: -1 }, { limit: 1.5 }, { limit: Infinity }]) {
    assert.throws(() => readLimit(payload), {
      name: "TypeError", message: "limit must be a non-negative integer",
    });
  }
});

test("tenant isolation, order and null handling are preserved", () => {
  const rows = [
    { id: "b", tenantId: "north", amount: 0 },
    { id: "hidden", tenantId: "south", amount: 99 },
    { id: "a", tenantId: "north", amount: null },
  ];
  assert.deepEqual(tenantAmounts(rows, "north"), [{ id: "b", amount: 0 }, { id: "a", amount: 0 }]);
  assert.deepEqual(tenantAmounts(rows, "missing"), []);
});

test("positive accumulation behavior is preserved", () => {
  assert.equal(sumPositive([]), 0);
  assert.equal(sumPositive([-3, 0, 2, 4, NaN]), 6);
  assert.equal(sumPositive([0.1, 0.2]), 0.1 + 0.2);
});

test("separate policy APIs stay available", () => {
  assert.equal(purchaseFee(100), 2);
  assert.equal(salesCommission(100), 2);
});
