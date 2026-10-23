// Run: node --test shirts/tests   (Stripe is mocked; no network or keys needed)
import test from "node:test";
import assert from "node:assert/strict";
import { priceCart, validateCustomer, onRequestPost } from "../functions/api/checkout.js";

const cust = { name: "Pat Smith", email: "pat@example.com", addr1: "1 Main St", city: "Tahlequah", state: "OK", zip: "74464" };
const cart = [
  { kind: "shirt", design: "d1", color: "Black", fit: "adult", size: "L", qty: 2 },
  { kind: "shirt", design: "d4", color: "White", fit: "youth", size: "M", qty: 1 },
  { kind: "book", book: "b1", qty: 1 }
];

test("prices shirts, books and tiered shipping in cents", () => {
  const c = priceCart(cart);
  assert.equal(c.subtotal, 2 * 2000 + 1500 + 1000);
  assert.equal(c.count, 4);
  assert.equal(c.shipping, 1599);
  assert.equal(c.total, 6500 + 1599);
  const shipFor = n => priceCart([{ kind: "book", book: "b1", qty: n }]).shipping;
  assert.deepEqual([1, 2, 3, 4, 5, 9].map(shipFor), [899, 1199, 1599, 1599, 1799, 1799]);
});

test("orders are capped at 10 items", () => {
  assert.equal(priceCart([{ kind: "book", book: "b1", qty: 10 }]).count, 10);
  assert.throws(() => priceCart([{ kind: "book", book: "b1", qty: 11 }]), /limited to 10.*info@tygwy\.art/);
  assert.throws(() => priceCart([{ kind: "book", book: "b1", qty: 6 }, { kind: "book", book: "b2", qty: 5 }]), /limited to 10/);
});

test("client-supplied prices are ignored", () => {
  const c = priceCart([{ kind: "shirt", design: "d1", color: "Black", fit: "adult", size: "L", qty: 1, price: 1, cents: 1 }]);
  assert.equal(c.subtotal, 2000);
});

test("rejects bad selections and quantities", () => {
  for (const bad of [
    [{ kind: "shirt", design: "d1", color: "Red", fit: "adult", size: "L", qty: 1 }],
    [{ kind: "shirt", design: "d1", color: "Black", fit: "youth", size: "XL", qty: 1 }],
    [{ kind: "shirt", design: "nope", color: "Black", fit: "adult", size: "L", qty: 1 }],
    [{ kind: "book", book: "zzz", qty: 1 }],
    [{ kind: "book", book: "b1", qty: 0 }],
    [{ kind: "book", book: "b1", qty: 21 }],
    [{ kind: "book", book: "b1", qty: -3 }],
    [{ kind: "book", book: "b1", qty: "2" }],
    []
  ]) assert.throws(() => priceCart(bad));
});

test("continental U.S. only", () => {
  assert.equal(validateCustomer(cust).state, "OK");
  for (const state of ["AK", "HI", "PR", "GU", "AA", ""]) assert.throws(() => validateCustomer({ ...cust, state }), /continental|address/i);
  assert.throws(() => validateCustomer({ ...cust, zip: "ABCDE" }));
  assert.throws(() => validateCustomer({ ...cust, email: "nope" }));
});

function withClock(iso, fn) {
  const real = Date.now; Date.now = () => +new Date(iso);
  return Promise.resolve(fn()).finally(() => { Date.now = real; });
}
const req = (body) => new Request("https://shop.example.com/api/checkout", { method: "POST", body: JSON.stringify(body) });

test("closed after the deadline, not yet open before the start", async () => {
  await withClock("2026-11-14T00:30:00-06:00", async () => {
    const r = await onRequestPost({ request: req({ items: cart, customer: cust }), env: { STRIPE_SECRET_KEY: "sk_test_x" } });
    assert.equal(r.status, 403);
  });
  await withClock("2026-10-01T12:00:00-05:00", async () => {
    const r = await onRequestPost({ request: req({ items: cart, customer: cust }), env: { STRIPE_SECRET_KEY: "sk_test_x" } });
    assert.equal(r.status, 403);
  });
});

test("during the sale: sends the right session to Stripe and returns its URL", async () => {
  const realFetch = globalThis.fetch; let seen;
  globalThis.fetch = async (url, init) => { seen = { url, init }; return new Response(JSON.stringify({ url: "https://checkout.stripe.com/c/pay/cs_test_123" }), { status: 200 }); };
  try {
    await withClock("2026-11-01T12:00:00-06:00", async () => {
      const r = await onRequestPost({ request: req({ items: cart, customer: cust, returnPath: "/" }), env: { STRIPE_SECRET_KEY: "sk_test_x" } });
      assert.equal(r.status, 200);
      const out = await r.json();
      assert.equal(out.url, "https://checkout.stripe.com/c/pay/cs_test_123");
      assert.equal(out.total, 8099);
    });
    assert.equal(seen.url, "https://api.stripe.com/v1/checkout/sessions");
    assert.equal(seen.init.headers.Authorization, "Bearer sk_test_x");
    const p = new URLSearchParams(seen.init.body);
    assert.equal(p.get("mode"), "payment");
    assert.equal(p.get("line_items[0][price_data][unit_amount]"), "2000");
    assert.equal(p.get("line_items[0][quantity]"), "2");
    assert.equal(p.get("line_items[0][price_data][product_data][name]"), "Cherokee Nation — Black — Adult Unisex L");
    assert.equal(p.get("line_items[3][price_data][unit_amount]"), "1599");           // shipping line
    assert.equal(p.get("payment_intent_data[shipping][address][state]"), "OK");
    assert.equal(p.get("payment_intent_data[shipping][address][country]"), "US");
    assert.equal(p.get("metadata[ship_by]"), "November 20, 2026");
    assert.equal(p.get("success_url"), "https://shop.example.com/?paid=1");
    assert.equal(p.get("customer_email"), "pat@example.com");
  } finally { globalThis.fetch = realFetch; }
});

test("return path can't redirect off-site", async () => {
  const realFetch = globalThis.fetch; let seen;
  globalThis.fetch = async (u, init) => { seen = init; return new Response(JSON.stringify({ url: "https://checkout.stripe.com/x" })); };
  try {
    await withClock("2026-11-01T12:00:00-06:00", async () => {
      await onRequestPost({ request: req({ items: cart, customer: cust, returnPath: "//evil.com/x" }), env: { STRIPE_SECRET_KEY: "k" } });
    });
    assert.equal(new URLSearchParams(seen.body).get("success_url"), "https://shop.example.com/?paid=1");
  } finally { globalThis.fetch = realFetch; }
});

test("return links use the public site (tygwy.art/flash) but never an unknown origin", async () => {
  const realFetch = globalThis.fetch; const seen = [];
  globalThis.fetch = async (u, init) => { seen.push(new URLSearchParams(init.body).get("success_url")); return new Response(JSON.stringify({ url: "https://checkout.stripe.com/x" })); };
  const mk = origin => new Request("https://proj.pages.dev/api/checkout", { method: "POST", headers: { Origin: origin }, body: JSON.stringify({ items: cart, customer: cust, returnPath: "/flash/" }) });
  try {
    await withClock("2026-11-01T12:00:00-06:00", async () => {
      await onRequestPost({ request: mk("https://tygwy.art"), env: { STRIPE_SECRET_KEY: "k" } });
      await onRequestPost({ request: mk("https://evil.example"), env: { STRIPE_SECRET_KEY: "k" } });
    });
    assert.deepEqual(seen, ["https://tygwy.art/flash/?paid=1", "https://proj.pages.dev/flash/?paid=1"]);
  } finally { globalThis.fetch = realFetch; }
});

test("Stripe failure is reported without leaking details", async () => {
  const realFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({ error: { message: "secret detail" } }), { status: 401 });
  try {
    await withClock("2026-11-01T12:00:00-06:00", async () => {
      const r = await onRequestPost({ request: req({ items: cart, customer: cust }), env: { STRIPE_SECRET_KEY: "k" } });
      assert.equal(r.status, 502);
      assert.ok(!(await r.text()).includes("secret detail"));
    });
  } finally { globalThis.fetch = realFetch; }
});
