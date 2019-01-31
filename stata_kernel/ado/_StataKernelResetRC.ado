capture program drop _StataKernelResetRC
program _StataKernelResetRC
    syntax, num(int)
    cap exit `num'
end
