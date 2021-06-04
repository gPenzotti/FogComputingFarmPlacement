# FogComputingFarmPlacement

This Repository contains the code for the simulations of the paper entitled "An N-Tier Fog Architecture for Smart Farming".

In particular there are the following main files:
- placeService.py, is used to generate the allocation matrix between the network and the applications. Inside, the functions of the config directory are called which are used to generate the applications in a pseudo-random way. The placement results are plotted with the functions contained in plotsGenerator.py
- runSimulation.py, set and run the simulation. The simulation is performed using the YAFS simulator (https://github.com/acsicuib/YAFS/tree/YAFS3) in the version for Python 3. YAFS is required in order to run the code.
- analyze_results.py, takes care of analyzing the simulation results.

After installing the dependencies and configuring the network parameters, for code execution:

``` bash
    python placeService.py
    python runSimulation.py
    python analyze_results.py
```
