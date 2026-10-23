/*
 * POST /api/checkout  — creates a Stripe Checkout Session and returns { url }.
 *
 * The browser only sends WHAT was ordered (ids, sizes, quantities) and WHO it ships to.
 * Prices, shipping, the sale window and the continental-US rule all live HERE, so they
 * can't be changed from the browser. Keep CATALOG / SHIPPING_TIERS in sync with CONFIG
 * in index.html (the page's totals are only an estimate; Stripe charges what this computes).
 *
 * Needs one secret: STRIPE_SECRET_KEY (Cloudflare Pages → Settings → Variables and Secrets).
 * Runs on Cloudflare Pages Functions; no dependencies (talks to Stripe's REST API directly).
 */

const SALE = { starts: "2026-10-22T00:00:00-05:00", ends: "2026-11-13T23:59:00-06:00" };
const SHIPS_BY_LABEL = "November 20, 2026";   // 1 week after the sale ends

// cents
const CATALOG = {
  colors: ["Black", "White"],
  fits: {
    youth: { label: "Youth",        price: 1500, sizes: ["S", "M", "L"] },
    adult: { label: "Adult Unisex", price: 2000, sizes: ["S", "M", "L", "XL", "2XL"] }
  },
  designs: { d1: "Cherokee Nation", d2: "Cherokee", d3: "1st Americans", d4: "Yawnsee", d5: "Yo-na" },
  books:   { b1: { title: "1st American: Cherokee", price: 1000 }, b2: { title: "Forest Relatives", price: 1200 } }
};

// USPS Ground Advantage from Tahlequah, OK 74464. Flat rate per order: [max total items, cents]. 5+ is a starting rate.
const SHIPPING_TIERS = [[1, 899], [2, 1199], [4, 1599], [Infinity, 1799]];

const MAX_QTY_PER_LINE = 20, MAX_LINES = 40;
const MAX_ITEMS_PER_ORDER = 10;   // bigger orders need a custom shipping quote — keep in sync with CONFIG.maxItems
// Continental U.S.: 48 states + DC (no AK, HI, territories, APO/FPO)
const STATES = new Set(("AL AZ AR CA CO CT DE DC FL GA ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY").split(" "));

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", "Cache-Control": "no-store" } });
const bad = (msg, status = 400) => json({ error: msg }, status);
const clean = (v, max) => String(v ?? "").replace(/[\u0000-\u001f]/g, " ").trim().slice(0, max);

export function priceCart(rawItems) {
  if (!Array.isArray(rawItems) || !rawItems.length) throw new Error("Your order is empty.");
  if (rawItems.length > MAX_LINES) throw new Error("Too many line items.");
  const lines = []; let count = 0;
  for (const it of rawItems) {
    const qty = Number.isInteger(it?.qty) ? it.qty : NaN;
    if (!(qty >= 1 && qty <= MAX_QTY_PER_LINE)) throw new Error("Invalid quantity.");
    if (it.kind === "shirt") {
      const name = CATALOG.designs[it.design], fit = CATALOG.fits[it.fit];
      if (!name || !fit || !CATALOG.colors.includes(it.color) || !fit.sizes.includes(it.size)) throw new Error("Invalid shirt selection.");
      lines.push({ name: `${name} — ${it.color} — ${fit.label} ${it.size}`, cents: fit.price, qty });
    } else if (it.kind === "book") {
      const b = CATALOG.books[it.book];
      if (!b) throw new Error("Invalid book selection.");
      lines.push({ name: b.title + " (book)", cents: b.price, qty });
    } else throw new Error("Invalid item.");
    count += qty;
  }
  if (count > MAX_ITEMS_PER_ORDER) throw new Error(`Online orders are limited to ${MAX_ITEMS_PER_ORDER} items. For a larger order, please email info@pe-church.online for a custom shipping quote.`);
  const shipping = SHIPPING_TIERS.find(([max]) => count <= max)[1];
  const subtotal = lines.reduce((a, l) => a + l.cents * l.qty, 0);
  return { lines, count, shipping, subtotal, total: subtotal + shipping };
}

export function validateCustomer(c) {
  const f = {
    name: clean(c?.name, 100), email: clean(c?.email, 150), addr1: clean(c?.addr1, 120), addr2: clean(c?.addr2, 120),
    city: clean(c?.city, 80), state: clean(c?.state, 2).toUpperCase(), zip: clean(c?.zip, 10), notes: clean(c?.notes, 400)
  };
  if (!f.name || !f.addr1 || !f.city) throw new Error("Please complete the ship-to address.");
  if (!/^\S+@\S+\.\S+$/.test(f.email)) throw new Error("That email doesn't look right.");
  if (!STATES.has(f.state)) throw new Error("Sorry — we only ship to the continental U.S. (48 states + DC).");
  if (!/^\d{5}(-\d{4})?$/.test(f.zip)) throw new Error("Please enter a valid 5-digit ZIP code.");
  return f;
}

export function buildStripeParams({ cart, cust, origin, returnPath, now = Date.now() }) {
  const p = new URLSearchParams();
  p.set("mode", "payment");
  p.set("success_url", `${origin}${returnPath}?paid=1`);
  p.set("cancel_url", `${origin}${returnPath}`);
  p.set("customer_email", cust.email);
  p.set("expires_at", String(Math.floor(now / 1000) + 31 * 60));
  const all = [...cart.lines, { name: "USPS Ground Advantage shipping & handling", cents: cart.shipping, qty: 1 }];
  all.forEach((l, i) => {
    p.set(`line_items[${i}][quantity]`, String(l.qty));
    p.set(`line_items[${i}][price_data][currency]`, "usd");
    p.set(`line_items[${i}][price_data][unit_amount]`, String(l.cents));
    p.set(`line_items[${i}][price_data][product_data][name]`, l.name);
  });
  // ship-to shows on the payment in the Stripe Dashboard
  const s = "payment_intent_data[shipping]";
  p.set(`${s}[name]`, cust.name);
  p.set(`${s}[address][line1]`, cust.addr1);
  if (cust.addr2) p.set(`${s}[address][line2]`, cust.addr2);
  p.set(`${s}[address][city]`, cust.city);
  p.set(`${s}[address][state]`, cust.state);
  p.set(`${s}[address][postal_code]`, cust.zip);
  p.set(`${s}[address][country]`, "US");
  p.set("payment_intent_data[description]", `Heritage Month flash sale — ships by ${SHIPS_BY_LABEL}`);
  for (const pre of ["metadata", "payment_intent_data[metadata]"]) {
    p.set(`${pre}[ship_by]`, SHIPS_BY_LABEL);
    if (cust.notes) p.set(`${pre}[notes]`, cust.notes);
  }
  return p;
}

export async function onRequestPost({ request, env }) {
  const now = Date.now();
  if (now < +new Date(SALE.starts)) return bad("This sale hasn't opened yet.", 403);
  if (now > +new Date(SALE.ends)) return bad("Sorry — this sale has ended. Visit 1stn8tions.store for regular pricing.", 403);
  if (!env.STRIPE_SECRET_KEY) return bad("Checkout isn't configured yet.", 500);

  let body;
  try { body = await request.json(); } catch { return bad("Bad request."); }

  let cart, cust;
  try { cart = priceCart(body.items); cust = validateCustomer(body.customer); }
  catch (e) { return bad(e.message); }

  const origin = new URL(request.url).origin;
  const rp = typeof body.returnPath === "string" && /^\/[A-Za-z0-9\-_./]*$/.test(body.returnPath) && !body.returnPath.includes("//") ? body.returnPath : "/";

  const res = await fetch("https://api.stripe.com/v1/checkout/sessions", {
    method: "POST",
    headers: { Authorization: `Bearer ${env.STRIPE_SECRET_KEY}`, "Content-Type": "application/x-www-form-urlencoded" },
    body: buildStripeParams({ cart, cust, origin, returnPath: rp, now })
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || !data.url) {
    console.error("Stripe error", res.status, data?.error?.message);
    return bad("Couldn't start checkout. Please try again in a moment.", 502);
  }
  return json({ url: data.url, total: cart.total });
}
