* Written by Mauricio Caceres
* August 19, 2018
* version 0.1
program _StataKernelExportDelim
    syntax [varlist] [if/] [in/] using, [*]
    if ( "`if'" != "" ) {
        local stype = cond(`=_N' < maxlong(), "long", "double")
        tempvar touse sumtouse
        gen byte `touse' = `if'
        gen `stype' `sumtouse' = sum(`touse')
        local last = `=`sumtouse'[_N]'

        gettoken f in: in, p(/)
        gettoken s l:  in, p(/)

        if ( "`l'" == "" ) {
            local ifin (`sumtouse' == `f')
        }
        else {
            local ifin (`sumtouse' >= `f') & (`sumtouse' <= `l') & `touse'
        }
    }
    else if ( "`in'" != "" ) {
        local ifin in `in'
    }
    else {
        local ifin
    }
    export delimited `varlist' `using' `ifin', `options'
end
