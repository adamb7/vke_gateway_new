'''
TEST
'''

import time
import threading
from enum import Enum

class Errors():
        GatewayError = 0
        GatewayPowerError = 1
        BeltPLCError = 2
        RFIDError = 3
        ForkliftPowerError = 4
        TankError = 5

class DemoErrors():
        
    def __init__(self):
        self.InitErrors()
        
    def InitErrors(self):
        self.gatewayError = False
        self.gatewayPowerError = False
        self.beltPLCError = False
        self.rfidError = False
        self.forkliftError = False
        self.tankError = False
    
    def IsGatewayErrorActive(self):
        if self.gatewayError or self.gatewayPowerError:
            return True
        
        return False
    
    '''
    Switch logika amelyet mindenki ajanl a neten
    ''' 
    '''
    Ez a metodus hasznalja a switch logikat
    '''
    #ebbe trycatch, es return hogy sikerult e
    def SetError(self, errorType, value):
        set = self.switcher.get(errorType)
        set(self,value)
    
    def SetGWError(self,value):
        self.gatewayError = value
        
    def SetGWPowerError(self,value):
        self.gatewayPowerError = value
        
    def SetBeltPLCError(self,value):
        self.beltPLCError = value
        
    def SetRFIDError(self,value):
        self.rfidError = value
        
    def SetForklifError(self,value):
        self.forkliftError = value
        
    def SetTankError(self,value):
        self.tankError = value
        
    switcher = {
        0: SetGWError,
        1: SetGWPowerError,
        2: SetBeltPLCError,
        3: SetRFIDError,
        4: SetForklifError,
        5: SetTankError
        }
        
        
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
              
    
 
 
 
def StartLogic():
    t = threading.Thread(target=main)
    t.setDaemon(True)
    t.start()
        
def main():
    #lehetne arg is de nem akarom
    #egy ideje nem lett frissitve ez a logika, nem mukodik helyesen
    errors = Errors()
    demoErrors = DemoErrors()
    
    demoErrors.SetError(errors.GatewayError,True)
    print demoErrors.gatewayError
    
    demoErrors.SetError(errors.GatewayError,False)
    print demoErrors.gatewayError
    
    '''
    ml = MainLogic(3,6)
    
    i = 0
    while True:
        ml.UpdatePosition(i)
        if i < 3:
            i += 1
        else:
            i = 0
        
        time.sleep(1)
        
    '''
        
        
if __name__ == '__main__':
    try:
        main()
        
        
    except KeyboardInterrupt:
        print("Keyboard Interrupt")
        
        