#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt


class plotsGenerator:
    
    def __init__(self, sp, resultFolder):
        
        self.sp = sp
        self.terminal = True
        self.resultFolder = resultFolder


    def plotNodeResource(self):
        ####Plot for node ordered vs service resources
        #nodeid:request
        #statisticsNodesRequest = {}
    
        fig, ax = plt.subplots(figsize=(8.5,5.5))

        plt.xlabel('Node id',fontsize=18)
        plt.ylabel('Resource usage (%)',fontsize=18)


        vlines = list()
        level = 1
        for i,v in enumerate(self.sp.nodeResUse):
            l = self.sp.ec.G.nodes[i]["level[z]"]
            if l != level: 
                level = l
                vlines.append(i)


        plt.plot(self.sp.nodeResUse, c="#332747", label="level order",linewidth=2.0)

        for i in vlines:
            plt.axvline(x=i, ymin = 0, linewidth=2.0, c = "#ff0000" )# #CC6666
        
        plt.fill_between([i for i in range(len(self.sp.nodeResUse))],  0, self.sp.nodeResUse, facecolor="#a686db", alpha=.7)

        plt.yticks(fontsize=16)
        plt.xticks(fontsize=16)
    
 
        plt.grid(False)
        if self.terminal:
            plt.show()
    
        fig.savefig('./'+self.resultFolder+'/nodevsresourceuse.pdf',format='pdf')
    
        plt.close(fig)    
        
    
    def plotNodeResourcePerLevel(self):
        ####Plot for node ordered vs service resources
        #nodeid:request
        #statisticsNodesRequest = {}
        

        levels = [0 for i in range(0,7)]
        level_counter = 0
        level = 1
        for i in self.sp.ec.G.nodes:
            l = self.sp.ec.G.nodes[i]["level[z]"]
            if l != level: 
                if levels[level] != 0:
                    levels[level] = float(levels[l-1]) / level_counter
                print(level, level_counter, levels[level])

                level = l
                level_counter = 0
            else:
                levels[l] = levels[l] + self.sp.nodeResUse[i]
            
            level_counter = level_counter  +1

        labels = ['gways', 'fog T1', 'fog T2','fog T3','fog T4', 'cloud']
        values = levels[1:]

        print(labels)
        print(values)
        
        
        fig, ax = plt.subplots(figsize=(8.0,5.0))

        plt.xlabel(labels,fontsize=18)
        plt.ylabel(values,fontsize=18)
        plt.barh(labels, values)
        plt.yticks(fontsize=16)
        plt.xticks(fontsize=16)

        plt.xlim(0,0.35)

        for i, v in enumerate(values):
            x = v + 0.05
            ax.text(x, i + .25, str("%.4f" % v), color='blue', fontweight='bold')
    
        plt.grid(False)
        if self.terminal:
            plt.show()
    
        plt.savefig('./'+self.resultFolder+'/nodevsresourceuse_level.pdf',format='pdf')
    
        plt.close(fig) 
