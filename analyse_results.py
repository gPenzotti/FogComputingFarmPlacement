#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy import stats
from pandas import Series, date_range
import json
import matplotlib.patheffects as pe

time = 1000000
pathSimple ="exp_results/"
pathJson ="exp_json/"

def getRbyApp(df,dtmp):
    # Computes the Response time by (App,User)
    # It takes into account the number of messages (mode) that it sends each (App,User)
    # - df : csv file, - dtmp: user lines grouped by (app, user)
    dealines = list()
    with open(pathJson+'apps_deadlines.json', 'r') as f:
        dealines = json.load(f)
    myDeadlines = dealines
    # print(myDeadlines)
    dr = pd.DataFrame(columns=['app', 'user', 'avg','std','m','r','invalid','over']) #m - number of msgs sented
    times = []
    ixloc =0

    timed = list()

    for g in dtmp.keys():
        # Each communication of each user has an unique id along all messages exchanges!  
        ids = dtmp[g]
        responses = []
        messages = []
        over = 0
        #Firstly, it computes the mode in all the app,user transmissions
        for i in ids:  
            messages.append(df[df.id==i].shape[0]) # number of messages send by the user app
       
        # Requests with a inferior number of messages are filtered
        # They're caused by a fault link
        msg = np.array(messages)
        mode = stats.mode(msg).mode[0] #mode is the most present value, so all the executed app msgs exchange

        # Secondly, if each transmission has the same mode then the time is storaged
        invalid =0
        for i in ids:
            dm = df[df.id==i]
            if mode == dm.shape[0]:
                r =dm['time_out'].max()-dm['time_emit'].min()
                timed.append(r)
                if r <= myDeadlines[str(g[0])]:
                    responses.append(r)
                    times.append(dm['time_emit'].min())
                else:
                       over+=1
            else:
                invalid+=1
        
        resp = np.array(responses)
   
        avg = resp.mean()
        dsv = resp.std()
        dr.loc[ixloc] = [g[0],g[1],avg,dsv,mode,resp,invalid,over]
        # print (g,"\t",len(dtmp[g]),"\t",invalid,"\t",over)
        print (dr.loc[ixloc])
        print("-"*10)
        ixloc+=1
    #print(min(timed), max(timed)) #per farsi una idea nel settaggio deadline
    return dr,times

### It computes the Response of each app
def getAllR(dr):
    dar = pd.DataFrame(columns=['app','r'])
    ixloc  =0
    for k,g in dr.groupby(["app"]):
        values = np.array([])
        for item in g.values:
            values= np.concatenate((values,item[5]), axis=0) #item 5 is "r"
        dar.loc[ixloc] = [k,values]
        ixloc+=1
    return dar

# The csv file result of a YAFS simulationthe is a cvs as follow:
# type,app,module,message,DES.src,DES.dst,TOPO.src,TOPO.dst,module.src,service,time_in,time_out,time_emit,time_reception
# - type It represent the entity who run the taks: a module (COMP_M) or an actuator (SINK_M)
# - app application name
# - module Module or service who manages it
# - service service time
# - message message name
# - DES.src DES process who send this message
# - DES.dst DES process who receive this message (the previous module)
# - TOPO.src ID node topology where the DES.src module is deployed
# - TOPO.dst ID node topology where the DES.dst module is deployed
# - module.src the module or service who send this message
# - service service time
# - time_in time when the module accepts it
# - time_out time when the module finishes its process
# - time_emit time when the message was sent
# - time_reception time when the message is accepted by the module
# - id identify the communication of the user,app


path = pathSimple+"Results__%s_0"%time
pathRND = pathSimple+"Results_RND_FAIL__%s_0.csv"%time
NEW = False

# Normal loads
df = pd.read_csv(path + ".csv")
dtmp = df[df["module.src"]=="None"].groupby(['app','TOPO.src'])['id'].apply(list)# dtmp group all the source msgs (from the user) by app and TOPO.src (node who sent this msg)
dr,timeC = getRbyApp(df,dtmp)
drAll = getAllR(dr)

print(min(timeC),max(timeC))

# fails
df4 = pd.read_csv(pathRND)
dtmp5 = df4[df4["module.src"]=="None"].groupby(['app','TOPO.src'])['id'].apply(list)
drFAILR,timesFailR = getRbyApp(df4,dtmp5)
drAllFAILR = getAllR(drFAILR)

###
### Plots
###

## results with fails
dFailsCR = pd.DataFrame(index=np.array(timesFailR).astype('datetime64[s]')) # raccolgo tutti i tempi di inizio richiesta
dFailsCR["QTY"]=np.ones(len(timesFailR)) # array tutto a 1
dFailsCR = dFailsCR.resample('500s').agg(dict(QTY='sum')) # contro le richieste ogni 500s
QTYFailsCR = dFailsCR.QTY.values # solo i valori

## Clean results
dC = pd.DataFrame(index=np.array(timeC).astype('datetime64[s]'))
dC["QTY"]=np.ones(len(timeC))
dC = dC.resample('500s').agg(dict(QTY='sum'))
QTYC = dC.QTY.values

# np.save("res_analysis/QTYC.npy",QTYC)
# np.save("res_analysis/QTYFailsCR.npy",QTYFailsCR)
# dr.to_pickle("res_analysis/dr.pkl")

ticks = range(len(QTYC))
ticksV = np.array(ticks)*10

## Unifiend length (0 at the end)
QTYFailsCR = np.concatenate((QTYFailsCR,np.zeros(len(QTYC)-len(QTYFailsCR))))

fig, ax = plt.subplots(figsize=(32.0,8.0))
ax.plot(ticks, QTYC,color='#8c79ab',alpha=1.,linewidth=2)
ax.plot(ticks, QTYFailsCR, color='#c48143',alpha=1.,linewidth=2)

z = np.polyfit(ticks, QTYC, 10) 
p = np.poly1d(z) 
ax1 = ax.plot(ticks,p(ticks),"-",color='#a389de',linewidth=6,label="Total requests",path_effects=[pe.Stroke(linewidth=8, foreground='#760da2'), pe.Normal()])

idx = np.isfinite(QTYFailsCR) & np.isfinite(QTYFailsCR) 
z1 = np.polyfit(np.array(ticks)[idx], np.array(QTYFailsCR)[idx], 10)
p1 = np.poly1d(z1) 
ax2 = ax.plot(ticks,p1(ticks),"-",color='#d6b55a',linewidth=6,label="Total request with failures",path_effects=[pe.Stroke(linewidth=8, foreground='#ad4c1c'), pe.Normal()])

ax.set_xlabel("Simulation time", fontsize=22)
ax.set_ylabel("Number of requests", fontsize=22)
ax.tick_params(labelsize=20)
ax.set_xlim(-20,2020)

plt.legend(loc="lower left",fontsize=20)
plt.tight_layout()
plt.savefig('Sim_result.pdf', format='pdf', dpi=600)
plt.show()




# def set_box_color(bp, color):
#     plt.setp(bp['boxes'], color=color)
#     plt.setp(bp['whiskers'], color=color)
#     plt.setp(bp['caps'], color=color)
#     plt.setp(bp['medians'], color=color)
#
# def drawBoxPlot_Both_USER_ax(app,dr,drILP,ax):
#    data_a=dr[dr.app==app].r.values
#    data_b=drILP[drILP.app==app].r.values
#    ticks = list(np.sort(dr[dr.app==app].user.unique()))
#    bpl = ax.boxplot(data_a, positions=np.array(range(len(data_a)))*2.0-0.4, sym='', widths=0.55,
#                     whiskerprops = dict(linewidth=2),
#                    boxprops = dict(linewidth=2),
#                     capprops = dict(linewidth=2),
#                    medianprops = dict(linewidth=2))
#    bpI = ax.boxplot(data_b, positions=np.array(range(len(data_b)))*2.0+0.4, sym='', widths=0.55,
#                        whiskerprops = dict(linewidth=2),
#                    boxprops = dict(linewidth=2),
#                     capprops = dict(linewidth=2),
#                    medianprops = dict(linewidth=2))
#    set_box_color(bpl, '#a6bddb')
#    set_box_color(bpI, '#e34a33')
#    ax.get_xaxis().set_ticks(range(0, len(ticks) * 2, 2))
#    ax.set_xticklabels(ticks)
#    ax.set_xlim(-2, len(ticks)*2)
#    ax.plot([], c='#a6bddb', label="Simulation",linewidth=3)
#
# fig, axlist = plt.subplots(nrows=4, ncols=5, figsize=(14, 10))
# for idx,ax in enumerate(axlist.flatten()):
#    drawBoxPlot_Both_USER_ax(idx,dr,dr,ax)
#
# fig.subplots_adjust(top=0.9, left=0.1, right=0.9, bottom=0.12)
# fig.subplots_adjust(hspace=0.4,wspace=0.35)
# axlist.flatten()[-2].legend(loc='upper center', bbox_to_anchor=(-0.85, -0.43), ncol=4,fontsize=16 )
#
# axlist[3][2].set_xlabel('IoT devices (Gateways id.)',fontsize=14)
# axlist[1][0].set_ylabel('Response time (ms)',fontsize=14)
# axlist[1][0].yaxis.set_label_coords(-0.4, 0)
# ax.tick_params(labelsize=12)
# plt.savefig('Boxplot.pdf', format='pdf', dpi=600)
# plt.show()



