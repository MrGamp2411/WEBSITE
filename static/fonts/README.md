# Font Assets

This directory stores binary font files that are required by the stylesheets under
`static/css/vendor/`. The binaries themselves are not tracked in git, so remember to
download them before building production bundles.

## Bootstrap Icons

`static/css/vendor/bootstrap-icons.css` expects version 1.10.5 of the Bootstrap
Icons font. Place the following files here:

- `bootstrap-icons.woff2`
- `bootstrap-icons.woff`

Download commands (run from the project root):

```bash
curl -sSLo static/fonts/bootstrap-icons.woff2 \
  https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/fonts/bootstrap-icons.woff2
curl -sSLo static/fonts/bootstrap-icons.woff \
  https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/fonts/bootstrap-icons.woff
```

## Inter (400, 600, 700)

`static/css/vendor/inter.css` self-hosts the Inter font for weights 400, 600, and 700
using the Latin subset. Add both the WOFF2 and WOFF versions for each weight:

- `inter-latin-400-normal.woff2`
- `inter-latin-400-normal.woff`
- `inter-latin-600-normal.woff2`
- `inter-latin-600-normal.woff`
- `inter-latin-700-normal.woff2`
- `inter-latin-700-normal.woff`

You can retrieve binaries that match the checked-in CSS with:

```bash
curl -sSLo static/fonts/inter-latin-400-normal.woff2 \
  https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.19/files/inter-latin-400-normal.woff2
curl -sSLo static/fonts/inter-latin-400-normal.woff \
  https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.19/files/inter-latin-400-normal.woff
curl -sSLo static/fonts/inter-latin-600-normal.woff2 \
  https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.19/files/inter-latin-600-normal.woff2
curl -sSLo static/fonts/inter-latin-600-normal.woff \
  https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.19/files/inter-latin-600-normal.woff
curl -sSLo static/fonts/inter-latin-700-normal.woff2 \
  https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.19/files/inter-latin-700-normal.woff2
curl -sSLo static/fonts/inter-latin-700-normal.woff \
  https://cdn.jsdelivr.net/npm/@fontsource/inter@5.0.19/files/inter-latin-700-normal.woff
```

Include these files in deployment artifacts so typography renders correctly without
external HTTP requests.
