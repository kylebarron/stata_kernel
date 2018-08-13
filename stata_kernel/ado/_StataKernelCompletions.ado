capture program drop _StataKernelCompletions
program _StataKernelCompletions
    local userTrace `c(trace)'
    set trace off
    syntax [varlist]
    disp "%mata%"
    mata mata desc
    disp "%varlist%"
    disp `"`varlist'"'
    disp "%globals%"
    disp `"`:all globals'"'
    * NOTE: This only works for globals; locals are, well, local ):
    * disp "%locals%"
    * mata : invtokens(st_dir("local", "macro", "*")')
    disp "%scalars%"
    disp `"`:all scalars'"'
    disp "%matrices%"
    disp `"`:all matrices'"'
    set trace `userTrace'
end
