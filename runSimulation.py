#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import json
import os

from yafs.core import Sim
from yafs.application import Application,Message
from yafs.topology import Topology
from yafs.placement import JSONPlacement,JSONPlacementOnCloud
from yafs.distribution import deterministicDistributionStartPoint
import numpy as np
import matplotlib.pyplot as plt
from selection_multipleDeploys import DeviceSpeedAwareRouting
from jsonPopulation import JSONPopulation

import time
import random

# fractional_selectivity is not implemented in YAFS3)
def fractional_selectivity(threshold):
    return random.random() <= threshold


def create_applications_from_json(data):
    applications = {}
    for app in data:
        a = Application(name=app["name"])
        modules = [{"None":{"Type":Application.TYPE_SOURCE}}]
        for module in app["module"]:
            modules.append({module["name"]: {"RAM": module["RAM"], "Type": Application.TYPE_MODULE}})
        a.set_modules(modules)

        ms = {}
        for message in app["message"]:
            ms[message["name"]] = Message(message["name"],message["s"],message["d"],instructions=message["instructions"],bytes=message["bytes"])
            if message["s"] == "None":
                a.add_source_messages(ms[message["name"]])

        for idx, message in enumerate(app["transmission"]):
            if "message_out" in message.keys():
                a.add_service_module(message["module"],ms[message["message_in"]], ms[message["message_out"]], fractional_selectivity, threshold=1.0)
            else:
                a.add_service_module(message["module"], ms[message["message_in"]])

        applications[app["name"]]=a

    return applications

def getProcessFromThatNode(sim, node_to_remove):
    #It returns the software modules (a list of identifiers of DES process) deployed on this node
    # Used with Dynamic Failures Strategy 
    if node_to_remove in sim.alloc_DES.values():
        DES = []
        # This node can have multiples DES processes on itself
        for k, v in sim.alloc_DES.items():
            if v == node_to_remove:
                DES.append(k)
        return DES,True
    else:
        return [],False


idxFControl = 0
def failureControl(sim,filelog,ids):
    #It controls the elimination of a node
    global idxFControl
    nodes = list(sim.topology.G.nodes())
    if len(nodes)>1:
        try:
            node_to_remove = ids[idxFControl]
            idxFControl +=1
            
            # Do not remove gateway 
            if node_to_remove < 20:
                return

            keys_DES,someModuleDeployed = getProcessFromThatNode(sim, node_to_remove)

            #print ("\n\nRemoving node: %i, Total nodes: %i" % (node_to_remove, len(nodes)))
            #print ("\tStopping some DES processes: %s\n\n"%keys_DES)
            filelog.write("%i,%s,%d\n"%(node_to_remove, someModuleDeployed,sim.env.now))

            #Print some information:
            # for des in keys_DES:
            #     if des in sim.alloc_source.keys():
            #         print("Removing a Gtw/User entity\t"*4)

            sim.remove_node(node_to_remove)
            for key in keys_DES:
                sim.stop_process(key)
        except IndexError:
            None

    else:
        sim.stop = True ## Stop the simulation if all nodes are failed


def main(simulated_time,path_json, resultspath, specificSuffix,it):
    
    # Upload from json files
    
    # TOPOLOGY
    t = Topology()
    dataNetwork = json.load(open(path_json+'networkDefinition.json'))
    t.load(dataNetwork)
    t.write("network.gexf")

    
    # APPLICATION
    dataApp = json.load(open(path_json+'appDefinition.json'))
    apps = create_applications_from_json(dataApp)
    #for app in apps:
    #  print apps[app]

    
    #PLACEMENT algorithm
    placementJson = json.load(open(path_json+'allocDefinition%s.json'%specificSuffix))
    placement = JSONPlacement(name="Placement",json=placementJson)


    # POPULATION algorithm
    dataPopulation = json.load(open(path_json+'usersDefinition.json'))
    pop = JSONPopulation(name="Statical", json=dataPopulation, iteration=it)

    # SELECTOR algorithm
    selectorPath = DeviceSpeedAwareRouting()

    
    # SIMULATION Engine
    stop_time = simulated_time
    s = Sim(t, default_results_path=resultspath + "Results_%s_%i_%i" % (specificSuffix, stop_time,it))

    #For each deployment the user - population have to contain only its specific sources
    for aName in apps.keys():
        print ("Deploying app: ",aName)
        pop_app = JSONPopulation(name="Statical_%s" % aName, json={}, iteration=it)
        data = []
        for element in pop.data["sources"]:
            if element['app'] == aName:
                data.append(element)
        pop_app.data["sources"]=data

        s.deploy_app2(apps[aName], placement, pop_app, selectorPath) #deprecated in YAFS3


    s.run(stop_time, test_initial_deploy=False, show_progress_monitor=False)

    # 
    # Sim with Dynamic Failure of nodes
    #
    stop_time = simulated_time
    s_f = Sim(t, default_results_path=resultspath + "Results_RND_FAIL__%i_%i" % (stop_time,it)) 
    
    dynamicFail = True
    if dynamicFail:
        time_shift = 10000
        distribution = deterministicDistributionStartPoint(name="Deterministic", time=time_shift,start=10000)
        failurefilelog = open(path_json+"Failure_%s_%i.csv" % (specificSuffix,stop_time),"w")
        failurefilelog.write("node, module, time\n")
        randomValues = np.load(path_json+"random.npy") #print(randomValues)
        print(random)
        
        s_f.deploy_monitor("Failure Generation", failureControl, distribution,sim=s,filelog=failurefilelog,ids=randomValues)

    #For each deployment the user - population have to contain only its specific sources
    for aName in apps.keys():
        print ("Deploying app: ",aName)
        pop_app = JSONPopulation(name="Statical_%s" % aName, json={}, iteration=it)
        data = []
        for element in pop.data["sources"]:
            if element['app'] == aName:
                data.append(element)
        pop_app.data["sources"]=data

        s_f.deploy_app2(apps[aName], placement, pop_app, selectorPath) #deprecated


    s_f.run(stop_time, test_initial_deploy=False, show_progress_monitor=False) #TEST to TRUE


if __name__ == '__main__':

    simtime = 1000000
    
    pathJSON = "exp_json/"
    pathResults = "exp_results/"

    print (os.getcwd())

    for i in range(1): # Num of iteration
        random.seed(i)
        np.random.seed(i)
        
        start_time = time.time()
        print ("Running Partition ", i)
        main(simulated_time=simtime,  path_json=pathJSON, resultspath= pathResults, specificSuffix='',it=i)
        print("\n--- End after %s seconds ---" % (time.time() - start_time))


    print ("Simulation Done")


