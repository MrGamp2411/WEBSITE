# AGENT Notes

- `static/css/components.css` (and its minified counterpart) contains styles for cards and bars.
- Desktop bar card width and height are fixed at `400px` and `450px`.
- Desktop bar card height was reduced by 50px.
- Mobile card styles remain at `width:300px` and `height:400px` via media queries.
- Bar card markup resides in `templates/home.html` and `templates/search.html`, while related behavior lives in `static/js/app.js` and `static/js/search.js`.
- Carousel arrow controls compute width from the first *visible* card; hiding the first item can break navigation if not accounted for.
