# -*- cod"ing: utf-8 -*-
'''

@author:    Liam Stubbington, 
            RT Physicist, Cambridge University Hospitals NHS Foundation Trust

'''
from datetime import datetime as dt 
from os.path import normpath, join
from csv import DictWriter as dw

class NHSProKnowLog():
    '''
    Logging object template. 

    Writes a list of strings, or a list of dicts to a log file. 
    The default filename and path contains the time of instantiation. 
    
    '''
    def __init__(self, log_path: str = ".", 
                log_lines: list = None, headers = None):

        self.log_lines = log_lines
        self.log_path = log_path
        self.headers = headers
        
        if self.log_lines:

            now = dt.now().strftime("%y-%M-%d-%H-%M-%S")
            f_name = now + "_nhs_pk.log"

            if not self.log_path:
                log_path = "./log"

            self.f_out = normpath(join(log_path, f_name))

            if isinstance(log_lines[0], dict):
                self.write_list_of_dicts() 
            else:
                self.write_list_of_strs() 
    
    def write_list_of_strs(self):

        try:
            with open(self.f_out, 'a', encoding='utf-8') as f:
                if self.headers:
                    f.write(self.headers + "\n")
                for line in self.log_lines:
                    f.write(line + "\n")

        except: 
            raise FileNotFoundError() 

    def write_list_of_dicts(self):
        try:
            with open(self.f_out, 'a', encoding='utf-8', newline = '') as f:
                a_dw = dw(f, self.headers)
                a_dw.writeheader()
                a_dw.writerows(self.log_lines)
        except:
            raise FileNotFoundError()