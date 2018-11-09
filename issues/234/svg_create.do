sysuse auto

tw lfitci mpg price
graph export mpg_price_$S_OS.svg, replace

tw lfitci price weight
graph export price_weight_$S_OS.svg, replace
