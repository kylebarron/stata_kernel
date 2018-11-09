Each of the SVG examples in this folder were created with Stata 15.1 by running `stata -b do svg_create.do`.

Then in Bash you can create `example.html` with:

```bash
echo '<!DOCTYPE html>' > example.html
echo '<html>' >> example.html
echo '<body>' >> example.html
cat mpg_price_Unix.svg >> example.html
cat price_weight_Unix.svg >> example.html
echo '</body>' >> example.html
echo '</html>' >> example.html
```
