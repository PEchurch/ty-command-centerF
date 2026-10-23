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

## Fulfilling orders
Each paid order shows in the Stripe Dashboard → Payments, with the ship-to address on the payment and the items listed on the
Checkout Session (e.g. "Cherokee Nation — Black — Adult Unisex L"). Everything ships one week after the sale ends.

## Starting the next sale (Thanksgiving / Christmas)
Update dates, designs, books, prices in `index.html` **and** `functions/api/checkout.js`, then run `node --test shirts/tests/checkout.test.mjs`.

## Rules enforced on the server
Sale window (no orders before open / after close), real prices, quantities 1–20 per line, valid sizes/colors,
continental U.S. only (48 states + DC), ship-to ZIP format.
