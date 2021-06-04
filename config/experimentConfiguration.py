#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

from .TopologyGenerator import TopologyGenerator
import networkx as nx
import json
import random

class ExperimentConfiguration:

    def __init__(self, expDir):

        self.expDirectory = expDir
        
        # Network
        self.IOT_DEVICES_NUM = 100
        self.NETWORK_LEVELS_NUM = 7 # IOT, GATEWAY, FOG0, FOG1, FOG2, FOG3, CLOUD
        self.REDUCTION_FACTOR_1 = 5 # IOT -> GATEWAY nodes reduction factor
        self.LINK_GENERATION_PROBABILITY_FOG0 = 0
        self.REDUCTION_FACTOR_2 = 3/2 # FOG-i -> FOG-i+1 nodes reduction factor (3/2 means multuplying by 2/3)
        self.HUB_GENERATION_PROBABILITY = 0.1

        self.PRIVACY_ASSIGNEMENT = "random.randrange(0,100) <= 20" #20 percento di probabilità di assegnare privacy

        # Node Ram      
        self.FUNC_NODE_RAM_FOG0 = "random.randrange(15, 19)"
        self.FUNC_NODE_RAM_FOG1 = "random.randrange(17, 21)"
        self.FUNC_NODE_RAM_FOG2 = "random.randrange(19, 23)"
        self.FUNC_NODE_RAM_FOG3 = "random.randrange(21, 25)"
        self.FUNC_NODE_RAM_CLOUD = "9999999"

        # Node speed [insts/ ms]
        self.FUNC_NODE_IPT_FOG0 = "random.randrange(200, 700)"
        self.FUNC_NODE_IPT_FOG1 = "random.randrange(300, 800)"
        self.FUNC_NODE_IPT_FOG2 = "random.randrange(400, 900)"
        self.FUNC_NODE_IPT_FOG3 = "random.randrange(500, 1000)"
        self.FUNC_NODE_IPT_CLOUD = "9999"

        # Propagation time
        self.FUNC_EDGE_PR_SAME_LEVEL = "random.randrange(5, 30)"
        self.FUNC_EDGE_PR_ADJ_LEVEL = "random.randrange(5, 10)"
        self.FUNC_EDGE_PR_NON_ADJ_LEVEL_1 = "random.randrange(7, 12)"
        self.FUNC_EDGE_PR_NON_ADJ_LEVEL_2 = "random.randrange(9, 15)"

        # Edges Bandwith [Bytes/ms]
        self.FUNC_EDGE_BW_SAME_LEVEL = "random.randrange(50000, 75000)"
        self.FUNC_EDGE_BW_ADJ_LEVEL = "random.randrange(50000, 75000)"
        self.FUNC_EDGE_BW_NON_ADJ_LEVEL_1 = "random.randrange(50000, 75000)"
        self.FUNC_EDGE_BW_NON_ADJ_LEVEL_2 = "random.randrange(50000, 75000)"

        # Apps 
        self.NUMBER_OF_APPS = 20
        self.FUNC_APP_GENERATION = "nx.gn_graph(random.randint(2,7))"
        self.FUNC_APP_DEADLINES = "random.randint(1000, 150000)"#"random.randint(2600, 6600)"
        self.FUNC_SERVICE_RESOURCES = "random.randint(1,4)" 
        self.FUNC_SERVICEINSTR = "random.randint(20000,60000)"
        self.FUNC_SERVICEMESSAGESIZE = "random.randint(1500000,4500000)"

        self.FUNC_REQUESTPROB = "random.random()/4"
        self.FUNC_USERREQRAT = "random.randint(200,1000)"
        
    def userGeneration(self):
        
        # Generation of the initial messagges
        # Every Gateways must call at least one application

        user_json = {}
        
        self.users = []
        
        self.apps_requests = []
        for i in range(0,self.NUMBER_OF_APPS):
            user_request_list = set()
            prob_of_requested = eval(self.FUNC_REQUESTPROB)
            at_least_one_allocated = False
            for j in self.gateways_devices:
                if random.random()<prob_of_requested:
                    one_user={}
                    one_user['app']=str(i)
                    one_user['message']="M.USER.APP."+str(i)
                    one_user['id_resource']=j
                    one_user['lambda']=eval(self.FUNC_USERREQRAT)
                    user_request_list.add(j)
                    self.users.append(one_user)
                    at_least_one_allocated = True
            if not at_least_one_allocated:
                j=random.randint(0,len(self.gateways_devices)-1)
                one_user={}
                one_user['app']=str(i)
                one_user['message']="M.USER.APP."+str(i)
                one_user['id_resource']=j
                one_user['lambda']=eval(self.FUNC_USERREQRAT)
                user_request_list.add(j)
                self.users.append(one_user)
            self.apps_requests.append(user_request_list)
        
        user_json['sources']=self.users
        
        file = open(self.expDirectory+ "usersDefinition.json","w")
        file.write(json.dumps(user_json))
        file.close()     

    def appGeneration(self):

        # Generation of the applications

        self.number_of_services = 0
        self.apps = []
        self.apps_resources = []
        self.apps_privacies = []
        self.apps_deadlines = {}
        self.services_resources = {}
        self.services_privacies = {}
        self.apps_source_service = []
        self.apps_source_message = []
        self.map_service_to_app = []
        self.map_serviceid_to_servicename = []
        self.apps_total_MIPS = []
        app_json = []
        privacies = []
        
        for i in range(self.NUMBER_OF_APPS):
            app_temp = {}
            labels_temp = {}
            APP = eval(self.FUNC_APP_GENERATION)
            
            # Privacy has to be calculated before the "inversion" of edges direction
            for n in APP.nodes:
                num_of_hops = len(nx.shortest_path(APP, n, 0))
                privacies.append(num_of_hops + 1)

            for n in range(len(APP.nodes)):
                labels_temp[n] = str(n)
            
            edge_list_ = []

            for e in APP.edges:
                edge_list_.append(e)

            # edges from 1 to 0 (as they are generated) get inverted (from 0 to 1)
            for e in edge_list_:
                APP.remove_edge(e[0], e[1])
                APP.add_edge(e[1], e[0])

            mapping = dict(zip(APP.nodes, range(self.number_of_services, self.number_of_services + len(APP.nodes))))
            APP = nx.relabel_nodes(APP, mapping)

            self.number_of_services = self.number_of_services + len(APP.nodes)

            self.apps.append(APP)

            for n in APP.nodes:
                self.services_resources[n] = eval(self.FUNC_SERVICE_RESOURCES)
                 
            self.apps_resources.append(self.services_resources)

            topologicorder_ = list(nx.topological_sort(APP))
            source = topologicorder_[0]
        
            self.apps_source_service.append(source)
            
            self.apps_deadlines[i] = eval(self.FUNC_APP_DEADLINES)
            app_temp['id']=i
            app_temp['name']=str(i)
            app_temp['deadline']=self.apps_deadlines[i]
        
            app_temp['module']=list()
        
            edge_number=0
            app_temp['message']=list()
        
            app_temp['transmission']=list()
        
            total_MIPS = 0
        
            for n in APP.nodes:
                self.map_service_to_app.append(str(i))
                self.map_serviceid_to_servicename.append(str(i)+'_'+str(n))
                node_temp={}
                node_temp['id']=n
                node_temp['name']=str(i)+'_'+str(n)
                p = privacies[n] if eval(self.PRIVACY_ASSIGNEMENT) else self.NETWORK_LEVELS_NUM
                self.services_privacies[n] = p
                node_temp['privacy'] = p
                node_temp['RAM']=self.services_resources[n]
                node_temp['type']='MODULE'
                if source==n:
                    edge_temp={}
                    edge_temp['id']=edge_number
                    edge_number = edge_number +1
                    edge_temp['name']="M.USER.APP."+str(i)
                    edge_temp['s']= "None"
                    edge_temp['d']=str(i)+'_'+str(n)
                    edge_temp['instructions']=eval(self.FUNC_SERVICEINSTR)
                    total_MIPS = total_MIPS + edge_temp['instructions']
                    edge_temp['bytes']=eval(self.FUNC_SERVICEMESSAGESIZE)
                    app_temp['message'].append(edge_temp)
                    self.apps_source_message.append(edge_temp)
                    
                    for o in APP.edges:
                        if o[0]==source:
                            transmission_temp = {}
                            transmission_temp['module']=str(i)+'_'+str(source)
                            transmission_temp['message_in']="M.USER.APP."+str(i)
                            transmission_temp['message_out']=str(i)+'_('+str(o[0])+"-"+str(o[1])+")"
                            app_temp['transmission'].append(transmission_temp)

                app_temp['module'].append(node_temp)

            self.apps_privacies.append(self.services_privacies)

            for n in APP.edges:
                edge_temp={}
                edge_temp['id']=edge_number
                edge_number = edge_number +1
                edge_temp['name']=str(i)+'_('+str(n[0])+"-"+str(n[1])+")"
                edge_temp['s']=str(i)+'_'+str(n[0])
                edge_temp['d']=str(i)+'_'+str(n[1])
                edge_temp['instructions']=eval(self.FUNC_SERVICEINSTR)
                total_MIPS = total_MIPS + edge_temp['instructions']
                edge_temp['bytes']=eval(self.FUNC_SERVICEMESSAGESIZE)
                app_temp['message'].append(edge_temp)
                dest_node = n[1]
                for o in APP.edges:
                    if o[0]==dest_node:
                        transmission_temp = {}
                        transmission_temp['module']=str(i)+'_'+str(n[1])
                        transmission_temp['message_in']=str(i)+'_('+str(n[0])+"-"+str(n[1])+")"
                        transmission_temp['message_out']=str(i)+'_('+str(o[0])+"-"+str(o[1])+")"
                        app_temp['transmission'].append(transmission_temp)
        
        
            for n in APP.nodes:
                outgoing_edges = False
                for m in APP.edges:
                    if m[0]==n:
                        outgoing_edges = True
                        break
                if not outgoing_edges:
                    for m in APP.edges:
                        if m[1]==n:
                            transmission_temp = {}
                            transmission_temp['module']=str(i)+'_'+str(n)
                            transmission_temp['message_in']=str(i)+'_('+str(m[0])+"-"+str(m[1])+")"
                            app_temp['transmission'].append(transmission_temp)
        
            self.apps_total_MIPS.append(total_MIPS)
        
            app_json.append(app_temp)
        
        with open(self.expDirectory+'apps_deadlines.json', 'w') as f:
            json.dump(self.apps_deadlines, f)

        file = open(self.expDirectory+ "appDefinition.json","w")
        file.write(json.dumps(app_json, indent=2))
        file.close()

    def networkGeneration(self):

        # Generation of the network topology

        network_graph = TopologyGenerator.generate_topology(
                                            iot_nodes=self.IOT_DEVICES_NUM,
                                            YAFS_sim=True,
                                            levels=self.NETWORK_LEVELS_NUM,
                                            fog0_reduction_factor=self.REDUCTION_FACTOR_1,
                                            edge_prob_0=self.LINK_GENERATION_PROBABILITY_FOG0,
                                            fogi_reduction_factor=self.REDUCTION_FACTOR_2,
                                            hub_prob=self.HUB_GENERATION_PROBABILITY,
                                            min_conn_to_up=self.NETWORK_LEVELS_NUM + 4, # VALUE TO BE CHECKED
                                            max_conn_to_up=self.NETWORK_LEVELS_NUM + 13,# VALUE TO BE CHECKED
                                            all_to_cloud=True)
        self.nodeResources = {}
        self.nodeSpeed = {}
                    
        for i in range(len(network_graph.nodes)):
            # GATEWAYS
            if network_graph.nodes[i]["level[z]"] == 1:
                network_graph.nodes[i]["RAM"] = 0
                network_graph.nodes[i]["IPT"] = 0
            # FOG0
            if network_graph.nodes[i]["level[z]"] == 2:
                network_graph.nodes[i]["RAM"] = eval(self.FUNC_NODE_RAM_FOG0)
                network_graph.nodes[i]["IPT"] = eval(self.FUNC_NODE_IPT_FOG0)
            # FOG1
            elif network_graph.nodes[i]["level[z]"] == 3:
                network_graph.nodes[i]["RAM"] = eval(self.FUNC_NODE_RAM_FOG1)
                network_graph.nodes[i]["IPT"] = eval(self.FUNC_NODE_IPT_FOG1)
            # FOG2
            elif network_graph.nodes[i]["level[z]"] == 4:
                network_graph.nodes[i]["RAM"] = eval(self.FUNC_NODE_RAM_FOG2)
                network_graph.nodes[i]["IPT"] = eval(self.FUNC_NODE_IPT_FOG2)
            # FOG3
            elif network_graph.nodes[i]["level[z]"] == 5:
                network_graph.nodes[i]["RAM"] = eval(self.FUNC_NODE_RAM_FOG3)
                network_graph.nodes[i]["IPT"] = eval(self.FUNC_NODE_IPT_FOG3)
            # CLOUD
            elif network_graph.nodes[i]["level[z]"] == 6:
                network_graph.nodes[i]["RAM"] = eval(self.FUNC_NODE_RAM_CLOUD)
                network_graph.nodes[i]["IPT"] = eval(self.FUNC_NODE_IPT_CLOUD)
            self.nodeResources[i]=  network_graph.nodes[i]["RAM"]
            self.nodeSpeed[i]= random.randint(500,1000) # Instruction/t [ms] - non so se è utile

        for u, v in network_graph.edges:
            if network_graph.nodes[u]["level[z]"] == network_graph.nodes[v]["level[z]"]:
                network_graph[u][v]["PR"] = eval(self.FUNC_EDGE_PR_SAME_LEVEL)
                network_graph[u][v]["BW"] = eval(self.FUNC_EDGE_BW_SAME_LEVEL)

            elif abs(int(network_graph.nodes[u]["level[z]"]) - int(network_graph.nodes[v]["level[z]"])) == 1:
                network_graph[u][v]["PR"] = eval(self.FUNC_EDGE_PR_ADJ_LEVEL)
                network_graph[u][v]["BW"] = eval(self.FUNC_EDGE_BW_ADJ_LEVEL)
            elif abs(int(network_graph.nodes[u]["level[z]"]) - int(network_graph.nodes[v]["level[z]"])) == 2:
                network_graph[u][v]["PR"] = eval(self.FUNC_EDGE_PR_NON_ADJ_LEVEL_1)
                network_graph[u][v]["BW"] = eval(self.FUNC_EDGE_BW_NON_ADJ_LEVEL_1)
            else:
                network_graph[u][v]["PR"] = eval(self.FUNC_EDGE_PR_NON_ADJ_LEVEL_2)
                network_graph[u][v]["BW"] = eval(self.FUNC_EDGE_BW_NON_ADJ_LEVEL_2)

        self.gateways_devices = [n for n in network_graph.nodes if network_graph.nodes[n]["level[z]"]== 1]
        self.G = network_graph
        
        

        file = open(self.expDirectory + "networkDefinition.json", 'w')
        json.dump(dict(entity=[dict(id=n, 
                                    RAM=network_graph.nodes[n]["RAM"], 
                                    IPT=network_graph.nodes[n]["IPT"],
                                    level=network_graph.nodes[n]["level[z]"]) for n in network_graph.nodes()],
                       link=[dict(s=u, 
                                  d=v, 
                                  PR=network_graph[u][v]["PR"],
                                  BW=network_graph[u][v]["BW"]) for u,v in network_graph.edges()]),
                                  file,
                                  indent=2)
        

if __name__ == "__main__":
    EC = ExperimentConfiguration()
    EC.networkGeneration()
    EC.appGeneration()
    EC.userGeneration()
