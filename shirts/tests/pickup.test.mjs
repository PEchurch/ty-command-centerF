// Run: node --test shirts/tests (Stripe is mocked; no network or keys needed)
import test from "node:test";
import assert from "node:assert/strict";
import { priceCart, validateCustomer, buildStripeParams, onRequestPost } from "../functions/api/checkout.js";

const cart = [
  { kind: "shirt", design: "d1", color: "Black", fit: "adult", size: "L", qty: 2 },
  { kind: "book", book: "b1", qty: 1 }
];
const pickup = { fulfillment: "pickup", name: "Pat Smith", email: "pat@example.com", phone: "(918) 555-0142" };
const ship = { name: "Pat Smith", email: "pat@example.com", addr1: "1 Main St", city: "Tahlequah", state: "OK", zip: "74464" };

test("pickup has no shipping charge; shipping is unchanged by default", () => {
  const p = priceCart(cart, "pickup"), s = priceCart(cart);
  assert.equal(p.shipping, 0);
  assert.equal(p.total, p.subtotal);
  assert.equal(s.shipping, 1599);
  assert.equal(s.total, s.subtotal + 1599);
});

test("pickup needs name, email and a phone number — but no address", () => {
  const c = validateCustomer(pickup);
  assert.equal(c.fulfillment, "pickup");
  assert.equal(c.addr1, "");
  for (const bad of [{ ...pickup, phone: "" }, { ...pickup, phone: "12345" }, { ...pickup, phone: "1".repeat(20) },
    { ...pickup, name: "" }, { ...pickup, email: "nope" }]) assert.throws(() => validateCustomer(bad));
});

test("shipping still enforces the continental U.S. address rules (default fulfillment)", () => {
  assert.equal(validateCustomer(ship).fulfillment, "ship");
  assert.throws(() => validateCustomer({ ...ship, state: "AK" }), /continental/i);
  assert.throws(() => validateCustomer({ ...ship, addr1: "" }), /address/i);
  // a client can't skip the address by sending junk for fulfillment
  assert.throws(() => validateCustomer({ ...pickup, fulfillment: "drone", addr1: "" }), /address/i);
});

test("pickup session: no shipping line, no ship-to, phone recorded", () => {
  const p = buildStripeParams({ cart: priceCart(cart, "pickup"), cust: validateCustomer(pickup), origin: "https://x.test", returnPath: "/" });
  assert.equal(p.get("line_items[2][quantity]"), null); // 2 lines only: shirt + book
  assert.equal(p.get("line_items[1][price_data][unit_amount]"), "1000");
  assert.equal([...p.keys()].some(k => k.startsWith("payment_intent_data[shipping]")), false);
  assert.equal(p.get("metadata[fulfillment]"), "pickup");
  assert.equal(p.get("metadata[phone]"), "(918) 555-0142");
  assert.equal(p.get("payment_intent_data[metadata][phone]"), "(918) 555-0142");
  assert.match(p.get("payment_intent_data[description]"), /LOCAL PICKUP/);
  assert.equal(p.get("metadata[ship_by]"), "November 20, 2026");
});

test("shipped session unchanged: shipping line + ship-to", () => {
  const p = buildStripeParams({ cart: priceCart(cart), cust: validateCustomer(ship), origin: "https://x.test", returnPath: "/" });
  assert.equal(p.get("line_items[2][price_data][unit_amount]"), "1599");
  assert.equal(p.get("payment_intent_data[shipping][address][state]"), "OK");
  assert.equal(p.get("metadata[fulfillment]"), "ship");
});

test("end to end: pickup order total excludes S&H", async () => {
  const real = globalThis.fetch, realNow = Date.now; let seen;
  globalThis.fetch = async (u, init) => { seen = init; return new Response(JSON.stringify({ url: "https://checkout.stripe.com/x" })); };
  Date.now = () => +new Date("2026-11-01T12:00:00-06:00");
  try {
    const r = await onRequestPost({ request: new Request("https://shop.example.com/api/checkout", { method: "POST", body: JSON.stringify({ items: cart, customer: pickup, returnPath: "/" }) }), env: { STRIPE_SECRET_KEY: "k" } });
    assert.equal(r.status, 200);
    assert.equal((await r.json()).total, 2 * 2000 + 1000);
    assert.equal(new URLSearchParams(seen.body).get("metadata[fulfillment]"), "pickup");
  } finally { globalThis.fetch = real; Date.now = realNow; }
});
