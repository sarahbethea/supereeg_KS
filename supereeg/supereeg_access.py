import supereeg as se
import numpy as np
import warnings 
warnings.simplefilter("ignore")
import scipy.io
from pathlib import Path
import os

# Script to aid in supereeg model creation with Kai Miller EEG dataset, only supports .mat files with data and locs keys

class EA:
    
    def __init__(self, paths_data, paths_locs,subjects,sample_rate):
        # Class takes array of file paths for data and location files and sample rate of data
        self.subjects = subjects
        self.paths_data = paths_data
        self.paths_locs = paths_locs
        self.sample_rate = sample_rate
        self.datas = []
        self.locs = []
        # Loop to load in .mat file for both data and locs
        for i in range(len(paths_data)):
            mat_data = scipy.io.loadmat(paths_data[i])
            mat_loc = scipy.io.loadmat(paths_locs[i])
            self.datas.append(mat_data["data"])
            self.locs.append(mat_loc["locs"])

        # Declares array that will hold all brain objects(bo) and loop to make bo
        self.bos = []
        for i in range(len(self.datas)):
            meta = {"subjectID": subjects[i],
                    "index": i}
            self.bos.append(se.Brain(self.datas[i],self.locs[i],sample_rate=self.sample_rate,meta=meta))

        self.mos = []
    
    def get_data(self):
        return self.datas
    
    def get_locs(self):
        return self.locs
    
    def get_bos(self):
        return self.bos
    
    def get_mos(self):
        if len(self.mos) == 0:
            print("No models have been created")
        return self.mos
    
    def make_all_mo(self):
        for i in range(len(self.bos)):
            self.mos.append(se.Model(self.bos[i],self.locs[i]))
    
    def make_mo(self,bo,locs):
        mo = se.Model(bo,locs=locs)
        self.mos.append(mo)
        return mo
    
    def combine_mos(self, exclude_mos=None):
        
        if exclude_mos == None:
            big_mo = self.mos[0]
            i=1
            for i in range(len(self.mos)-1):
                big_mo += self.mos[i]

            return big_mo
        else:
            new_mos = self.mos
            for i in range(len(exclude_mos)):
                new_mos.pop(exclude_mos[i])

            big_mo = new_mos[0]
            j=1
            for j in range(len(new_mos)-1):
                big_mo += new_mos[j]
            
            return new_mos,big_mo



                


    


    '''def remove_mo(self, index):
        rmv_mo = self.mos.pop(index)
        return rmv_mo
    
    def remove_bo(self, index):
        rmv_bo = self.bos.pop(index)
        return rmv_bo
    
    def remove_allmo(self):
        self.mos = []
    
    def remove_allbo(self):
        self.bos = []
    
    def remove_alldata(self):
        self.datas = []
    
    def remove_alllocs(self):
        self.locs = []

    def remove_data(self,index):
        rmv_data = self.datas.pop(index)
        self.paths_data.pop(index)
        return rmv_data
    
    def remove_locs(self,index):
        rmv_locs = self.locs.pop(index)
        self.paths_locs.pop(index)
        return rmv_locs
    
    def remove_DL(self,index):
        rmv_data = self.datas.pop(index)
        rmv_locs = self.locs.pop(index)
        self.paths_data.pop(index)
        self.paths_locs.pop(index)
        return rmv_data, rmv_locs'''
