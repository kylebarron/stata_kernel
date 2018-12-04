# Remote Unix/Linux Servers

## Introduction

There are two ways to use Jupyter on a remote Unix/Linux server.

- The less-usable way, but which is simpler to get started with, is simply using [Jupyter Console](../console) within a remote terminal. This gives you many—but not all—of the features of `stata_kernel`, including syntax highlighting, free-flowing comments, autocompletions, and `#delimit ;` support. To do this, all you need to do is install `stata_kernel` on the remote server (Stata must also be installed on that remote server).

- The much more powerful way to run Jupyter on a remote server is to set it up so that you're working with Jupyter Notebook in your local web browser, or with Hydrogen in Atom running locally, but where all the computation happens on the remote server. This is a little more involved to set up, but, once running, makes working on a remote server effortless.

    This setup is one of my favorite parts of Jupyter. The only information communicated to the server is the input command as text, and the only information communicated back from the server to the local computer is the output of the command. Since very little information is sent back and forth, this setup has very low latency, which means that it's fast even on slower networks: if you're waiting on output, it's likely because Stata is slow, not the connection.

    When using a program like `tmux` or `screen` on the server, you can reconnect _to the same Jupyter kernel_ (and thus the same Stata session) after becoming disconnected from the network (i.e. if a VPN times out). In contrast, with a normal console or GUI Stata session, there is no way to reconnect to the running Stata session, and you'd have to recreate the state of the environment from scratch.

The rest of this document explains how to set up the latter method.

!!! warning

    It's important to understand the security implications of allowing remote
    access to your machine. An improperly configured server or a Jupyter
    Notebook server without a password could allow an attacker to run arbitrary
    code on your computer, conceivably accessing private data or deleting files.

## Overview

To understand how to set this up, it's helpful to know a bit about how Jupyter works.
Jupyter has a client-server model:

- the _client_ (i.e. the Notebook, Hydrogen, or console) accepts user input and displays output.
- the _server_ (the Jupyter internals) receives input from the client, forwards it to Stata, retrieves the results, and sends them back to the client.

Usually, both the client and server run on the same computer.
However, because these are two separate programs, this is not a requirement. They just need to be able to communicate with each other.

 When working with remote servers, you'll instead run the client on the computer you're physically touching and the server on the computer on which computation should happen.

### Network Ports

A network [_port_](https://en.wikipedia.org/wiki/Port_(computer_networking)) is a logical construct that simplifies client-server communication and allows for many different types of communication on the same computer.

By default, the Jupyter server process runs on port `8888`. This is why, when you open up Jupyter Notebook in your web browser, you'll usually see `http://localhost:8888` in the address bar. This means that the Jupyter server process is emitting data on port `8888` on the local computer.

When working with Jupyter remotely, you'll have to know what port Jupyter is running on so that you can _forward_ the remote port to your local computer during the SSH connection. This is the core of the step that connects the server process on the remote computer to the client process on the local computer.

## Set up

There are two options for what to use on the server:

- [Jupyter Notebook Server](https://jupyter-notebook.readthedocs.io/en/stable/public_server.html): This is relatively simple to set up and does not need administrator privileges. Though not designed for use on a multi-user server, it is possible to use on one.
- [JupyterHub](https://github.com/jupyterhub/jupyterhub): This is Jupyter's official solution for servers with multiple users. This is much more difficult to set up (and might need administrator privileges) and I won't go into details here.

The rest of this guide assumes you're installing the Jupyter Notebook server. [Full documentation is here](https://jupyter-notebook.readthedocs.io/en/stable/public_server.html).

!!! info

    `stata_kernel` must be installed on the server, the computer that is doing the computations. Neither Jupyter nor `stata_kernel` (nor Stata) needs to be installed on the client computer.

    The following instructions assume you are able to connect to the remote server
    through SSH. Setting up an SSH server is outside the scope of this guide.

### Creating the configuration file

On the _server_ computer run in a terminal

```
jupyter notebook --generate-config
```

This creates a configuration file at one of three locations on the remote computer:

- Windows: `C:\Users\USERNAME\.jupyter\jupyter_notebook_config.py`
- OS X: `/Users/USERNAME/.jupyter/jupyter_notebook_config.py`
- Linux: `/home/USERNAME/.jupyter/jupyter_notebook_config.py`


### Connecting with SSH

#### Linux and macOS

A usual SSH connection can be created from the terminal by running:

```
ssh username@host
```

In order to connect to the remote Jupyter session, we need to forward the port that Jupyter is running on from the remote computer to the local computer. If Jupyter is running on port `8888`, we can forward the remote port to the same local port by running

```
ssh username@host -L 8888:localhost:8888
```

#### Windows

![Mobaxterm local port forwarding](../img/mobaxterm-local-port-forwarding.png)

[Here's information](https://blog.mobatek.net/post/ssh-tunnels-and-port-forwarding/#simple-explanation-of-ssh-tunnels-and-port-forwarding:b8ebdf9b2cb412a3a77c16c73c0d31ed) for how to forward a remote port using Mobaxterm. In MobaXterm, go to Tools > MobaxtermTunnel > New. You want:

- select `Local port forwarding`
- The "My computer with MobaXterm" box on the left (`12345` in the image) is customarily `8888`, though it can be any 4- or 5-digit number. This is the number you'll type into your local web browser, i.e. `http://localhost:8888`.
- The "SSH server" box in the bottom right should have your server's hostname and username.
- The "Remote server" box in the top right should have your server's hostname again and then the port on which Jupyter is running. Usually this is `8888`.

### Starting Jupyter Notebook

Run `jupyter notebook --no-browser --port=8888` in the remote terminal.

On your local computer, go to `http://localhost:8888`. It should ask you for a token to sign in, which normally will be printed in the remote console once Jupyter Notebook starts.

Then you can start a Jupyter Notebook session with the Stata kernel like usual.

Here's [more documentation](https://nteract.gitbooks.io/hydrogen/docs/Usage/RemoteKernelConnection.html) for connecting to a remote kernel from Hydrogen. You can even connect to multiple servers at the same time.
