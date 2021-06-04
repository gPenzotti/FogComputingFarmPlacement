#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

from http import client
from platform import node
import random
from typing import Dict
from config.experimentConfiguration import ExperimentConfiguration
import pathlib
from utils.plotsGenerator import plotsGenerator
import os
import operator
import networkx as nx
import json
import time
from networkx.algorithms import community
import itertools
import matplotlib.pyplot as plot


class ServicePlacement:
    
    def __init__(self, ec, resultFolder):
        
        self.ec = ec

        self.resultFolder = resultFolder
         #(deadline,shortestdistance):occurrences
        self.statisticsDistanceDeadline = {}
        
        #(service,deadline):occurrences
        self.statisticsServiceInstances = {}
        
        #distance:numberOfuserThatRequest
        self.statisticsDistancesRequest = {}
        
        #nodeid:numberOfuserThatRequest
        self.statisticsNodesRequest = {}
        
        #(nodeid,serviceId):ocurrences
        self.statisticsNodesServices = {}
        
        #(centrality,resources):occurrences
        self.statisticsCentralityResources = {}

    def solve(self):

        ### DEBUG
        # node_neigh = {}
        # for node in self.ec.G.nodes:
        #     nl = len(list(self.ec.G.neighbors(node)))
        #     if nl in node_neigh:
        #         node_neigh[nl] += 1
        #     else:
        #         node_neigh[nl] = 1
        # print(node_neigh)
        # exit()
        ###
        
        
        t = time.time()
        
        # Services ordering
        self.topologicOrderedApp = list()
        for APP in self.ec.apps:
            self.topologicOrderedApp.append(list(nx.topological_sort(APP))) 
   
        # Placement Matrix
        self.service2DevicePlacementMatrix = [[0 for j in range(len(self.ec.G.nodes))] for i in range(self.ec.number_of_services)]        
        self.centralityValuesNoOrdered = nx.betweenness_centrality(self.ec.G,weight="weight") # pre statistica

        # Init nodes consumed resources 
        self.nodeUsedResources = {}
        for i in self.ec.G.nodes:
            self.nodeUsedResources[i]=0.0
        
        # Sorting the apps by deadline (and level)  
        sortedAppsDeadlines = sorted(self.ec.apps_deadlines.items(), key=operator.itemgetter(1))

        allocatedApp_Dict = {} 
        for i,v in enumerate(self.ec.apps_requests):
            allocatedApp_Dict[i] = {}
            for gy in v:
                allocatedApp_Dict[i][gy] = False 
        
        print("Starting placement policy.....")

        for appToAllocate in sortedAppsDeadlines:
            appId=appToAllocate[0] #taking app id
            print("######### \n\n~~~Starting iteration for app[",appId,"]")
            # Calculate Latency of the nodes for this app 
            self.calculateLatencyNetwork(appId) 
            
            ### DEBUG
            # for s in self.ec.apps[appId]:
            #     print ("[", appId,"]", s, " - predecessor: ", [i for i in self.ec.apps[appId].predecessors(s)])
            # nx.draw_networkx(self.ec.apps[appId])
            # plot.show()
            # continue
            ###

            nodesWithClients = self.ec.apps_requests[appId] 

            # ClientId is a gateway
            for clientId in nodesWithClients:

                print("## ~~~Client[",clientId,"]")
                #placed_=False
            
                servicesToPlace = set()
                for i in self.topologicOrderedApp[appId]:
                    servicesToPlace.add(i)

                availableResourcesNodes = {}
                availableSpeedNodes = {}
                for dev in self.ec.G.nodes:
                    availableResourcesNodes[dev]=self.ec.nodeResources[dev]-self.nodeUsedResources[dev]
                    availableSpeedNodes[dev]=self.ec.nodeSpeed[dev]

                tempServiceAlloc = {}
                for servId in self.topologicOrderedApp[appId]:
                    tempServiceAlloc[servId]= None

                appPlaced = True

                for service in self.topologicOrderedApp[appId]:
                    # The services are ordered
                    service_placed = False

                    requiredResources = self.ec.apps_resources[appId][service]
                    requiredPrivacy = self.ec.apps_privacies[appId][service]
                    print("# RequiredResources:", requiredResources, "| requiredPrivacy:", requiredPrivacy, "| service:", service, "| appId:", appId)

                    candidatesNodes = list()

                    if len([i for i in self.ec.apps[appId].predecessors(service)]) == 0:
                        # We are in the gateway
                        neighbors = self.ec.G.neighbors(clientId)                
                        orderedNeighbors=self.devicesFirstFitDescendingOrder(neighbors, clientId ,appId)
                        candidatesNodes = orderedNeighbors
                    else:
                        # We are in a fog/cloud node
                        pred_serv = [i for i in self.ec.apps[appId].predecessors(service)][0]
                        host = tempServiceAlloc[pred_serv]
                        
                        neighbors = self.ec.G.neighbors(host)
                        orderedNeighbors=self.devicesFirstFitDescendingOrder(neighbors, host ,appId)
                        orderedNeighbors.insert(0,host)
                        candidatesNodes = orderedNeighbors
                        
                    for devId in candidatesNodes:
                        # Privacy Check
                        if requiredPrivacy >= self.ec.G.nodes[devId]["level[z]"]:
                            # Resources Check
                            if availableResourcesNodes[devId]>=requiredResources:
                                # Temporary Placement
                                tempServiceAlloc[service]= devId 
                                availableResourcesNodes[devId] = availableResourcesNodes[devId] - requiredResources
                                print ("[APP: ", str(appId),"]Temp-allocation of service ",str(service),"[", requiredResources ,"] in device ",str(devId) , " res[", availableResourcesNodes[devId] , "/", self.ec.nodeResources[devId],"]")

                                service_placed = True
                                break
                    
                    if service_placed == False:
                        # If we can't place a service, we can't place the app
                        print ("[WARNING] Fail to allocate app "+str(appId)+" for gateway "+str(clientId))
                        appPlaced = False
                        
                        ### DEBUG
                        print("-------------------")
                        candidatesNodes = list()
                        if len([i for i in self.ec.apps[appId].predecessors(service)]) == 0:
                            neighbors = self.ec.G.neighbors(clientId)
                            orderedNeighbors=self.devicesFirstFitDescendingOrder(neighbors, clientId ,appId)
                            candidatesNodes = orderedNeighbors
                            print("candidatesNodes of gateway :", clientId, "[", self.ec.G.nodes[clientId]["level[z]"],"]")
                        else:
                            pred_serv = [i for i in self.ec.apps[appId].predecessors(service)][0]
                            host = tempServiceAlloc[pred_serv]
                            neighbors = self.ec.G.neighbors(host)
                            orderedNeighbors=self.devicesFirstFitDescendingOrder(neighbors, host ,appId)
                            orderedNeighbors.insert(0,host)
                            candidatesNodes = orderedNeighbors
                            print("candidatesNodes of host :", host, "[", self.ec.G.nodes[host]["level[z]"],"]")
                        for devId in candidatesNodes:
                            print(devId, "[", self.ec.G.nodes[devId]["level[z]"],"] - Temporary Availaible Res:", availableResourcesNodes[devId],"(max:", self.ec.nodeResources[devId],") - Required Res:",requiredResources, ", Required Privacy:",requiredPrivacy)
                        print("-------------------")
                        ### DEBUG
                        break
                    
                if appPlaced == False:
                    allocatedApp_Dict[appId][clientId] = False 
                else:
                    allocatedApp_Dict[appId][clientId] = True
                    # Permanent Placement
                    for servId,deviceId in tempServiceAlloc.items():
                        self.service2DevicePlacementMatrix[servId][deviceId]=1
                        self.nodeUsedResources[deviceId]=self.nodeUsedResources[deviceId]+self.ec.apps_resources[appId][servId]
                    placed_=True

            #Out of gateways loop
            print("######### End of iteration for app[",appId,"]")
            success = 0
            tot = 0
            for k,v in allocatedApp_Dict[appId].items():
                tot += 1
                if v ==True: 
                    success += 1 
            print("Result [",success,"/",tot, " ]:", allocatedApp_Dict[appId])
        #Out of the apps loop
        success = 0
        tot = 0
        for j in allocatedApp_Dict:        
            for k,v in allocatedApp_Dict[j].items():
                tot += 1
                if v ==True: 
                    success += 1 
        print("\nFINAL Result [",success,"/",tot, " ]")

        print("\n\nEnd of Service Placement in ", str(time.time() -t), "\nwriting statistics...\n")  

        # Statistics

        self.writeStatisticsDevices(self.service2DevicePlacementMatrix)
        
        servicesInCloud = 0
        servicesInFog = 0
        
        allAlloc = {}
        myAllocationList = list()
        for idServ in range(self.ec.number_of_services):
            for idDevice in range(len(self.ec.G.nodes)):
                if self.service2DevicePlacementMatrix[idServ][idDevice]==1:
                    if self.ec.G.nodes[idDevice]["level[z]"] in [2,3,4,5]:
                    # Counting Nodes
                        myAllocation = {}
                        myAllocation['app']=self.ec.map_service_to_app[idServ]
                        myAllocation['module_name']=self.ec.map_serviceid_to_servicename[idServ]
                        myAllocation['id_resource']=idDevice
                        myAllocationList.append(myAllocation)
                        servicesInFog = servicesInFog + 1
                    elif self.ec.G.nodes[idDevice]["level[z]"] == 6: #"cloud":
                        myAllocation = {}
                        myAllocation['app']=self.ec.map_service_to_app[idServ]
                        myAllocation['module_name']=self.ec.map_serviceid_to_servicename[idServ]
                        myAllocation['id_resource']=self.ec.cloudId
                        myAllocationList.append(myAllocation)
                        servicesInCloud = servicesInCloud +1    
        
        self.nodeResUse, self.nodeNumServ = self.calculateNodeUsage(self.service2DevicePlacementMatrix)
        print ("Number of services in cloud (partition) (servicesInCloud): "+str(servicesInCloud))
        print ("Number of services in fog (partition) (servicesInFog): "+str(servicesInFog))

        globaldevresources = 0
        for idDev in self.ec.G.nodes:
            if self.ec.G.nodes[idDev]["level[z]"] in [2,3,4,5]:
                #print(idDev, "-", self.ec.nodeResources[idDev], "-",self.ec.G.nodes[idDev]["level[z]"])
                globaldevresources = globaldevresources + self.ec.nodeResources[idDev]
        
        globalresServ = 0 
        for idServ in range(0,len(self.service2DevicePlacementMatrix)):
            for idDev in range(0,len(self.service2DevicePlacementMatrix[idServ])):
                if self.service2DevicePlacementMatrix[idServ][idDev]==1:
                    globalresServ=globalresServ+self.ec.services_resources[idServ]
        print("Global Nodes Resources: ", globaldevresources)
        print("Global Services Resources: ", globalresServ)

        # Saving
        
        allAlloc['initialAllocation']=myAllocationList

        file = open(self.resultFolder+"/allocDefinition.json","w")
        file.write(json.dumps(allAlloc))
        file.close()
                
        return self.service2DevicePlacementMatrix

                
    def devicesFirstFitDescendingOrder(self, nodes, source_node, appId):

        mips_ = float(self.ec.apps_total_MIPS[appId])
        nodeTotalTime = {}


        for devId in nodes:
             
            # Only for fog nodes
            if self.ec.G.nodes[devId]["level[z]"] in [2,3,4,5]:
                # Processing time for the app in node devId 
                processTime = mips_ / float(self.ec.G.nodes[devId]['IPT']) 
                # Propagation Time from source to devId
                netTime = nx.shortest_path_length(self.ec.G,source=source_node,target=devId,weight="weight")    
                
                # Propagation time plus Processing time
                nodeTotalTime[devId] = processTime + netTime

        #Sorting nodes
        nodeTotalTimeSorted = sorted(nodeTotalTime.items(), key=operator.itemgetter(1))

        sortedList = list()

        for i in nodeTotalTimeSorted:
            sortedList.append(i[0])

        return sortedList

    def calculateLatencyNetwork(self,appId):
        # Calculate the latency for each node in the network using source msg
        size = float(self.ec.apps_source_message[appId]['bytes'])
        for e in self.ec.G.edges:
            self.ec.G[e[0]][e[1]]['weight']=float(self.ec.G[e[0]][e[1]]['PR'])+ (size/float(self.ec.G[e[0]][e[1]]['BW'])) #latency formula

    # Unused
    def calculateLatencyGraph(self, graph, appId):
        # For graph object
        size = float(self.ec.apps_source_message[appId]['bytes'])
        for e in graph.edges:
            graph[e[0]][e[1]]['weight']=float(graph[e[0]][e[1]]['PR'])+ (size/float(graph[e[0]][e[1]]['BW'])) #sarebbe la latenza, cioè quanto pesa questo collegamento al msg sorgente

    def writeStatisticsAllocation(self,tempServiceAlloc,clientId,appId):
        
            for talloc_ in tempServiceAlloc.items():
        
                dist_ = nx.shortest_path_length(self.ec.G,source=clientId,target=talloc_[1],weight="weight")
        
                mykey_=dist_
                if mykey_ in self.statisticsDistancesRequest:
                    self.statisticsDistancesRequest[mykey_]= self.statisticsDistancesRequest[mykey_]+1
                else:
                    self.statisticsDistancesRequest[mykey_]=1
        
                mykey_=talloc_[1]
                if mykey_ in self.statisticsNodesRequest:
                    self.statisticsNodesRequest[mykey_]= self.statisticsNodesRequest[mykey_]+1
                else:
                    self.statisticsNodesRequest[mykey_]=1
        
                mykey_=(talloc_[1],talloc_[0])
                if mykey_ in self.statisticsNodesServices:
                    self.statisticsNodesServices[mykey_]= self.statisticsNodesServices[mykey_]+1
                else:
                    self.statisticsNodesServices[mykey_]=1
        
        
                mykey_=(self.ec.appsDeadlines[appId],dist_)
                if mykey_ in self.statisticsDistanceDeadline:
                    self.statisticsDistanceDeadline[mykey_]= self.statisticsDistanceDeadline[mykey_]+1
                else:
                    self.statisticsDistanceDeadline[mykey_]=1
        
                mykey_=(talloc_[0],self.ec.appsDeadlines[appId])
                if mykey_ in self.statisticsServiceInstances:
                    self.statisticsServiceInstances[mykey_]=self.statisticsServiceInstances[mykey_]+1
                else:
                    self.statisticsServiceInstances[mykey_]=1

    def writeStatisticsDevices(self,service2DevicePlacementMatrix):
    
        for devId in self.ec.G.nodes:
            if self.ec.nodeResources[devId] > 0:
                mypercentageResources_ = float(self.nodeUsedResources[devId])/float(self.ec.nodeResources[devId])
            else: 
                mypercentageResources_ = 0
            mycentralityValues_ = self.centralityValuesNoOrdered[devId]
            mykey_=(mycentralityValues_,mypercentageResources_)
            if mykey_ in self.statisticsCentralityResources:
                self.statisticsCentralityResources[mykey_]=self.statisticsCentralityResources[mykey_]+1
            else:
                self.statisticsCentralityResources[mykey_]=1
    
    def calculateNodeUsage(self,service2DevicePlacementMatrix):
    
        nodeResUse = list()
        nodeNumServ = list()
        
        for i in service2DevicePlacementMatrix[0]:
            nodeResUse.append(0.0)
            nodeNumServ.append(0)
            
        for idServ in range(0,len(service2DevicePlacementMatrix)):
            for idDev in range(0,len(service2DevicePlacementMatrix[idServ])):
                if service2DevicePlacementMatrix[idServ][idDev]==1:
                    nodeNumServ[idDev]=nodeNumServ[idDev]+1
                    nodeResUse[idDev]=nodeResUse[idDev]+self.ec.services_resources[idServ]
                    
        for idDev in range(0,len(service2DevicePlacementMatrix[0])):
            if self.ec.nodeResources[idDev] > 0:
                nodeResUse[idDev] = nodeResUse[idDev] / self.ec.nodeResources[idDev]
            else:
                nodeResUse[idDev] = 0
        
        #nodeResUse = sorted(nodeResUse)
        #nodeNumServ = sorted(nodeNumServ)        

        return nodeResUse, nodeNumServ 
        
    

random.seed(8)
# random.seed(time.time) # it will change every time

verbose_log = False

generatePlots = True

expDirectory = "exp_json"
plotFolder = "plots"

path = pathlib.Path(expDirectory)
path.mkdir(parents=True, exist_ok=True)

path_plots = pathlib.Path(plotFolder)
path.mkdir(parents=True, exist_ok=True)

abs_path = str(path.absolute())+"/"
abs_path_plot = str(path_plots.absolute())+"/"
ec = ExperimentConfiguration(abs_path)
ec.networkGeneration()
ec.appGeneration()
ec.userGeneration()

s = ServicePlacement(ec, abs_path)
matrix_result = s.solve()


# plots
plot_ = plotsGenerator(s, abs_path_plot)
plot_.plotNodeResource()
plot_.plotNodeResourcePerLevel()

