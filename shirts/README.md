# Flash-sale shop (`shirts/`)

Static page (`index.html`) + one serverless function (`functions/api/checkout.js`) that creates Stripe Checkout sessions.
Everything the sale needs is in the `CONFIG` block at the top of `index.html` — and the matching constants at the top of
`functions/api/checkout.js` (prices, shipping tiers, sale dates, ships-by date). **Edit both together**; the server is what Stripe actually charges.

## Deploy (Cloudflare Pages, free tier)
1. Cloudflare → Workers & Pages → Create → Pages → connect this GitHub repo.
2. **Root directory:** `shirts` · **Build command:** none · **Output directory:** `/` (so only this folder is published).
3. Settings → Variables and Secrets → add secret **`STRIPE_SECRET_KEY`**.
   Start with your Stripe **test** key (`sk_test_…`), place a test order with card `4242 4242 4242 4242`, then swap in the live key (`sk_live_…`).
   Never put the key in the repo or the page.
4. Point your domain at the Pages project.

## Putting it at tygwy.art/flash
The page works from any path (`/flash/`) or its own subdomain. Pick the one that matches where tygwy.art lives:

**A. tygwy.art is on Cloudflare (DNS proxied) — path `/flash`:** add this Worker with the route `tygwy.art/flash*`
(replace `YOUR-PROJECT` with the Pages project name):
```js
export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === "/flash") return Response.redirect(url.origin + "/flash/" + url.search, 301);
    url.hostname = "YOUR-PROJECT.pages.dev";
    url.pathname = url.pathname.replace(/^\/flash/, "") || "/";
    return fetch(new Request(url, request));
  }
};
```
**B. tygwy.art is on another host (Squarespace, Wix, WordPress, GoDaddy…):** use a subdomain instead — add the custom domain
`flash.tygwy.art` to the Pages project and a CNAME record pointing to it, then have `tygwy.art/flash` redirect to it.
(Moving the whole domain's DNS to Cloudflare, which is free, also makes option A possible.)

Stripe's return links are limited to the origins listed in `SITE_ORIGINS` in `functions/api/checkout.js` (add `https://flash.tygwy.art` if you use option B).

## Fulfilling orders
Each paid order shows in the Stripe Dashboard → Payments, with the ship-to address on the payment and the items listed on the
Checkout Session (e.g. "Cherokee Nation — Black — Adult Unisex L"). Everything ships one week after the sale ends.

## Starting the next sale (Thanksgiving / Christmas)
Update dates, designs, books, prices in `index.html` **and** `functions/api/checkout.js`, then run `node --test shirts/tests/checkout.test.mjs`.

## Rules enforced on the server
Sale window (no orders before open / after close), real prices, quantities 1–20 per line, valid sizes/colors,
continental U.S. only (48 states + DC), ship-to ZIP format.
