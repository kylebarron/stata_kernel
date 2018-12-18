capture program drop _StataKernelLog
program _StataKernelLog

    * Hold r() results
    if ( `"`0'"' == "off" ) {
        cap _return drop _StataKernelR
        _return hold _StataKernelR
    }

    * Loop through log files and close or reopen them all
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

    * Restore r() results
    if ( `"`0'"' == "on" ) {
        cap _return restore _StataKernelR
        cap _return drop _StataKernelR
    }
end
