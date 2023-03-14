# Electrical Grid Simulator (EGS)
The *Electrical Grid Simulator* (abbreviated as **EGS**) is a graphical user interface for simulating electrical networks based on the [pandapower](https://www.pandapower.org/) library. The main objective is to allow the creation of mathematical models for steady-state electrical grids from a user-friendly graphical interface.

<img src="./img/app_icon.png" alt="EGS logo" width="200">


## Goals
- Providing a minimalist, modern and good-looking interface.
- Multiplatform: GNU/Linux, MS Windows and Apple MacOS (not tested on MacOS).
- Providing an extension system to expand its capabilities (WIP, not available yet).


## How it works
Every time the user inserts and connects an element to the network, the application replicates the addition in a **pandapower network**. Thus, the parameters of a component are updated in the pandapower network when they are modified from the graphical interface.

The network configured from the interface is designated as **Graph**, while the corresponding pandapower model is denoted as **Data model**. This synchronization works in the **Graph -> Data model** direction, i.e. changes in the **Graph** are automatically registered into the **Data model**, and not the other way around. However, the contents of the **Data model** can be consulted at any time. 

According to the structure proposed by the pandapower library, the **Data model** consists of a set of tables ([pandas DataFrame type objects](https://en.wikipedia.org/wiki/Pandas_(software))). Each table (**DataFrame**) contains the parameters of a certain type of component. The types of components supported by pandapower are those indicated in [this documentation link](https://pandapower.readthedocs.io/en/latest/). At this moment, most of these components are also supported by EGS.

![Main window: Graph view](img/1_Main_Window.png)


## Main features

