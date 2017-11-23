from __future__ import division
from yahmm import *
import time
import collections
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import pylab
from graphviz import Digraph

BIOALPHABET="ARNDCQEGHILKMFPSTWYVBZX".split() #Protein alphabet

#plot a profile-HMM based on its structure using graphviz
def plotHMM(edges,match_ids,delete_ids,insert_ids,matchEmissionProbs,sequences):
	g = Digraph('G', filename='cluster.gv',format="pdf",engine="dot")

	c0 = Digraph('cluster_0')
	c0.body.append('style=filled')
	c0.body.append('color=white')
	c0.attr('node', shape='box')
	c0.node_attr.update(color='orange', style='filled')
	match_ids_without_StartEnd=match_ids[:]
	index=match_ids.index("Global Sequence Aligner-end")
	match_ids_without_StartEnd.pop(index)
	index=match_ids.index("Global Sequence Aligner-start")
	match_ids_without_StartEnd.pop(index)
	for match_id in match_ids:
		c0.node(match_id)

	c1 = Digraph('cluster_1')
	c1.body.append('style=filled')
	c1.body.append('color=white')
	c1.attr('node', shape='doubleoctagon')
	c1.node_attr.update(color="orange",penwidth="1")
	for insert_id in insert_ids:
		c1.node(insert_id)
	c1.edge_attr.update(color='white')
	for i in range(len(insert_ids)-1):
		c1.edge(insert_ids[i], insert_ids[i+1])	

	c2 = Digraph('cluster_2')
	c2.body.append('style=filled')
	c2.body.append('color=white')
	c2.attr('node', shape='circle')
	c2.node_attr.update(color="orange",penwidth="2")
	for  delete_id in delete_ids:
		c2.node(delete_id)

	c3 = Digraph('cluster_3')
	c3.body.append('style=filled')
	c3.body.append('color=white')
	c3.attr('node', shape='box')
	c3.node_attr.update(color='white', style='filled',fontsize="14")
	mIds=[]
	for i, match in enumerate(matchEmissionProbs):
		s=match_ids_without_StartEnd[i]
		for j,symbol in enumerate(match):
			if match[symbol]>0.05: s+= "%s"%symbol+"   %.2f"%match[symbol]+"\n"
		mIds.append(s)
	c3.edge_attr.update(color='white')
	for mid in mIds: 
		c3.node(mid)
	for i in range(len(mIds)-1):
		c3.edge(mIds[i], mIds[i+1])

	#the graph is basicaly split in 4 clusters
	g.subgraph(c3)
	g.subgraph(c0)
	g.subgraph(c1)
	g.subgraph(c2)

	#add edges
	for h in edges: g.edge(h[0], h[1], label="%.6f"%h[2],len='1.00')

	g.node('Global Sequence Aligner-start', shape='box')
	g.node('Global Sequence Aligner-end', shape='box')
	g.edge_attr.update( arrowsize='0.5')
	g.body.extend(['rankdir=LR', 'size="160,100"'])
	g.view()

#a simpler profile-HMM plotter
def plotHMMsimple(profHMM,match_ids,delete_ids,insert_ids):
	G = nx.DiGraph()
	for state1 in profHMM:
		for state2 in profHMM[state1]:
			G.add_edges_from([(state1,state2)], weight=profHMM[state1][state2])
	edge_labels=dict([((u,v,),"%.2f"%d['weight']) for u,v,d in G.edges(data=True)])
	edge_colors = ['black' for edge in G.edges()]
	values =[]
	labels={}
	i=0
	for node in G.nodes():
	 if node in match_ids: 	values.append(0.5)
	 if node in insert_ids: values.append(0.2)
	 if node in delete_ids: values.append(0)
	 i+=1
	pos=nx.circular_layout(G)
	pos={}
	for id in match_ids:
		if id not in ["model.star","model.end"]:
			pos.update({id:np.array([1+match_ids.index(id),0])})
		if id=="model.start":
			pos.update({id:np.array([-1,2])})
		if id=="model.end":
			pos.update({id:np.array([1+match_ids.index(id)+1,2])})
	for id in delete_ids:
		pos.update({id:np.array([1.5+delete_ids.index(id),4])})
	for id in insert_ids:
		pos.update({id:np.array([1+insert_ids.index(id),2])})
	nx.draw_networkx_labels(G,pos,font_size=12)
	nx.draw_networkx_edge_labels(G,pos,edge_labels=edge_labels,font_size=12)
	nx.draw(G,pos,node_color = values, node_size=1000,edge_color=edge_colors,edge_cmap=plt.cm.Reds)
	plt.show()

#return the following structures based on an alignment: one (profHMM) containing the state transition probabilities and the other one (matchEmissionProbs) the emission probabilities of each match state. Also match states, insertion, detele state ids
def computeProfHMMStructurefromAlignment(sequences,Alphabet=BIOALPHABET,gapRatiotoMatchStates=0.4,pseudoCountTransition=1,sequenceWeight=10,pseudoEmissionCount=1,plot=False):
	L=len(sequences[0])
	ns=len(sequences)

	#Emission prob template with psuedo emission counts
	alphabet_distribution={}
	for char in Alphabet: alphabet_distribution.update({char:pseudoEmissionCount})

	#compute which columns will become match states, emission probs per state
	#the blueprint is a vector that helps us create the profHMM later
	blueprint=[]
	matchEmissionProbs=[]
	for i in range(L):
		column=np.array([sequences[j][i] for j in range(ns): column.append()])

		#most frequent symbol per column ratio 
		most_frequent_ratio=collections.Counter(column[np.where(column!="-")]).most_common(1)[0][1]/len(column)
	
		number_of_gaps=np.where(column=="-")[0].shape[0]
		gap_ratio=number_of_gaps/len(column)
		if gap_ratio>=gapRatiotoMatchStates :# #this is an insert state
			blueprint.append(1) 
		else:   #this is a match state. We compute the emission probs
			blueprint.append(0)
			newMatchEmissionProbs=alphabet_distribution.copy()
			counts=collections.Counter(column)
			for char in counts:
				if char!="-": newMatchEmissionProbs[char]+=counts[char]*sequenceWeight #important formula
			#convert to probs
			sum=0
			for char in newMatchEmissionProbs: sum+=newMatchEmissionProbs[char]
			for char in newMatchEmissionProbs: newMatchEmissionProbs[char]=newMatchEmissionProbs[char]/sum
			matchEmissionProbs.append(newMatchEmissionProbs)
	blueprint=np.array(blueprint) #we have our blueprint
	
	#generate initial structure
	numberOfMatchStates=np.where(blueprint==0)[0].shape[0]+2 #plus begin end
	numberOfDeleteStates=np.where(blueprint==0)[0].shape[0]+2 
	numberOfInsertStates=np.where(blueprint==0)[0].shape[0]+2
	pseudo=pseudoCountTransition #the pseudo count added to every transition between states
	weight=sequenceWeight #the weight of each sequence in terms of counts

	#create structure of states
	profHMM={} #the most important structure of the function. holds the transition probs
	match_ids=[]
	insert_ids=[]
	delete_ids=[]
	for i in range(0,numberOfMatchStates):
		profHMM.update({"M"+str(i):{}})
		match_ids.append("M"+str(i))
		#MATCH.append("M"+str(i+1))
	for i in range(0,numberOfDeleteStates):
		profHMM.update({"D"+str(i):{}})
		delete_ids.append("D"+str(i))
	for i in range(0,numberOfInsertStates):
		profHMM.update({"I"+str(i):{}})
		insert_ids.append("I"+str(i))

	#assign transition probabilities
	for i in range(0,numberOfInsertStates-1):
		profHMM[insert_ids[i]].update({match_ids[i+1]:pseudo,insert_ids[i]:pseudo,delete_ids[i+1]:pseudo})
	#Delete states
	for i in range(0,numberOfDeleteStates-1):
		profHMM[delete_ids[i]].update({match_ids[i+1]:pseudo, delete_ids[i+1]:pseudo,insert_ids[i]:pseudo})
	#match states
	for i in range(0,numberOfMatchStates-1):
		profHMM[match_ids[i]].update({match_ids[i+1]:0, delete_ids[i+1]:pseudo,insert_ids[i]:pseudo})

	#compute path on hmm for each sequence and update state transition counts
	for sequence in sequences:
		sequence=np.array(list(sequence))
		gap_blueprint=np.where(sequence=="-")[0]
		gp=np.zeros(len(blueprint))
		gp[gap_blueprint]=1
		path=["M0"]
		count=0
		for i in range(len(blueprint)):
		 	if gp[i]==0 and blueprint[i]==0: 
		 		count+=1
		 		path.append("M"+str(count))
		 	if gp[i]==1 and blueprint[i]==0: 
		 		count+=1
		 		path.append("D"+str(count)) 		
		 	if gp[i]==1 and blueprint[i]==1: nothing=1#path.append("d")
		 	if gp[i]==0 and blueprint[i]==1: path.append("I"+str(count))
		path.append(match_ids[-1])
		for i in range(len(path)-1):profHMM[path[i]][path[i+1]]+=weight

	profHMM[match_ids[0]].update( {delete_ids[1]:0,insert_ids[0]:0})

	#delete first and last deletion states
	todel=[]
	for state1 in profHMM:
		for state2 in profHMM[state1]:
			if state2 in [delete_ids[0],delete_ids[-1]]:
				todel.append([state1,state2])
		if state1 in [delete_ids[0],delete_ids[-1]]:
				todel.append([state1])
	for m in todel:
		if len(m)==2:del profHMM[m[0]][m[1]]
		if len(m)==1:del profHMM[m[0]]
	delete_ids.pop(-1)
	delete_ids.pop(0)

	#delete last insertion state
	del profHMM[insert_ids[-1]]
	insert_ids.pop(-1)

	#change names of first and last match states
	todel=[]
	for state1 in profHMM:
		for state2 in profHMM[state1]:
			if state2==match_ids[0]: todel.append([state1,state2])
			if state2==match_ids[-1]:todel.append([state1,state2])
		if state1==match_ids[0]:todel.append([state1])
		if state1==match_ids[-1]:todel.append([state1])
	for m in todel:
		if len(m)==2:
			temp=profHMM[m[0]][m[1]]
			del profHMM[m[0]][m[1]]
			if m[1]==match_ids[0]:profHMM[m[0]].update({"model.start":temp})	
			if m[1]==match_ids[-1]:profHMM[m[0]].update({"model.end":temp})		
		if len(m)==1: 
			temp=profHMM[m[0]]
			del profHMM[m[0]]
			if m[0]==match_ids[0]:profHMM.update({"model.start":temp})	
			if m[0]==match_ids[-1]:profHMM.update({"model.end":temp})	
	match_ids[0]="model.start"
	match_ids[-1]="model.end"

	#Convert counts to probs
	for state1 in profHMM:
		sum=0
		for state2 in profHMM[state1]: sum+=profHMM[state1][state2]
		if sum!=0:
			for state2 in profHMM[state1]: profHMM[state1][state2]=profHMM[state1][state2]/sum
		else:
		 	for state2 in profHMM[state1]: profHMM[state1][state2]=0.5 #to agree with matlab
	return profHMM,matchEmissionProbs,match_ids,insert_ids,delete_ids,blueprint

#bake a profile HMM model from the structures created by computeProfHMMStructurefromAlignment
def createProfileHMMfromStructure(profHMM,matchEmissionProbs,match_ids,insert_ids,delete_ids,Alphabet=BIOALPHABET,uniformInsertionProbs=True,nullEmission=[]):
	model = Model( name="Global Sequence Aligner" )
	
	#compute the symbol distribution for insertion emissions
	if uniformInsertionProbs:
		probOfChar=1/len(Alphabet)
		distribution={}
		for char in Alphabet: distribution.update({char:probOfChar})
		i_d = DiscreteDistribution( distribution )
	else:
		i_d = DiscreteDistribution( nullEmission )


	#create the insert states, each with a uniform insertion distribution
	I=[]
	S={}
	for insert_id in insert_ids:
		i0 = State( i_d, name=insert_id )
		S.update({insert_id:i0})

	#create the match states with small chances of mismatches
	match_ids_without_StartEnd=match_ids[:]
	match_ids_without_StartEnd.pop(-1)
	match_ids_without_StartEnd.pop(0)
	for match_id in match_ids_without_StartEnd:
		index=match_ids_without_StartEnd.index(match_id)
		emissionProb=matchEmissionProbs[index]
		m1 = State( DiscreteDistribution(emissionProb) , name=match_id )
		S.update({match_id:m1})
	
	#create the silent delete states
	D=[]
	for delete_id in delete_ids:
		d1 = State( None, name=delete_id )
		S.update({delete_id:d1})

	#add all the states to the model
	model.add_states([S[i] for i in S])

	for state1 in profHMM:
		if state1!="model.end":
			for state2 in profHMM[state1]:
				if (state1 not in ["model.start","model.end"]) and (state2 not in ["model.start","model.end"]) :
					model.add_transition( S[state1], S[state2], profHMM[state1][state2] )
				if state1=="model.start":model.add_transition( model.start, S[state2], profHMM[state1][state2] )
				if state1=="model.end": model.add_transition( model.end, S[state2], profHMM[state1][state2] )
				if state2=="model.start": model.add_transition( S[state1], model.end, profHMM[state1][state2] )
				if state2=="model.end":model.add_transition( S[state1], model.end, profHMM[state1][state2] )
	model.bake()
	return model

#create a profile HMM based on an alignment of sequences on an alphabet
def profileHMM(alignment,alphabet=BIOALPHABET,gapRatiotoMatchStates=0.2,pseudoCountTransition=1,sequenceWeight=10,pseudoEmissionCount=1,plot_=False,uniformInsertionProbs=True,nullEmission=[]):
	print "Create structure..."
	profHMM,matchEmissionProbs,match_ids,insert_ids,delete_ids,blueprint=computeProfHMMStructurefromAlignment(alignment,alphabet,gapRatiotoMatchStates,pseudoCountTransition,sequenceWeight,pseudoEmissionCount,plot_)

	print "Bake profile HMM model..."
	model=createProfileHMMfromStructure(profHMM,matchEmissionProbs,match_ids,insert_ids,delete_ids,alphabet,uniformInsertionProbs,nullEmission)
	return model,blueprint

#compare a single sequence to a profile HMM using viterbi decoding
def compareSequenceToProfHMM(model,sequence):
	logp, path = model.viterbi( list(sequence.replace("-","")) )
	return logp,path


    