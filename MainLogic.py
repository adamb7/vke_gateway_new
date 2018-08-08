#!/usr/bin/env python2

class MainLogic:

    def __init__(self, checkpoints, laps):
        self._maxCheckpoints = checkpoints
        self._maxlaps = laps

        self._Init()

    def _Init(self):
        self._lastpos = self._maxCheckpoints - 1 # kezdeti pozicio az a 0 elotti 2-es
#        self._nextpos = self._lastpos + 1 # ennek 0-nak kellene lennie szerintem
        self._nextpos = 0
        self._lap = -1 # hany kort ment eddig
        self._running = False # nem megy

        self._PrintState()

    #majd atnvezeni mert a felelossege kibovult
    def _CheckNext(self):
        if self._nextpos == self._maxCheckpoints:
            self._nextpos = 0

        if self._lastpos == 0:
            self._lap += 1

    def UpdatePosition(self,inputpos): # megkapja, hogy melyik harmadban van az auto 0,1,2
        self._lastpos = inputpos
        self._nextpos = inputpos + 1

        self._CheckNext() # limiteli a nextpos-t, illetve noveli a kor szamolot, ha kell

        self._PrintState()

        #ez keruljon majd kulon classba -- micsoda?


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

