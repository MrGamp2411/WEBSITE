# Bootstrap Icons Font Assets

The Bootstrap Icons stylesheet in `static/css/vendor/bootstrap-icons.css` expects the
version 1.10.5 font files to live alongside this README.

Please download the upstream assets and place them in this directory so the icons
render correctly:

- `bootstrap-icons.woff2`
- `bootstrap-icons.woff`

You can retrieve the exact files that match the checked-in stylesheet with the
following commands (run from the project root):

```bash
curl -sSLo static/fonts/bootstrap-icons.woff2 \
  https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/fonts/bootstrap-icons.woff2
curl -sSLo static/fonts/bootstrap-icons.woff \
  https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/fonts/bootstrap-icons.woff
```

These files are binary and therefore not committed to the repository. Make sure to
add them to your deployment artifact so the icon font loads without 404s.
