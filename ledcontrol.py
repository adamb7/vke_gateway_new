#!/usr/bin/env python2
import RPi.GPIO as GPIO
from threading import Thread,Lock,RLock
import time
import copy

# az animacioknal vannak olyanok, aminek valami initial state is van, ezt igy konyebb megcsinalni

class LEDAnimationOff:

 	def animate(self):
		return {'r': False, 'g': False, 'b': False}


class LEDAnimationGood:

 	def animate(self):
		return {'r': False, 'g': True, 'b': False}


class LEDAnimationReady:

	def animate(self):
		return {'r': True, 'g': False, 'b': False}


class LEDAnimationError:

	def __init__(self):
		self._state = True
		self._counter = 10

 	def animate(self):

		if self._counter > 0:
			self._counter -= 1
		else:
			self._state = not self._state

		return {'r': self._state, 'g': False, 'b': False}


class LEDAnimationSwitching:

	def __init__(self):
		self._state = True

 	def animate(self):

		self._state = not self._state

		return {'r': self._state, 'g': not self._state, 'b': False }


class LEDAnimationBlue:

 	def animate(self):

		return {'r': False, 'g': False, 'b': True}


# -- the main thing --

class LEDControl(Thread):

	def __init__(self,gpio_conf,default_anim,inverted=True):

		Thread.__init__(self)

		self._anims = {}

		for k,v in gpio_conf.iteritems():	# configure all led pins as outputs
			for cn,cp in v.iteritems(): # colorname & colorpin
				GPIO.setup(cp,GPIO.OUT) # values should be in [r g b]

			self._anims[k] = copy.deepcopy(default_anim) # Explained bellow


		if inverted:
			self._on = GPIO.LOW
			self._off = GPIO.HIGH
		else:
			self._on = GPIO.HIGH
			self._off = GPIO.LOW

		self._gpio_conf = gpio_conf
		self._blackout = False
		self._running = True
		self._ledlock = Lock()
		self._command_lock = RLock()

	def _setLED(self,id,color,state): # setting a led's state by it's ID
		if self._blackout:
			return

		with self._ledlock:
			try:
				GPIO.output(self._gpio_conf[id][color],self._on if state else self._off)
			except KeyError: # missing leds
				pass

	def _getLED(self,id,color): # get led state by it's ID
		with self._ledlock:
			try:
				return GPIO.input(self._gpio_conf[id][color]) == self._on
			except KeyError: # missing leds
				return None

	def _setLEDRGB(self,id,rgb):
		for c in ['r','g','b']:
			self._setLED(id,c,rgb[c])


	def _turnOffAll(self): # this should be considered as critical as well, so we lock this as one operation
		with self._ledlock:
			for k,v in self._gpio_conf.iteritems():
				for cn,cp in v.iteritems():
					GPIO.output(cp,self._off)

	def _cleanup(self):

		pins_to_cleanup = []

		for k,v in self._gpio_conf.iteritems():
			for cn,cp in v.iteritems():
				pins_to_cleanup.append(cp)

		if pins_to_cleanup:
			GPIO.cleanup(pins_to_cleanup)

	# thread

	def run(self):

		while self._running:

			with self._command_lock: # no command should be issueed while we are setting the leds
				for k,v in self._anims.iteritems(): # key - name of the led group, value - animation to be applied
					try:
						self._setLEDRGB(k,v.animate())

					except KeyError: # missing animations
						pass


			time.sleep(0.25)

		self._cleanup()

	# public stuff

	def shutdown(self):
		self._running = False


	def setAnimation(self,id,anim):
		with self._command_lock:
			self._anims[id] = anim


	def setAllAnimation(self,anim):
		with self._command_lock:
			for k in self._anims:
				self._anims[k] = copy.deepcopy(anim) # ez azert kell, hogy ne ugyanaz az objektum legyen minden csoporthoz rendelve, es igy amikor meghivjuk az animate-t tobb csoporton, az affecteli a tobbit


	def setBlackout(self,state):
		with self._command_lock:
			self._blackout = state
			if state:
				self._turnOffAll()
