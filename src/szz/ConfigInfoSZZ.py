'''
  Common script to process configuration file
'''


import sys
import os
from distutils import util

from os.path import dirname
sys.path.append(os.path.join(dirname(__file__),'..','util'))

import Util
from ConfigInfo import ConfigInfo


class ConfigInfoSZZ(ConfigInfo):
  
  def __init__(self, newFile):
  
    ConfigInfo.__init__(self, newFile)    
    self.config_szz    = self.cfg.ConfigSectionMap('SZZ')
   
      
  def getSnapshotInterval(self):
    
    self.interval_option = bool(util.strtobool(self.config_szz['interval_option']))
    if self.interval_option is True:
      self.snapshot_interval = int(self.config_szz['snapshot_interval'])
    else:
      self.snapshot_interval = -1
    return self.snapshot_interval
    
  def getShaFiles(self):
    self.snapshot_sha_file = self.config_szz['snapshot_sha_file']
    return self.snapshot_sha_file
      
    
    
  
