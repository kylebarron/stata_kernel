#!/bin/bash

css=stata_kernel/docs/css/pandoc.css
kernel=stata_kernel/docs/index
magics=stata_kernel/docs/using_stata_kernel/magics

cd ../../docs/src
pandoc --self-contained --css=../../${css} -t html5 -o ../../${kernel}.html index.md
pandoc --self-contained -t plain -o ../../${kernel}.txt index.md
cd using_stata_kernel
pandoc --self-contained --css=../../../${css} -t html5 -o ../../../${magics}.html magics.md
pandoc --self-contained -t plain -o ../../../${magics}.txt magics.md
cd ../../../stata_kernel/docs

python make_href
