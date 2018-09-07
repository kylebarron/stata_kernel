#!/bin/bash

css=stata_kernel/docs/css/pandoc.css
kernel=stata_kernel/docs/index
magics=stata_kernel/docs/using_stata_kernel/magics

# index.md
cd ../../docs/src
echo '<style type="text/css">' > _tmp
cat ../../${css} >> _tmp
echo '</style>' >> _tmp 

pandoc -H ./_tmp -t html5 -o ../../${kernel}.html index.md
pandoc -t plain -o ../../${kernel}.txt index.md
rm _tmp

# using_stata_kernel/magics.md
cd using_stata_kernel
echo '<style type="text/css">' > _tmp
cat ../../../${css} >> _tmp
echo '</style>' >> _tmp 

pandoc -H _tmp -t html5 -o ../../../${magics}.html magics.md
pandoc -t plain -o ../../../${magics}.txt magics.md
rm _tmp

# clean pandoc html
cd ../../../stata_kernel/docs
python make_href
