# tygwy.art

Static site: `index.html` + `style.css` + `img/`. No build step.

Deploy on Cloudflare Pages (root `/`, no build command), then point tygwy.art at it.
The shop lives at `/flash/` (see the `ty-command-centerF` repo, `shirts/`).
Pages: `/aboutTy/`, `/unnu/`, `/films/`, `/books/`, `/art/`, `/speaking/`, `/contact/`. Social links: edit `SOCIALS` in `aboutTy/index.html`. Videos/docs: edit `MEDIA` in `films/index.html`. `_redirects`, `robots.txt`, `sitemap.xml` and `404.html` are Cloudflare Pages ready.

Publish videos and docs by editing the `MEDIA` list at the bottom of `index.html`.
