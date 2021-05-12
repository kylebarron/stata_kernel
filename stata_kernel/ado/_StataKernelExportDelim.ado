program _StataKernelExportDelim
    syntax [varlist] [if/] [in/] using, [*]

    if ( !`=_N > 0' ) error 2000

    if ( "`in'" == "" ) local in 1/200

    if ( "`if'" != "" ) {
        local stype = cond(`=_N' < maxlong(), "long", "double")
        tempvar touse sumtouse index
        gen byte `touse' = `if'
        gen `stype' `sumtouse' = sum(`touse')
        gen `stype' `index' = _n
        local last = `=`sumtouse'[_N]'
        gettoken f in: in, p(/)
        gettoken s l:  in, p(/)
        if ( "`l'" == "" ) {
            local ifin (`sumtouse' == `f') & `touse'
        }
        else {
            local ifin (`sumtouse' >= `f') & (`sumtouse' <= `l') & `touse'
        }
    }
    else {
        local ifin in `in'
    }

    qui export delimited `index' `varlist' `using' `ifin', replace `options'
    list `varlist' `ifin'
end
