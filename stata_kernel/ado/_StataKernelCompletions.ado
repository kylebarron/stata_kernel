capture program drop _StataKernelCompletions
program _StataKernelCompletions
    set more off
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
    disp "%logfiles%"
    qui log query _all
    if ( `"`r(numlogs)'"' != "" ) {
        forvalues l = 1 / `r(numlogs)' {
            * Skip stata automation log
            if ( `"`r(name`l')'"' != "stata_kernel_log" ) {
                disp r(filename`l')
            }
        }
    }
    disp "%scalars%"
    disp `"`:all scalars'"'
    disp "%programs%"
    program dir
    disp "%matrices%"
    disp `"`:all matrices'"'
end
