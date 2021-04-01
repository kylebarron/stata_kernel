Emacs Org Mode (using Babel) is a package for the Emacs text editor that connects with Jupyter kernels, such as stata_kernel, 
to display results interactively inside the text editor.  Emacs also allows full console access to jupyter kernels 
for an interactive Stata experience. Like jupyter notebook or lab, it allows for mixing of text narrative, latex math, 
with code and Stata results.  Emacs Org Mode allows for fine grained control of document output for producing pdf manuscripts.

Installation instructions can be found [here](https://rlhick.people.wm.edu/posts/stata_kernel_emacs.html).

* Caveats 
1.  Emacs Org Mode will not currently display `html` output from the `%head` or `%help` magics.  Using code block option `:display text/plain`  
2.  Some graphical output will not display export correctly.  The problem and solution are described in the installation instruction link.  
