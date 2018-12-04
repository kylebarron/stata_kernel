capture program drop _StataKernelLog
program _StataKernelLog
    set more off
    set trace off
    qui log query _all
    local lognames
    if ( `"`r(numlogs)'"' != "" ) {
        qui forvalues l = 1 / `r(numlogs)' {
            local lognames `lognames' `r(name`l')'
        }
    }
    if ( `"`0'"' == "off" ) {
        qui foreach logname of local lognames {
            if ( `"`logname'"' == "stata_kernel_log" ) {
                * Skip stata automation log
            }
            else if ( `"`logname'"' == "<unnamed>" ) {
                log off
            }
            else {
                log off `logname'
            }
        }
    }
    else if ( `"`0'"' == "on" ) {
        qui foreach logname of local lognames {
            if ( `"`logname'"' == "stata_kernel_log" ) {
                * Skip stata automation log
            }
            else if ( `"`logname'"' == "<unnamed>" ) {
                log on
            }
            else {
                log on `logname'
            }
        }
    }
    else {
        disp as err "Can only switch logs -on- or -off-"
        exit 198
    }
end
