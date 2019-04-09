#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct  7 15:21:55 2018

@author: mishugeb
"""
from scipy.cluster import hierarchy
import matplotlib.pyplot as plt
plt.switch_backend('agg')
import nimfa 
import numpy as np
import pandas as pd
from sklearn import metrics
import time
import multiprocessing
from functools import partial
from scipy.optimize import minimize
from numpy import linalg as LA
from random import shuffle
import sigProfilerPlotting as plot
import string 
import os
import scipy
os.environ["MKL_NUM_THREADS"] = "1" 
os.environ["NUMEXPR_NUM_THREADS"] = "1" 
os.environ["OMP_NUM_THREADS"] = "1"
import sigproextractor as cosmic




"""################################################################## Vivid Functions #############################"""

############################################################## FUNCTION ONE ##########################################
def make_letter_ids(idlenth = 10):
    listOfSignatures = []
    letters = list(string.ascii_uppercase)
    letters.extend([i+b for i in letters for b in letters])
    letters = letters[0:idlenth]
    
    for j,l in zip(range(idlenth),letters)  :
        listOfSignatures.append("Signature "+l)
    listOfSignatures = np.array(listOfSignatures)
    return listOfSignatures

############################################################## FUNCTION ONE ##########################################    
def signature_plotting_text(value, text, Type):
    name = text + ": "
    name_list =[]
    for i in value:
        
        if Type=="integer":  
            i = int(i)
            i = format(i, ',d')            
        elif Type=="float":
            i = round(i,2)
        name_list.append(name + str(i))
    return(name_list)


############################################################## FUNCTION ONE ##########################################
def split_list(lst, splitlenth):
    newlst = []
    for i in range(0, len(lst), splitlenth):
        try: 
            newlst.append([lst[i], lst[i+1]])
        
        except: 
            newlst.append([lst[i]])
            
    return newlst


################################################################### FUNCTION ONE ###################################################################
# Calculates elementwise standard deviations from a list of matrices 
def mat_ave_std(matlst):

    matsum = np.zeros(matlst[0].shape)
    for i in matlst:
        matsum = matsum+i
    matavg = matsum/len(matlst)
    
    matvar=np.zeros(matlst[0].shape)
    for i in matlst:
        matvar = matvar+(i-matavg)**2
    matvar= matvar/len(matlst)
    matstd = matvar**(1/2)
    
    return matavg, matstd


"""############################################## Functions for modifications of Sample Matrices ##################"""           
def normalize_samples(genomes, normalize=True, all_samples=True, number=30000):
    if normalize == True:
        if all_samples==False:        
            total_mutations = np.sum(genomes, axis=0)
            indices = np.where(total_mutations>number)[0]
            results = genomes[:,list(indices)]/total_mutations[list(indices)][:,np.newaxis].T*number
            results = np.round(results, 0)
            results = results.astype(int)
            genomes[:,list(indices)] = results
        else:    
            total_mutations = np.sum(genomes, axis=0)          
            genomes = (genomes/total_mutations.T*number)
            genomes = np.round(genomes, 0)
            genomes = genomes.astype(int)
            
    return genomes


    

def split_samples(samples, intervals, rescaled_items, colnames):

    colnames = np.array(colnames)
    total_mutations = samples.sum(axis =0)

    
    max_total = np.max(total_mutations)+1
    
    intervals = np.array(intervals )
    rescaled_items = np.array(rescaled_items)
    selected_indices, = np.where(intervals<=max_total)
    
    intervals=intervals[selected_indices]
    rescaled_items=rescaled_items[selected_indices]
   
    rescaled_items = list(rescaled_items)
   
    
    sample_list = []
    sample_total = []
    rescale_list = []
    rescale_values = []
    colnames_list = []
    ranges = list(intervals)+[max_total]
    #print(ranges)
    for i in range(len(ranges)-1):    
        sub_sample, = np.where((total_mutations<=ranges[i+1]) & (total_mutations>ranges[i]))
        if samples[:,sub_sample].shape[1]>0:
            sample_list.append(samples[:,sub_sample])
            colnames_list.append(list(colnames[sub_sample]))
            sample_total.append(np.sum(samples[:,sub_sample], axis=0))
            rescale_list.append(rescaled_items[i])
            rescale_values.append(ranges[i])
      
    return(sample_list, colnames_list, sample_total, rescale_list, rescale_values) 
    
   
def denormalize_samples(genomes, original_totals, normalization_value=30000):
    normalized_totals = np.sum(genomes, axis=0)
    results = genomes/normalized_totals*original_totals
    results = np.round(results,0)
    results = results.astype(int)
    return results 
##################################################################################################################    




    

    



"""###################################################### Fuctions for NON NEGATIVE MATRIX FACTORIZATION (NMF) #################"""
def nnmf(genomes, nfactors):
    genomes = np.array(genomes)
    nmf = nimfa.Nmf(genomes, max_iter=100000, rank=nfactors, update='divergence', objective='div', test_conv= 30)
    nmf_fit = nmf()
    W = nmf_fit.basis()
    H = nmf_fit.coef()
    return W, H




def BootstrapCancerGenomes(genomes):
    np.random.seed() # Every time initiate a random seed so that all processors don't get the same seed
    #normalize the data 
    a = pd.DataFrame(genomes.sum(0))  #performing the sum of each column. variable a store the sum
    a = a.transpose()  #transfose the value so that if gets a proper dimention to normalize the data
    repmat = pd.concat([a]*genomes.shape[0])  #normalize the data to get the probility of each datapoint to perform the "random.multinomial" operation
    normGenomes = genomes/np.array(repmat)      #part of normalizing step
    
    
    #Get the normGenomes as Matlab/ alternation of the "mnrnd" fuction in Matlap
    #do the Boostraping 
    dataframe = pd.DataFrame() #declare an empty variable to populate with the Bootstrapped data
    for i in range(0,normGenomes.shape[1]):
        #print a.iloc[:,i]
        #print normGenomes.iloc[:,i]
        dataframe[i]=list(np.random.multinomial(a.iloc[:,i], normGenomes.iloc[:,i], 1)[0])
        
        
    return dataframe


def nmf(genomes=1, totalProcesses=1, resample=True):   
    #tic = time.time()
    genomes = pd.DataFrame(genomes) #creating/loading a dataframe/matrix
    if resample == True:
        bootstrapGenomes= BootstrapCancerGenomes(genomes)
        bootstrapGenomes[bootstrapGenomes<0.0001]= 0.0001
        W, H = nnmf(bootstrapGenomes,totalProcesses)  #uses custom function nnmf
    else:
        W, H = nnmf(genomes,totalProcesses)  #uses custom function nnmf
    #print ("initital W: ", W); print("\n");
    #print ("initial H: ", H); print("\n");
    W = np.array(W)
    H = np.array(H)
    total = W.sum(axis=0)[np.newaxis]
    #print ("total: ", total); print("\n");
    W = W/total
    H = H*total.T
    #print ("process " +str(totalProcesses)+" continues please wait... ")
    #print ("execution time: {} seconds \n".format(round(time.time()-tic), 2))    
    
    return W, H
# NMF version for the multiprocessing library
def pnmf(pool_constant=1, genomes=1, totalProcesses=1, resample=True):
    tic = time.time()
    genomes = pd.DataFrame(genomes) #creating/loading a dataframe/matrix
    if resample == True:
        bootstrapGenomes= BootstrapCancerGenomes(genomes)
        bootstrapGenomes[bootstrapGenomes<0.0001]= 0.0001
        W, H = nnmf(bootstrapGenomes,totalProcesses)  #uses custom function nnmf
    else:
        W, H = nnmf(genomes,totalProcesses)  #uses custom function nnmf
    #print ("initital W: ", W); print("\n");
    #print ("initial H: ", H); print("\n");
    W = np.array(W)
    H = np.array(H)
    total = W.sum(axis=0)[np.newaxis]
    #print ("total: ", total); print("\n");
    W = W/total
    H = H*total.T
    print ("process " +str(totalProcesses)+" continues please wait... ")
    print ("execution time: {} seconds \n".format(round(time.time()-tic), 2))
    return W, H


def parallel_runs(genomes=1, totalProcesses=1, iterations=1,  n_cpu=-1, verbose = False, resample=True):
    if verbose:
        print ("Process "+str(totalProcesses)+ " is in progress\n===================================>")
    if n_cpu==-1:
        pool = multiprocessing.Pool()
    else:
        pool = multiprocessing.Pool(processes=n_cpu)
        
  
    pool_nmf=partial(pnmf, genomes=genomes, totalProcesses=totalProcesses, resample=resample)
    result_list = pool.map(pool_nmf, range(iterations)) 
    pool.close()
    pool.join()
    
    return result_list
####################################################################################################################



"""################################################################### FUNCTIONS TO CALCULATE DISTANCES BETWEEN VECTORS ###################################################################"""
################################################################### FUNCTION ONE ###################################################################
#function to calculate the cosine similarity
def cos_sim(a, b):
      
    
    """Takes 2 vectors a, b and returns the cosine similarity according 
    to the definition of the dot product
    
    Dependencies: 
    *Requires numpy library. 
    *Does not require any custom function (constructed by me)
    
    Required by:
    * pairwise_cluster_raw
    	"""
    if np.sum(a)==0 or np.sum(b) == 0:
        return 0.0      
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return dot_product / (norm_a * norm_b)


    
################################################################### FUNCTION ONE ###################################################################
#function to calculate multiple similarities/distances
def calculate_similarities(genomes, est_genomes, sample_names):
    from numpy import inf
    cosine_similarity_list = []
    kl_divergence_list = []
    l1_norm_list = []
    l2_norm_list = []
    total_mutations_list = []
    relative_l1_list = []
    relative_l2_list = []
    for i in range(genomes.shape[1]):
        p_i = genomes[:,i]
        q_i = est_genomes[:, i]
        cosine_similarity_list.append(round(cos_sim(p_i,q_i ),3))
        kl_divergence_list.append(round(scipy.stats.entropy(p_i,q_i),2))
        l1_norm_list.append(round(np.linalg.norm(p_i-q_i , ord=1),3))
        relative_l1_list.append(round((l1_norm_list[-1]/np.linalg.norm(p_i, ord=1))*100,3))
        l2_norm_list.append(round(np.linalg.norm(p_i-q_i , ord=2),3))
        relative_l2_list.append(round((l2_norm_list[-1]/np.linalg.norm(p_i, ord=2))*100,3))
        total_mutations_list.append(np.sum(p_i))
    kl_divergence_list = np.array(kl_divergence_list)
    kl_divergence_list[kl_divergence_list == inf] =1000
    similarities_dataframe = pd.DataFrame({"Sample Names": sample_names, \
                                           "Total Mutations":total_mutations_list, \
                                           "Cosine Similarity": cosine_similarity_list, \
                                           "L1 Norm": l1_norm_list, \
                                           "L1_Norm_%":relative_l1_list, \
                                           "L2 Norm": l2_norm_list, \
                                           "L2_Norm_%": relative_l2_list, \
                                           "KL Divergence": kl_divergence_list})
    similarities_dataframe = similarities_dataframe.set_index("Sample Names")
    return [similarities_dataframe, cosine_similarity_list]




"""################################################################### CLUSTERING FUNCTIONS ###################################################################"""
################################################################### FUNCTION ONE ###################################################################
# function to calculate the centroids

################################################################### FUNCTION  ###################################################################
def pairwise_cluster_raw(mat1=([0]), mat2=([0]), mat1T=([0]), mat2T=([0])):  # the matrices (mat1 and mat2) are used to calculate the clusters and the lsts will be used to store the members of clusters
    
    """ Takes a pair of matrices mat1 and mat2 as arguments. Both of the matrices should have the 
    equal shapes. The function makes a partition based clustering (the number of clusters is equal 
    to the number of colums of the matrices, and not more column is assigned into a cluster from 
    a single matrix). It return the list of clusters  as "lstCluster" and the list of clusters 
    based on their indeces of the vectors in their original matrices. Please run the 
    test of function/example code provided below the for better understanding. 
    
     Dependencies:
        *cos_sim
        
    Required by:
        *pairwise_cluster_init 
        *pairwise_cluster_elong
    
    
    """
    
    
    con_mat = np.zeros((mat1.shape[1],mat2.shape[1]))
    for i in range(0, mat1.shape[1]):
        for j in range(0,mat2.shape[1]):
            con_mat[i, j] = cos_sim(mat1[:,i], mat2[:,j])  #used custom function
    
    
    
    maximums = np.argmax(con_mat, axis = 1) #the indices of maximums
    uniques = np.unique(maximums) #unique indices having the maximums

        
    lstCluster=[]
    lstClusterT=[]
    idxPair= []  
    
    # check if more than one centroids have their maximums in the same indices
    if len(maximums)!=len(uniques):
        diffRank = np.zeros([len(con_mat), 2])    
        for i in range(len(con_mat)):
            centroid = con_mat[i]
            value_order= np.argsort(centroid)
            first_highest_value_idx = value_order[-1]
            second_highest_value_idx = value_order[-2]
            diffRank[i,0] =  i
            diffRank[i, 1] = centroid[first_highest_value_idx]-centroid[second_highest_value_idx]
        diffRank = diffRank[diffRank[:,1].argsort(kind='mergesort')]
        diffRank = diffRank.astype(int)

  
    
        for a in range(len(diffRank)-1,-1, -1):
            i = diffRank[a,0]
            j = con_mat[i,:].argmax()
            con_mat[i,:]=0
            con_mat[:,j]=0
            lstCluster.append([mat1[:,i], mat2[:,j]])
            idxPair.append([i,j])   #for debugging
            lstClusterT.append([mat1T[i,:], mat2T[j, :]])
    
    
    else:
        for a in range(0,mat1.shape[1]):
        
            i,j=np.unravel_index(con_mat.argmax(), con_mat.shape) 
            lstCluster.append([mat1[:,i], mat2[:,j]])
            idxPair.append([i,j])   #for debugging
            lstClusterT.append([mat1T[i,:], mat2T[j, :]])
            con_mat[i,:]=0
            con_mat[:,j]=0
        
    return lstCluster, idxPair, lstClusterT
         





################################################################### FUNCTION  ###################################################################
def reclustering(tempWall=0, tempHall=0, processAvg=0, exposureAvg=0):
    # exposureAvg is not important here. It can be any matrix with the same size of a single exposure matrix
    iterations = int(tempWall.shape[1]/processAvg.shape[1])
    processes =  processAvg.shape[1]
    idxIter = list(range(0, tempWall.shape[1], processes))
   
    processes3D = np.zeros([processAvg.shape[1], processAvg.shape[0], iterations])
    exposure3D = np.zeros([exposureAvg.shape[0], iterations, exposureAvg.shape[1]])
    
    for  iteration_number in range(len(idxIter)):
        
        
        #print(i)
        statidx = idxIter[iteration_number]
        loopidx = list(range(statidx, statidx+processes))
        lstCluster, idxPair, lstClusterT = pairwise_cluster_raw(mat1=processAvg, mat2=tempWall[:, loopidx], mat1T=exposureAvg, mat2T=tempHall[loopidx,:])
        
        for cluster_items in idxPair:
            cluster_number = cluster_items[0]
            query_idx = cluster_items[1]
            processes3D[cluster_number,:,iteration_number]=tempWall[:,statidx+query_idx]
            exposure3D[cluster_number, iteration_number, :] = tempHall[statidx+query_idx,:]
            
    
    
    count = 0
    labels=[]
    clusters = pd.DataFrame()
    for cluster_id in range(processes3D.shape[0]):
        cluster_vectors = pd.DataFrame(processes3D[cluster_id,:,:])
        clusters = clusters.append(cluster_vectors.T)
        for k in range(cluster_vectors.shape[1]):
            labels.append(count)
        count= count+1
    
    
    
    try:
        SilhouetteCoefficients = metrics.silhouette_samples(clusters, labels, metric='cosine')
    
        
    
    except:
        SilhouetteCoefficients = np.ones((len(labels),1))
        
        
        
        
    avgSilhouetteCoefficients = np.mean(SilhouetteCoefficients)
    
    #clusterSilhouetteCoefficients 
    splitByCluster = np.array_split(SilhouetteCoefficients, processes3D.shape[0])
    clusterSilhouetteCoefficients = np.array([])
    for i in splitByCluster:
        
        clusterSilhouetteCoefficients=np.append(clusterSilhouetteCoefficients, np.mean(i))
        
    processAvg = np.mean(processes3D, axis=2).T
    processSTE = scipy.stats.sem(processes3D, axis=2, ddof=1).T
    exposureAvg = np.mean(exposure3D, axis=1) 
    exposureSTE = scipy.stats.sem(exposure3D, axis=1, ddof=1)
    
        
    return  processAvg, exposureAvg, processSTE,  exposureSTE, avgSilhouetteCoefficients, clusterSilhouetteCoefficients




def cluster_converge_innerloop(Wall, Hall, totalprocess):
    
    processAvg = np.random.rand(Wall.shape[0],totalprocess)
    exposureAvg = np.random.rand(totalprocess, Hall.shape[1])
    
    result = 0
    convergence_count = 0
    while True:
        processAvg, exposureAvg, processSTE,  exposureSTE, avgSilhouetteCoefficients, clusterSilhouetteCoefficients = reclustering(Wall, Hall, processAvg, exposureAvg)
        
        if result == avgSilhouetteCoefficients:
            break
        elif convergence_count == 10:
            break
        else:
            result = avgSilhouetteCoefficients
            convergence_count = convergence_count + 1
        
    return processAvg, exposureAvg, processSTE,  exposureSTE, avgSilhouetteCoefficients, clusterSilhouetteCoefficients

"""
#############################################################################################################
#################################### Functions For Single Sample Algorithms #############################
#############################################################################################################
"""
def parameterized_objective2_custom(x, signatures, samples):
    rec = np.dot(signatures, x)
    try:
        y = LA.norm(samples-rec[:,np.newaxis])
    except:
        y = LA.norm(samples-rec)
    return y


def constraints1(x, samples):
    sumOfSamples=np.sum(samples, axis=0)
    #print(sumOfSamples)
    #print(x)
    result = sumOfSamples-(np.sum(x))
    #print (result)
    return result


def create_bounds(idxOfZeros, samples, numOfSignatures):
    total = np.sum(samples)
    b = (0.0, float(total))
    lst =[b]*numOfSignatures
    
    for i in idxOfZeros:
        lst[i] = (0.0, 0.0) 
    
    return lst 





# to do the calculation, we need: W, samples(one column), H for the specific sample, tolerence

def remove_all_single_signatures(W, H, genomes):
    # make the empty list of the successfull combinations
    successList = [0,[],0] 
    # get the cos_similarity with sample for the oringinal W and H[:,i]
    originalSimilarity= cos_sim(genomes, np.dot(W, H))
    # make the original exposures of specific sample round
    oldExposures = np.round(H)
    
    # set the flag for the while loop
    if len(oldExposures[np.nonzero(oldExposures)])>1:
        Flag = True
    else: 
        Flag = False
        return oldExposures
    # The while loop starts here
    while Flag: 
        
        # get the list of the indices those already have zero values
        if len(successList[1]) == 0:
            initialZerosIdx = list(np.where(oldExposures==0)[0]) 
            #get the indices to be selected
            selectableIdx = list(np.where(oldExposures>0)[0]) 
        elif len(successList[1]) > 1: 
            initialZerosIdx = list(np.where(successList[1]==0)[0]) 
            #get the indices to be selected
            selectableIdx = list(np.where(successList[1]>0)[0])
        else:
            print("iteration is completed")
            #break
        
        
        # get the total mutations for the given sample
        maxmutation = round(np.sum(genomes))
        
        # new signature matrix omiting the column for zero
        #Winit = np.delete(W, initialZerosIdx, 1)
        Winit = W[:,selectableIdx]
        
        # set the initial cos_similarity
        record  = [0.11, []] 
        # get the number of current nonzeros
        l= Winit.shape[1]
        
        for i in range(l):
            #print(i)
            loopSelection = list(range(l))
            del loopSelection[i]
            #print (loopSelection)
            W1 = Winit[:,loopSelection]
           
            
            #initialize the guess
            x0 = np.random.rand(l-1, 1)*maxmutation
            x0= x0/np.sum(x0)*maxmutation
            
            #set the bounds and constraints
            bnds = create_bounds([], genomes, W1.shape[1]) 
            cons1 ={'type': 'eq', 'fun': constraints1, 'args':[genomes]} 
            
            #the optimization step
            sol = minimize(parameterized_objective2_custom, x0, args=(W1, genomes),  bounds=bnds, constraints =cons1, tol=1e-15)
            
            #print (sol.success)
            #print (sol.x)
            
            #convert the newExposure vector into list type structure
            newExposure = list(sol.x)
            
            #insert the loopZeros in its actual position 
            newExposure.insert(i, 0)
            
            #insert zeros in the required position the newExposure matrix
            initialZerosIdx.sort()
            for zeros in initialZerosIdx:
                newExposure.insert(zeros, 0)
            
            # get the maximum value the new Exposure
            maxcoef = max(newExposure)
            idxmaxcoef = newExposure.index(maxcoef)
            
            newExposure = np.round(newExposure)
            
            
            if np.sum(newExposure)!=maxmutation:
                newExposure[idxmaxcoef] = round(newExposure[idxmaxcoef])+maxmutation-sum(newExposure)
                
            
            newSample = np.dot(W, newExposure)
            newSimilarity = cos_sim(genomes, newSample) 
             
            difference = originalSimilarity - newSimilarity
            #print(originalSimilarity)
            #print(newSample)
            #print(newExposure)
            #print(newSimilarity)
            
            #print(difference)
            #print (newExposure)
            #print (np.round(H))
            #print ("\n\n")
             
            if difference<record[0]:
                record = [difference, newExposure, newSimilarity]
            
            
        #print ("This loop's selection is {}".format(record))
        
        if record[0]>0.01:   
            Flag=False
        elif len(record[1][np.nonzero(record[1])])==1:
            successList = record 
            Flag=False
        else:
            successList = record
        #print("The loop selection is {}".format(successList))
        
        #print (Flag)
        #print ("\n\n")
    
    #print ("The final selection is {}".format(successList))
    
    if len(successList[1])==0:
        successList = [0.0, oldExposures, originalSimilarity]
    
    return successList[1]
    


def remove_all_single_signatures_pool(indices, W, exposures, totoalgenomes):
    i = indices
    H = exposures[:,i]
    genomes= totoalgenomes[:,i]
    # make the empty list of the successfull combinations
    successList = [0,[],0] 
    # get the cos_similarity with sample for the oringinal W and H[:,i]
    originalSimilarity= cos_sim(genomes, np.dot(W, H))
    # make the original exposures of specific sample round
    oldExposures = np.round(H)
    
    # set the flag for the while loop
    if len(oldExposures[np.nonzero(oldExposures)])>1:
        Flag = True
    else: 
        Flag = False
        return oldExposures
    # The while loop starts here
    while Flag: 
        
        # get the list of the indices those already have zero values
        if len(successList[1]) == 0:
            initialZerosIdx = list(np.where(oldExposures==0)[0]) 
            #get the indices to be selected
            selectableIdx = list(np.where(oldExposures>0)[0]) 
        elif len(successList[1]) > 1: 
            initialZerosIdx = list(np.where(successList[1]==0)[0]) 
            #get the indices to be selected
            selectableIdx = list(np.where(successList[1]>0)[0])
        else:
            print("iteration is completed")
            #break
        
        
        # get the total mutations for the given sample
        maxmutation = round(np.sum(genomes))
        
        # new signature matrix omiting the column for zero
        #Winit = np.delete(W, initialZerosIdx, 1)
        Winit = W[:,selectableIdx]
        
        # set the initial cos_similarity
        record  = [0.11, []] 
        # get the number of current nonzeros
        l= Winit.shape[1]
        
        for i in range(l):
            #print(i)
            loopSelection = list(range(l))
            del loopSelection[i]
            #print (loopSelection)
            W1 = Winit[:,loopSelection]
           
            
            #initialize the guess
            x0 = np.random.rand(l-1, 1)*maxmutation
            x0= x0/np.sum(x0)*maxmutation
            
            #set the bounds and constraints
            bnds = create_bounds([], genomes, W1.shape[1]) 
            cons1 ={'type': 'eq', 'fun': constraints1, 'args':[genomes]} 
            
            #the optimization step
            sol = minimize(parameterized_objective2_custom, x0, args=(W1, genomes),  bounds=bnds, constraints =cons1, tol=1e-15)
            
            #print (sol.success)
            #print (sol.x)
            
            #convert the newExposure vector into list type structure
            newExposure = list(sol.x)
            
            #insert the loopZeros in its actual position 
            newExposure.insert(i, 0)
            
            #insert zeros in the required position the newExposure matrix
            initialZerosIdx.sort()
            for zeros in initialZerosIdx:
                newExposure.insert(zeros, 0)
            
            # get the maximum value the new Exposure
            maxcoef = max(newExposure)
            idxmaxcoef = newExposure.index(maxcoef)
            
            newExposure = np.round(newExposure)
            
            
            if np.sum(newExposure)!=maxmutation:
                newExposure[idxmaxcoef] = round(newExposure[idxmaxcoef])+maxmutation-sum(newExposure)
                
            
            newSample = np.dot(W, newExposure)
            newSimilarity = cos_sim(genomes, newSample) 
             
            difference = originalSimilarity - newSimilarity
            #print(originalSimilarity)
            #print(newSample)
            #print(newExposure)
            #print(newSimilarity)
            
            #print(difference)
            #print (newExposure)
            #print (np.round(H))
            #print ("\n\n")
             
            if difference<record[0]:
                record = [difference, newExposure, newSimilarity]
            
            
        #print ("This loop's selection is {}".format(record))
        
        if record[0]>0.01:   
            Flag=False
        elif len(record[1][np.nonzero(record[1])])==1:
            successList = record 
            Flag=False
        else:
            successList = record
        #print("The loop selection is {}".format(successList))
        
        #print (Flag)
        #print ("\n\n")
    
    #print ("The final selection is {}".format(successList))
    
    if len(successList[1])==0:
        successList = [0.0, oldExposures, originalSimilarity]
    #print ("one sample completed")
    return successList[1]


#################################################################### Function to add signatures to samples from database #############################
def add_signatures(W, genome, cutoff=0.025):
    
    # This function takes an array of signature and a single genome as input, returns a dictionray of cosine similarity, exposures and presence 
    # of signatures according to the indices of the original signature array
    
    originalSimilarity = -1 # it can be also written as oldsimilarity
    maxmutation = round(np.sum(genome))
    init_listed_idx = []
    init_nonlisted_idx = list(range(W.shape[1]))
    finalRecord = [["similarity place-holder" ], ["newExposure place-holder"], ["signatures place-holder"]] #for recording the cosine difference, similarity, the new exposure and the index of the best signauture
    
    
    while True:
        bestDifference = -1 
        bestSimilarity = -1
        loopRecord = [["newExposure place-holder"], ["signatures place-holder"], ["best loop signature place-holder"]]
        for sig in init_nonlisted_idx:
            
            
            if len(init_listed_idx)!=0:
                loop_liststed_idx=init_listed_idx+[sig]
                loop_liststed_idx.sort()
                #print(loop_liststed_idx)
                W1 = W[:,loop_liststed_idx]
                #print (W1.shape)
                #initialize the guess
                x0 = np.random.rand(W1.shape[1], 1)*maxmutation
                x0= x0/np.sum(x0)*maxmutation
                
                #set the bounds and constraints
                bnds = create_bounds([], genome, W1.shape[1]) 
                cons1 ={'type': 'eq', 'fun': constraints1, 'args':[genome]} 
            # for the first time addintion  
            else:
                W1 = W[:,sig][:,np.newaxis]
                #print (W1.shape)        
                #initialize the guess
                x0 = np.ones((1,1))*maxmutation    
            
                #set the bounds and constraints
                bnds = create_bounds([], genome, 1) 
                cons1 ={'type': 'eq', 'fun': constraints1, 'args':[genome]} 
            
            #the optimization step
            sol = minimize(parameterized_objective2_custom, x0, args=(W1, genome),  bounds=bnds, constraints =cons1, tol=1e-30)
            
            #print(W1)
            #convert the newExposure vector into list type structure
            newExposure = list(sol.x)
            
            # get the maximum value of the new Exposure
            maxcoef = max(newExposure)
            idxmaxcoef = newExposure.index(maxcoef)
            
            newExposure = np.round(newExposure)
            
            # We may need to tweak the maximum value of the new exposure to keep the total number of mutation equal to the original mutations in a genome
            if np.sum(newExposure)!=maxmutation:
                newExposure[idxmaxcoef] = round(newExposure[idxmaxcoef])+maxmutation-sum(newExposure)
             
            # compute the estimated genome
            est_genome = np.dot(W1, newExposure)
            newSimilarity = cos_sim(genome[:,0], est_genome)
            
            difference = newSimilarity - originalSimilarity 
            
            # record the best values so far
            if difference>bestDifference:
                bestDifference = difference
                bestSimilarity = newSimilarity
                loopRecord = [newExposure, W1, sig]  #recording the cosine difference, the new exposure and the index of the best signauture
                #print(newSimilarity)
        
        # 0.01 is the thresh-hold for now 
        if bestSimilarity-originalSimilarity>cutoff:
            originalSimilarity = bestSimilarity
            init_listed_idx.append(loopRecord[2])
            init_nonlisted_idx.remove(loopRecord[2])
            init_listed_idx.sort()
            #print(originalSimilarity)
            finalRecord = [originalSimilarity, loopRecord[0], init_listed_idx, loopRecord[1], genome]
            #print (finalRecord)
            
            if len(init_nonlisted_idx)!= 0:
                
                continue
            else:
                break
        else:
            break
        
    #print(finalRecord)
    dictExposure= {"similarity":finalRecord[0], "exposures":finalRecord[1], "signatures": finalRecord[2]}  
    addExposure = np.zeros([W.shape[1]])
    addExposure[dictExposure["signatures"]]=dictExposure["exposures"]
    
    return  addExposure, finalRecord[0]



################################### Dicompose the new signatures into global signatures   #########################
def signature_decomposition(signatures, mtype, directory):
    
    paths = cosmic.__path__[0]
    
    if signatures.shape[0]==96:
        sigDatabase = pd.read_csv(paths+"/data/sigProfiler_SBS_signatures_2018_03_28.csv", sep=",")
        sigDatabase=sigDatabase.sort_values(['SubType'], ascending=[True])
        List=list("A"*24)+list("C"*24)+list("G"*24)+list("T"*24)
        sigDatabase['group']=List
        sigDatabase = sigDatabase.sort_values(['group', 'Type'], ascending=[True, True]).groupby('group').head(96).iloc[:,2:-1]
        signames = sigDatabase.columns 
        
        
    elif signatures.shape[0]==78:
        sigDatabase = pd.read_csv(paths+"/data/sigProfiler_DBS_signatures.csv", sep=",").iloc[:,1:]
        signames = sigDatabase.columns
    elif signatures.shape[0]==83:
        sigDatabase = pd.read_csv(paths+"/data/sigProfiler_ID_signatures.csv", sep=",").iloc[:,1:]
        signames = sigDatabase.columns
    else:
        sigDatabase = np.random.rand(signatures.shape[0],2)
        signames = list(range(signatures.shape[0]))
        
    sigDatabases = sigDatabase
    letters = list(string.ascii_uppercase)
    letters.extend([i+b for i in letters for b in letters])
    letters = letters[0:signatures.shape[1]]
    
    
    # replace the probability data of the process matrix with the number of mutation
    for i in range(signatures.shape[1]):
        signatures[:, i] =  signatures[:, i]*5000      #(np.sum(exposureAvg[i, :]))
    
    sigDatabase = np.array(sigDatabase)
    allsignatures = np.array([])
    newsig = list() # will create the letter based id of newsignatures
    newsigmatrixidx = list() # will create the original id of newsignature to help to record the original matrix
    fh = open(directory+"/comparison_with_gobal_ID_signatures.csv", "w")
    fh.write("De novo extracted, Global NMF Signatures, Similarity\n")
    fh.close()
    
    for i in range(signatures.shape[1]):
        
        
        exposures, similarity = add_signatures(sigDatabase, signatures[:,i][:,np.newaxis])
        #print(signames[np.nonzero(exposures)], similarity)
        #print(exposures[np.nonzero(exposures)]/np.sum(exposures[np.nonzero(exposures)])*100)
        exposure_percentages = exposures[np.nonzero(exposures)]/np.sum(exposures[np.nonzero(exposures)])*100
        listofinformation = list("0"*len(np.nonzero(exposures)[0])*3)
        
        count =0
        for j in np.nonzero(exposures)[0]:
            listofinformation[count*3] = signames[j]
            listofinformation[count*3+1] = round(exposure_percentages[count],2)
            listofinformation[count*3+2]="%"
            count+=1
        ListToTumple = tuple([mtype, letters[i]]+listofinformation+ [similarity])
        strings ="Signature %s-%s,"+" Signature %s (%0.2f%s) &"*(len(np.nonzero(exposures)[0])-1)+" Signature %s (%0.2f%s), %0.2f\n" 
        #print(strings%(ListToTumple))
        if len(np.nonzero(exposures)[0])<4:
            allsignatures = np.append(allsignatures, np.nonzero(exposures))
            fh = open(directory+"/comparison_with_gobal_ID_signatures.csv", "a")
            fh.write(strings%(ListToTumple))
            fh.close()
        else:
            newsig.append("Signature "+letters[i])
            newsigmatrixidx.append(i)
            fh = open(directory+"/comparison_with_gobal_ID_signatures.csv", "a")
            fh.write("Signature {}-{}, Signature {}-{}, {}\n".format(mtype, letters[i], mtype, letters[i], 1 ))
            fh.close()
            
       
    
    different_signatures = np.unique(allsignatures)
    different_signatures=different_signatures.astype(int)
    detected_signatures = signames[different_signatures]
    
    globalsigmats= sigDatabases.loc[:,list(detected_signatures)]
    newsigsmats=signatures[:,newsigmatrixidx]
    
    
    
    return {"globalsigids": list(detected_signatures), "newsigids": newsig, "globalsigs":globalsigmats, "newsigs":newsigsmats/5000} 





"""
#############################################################################################################
#################################### Decipher Signatures ###################################################
#############################################################################################################
"""
def decipher_signatures(genomes=[0], i=1, totalIterations=1, cpu=-1, mut_context="96", resample=True):
    m = mut_context
    
    tic = time.time()
    # The initial values accumute the results for each number of 
    totalMutationTypes = genomes.shape[0];
    totalGenomes = genomes.shape[1];
    totalProcesses = i
    
    print ("Extracting signature {} for mutation type {}".format(i, m))  # m is for the mutation context
    
    
    
    ##############################################################################################################################################################################         
    ############################################################# The parallel processing takes place here #######################################################################  
    ##############################################################################################################################################################################         
    results = parallel_runs(genomes=genomes, totalProcesses=totalProcesses, iterations=totalIterations,  n_cpu=cpu, verbose = False, resample=resample)
        
    toc = time.time()
    print ("Time taken to collect {} iterations for {} signatures is {} seconds".format(totalIterations , i, round(toc-tic, 2)))
    ##############################################################################################################################################################################       
    ######################################################### The parallel processing ends here ##################################################################################      
    ##############################################################################################################################################################################        
    
    
    ################### Achieve the best clustering by shuffling results list using a few iterations ##########        
    Wall = np.zeros((totalMutationTypes, totalProcesses * totalIterations));
    #print (Wall.shape)
    Hall = np.zeros((totalProcesses * totalIterations, totalGenomes));
    finalgenomeErrors = np.zeros((totalMutationTypes, totalGenomes, totalIterations));
    finalgenomesReconstructed = np.zeros((totalMutationTypes, totalGenomes, totalIterations))
    
    processCount=0
    for j in range(len(results)):
        W = results[j][0]
        H = results[j][1]
        finalgenomeErrors[:, :, j] = genomes -  np.dot(W,H);
        finalgenomesReconstructed[:, :, j] = np.dot(W,H);
        Wall[ :, processCount : (processCount + totalProcesses) ] = W;
        Hall[ processCount : (processCount + totalProcesses), : ] = H;
        processCount = processCount + totalProcesses;
    
    
    processes=i #renamed the i as "processes"    
    processAvg, exposureAvg, processSTE,  exposureSTE, avgSilhouetteCoefficients, clusterSilhouetteCoefficients = cluster_converge_innerloop(Wall, Hall, processes)
       
    

    return  processAvg, exposureAvg, processSTE, exposureSTE, avgSilhouetteCoefficients, np.round(clusterSilhouetteCoefficients,3), finalgenomeErrors, finalgenomesReconstructed, Wall, Hall, processes





################################################### Generation of probabilities for each processes given to A mutation type ############################################
def probabilities(W, H, index, allsigids, allcolnames):  
    
    # setting up the indices 
    rows = index
    cols = allcolnames
    sigs = allsigids
    
    W = np.array(W)
    H= np.array(H)
    # rebuild the original matrix from the estimated W and H 
    genomes = np.dot(W,H)
    
    
    result = 0
    for i in range(H.shape[1]): #here H.shape is the number of sample
        
        M = genomes[:,i][np.newaxis]
        #print (M.shape)
        
        probs = W*H[:,i]/M.T
        #print ("Sum of Probabilities for Sample {} is : ".format(i+1))
        #print(probs)
        #print ("Sum of Probabilities for Sample {} is: ".format(i+1))
        #print(probs.sum(axis=1)[np.newaxis].T) 
        
        
        probs = pd.DataFrame(probs)
        probs.columns = sigs
        col1 = [cols[i]]*len(rows)
        probs.insert(loc=0, column='Sample Names', value=col1)
        probs.insert(loc=1, column='MutationTypes', value = rows)
        #print (probs)
        #print ("\n")
        if i!=0:
            result = pd.concat([result, probs], axis=0)
        else:
            result = probs
    
        
    return result
#########################################################################################################################################################################        





"""        
##########################################################################################################################################################################
#################################################################### Data loading and Result Exporting  ###################################################################################
##########################################################################################################################################################################
"""

########################################################### Functions to load the MATLAB OBJECTS ###################

def extract_arrays(data, field, index=True):
    accumulator = list()
    if index==False:
        for i in data[field]:
            accumulator.append(i)
        return accumulator 
    else:        
        for i in data[field]:
            accumulator.append(i[0][0])
        return accumulator 

def extract_input(data):         
    originalGenome=data['originalGenomes']        
    cancerType = extract_arrays(data, 'cancerType', False)
    sampleNames = extract_arrays(data, 'sampleNames', True)
    subTypes = extract_arrays(data, 'subtypes', True)
    types = extract_arrays(data, 'types', True)
    allFields = [cancerType, originalGenome, sampleNames, subTypes, types]
    return allFields
########################################################################################################################

##################################### Get Input From CSV Files ##############################################

def read_csv(filename, folder = False):
    
  
    if folder==False:
        if type(filename) == str:
            genomes = pd.read_csv(filename, sep=",").iloc[:, :]   
        else:
            genomes = filename
    else:
    
        count = 1
        for file in os.listdir(filename):
            #print(count) 
            df = pd.read_csv(filename+"/"+file)
            if count==1:
                    genomes = df
            else:
                    genomes = pd.merge(genomes, df, on=["Mutation type", "Trinucleotide"])
            count += 1


    

    
    
    mtypes = [str(genomes.shape[0])]
    
    if mtypes == ['96']:
        # create the list to sort the mutation types
        orderlist = ['A[C>A]A', 'A[C>A]C', 'A[C>A]G', 'A[C>A]T', 'A[C>G]A', 'A[C>G]C', 'A[C>G]G', 'A[C>G]T', 'A[C>T]A', 'A[C>T]C', 'A[C>T]G', 'A[C>T]T',
                     'A[T>A]A', 'A[T>A]C', 'A[T>A]G', 'A[T>A]T', 'A[T>C]A', 'A[T>C]C', 'A[T>C]G', 'A[T>C]T', 'A[T>G]A', 'A[T>G]C', 'A[T>G]G', 'A[T>G]T',
                     'C[C>A]A', 'C[C>A]C', 'C[C>A]G', 'C[C>A]T', 'C[C>G]A', 'C[C>G]C', 'C[C>G]G', 'C[C>G]T', 'C[C>T]A', 'C[C>T]C', 'C[C>T]G', 'C[C>T]T',
                     'C[T>A]A', 'C[T>A]C', 'C[T>A]G', 'C[T>A]T', 'C[T>C]A', 'C[T>C]C', 'C[T>C]G', 'C[T>C]T', 'C[T>G]A', 'C[T>G]C', 'C[T>G]G', 'C[T>G]T',
                     'G[C>A]A', 'G[C>A]C', 'G[C>A]G', 'G[C>A]T', 'G[C>G]A', 'G[C>G]C', 'G[C>G]G', 'G[C>G]T', 'G[C>T]A', 'G[C>T]C', 'G[C>T]G', 'G[C>T]T',
                     'G[T>A]A', 'G[T>A]C', 'G[T>A]G', 'G[T>A]T', 'G[T>C]A', 'G[T>C]C', 'G[T>C]G', 'G[T>C]T', 'G[T>G]A', 'G[T>G]C', 'G[T>G]G', 'G[T>G]T',
                     'T[C>A]A', 'T[C>A]C', 'T[C>A]G', 'T[C>A]T', 'T[C>G]A', 'T[C>G]C', 'T[C>G]G', 'T[C>G]T', 'T[C>T]A', 'T[C>T]C', 'T[C>T]G', 'T[C>T]T',
                     'T[T>A]A', 'T[T>A]C', 'T[T>A]G', 'T[T>A]T', 'T[T>C]A', 'T[T>C]C', 'T[T>C]G', 'T[T>C]T', 'T[T>G]A', 'T[T>G]C', 'T[T>G]G', 'T[T>G]T']
        #Contruct the indeces of the matrix
        #setting index and columns names of processAvg and exposureAvg
        index1 = genomes.iloc[:,1]
        index2 = genomes.iloc[:,0]
        index = []
        for i, j in zip(index1, index2):
            index.append(i[0]+"["+j+"]"+i[2])
    
    
        index = np.array(pd.Series(index))
        genomes["index"] = index
    
    
        #sort the mutationa types
        genomes["index"]= pd.Categorical(genomes["index"], orderlist)
        genomes = genomes.sort_values("index")
        
    
        genomes = genomes.iloc[:,2:genomes.shape[1]]
    
        
    
        # set the index 
        genomes = genomes.set_index("index")
    
        # prepare the index and colnames variables
        index = np.array(orderlist)
        colnames = np.array(pd.Series(genomes.columns.tolist()))
    
    else:
        
        index = np.array(genomes.iloc[:,0])
        genomes = genomes.iloc[:,1:]
        genomes = genomes.loc[:, (genomes != 0).any(axis=0)]
        colnames = genomes.columns
       
        
        
   
    
    
    return(genomes, index, colnames, mtypes)


###################################################################################### Export Results ###########################################
def export_information(loopResults, mutation_context, output, index, colnames):
    
  
   
    
    # get the number of processes
    i = loopResults[-1]
    
    
   
    
    # get the mutationa contexts    
    #print ("The mutaion type is", mutation_type)    
    m = mutation_context
    if not (m=="DINUC"or m=="INDEL"):
        mutation_type = "SBS"+m
            
    else:
        if m == "DINUC":
            mutation_type = "DBS78"
        elif m== "INDEL":
            mutation_type = "ID83"
    # Create the neccessary directories
    subdirectory = output+"/All_solutions/"+mutation_type+"_"+str(i)+"_Signatures"
    if not os.path.exists(subdirectory):
        os.makedirs(subdirectory)
    
    
    
    #Export the loopResults as pickle objects
    
    #resultname = "signature"+str(i)
    
    # =============================================================================
    #         f = open(output+"/pickle_objects/"+resultname, 'wb')
    #         
    #         pickle.dump(loopResults, f)
    #         f.close()
    # =============================================================================
            
       
    #preparing the column and row indeces for the Average processes and exposures:  
    listOfSignatures = []
    letters = list(string.ascii_uppercase)
    letters.extend([i+b for i in letters for b in letters])
    letters = letters[0:i]
    
    for j,l in zip(range(i),letters)  :
        listOfSignatures.append("Signature "+l)
    listOfSignatures = np.array(listOfSignatures)
    
    #print("print listOfSignares ok", listOfSignatures)
        
    
    #Extract the genomes, processAVG, processStabityAvg
    genome= loopResults[0]
    #print ("genomes are ok", genome)
    processAvg= (loopResults[1])
    exposureAvg= (loopResults[2])
    processStabityAvg= (loopResults[5])
    #print ("processStabityAvg is ok", processStabityAvg)
    
    # Calculating and listing the reconstruction error, process stability and signares to make a csv file at the end
    reconstruction_error = round(LA.norm(genome-np.dot(processAvg, exposureAvg), 'fro')/LA.norm(genome, 'fro'), 2)
    
    
    #print ("reconstruction_error is ok", reconstruction_error)
    #print (' Initial reconstruction error is {} and the process stability is {} for {} signatures\n\n'.format(reconstruction_error, round(processStabityAvg,4), i))
    # Preparing the results to export as textfiles for each signature
    
    #First exporting the Average of the processes
    processAvg= pd.DataFrame(processAvg)
    processes = processAvg.set_index(index)
    processes.columns = listOfSignatures
    processes = processes.rename_axis("MutationType", axis="columns")
    #print(processes)
    #print("process are ok", processes)
    processes.to_csv(subdirectory+"/"+mutation_type+"_S"+str(i)+"_Signatures"+".txt", "\t", index_label=[processes.columns.name]) 
    
    #Second exporting the Average of the exposures
    exposureAvg = pd.DataFrame(exposureAvg.astype(int))
    exposures = exposureAvg.set_index(listOfSignatures)
    exposures.columns = colnames
    exposures = exposures.T
    exposures = exposures.rename_axis("Samples", axis="columns")
    #print("exposures are ok", exposures)
    exposures.to_csv(subdirectory+"/"+mutation_type+"_S"+str(i)+"_Activities.txt", "\t", index_label=[exposures.columns.name]) 
    
    
    # get the standard errors of the processes
    processSTE = loopResults[3]      
    #export the processStd file
    processSTE = pd.DataFrame(processSTE)
    processSTE = processSTE.set_index(index)
    processSTE.columns = listOfSignatures
    processSTE = processSTE.rename_axis("MutationType", axis="columns")
    processSTE.to_csv(subdirectory+"/"+mutation_type+"_S"+str(i)+"_Signatures_SEM_Error"+".txt", "\t", float_format='%.2E', index_label=[processes.columns.name]) 
    
    # get the standard errors of the exposures   
    exposureSTE = loopResults[4] 
    #export the exposureStd file
    exposureSTE = pd.DataFrame(exposureSTE)
    exposureSTE = exposureSTE.set_index(listOfSignatures)
    exposureSTE.columns = colnames
    exposureSTE = exposureSTE.T
    exposureSTE = exposureSTE.rename_axis("Samples", axis="columns")
    exposureSTE.to_csv(subdirectory+"/"+mutation_type+"_S"+str(i)+"_Activities_SEM_Error.txt", "\t", float_format='%.2E', index_label=[exposures.columns.name]) 
    
    all_similarities = loopResults[8].copy() 
    #all_similarities = all_similarities.replace(None, 1000)
    all_similarities['L1_Norm_%'] = all_similarities['L1_Norm_%'].astype(str) + '%'
    all_similarities['L2_Norm_%'] = all_similarities['L2_Norm_%'].astype(str) + '%'
    all_similarities.to_csv(subdirectory+"/"+mutation_type+"_S"+str(i)+"_Samples_stats.txt", sep="\t")
    
    signature_stats =  loopResults[9]               
    signature_stats = signature_stats.set_index(listOfSignatures)
    signature_stats = signature_stats.rename_axis("Signatures", axis="columns")
    signature_stats.to_csv(subdirectory+"/"+mutation_type+"_S"+str(i)+"_"+"Signatures_stats.txt", "\t", index_label=[exposures.columns.name]) 
    
    fh = open(output+"/All_solutions_stat.csv", "a") 
    print ('The reconstruction error is {} and the process stability is {} for {} signatures\n\n'.format(reconstruction_error, round(processStabityAvg,2), i))
    fh.write('{}, {}, {}\n'.format(i, round(processStabityAvg, 2), round(reconstruction_error, 2)))
    fh.close()
    
    
   
    ########################################### PLOT THE SIGNATURES ################################################
    #prepare the texts lists:
    stability_list = signature_plotting_text(loopResults[6], "Stability", "float")
    total_mutation_list = signature_plotting_text(loopResults[7], "Total Mutations", "integer")
    
    
    if m=="DINUC" or m=="78":        
        plot.plotDBS(subdirectory+"/"+mutation_type+"_S"+str(i)+"_Signatures"+".txt", subdirectory+"/Signature_plot" , "S"+str(i), "78", True, custom_text_upper=stability_list, custom_text_middle=total_mutation_list)
    elif m=="INDEL" or m=="83":
        plot.plotID(subdirectory+"/"+mutation_type+"_S"+str(i)+"_Signatures"+".txt", subdirectory+"/Signature_plot" , "S"+str(i), "94", True, custom_text_upper=stability_list, custom_text_middle=total_mutation_list)
    else:
        plot.plotSBS(subdirectory+"/"+mutation_type+"_S"+str(i)+"_Signatures"+".txt", subdirectory+"/Signature_plot", "S"+str(i), m, True, custom_text_upper=stability_list, custom_text_middle=total_mutation_list)
     
        
# =============================================================================
#     processAvg = pd.read_csv(subdirectory+"/"+mutation_type+"_S"+str(i)+"_Signatures_"+".txt", sep="\t", index_col=0)
#     exposureAvg = pd.read_csv(subdirectory+"/"+mutation_type+"_S"+str(i)+"_Sig_activities.txt", sep="\t", index_col=0)
#     probability = probabilities(processAvg, exposureAvg)
#     probability=probability.set_index("Sample")
#     probability.to_csv(subdirectory+"/mutation_probabilities.txt", "\t") 
# =============================================================================
    

#############################################################################################################
######################################## MAKE THE FINAL FOLDER ##############################################
#############################################################################################################
def make_final_solution(processAvg, allgenomes, allsigids, layer_directory, m, index, allcolnames, process_std_error = "none", signature_stabilities = " ", signature_total_mutations= " ", signature_stats = "none", penalty=0.025):
    # Get the type of solution from the last part of the layer_directory name
    solution_type = layer_directory.split("/")[-1]
    
    allgenomes = np.array(allgenomes)
    exposureAvg = np.zeros([processAvg.shape[1], allgenomes.shape[1]] )
    for g in range(allgenomes.shape[1]):
        
        exposures, similarity = add_signatures(processAvg, allgenomes[:,g][:,np.newaxis], cutoff=penalty)
        exposureAvg[:,g] = exposures
        
    
    processAvg= pd.DataFrame(processAvg.astype(float))
    processes = processAvg.set_index(index)
    processes.columns = allsigids
    processes = processes.rename_axis("MutationsType", axis="columns")
    processes.to_csv(layer_directory+"/"+solution_type+"_"+"Signatures.txt", "\t", float_format='%.8f',index_label=[processes.columns.name]) 
    
     
    exposureAvg = pd.DataFrame(exposureAvg.astype(int))
    allsigids = np.array(allsigids)
    exposures = exposureAvg.set_index(allsigids)
    exposures.columns = allcolnames
    exposures = exposures.T
    exposures = exposures.rename_axis("Samples", axis="columns")
    exposures.to_csv(layer_directory+"/"+solution_type+"_"+"Activities.txt", "\t", index_label=[exposures.columns.name]) 
    
    # Calcutlate the similarity matrices
    est_genomes = np.dot(processAvg, exposureAvg)
    all_similarities, cosine_similarities = calculate_similarities(allgenomes, est_genomes, allcolnames)
    all_similarities.iloc[:,[3,5]] = all_similarities.iloc[:,[3,5]].astype(str) + '%'
    all_similarities.to_csv(layer_directory+"/"+solution_type+"_Samples_stats.txt", sep="\t")
    
    
    if type(process_std_error) != str:
        process_std_error= pd.DataFrame(process_std_error)
        processSTE = process_std_error.set_index(index)
        processSTE.columns = allsigids
        processSTE = processSTE.rename_axis("MutationType", axis="columns")
        processSTE.to_csv(layer_directory+"/"+solution_type+"_"+"Signatures_SEM_Error.txt", "\t", float_format='%.2E', index_label=[processes.columns.name]) 
    
    if type(signature_stats)!=str:
        signature_stats = signature_stats.set_index(allsigids)
        signature_stats = signature_stats.rename_axis("Signatures", axis="columns")
        signature_stats.to_csv(layer_directory+"/"+solution_type+"_"+"Signatures_stats.txt", "\t", index_label=[exposures.columns.name]) 
    else:
        signature_total_mutations = np.sum(exposureAvg, axis =1).astype(int)
        signature_total_mutations = signature_plotting_text(signature_total_mutations, "Total Mutations", "integer")
        
       
    ########################################### PLOT THE SIGNATURES ################################################
    
    if m=="DINUC" or m=="78":
        plot.plotDBS(layer_directory+"/"+solution_type+"_"+"Signatures.txt", layer_directory+"/Signature_plot" , solution_type, "78", True, custom_text_upper= signature_stabilities, custom_text_middle = signature_total_mutations )
    elif m=="INDEL" or m=="83":
        plot.plotID(layer_directory+"/"+solution_type+"_"+"Signatures.txt", layer_directory+"/Signature_plot" , solution_type, "94", True, custom_text_upper= signature_stabilities, custom_text_middle = signature_total_mutations )
    else:
        plot.plotSBS(layer_directory+"/"+solution_type+"_"+"Signatures.txt", layer_directory+"/Signature_plot", solution_type, m, True, custom_text_upper= signature_stabilities, custom_text_middle = signature_total_mutations )
   
     
        
    #processAvg = pd.read_csv(layer_directory+"/"+solution_type+"_"+"Signatures.txt", sep="\t", index_col=0)
    #exposureAvg = pd.read_csv(layer_directory+"/"+solution_type+"_"+"Activities.txt", sep="\t", index_col=0)
    
    probability = probabilities(processAvg, exposureAvg, index, allsigids, allcolnames)
    probability=probability.set_index("Sample Names" )
    probability.to_csv(layer_directory+"/Mutation_Probabilities.txt", "\t") 
    
    try:
        clusters = dendrogram(exposureAvg, 0.05, layer_directory)
        clusters.to_csv(layer_directory+"/Cluster_of_Samples.txt", "\t") 
    except:
        pass
    
    
"""
#############################################################################################################
######################################### PLOTTING FUNCTIONS ##############################################
#############################################################################################################
"""

######################################## Clustering ####################################################
def dendrogram(data, threshold, layer_directory):
    colnames = data.columns
    data = np.array(data)

    Z = hierarchy.linkage(data.T, 'single',  'cosine')
    plt.figure(figsize=(15, 9))
    dn = hierarchy.dendrogram(Z, labels = colnames, color_threshold=threshold)
    plt.title("Clustering of Samples Based on Mutational Signatures" )
    plt.ylabel("Cosine Distance")
    plt.xlabel("Sample IDs")
    #plt.ylim((0,1))
    plt.savefig(layer_directory+'/dendrogram.pdf',figsize=(10, 8), dpi=300)
    # which datapoints goes to which cluster
    # The indices of the datapoints will be displayed as the ids 
    Y = hierarchy.fcluster(Z, threshold, criterion='distance', R=None, monocrit=None)
    dataframe = pd.DataFrame({"Cluster":Y, "Sample Names":list(colnames)})
    dataframe = dataframe.set_index("Sample Names")
    #print(dataframe)
    dictionary = {"clusters":Y, "informations":dn}
    
    return dataframe 


######################################## Plot the reconstruction error vs stabilities and select the optimum number of signature ####################################################   
def stabVsRError(csvfile, output, title, all_similarities_list, mtype= ""):
    
    
    data = pd.read_csv(csvfile, sep=",")
    
    #exracting and preparing other similiry matrices from the all_similarities_list
    median_l1 = []; maximum_l1 = []; median_l2 = []; maximum_l2 = []; median_kl = []; maximum_kl = [];
    for values in range(len(all_similarities_list)):
      all_similarities = all_similarities_list[values].iloc[:,[3,5,6]]
      
      
      median_l1.append(all_similarities["L1_Norm_%"].median())
      maximum_l1.append(all_similarities["L1_Norm_%"].max())
      median_l2.append(all_similarities["L2_Norm_%"].median())
      maximum_l2.append(all_similarities["L2_Norm_%"].max())
      median_kl.append(all_similarities["KL Divergence"].median())
      maximum_kl.append(all_similarities["KL Divergence"].max())
    
    medl1 = np.array(median_l1)/100
    medl1 = np.round(medl1, 3)
    # we will use the median_l1 and stability to select the optimal number of signatures
#---------------------------- alternative solution start -------------------------------------------------#
    def change_scale(x, cul = 1, cll = 0.0, nul = 1, nll = 0.0):
        
        current_upper_limit = cul
        current_lower_limit = cll
        new_upper_limit = nul
        new_lower_limit = nll
                
        slope = (new_upper_limit-new_lower_limit)/(current_upper_limit-current_lower_limit)
        y = slope*(x - current_upper_limit) + new_upper_limit
            
            
        return y  
    
    new_data=data
    new_data = new_data.set_index("Total Signatures")
    x = np.array(new_data)
    
    
    
    #scaled_RE = change_scale_array(x[:,0], cul = 1, cll = 0.0, nul = 0.5, nll = 0.0)
    #scaled_Stability = change_scale_array(x[:,1], cul = 1, cll = 0.0, nul = 0.5, nll = 0.0)
    
# =============================================================================
#     scaledRE = np.zeros(len(x[:,1]))
#     for i in range(len(x[:,1])):
#         
#         if x[i,1]>=0.1:
#             scaledRE[i] = change_scale(x[i,1], cul = 1, cll = 0.1, nul = 0.5, nll = 0.1)
#         elif x[i,1]<0.1:
#             scaledRE[i] = change_scale(x[i,1], cul = 0.1, cll = 0.0, nul = 0.1, nll = 0.085)
# =============================================================================
    scaledRE = medl1    
        
    scaledStability = np.zeros(len(x[:,0]))
    for i in range(len(x[:,0])):
        #print(x[i,0])
        if x[i,0]>=0.8:
            scaledStability[i] = change_scale(x[i,0], cul = 1, cll = 0.8, nul = 0.5, nll = 0.2)
        elif x[i,0]<0.8:
            scaledStability[i] = change_scale(x[i,0], cul = 0.8, cll = -1.0, nul = 0.05, nll = 0.001)
    
    
    results  = np.round(scaledStability/scaledRE,2)  
    
    #plt.plot(results)
    #plt.show()
    
    #get the alternative solution  
    alternative_solution  = np.argmax(results)
   
    
#---------------------------- alternative solution end -------------------------------------------------#
    
    
    # Create some mock data
    
    t = np.array(data.iloc[:,0])
    
    data1 = np.array(data.iloc[:,2])  #reconstruction error
    data2 = np.array(data.iloc[:,1])  #process stability
    
    
    #selecting the optimum signature using stability thresh-hold
    try:
        datanew = data[data['Stability']>0.90]
        datanew = datanew[(datanew["Total Signatures"] == datanew["Total Signatures"].max())]
        optimum_signature = int(datanew["Total Signatures"])
    
    except:
        print("No signature set crosses the limit of the thresh-hold. So we cannot recommend any optimum \n number of signature. Selecting the lowest signature number." )
        optimum_signature = data.iloc[0,0]
        

    
    #to the make the shadows with the optimum number of signatues in the plot
    shadow_start = optimum_signature-0.2
    shadow_end=optimum_signature+0.2
    
    alternative_solution = t[alternative_solution]
    shadow_alternative_start = alternative_solution-0.2
    shadow_alternative_end=alternative_solution+0.2
    
    
    fig, ax1 = plt.subplots(num=None, figsize=(10, 6), dpi=300, facecolor='w', edgecolor='k')
    
    color = 'tab:red'
    ax1.set_xlabel('Total Signatures')
    ax1.set_ylabel('Matrix Frobenius%', color=color)
    ax1.set_title(title)
    ax1.plot(t, data1, marker='o', color=color)
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.xaxis.set_ticks(np.arange(min(t), max(t)+1, 1))
    #ax1.axvspan(shadow_start, shadow_end, alpha=0.20, color='#ADD8E6')
    ax1.axvspan(shadow_alternative_start,  shadow_alternative_end, alpha=0.20, color='#0EF91E')         
    # manipulate the y-axis values into percentage 
    vals = ax1.get_yticks()
    ax1.set_yticklabels(['{:,.0%}'.format(x) for x in vals])
    
    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    color = 'tab:blue'
    ax2.set_ylabel('Signature Stability', color=color)  # we already handled the x-label with ax1
    ax2.plot(t, data2, marker='o', color=color)
    ax2.tick_params(axis='y', labelcolor=color)
    
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    #plt.show()
    plt.savefig(output+'/'+mtype+'_selection_plot.pdf')    
    
    plt.close()
    
    
    
   
    
 
    data.iloc[:,2] = data.iloc[:,2]*100
    data = data.assign(**{'Median Sample L1%': median_l1, 'Maximum Sample L1%': maximum_l1, 'Median Sample L2%': median_l2, 'Maximum Sample L2%': maximum_l2, 'Median Sample KL': median_kl, 'Maximum Sample KL': maximum_kl})  
    data=data.rename(columns = {'Stability':'Stability (AVG Silhouette)'})
    data = data.set_index("Total Signatures")
    #put percentage sign after the values from column 3 to 7 
    data.iloc[:,1:6] = data.iloc[:,1:6].astype(str) + '%'
    return alternative_solution, data
######################################## Plot Samples ####################################################
def plot_csv_sbs_samples(filename, output_path, project, mtype="96", percentage=False, custom_text_upper=" " ):

    
    
    data, index, colnames, _ = read_csv(filename, folder = False)
    data.index.names= ["MutationType"]
    data.to_csv("new_file.text", sep="\t")

    plot.plotSBS("new_file.text", output_path, project, mtype, False, custom_text_upper=" ")
    
    os.remove("new_file.text")
    
#plot_csv_sbs_samples("CNS-Oligo.96.csv" , "/Users/mishugeb/Desktop/new_plot", "project", mtype="96", percentage=False, custom_text_upper=" " )
