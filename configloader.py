import json
import ledcontrol

class ConfigLoader():

	def __init__(self,fname): # thorws: FileExceptions and JSON parse exceptions

		with open(fname) as f:
			self._conf = json.load(f)



	def getLedconfig(self):
		return self._conf['ledconfig']

	def getLedInversion(self):
		return self._conf['led_inverted']

	def getResetAnimation(self):

		if self._conf['rgb_led']:
			return ledcontrol.LEDAnimationBlue()
		else:
			return ledcontrol.LEDAnimationSwitching()
