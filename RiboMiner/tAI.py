#!/usr/bin/env python
# -*- coding:UTF-8 -*-
'''
@Author: Li Fajin
@Date: 2019-08-16 16:50:04
@LastEditors: Li Fajin
@LastEditTime: 2019-08-30 17:12:02
@Description:
This script is used for local tAI index calculation.
input
1) fasta files used for analysis. All files should be split by comma e.g. 1.fasta,2.fasta,3.fasta[required]
2) tRNA gene copy numbers, download from the GtRNAdb
col0: chr
col1: tRNA
col2: start position
col3: stop position
col4: isotype[AA]
col5: Anticodon [required]
col6: upstream sequence
col7: downstream sequence

Notes:
1) The script could output two files: one contains local tAI at each position along transcripts. And the other contains the global tAI.
2) input sequence must be cds sequences which could be generated by GetProteinCodingSequence.py.

'''

from .FunctionDefinition import *
import re
from collections import Counter
from math import pow
from operator import mul
from functools import reduce
from itertools import chain
from itertools import groupby
import Bio.Data.CodonTable as ct


def prepare_datas(tRNA_GCN_file,Codon_table):
	'''According to the GtRNAdb, some anti-codons(tRNA) such as AAA do not have gene copy numbers, so when I construct the codon_anticodon dict,
	 I did not add those codons without copy numbers. Actually, we can add those tRNAs as long as we define the copy numbers equals to 0 at the tRNA_GCN files,
	 in which case, when we calculate the absolute adaptiveness values, we dont have to design the numbers of tRNA, with just only one calculating methods,namely,
	 when len(tRNAs)==2
	 Reference:
	 1) 2004-Mario-tAI
	 2) 2010-Tamir Tuller-Cell
	 '''

	tRNA=pd.read_csv(tRNA_GCN_file,sep='\t')
	codonList=Codon_table.keys()
	tRNA_GCNs=Counter(tRNA['Anticodon'])
	tRNA_GCNs={tRNA.replace("T","U"):tRNA_GCNs[tRNA] for tRNA in tRNA_GCNs.keys()}
	codon_anticodon={
		'UUU':['GAA','AAA'], ## AAA copy number equals to 0
		'UUC':['GAA'],
		'UUA':['UAA'],
		'UUG':['UAA','CAA'],
		'UCU':['AGA','GGA'], ## GGA copy number equals to 0
		'UCC':['AGA','GGA'],
		'UCA':['AGA','UGA'],
		'UCG':['UGA','CGA'],
		'UAU':['AUA','GUA'],
		'UAC':['GUA'],
		'UAA':['UUA'],
		'UAG':['CUA'],
		'UGU':['ACA','GCA'],
		'UGC':['GCA'],
		'UGA':['UCA'],
		'UGG':['CCA'],
		'CUU':['AAG','GAG'], # GAG copy number equals to 0
		'CUC':['AAG','GAG'],
		'CUA':['AAG','UAG'],
		'CUG':['UAG','CAG'],
		'CCU':['AGG','GGG'],
		'CCC':['AGG','GGG'],
		'CCA':['AGG','UGG'],
		'CCG':['UGG','CGG'],
		'CAU':['GUG','AUG'],
		'CAC':['GUG'],
		'CAA':['UUG'],
		'CAG':['UUG','CUG'],
		'CGU':['ACG','GCG'], ## GCG 0
		'CGC':['ACG','GCG'],
		'CGA':['ACG','UCG'],
		'CGG':['UCG','CCG'],
		'AUU':['AAU','GAU'],
		'AUC':['AAU','GAU'],
		'AUA':['AAU','GAU','UAU'],
		'AUG':['CAU'],
		'ACU':['AGU','GGU'],
		'ACC':['AGU','GGU'], ## GGU 0
		'ACA':['AGU','UGU'],
		'ACG':['UGU','CGU'],
		'AAU':['AUU','GUU'],
		'AAC':['GUU'],
		'AAA':['UUU'],
		'AAG':['UUU','CUU'],
		'AGU':['ACU','GCU'],
		'AGC':['GCU'],
		'AGA':['UCU'],
		'AGG':['UCU','CCU'],
		'GUU':['AAC','GAC'], ## GAC 0
		'GUC':['AAC','GAC'],
		'GUA':['AAC','UAC'],
		'GUG':['UAC','CAC'],
		'GCU':['AGC','GGC'], ## GGC 0
		'GCC':['AGC','GCC'],
		'GCA':['AGC','UGC'],
		'GCG':['UGC','CGC'],
		'GAU':['GUC','AUC'], ## AUC 0
		'GAC':['GUC'],
		'GAA':['UUC'],
		'GAG':['UUC','CUC'],
		'GGU':['GCC','ACC'], ## ACC 0
		'GGC':['GCC','ACC'],
		'GGA':['UCC','ACC'],
		'GGG':['UCC','CCC']
	}
	anticodonList=set(list(reduce(chain,codon_anticodon.values())))
	for anticodon in anticodonList:
		if anticodon not in tRNA_GCNs.keys():
			tRNA_GCNs[anticodon]=0
		else:
			pass
	wobble_pair=["I:U","G:C","U:A","C:G","G:U","I:C","I:A","U:G","L:A"] ## A could transfer to I on natural conditions,A:A ==>> I:A
	wobble_pair_Svalues=[0,0,0,0,0.41,0.28,0.999,0.68,0.89] # 0.41(2004)/0.561(2010)
	Sij={k:v for k,v in  zip(wobble_pair,wobble_pair_Svalues)}
	return codonList,tRNA_GCNs,Sij,codon_anticodon

def reverse_complement(seq):
	seq_rc=''.join(["AUCGN"["UAGCN".index(n)] for n in seq[::-1]])
	return seq_rc

def calculate_absolute_adaptiveness_W(codon,GCN,Sij,codon_anticodon):
	anticodon=reverse_complement(codon)
	tRNAs=codon_anticodon[codon]
	if len(tRNAs)==1:
		if tRNAs[0][0]=="A":
			W=(1-Sij["I:U"])*GCN[tRNAs[0]]
		elif tRNAs[0][0]=="G":
			W=(1-Sij["G:C"])*GCN[tRNAs[0]]
		elif tRNAs[0][0]=="U":
			W=(1-Sij["U:A"])*GCN[tRNAs[0]]
		elif tRNAs[0][0]=="C":
			W=(1-Sij["C:G"])*GCN[tRNAs[0]]
		else:
			raise EOFError("Codons error!")
	elif len(tRNAs)==2:
		if codon[-1]=="U" and anticodon[0]=="A":
			W=(1-Sij["I:U"])*GCN[anticodon]+(1-Sij["G:U"])*GCN["G"+anticodon[1:]]
		if codon[-1]=="C" and anticodon[0]=="G":
			W=(1-Sij["G:C"])*GCN[anticodon]+(1-Sij["I:C"])*GCN["A"+anticodon[1:]]
		if codon[-1]=="A" and anticodon[0]=="U":
			W=(1-Sij["U:A"])*GCN[anticodon]+(1-Sij["I:A"])*GCN["A"+anticodon[1:]]
		if codon[-1]=="G" and anticodon[0]=="C":
			W=(1-Sij["C:G"])*GCN[anticodon]+(1-Sij["U:G"])*GCN["U"+anticodon[1:]]
	elif len(tRNAs)==3:
		W=(1-Sij["U:A"])*GCN[anticodon]+(1-Sij["I:A"])*GCN["A"+anticodon[1:]] ## no G:A wooble pairs
	return W

def calculate_geometric_mean(values):
	length=len(values)
	return pow(reduce(mul,values),1/length)


def calculate_relative_adaptiveness_w(codonList,GCN,Sij,codon_anticodon):
	w={}
	for codon in codonList:
		codon=codon.replace("T","U")
		W=calculate_absolute_adaptiveness_W(codon,GCN,Sij,codon_anticodon)
		w[codon]=W
	W_max=np.max(list(w.values()))
	W_without_zero=[w for w in w.values() if w !=0]
	W_geometric_mean=calculate_geometric_mean(W_without_zero)
	for k,v in w.items():
		if v != 0:
			w[k]=v/W_max
		else:
			w[k]=W_geometric_mean
	return w


def get_trans_frame_tAI(transcriptFile,codonList,GCN,Sij,codon_anticodon,upLength,downLength):
	fastaDict=fastaIter(transcriptFile)
	tAIDict=calculate_relative_adaptiveness_w(codonList,GCN,Sij,codon_anticodon)
	in_selectTrans=fastaDict.keys()
	startAI=np.zeros(int(upLength+downLength+1),dtype='float64')
	stoptAI=np.zeros(int(upLength+downLength+1),dtype='float64')
	startAIList=[]
	stoptAIList=[]
	startPos=[]
	stopPos=[]
	passTransSet=set()
	tAI={}
	tAI_codon={}
	i=len(in_selectTrans)
	for trans in in_selectTrans:
		i-=1
		tmptAI=[]
		cds_seq=fastaDict[trans]
		cds_seq=re.sub("T","U",cds_seq)
		if len(cds_seq)%3 != 0:
			continue
		codon_seq=[cds_seq[i:i+3] for i in np.arange(0,len(cds_seq),3)]
		for codon in codon_seq:
			tmptAI.append(tAIDict[codon])
		# normValue=np.sum(tmptAI)
		# normValue=np.mean(tmptAI) ## huge difference between two normalization methods
		# print("normvalue: ",normValue)
		tAI[trans]=calculate_geometric_mean(tmptAI)
		tAI_codon[trans]=tmptAI
		(tmpStartWin,tmpStartPos)=getWindowsVector(upLength,downLength,tmptAI,0) #start codon coor is 0 (0-based), codon level
		(tmpStopWin, tmpStopPos) =getWindowsVector(downLength,upLength,tmptAI,(len(tmptAI)-1))  #stop codon coor is len-1 (0-based) codon level
		startAIList.append(tmpStartWin)
		stoptAIList.append(tmpStopWin)
		startPos.append(tmpStartPos)
		stopPos.append(tmpStopPos)
		passTransSet.add(trans)
	startAIList=np.array(startAIList)
	startPos=np.array(startPos)
	stoptAIList=np.array(stoptAIList)
	stopPos=np.array(stopPos)
	for terms in np.arange(upLength+downLength+1):
		startAI[terms]=np.mean(startAIList[np.where(startPos[:,terms]==1),terms])
		stoptAI[terms] =np.mean(stoptAIList[np.where(stopPos[:,terms]==1),terms])

	print("Metaplots Transcript Number for fasta file"+transcriptFile+" is :"+str(len(passTransSet)),file=sys.stderr)
	return(startAI,stoptAI,tAI,tAI_codon)

def codon2AA(table=1):
	''' table=1 is a standard codon table'''
	codon2AA_dict={k: v.forward_table for k, v in ct.unambiguous_dna_by_id.items()}
	return codon2AA_dict[table]
def get_stop_codons(table=1):
	stop_codons_dict={k: v.stop_codons for k, v in ct.unambiguous_dna_by_id.items()}
	return stop_codons_dict[table]

def write_trans_file_tAI_dataframe(inFastaAttr,outFile):
	data=[]
	for fasta in inFastaAttr:
		k=pd.DataFrame([fasta.fastaLegend]*len(fasta.startAI))
		start=pd.DataFrame(fasta.startAI)
		stop=pd.DataFrame(fasta.stoptAI)
		tAI=pd.merge(start,stop,how="left",left_index=True,right_index=True)
		tAI=pd.merge(k,tAI,how="left",left_index=True,right_index=True)
		data.append(tAI)
	temp=data[0]
	if len(data) < 1:
		raise EOFError("Empty file, there is nothing in the file.")
	if len(data) == 1:
		temp.columns=["sample","start_tAI","stop_tAI"]
		temp.to_csv(outFile,sep="\t",index=0)
	else:
		for i in np.arange(1,len(data)):
			temp=np.vstack((temp,data[i]))
		temp=pd.DataFrame(temp,columns=["sample","start_tAI","stop_tAI"])
		temp.to_csv(outFile,sep="\t",index=0)

def write_tAI_of_each_gene(inFastaAttr,outFile):
	data=[]
	data_index=[]
	for fasta in inFastaAttr:
		d=fasta.tAI
		i=fasta.fastaLegend
		data.append(d)
		data_index.append(i)
	data=pd.DataFrame(data,index=data_index)
	data=data.T
	data.to_csv(outFile,sep="\t")
def write_codon_units_density(inFastaAttr,outFile):
	for fasta in inFastaAttr:
		with open(outFile+"_"+fasta.fastaLegend+"_codon_tAI.txt","w") as fout:
			for ts in fasta.tAI_codon :
				fout.write("%s" % ( ts ) ) #the first num codons
				for codons in range(len(fasta.tAI_codon[ts])):
					fout.write("\t%f" % ( fasta.tAI_codon[ts][codons] ) )
				fout.write("\n")
			#fout.write("\n\n")
def parse_args_for_tAI_calculation():
	parser=create_parser_for_tAI()
	(options,args)=parser.parse_args()
	(transcriptFiles,copy_numbers,outPrefix,trans_file_legend,upLength,downLength,table)=(options.transcriptFiles.split(","),options.copy_numbers,
	options.output_prefix,options.trans_file_legend.split(","),options.upstream_codon,options.downstream_codon,options.geneticCode)
	print("your input : "+ str(len(transcriptFiles))+" transcript files",file=sys.stderr)
	## handle bam file attr
	fasta_attr=[]
	for ii,jj in zip(transcriptFiles,trans_file_legend):
		fasta=fasta_attrbution(ii,jj)
		fasta_attr.append(fasta)
	print("Prepare the files used for tAI calculation...",file=sys.stderr)
	Codon_table=codon2AA(table=table)
	stopCodons=get_stop_codons(table=table)
	for stop_codon in stopCodons:
		Codon_table[stop_codon]="*"
	codonList,tRNA_GCNs,Sij,codon_anticodon=prepare_datas(copy_numbers,Codon_table)
	w=calculate_relative_adaptiveness_w(codonList,tRNA_GCNs,Sij,codon_anticodon)
	w=[[k,v] for k,v in w.items()]
	w=pd.DataFrame(w,columns=['codon','tAI'])
	w.to_csv("tAI_of_each_codon.txt",sep='\t',index=0)
	print("Finish the step of files preparation...",file=sys.stderr)
	print("Start the step of tAI calculations...",file=sys.stderr)

	for fasta in fasta_attr:
		(fasta.startAI,fasta.stoptAI,fasta.tAI,fasta.tAI_codon) = get_trans_frame_tAI(fasta.fastaName,codonList,tRNA_GCNs,Sij,codon_anticodon,upLength,downLength)

	print("Finish the step of get_trans_frame_tAI...",file=sys.stderr)
	write_trans_file_tAI_dataframe(fasta_attr,outPrefix+"_tAI_dataframe.txt")
	write_tAI_of_each_gene(fasta_attr,outPrefix+"_global_tAI.txt")
	write_codon_units_density(fasta_attr,outPrefix)
	print("Finish the step of write_bam_file_density",file=sys.stderr)

def main():
	parse_args_for_tAI_calculation()

if __name__ == "__main__":
	main()
