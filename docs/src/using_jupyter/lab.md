# JupyterLab

Jupyter Lab is the successor to [Jupyter Notebook](notebook.md), and allows for having multiple documents side-by-side.

### Starting JupyterLab

You can start JupyterLab by running:

```
jupyter lab
```

in your terminal or command prompt. Just like the Notebook, this should open up a page in your browser, where you can open a new Stata notebook or console.

### Syntax highlighting

To enable syntax highlighting for Stata with JupyterLab, you need to run (only once):

```bash
conda install -c conda-forge nodejs -y
jupyter labextension install jupyterlab-stata-highlight
```

If you didn't install Python from Anaconda, the `conda` command won't work and you'll need to install [Node.js](https://nodejs.org/en/download/) directly before running `jupyter labextension install`.

### Plugins

One of the benefits of JupyterLab over the Notebook is that it was designed for extensibility. There's a growing list of plugins that can be used with JupyterLab. Here's an unofficial list: <https://github.com/mauhai/awesome-jupyterlab>

### More info

Project documentation website:
<https://jupyterlab.readthedocs.io/en/stable/>

![](https://jupyterlab.readthedocs.io/en/stable/_images/jupyterlab.png)
