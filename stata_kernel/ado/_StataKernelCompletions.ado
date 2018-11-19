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
            disp r(filename`l')
        }
    }
    disp "%scalars%"
    disp `"`:all scalars'"'
    disp "%matrices%"
    disp `"`:all matrices'"'
end
