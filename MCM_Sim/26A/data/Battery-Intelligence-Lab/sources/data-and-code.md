Title: Data and code · Battery Intelligence Lab

URL Source: http://battery-intelligence-lab.github.io/data-and-code/

Published Time: Thu, 08 Jan 2026 16:20:30 GMT

Markdown Content:
In addition to our publications, we aim to make available models, data, and other useful information for our group and others to use. Please bear in mind that these are research-grade only; use them at your own risk and read the licence carefully before use.

* * *

##### Models

1.   PyBOP is an open-source parametrisation and optimisation package for battery models. It provides point-estimate and statistical methods for identification of electrochemical battery models. Visit the [GitHub repository](https://github.com/pybop-team/PyBOP) for more information.

2.   SLIDE is a C++ code that simulates degradation of lithium ion cells. It extends the single particle model with various degradation models from literature. Users can select which degradation models they want to use for a given simulation. Full details and code available at [github](https://github.com/davidhowey/SLIDE).

3.   Single particle model (SPM) for lithium-ion battery simulation implemented using spectral methods. Full details and code available at [github](https://github.com/davidhowey/Spectral_li-ion_SPM).

4.   Physics-based model of a supercapacitor, based on our paper [“Low-Order Mathematical Modelling of Electric Double Layer Supercapacitors Using Spectral Methods”](http://arxiv.org/abs/1412.0057). Get the [Matlab code from github](https://github.com/scro2542/Supercapacitor-Model).

5.   Code for a dual extended Kalman filter (EKF) for estimation of battery temperature from impedance, based on our paper [“Sensorless battery internal temperature estimation using a kalman filter with impedance measurement”](http://arxiv.org/abs/1501.06160). You can [download the Matlab code and data from github](https://github.com/robert-richardson/EKF-Battery-Impedance-Temperature). We also have a [number of other pieces of code](https://github.com/robert-richardson?tab=repositories) related to impedance temperature monitoring.

* * *

##### Data

1.   Oxford [Battery Degradation Dataset 1](http://dx.doi.org/10.5287/bodleian:KO2kdmYGg). Long term battery ageing tests of 8 Kokam (SLPB533459H4) 740 mAh lithium-ion pouch cells.

2.   Oxford [Energy trading battery degradation dataset](https://ora.ox.ac.uk/objects/uuid:9aae61af-2949-49f1-8ad5-6aea448979e5). Battery degradation data for energy trading with physical models contains data collected from a year-long experiment where six lithium-ion cells were following current profiles corresponding to real-world usage profiles. The profiles were designed for grid-connected batteries trading power on the day-ahead wholesale market. The data set contains monthly capacity measurements as well as measurements of current, voltage and temperature while the cells were being cycled. See `Readme.txt` for a full description of the data and the license under which it is made available.

3.   Oxford [Path dependence battery degradation dataset](https://ora.ox.ac.uk/objects/uuid:de62b5d2-6154-426d-bcbb-30253ddb7d1e). A long-term dataset collected to study the influence of path dependence in commercially available lithium-ion 18650 cells with nickel cobalt aluminium oxide (NCA) positive electrodes and graphite negative electrodes. 4 groups of 3 cells each were subjected to combined load profiles comprising fixed periods of calendar and cyclic aging applied in various orders. Cells in groups 1 and 2 were exposed to one day of cycling followed by five days of calendar aging at C/2 and C/4 respectively. Cells in groups 3 and 4 were exposed to two days of cycling followed by ten days of calendar aging at C/2 and C/4 respectively. The data collected while the cells were exposed to the combined profiles as well as the reference performance tests and electrochemical impedence spectroscopy data is included in this dataset.

* * *

##### Links to external sites

1.   Python Battery Mathematical Modelling [PyBaMM](https://www.pybamm.org/) - python implementations of many popular battery models

2.   Battery Archive, an awesome repository for battery data visualisation and analysis. [https://batteryarchive.org/](https://batteryarchive.org/)

3.   Centre for Advanced Life Cycle Engineering (CALCE) Battery Research Group [datasets](http://www.calce.umd.edu/batteries/data.htm)

4.   NASA Prognostics Data Repository - [Battery dataset](https://ti.arc.nasa.gov/tech/dash/groups/pcoe/prognostic-data-repository/)
