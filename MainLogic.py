'''
TEST
'''

import time
import threading
from enum import Enum

class MainLogic:
    
    def __init__(self, checkpoints, laps):
        self._maxCheckpoints = checkpoints
        self._maxlaps = laps
        
        self._Init()
        
    def _Init(self):   
        self._lastpos = self._maxCheckpoints - 1
        self._nextpos = self._lastpos + 1
        self._lap = -1
        self._running = False
        
        self._PrintState()
        
    #majd atnvezeni mert a felelossege kibovult
    def _CheckNext(self):
        if self._nextpos == self._maxCheckpoints:
            self._nextpos = 0
            
        if self._lastpos == 0:
            self._lap += 1
    
    def UpdatePosition(self,inputpos):
        self._lastpos = inputpos
        self._nextpos = inputpos + 1
            
        self._CheckNext()
        
        self._PrintState()
        
        #ez keruljon majd kulon classba
        
               
    def GetNext(self):
        return self._nextpos
    
    def GetLast(self):
        return self._lastpos
    
    def GetLap(self):
        return self._lap
    
    def SetRunning(self, value):
        self._running = value

    def IsRunning(self):
        return self._running

    def _PrintState(self):
        print("Next: %s, Last: %s, Lap: %s" % \
              (self._nextpos, self._lastpos, self._lap))

