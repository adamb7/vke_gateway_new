#!/usr/bin/env python2
import json
from threading import RLock

class FaultManagerScreen:


	error_ids = {"belt_dc_motor": 1, "belt_plc": 2, "pack_moving": 3, "tank_plc": 4,"forklift_plc": 5, "warehouse_RFID": 6, "gateway_power": 7,
		"belt_tank_power": 8, "forklift_power": 9, "warehouse_power": 10,"gateway": 11, "gateway_ping": 12, "belt_dc_motor_ping": 13,
		"belt_plc_ping": 14, "pack_moving_ping": 15, "tank_ping": 16,"forklift_plc_ping": 17, "warehouse_RFID_ping": 18, "gateway_power_sensor_ping": 19,
		"belt_tank_power_sensor_ping": 20, "forklift_power_sensor_ping": 21,"warehouse_power_sensor_ping": 22 }


	# color descriptions
	STATE_OK = "green"
	STATE_OFFLINE = "yellow"
	STATE_ERROR = "red"


	def __init__(self):

		self._states = {}

		self._locker = RLock()

		self._resetEverything()


	def _resetEverything(self):
		with self._locker:
			for k in self.error_ids:
				self._states[k] = {'root' : False, 'state' : self.STATE_OK } # state = color... csak mashogy hivom


	def _buildValues(self):
		with self._locker:

			values = []

			for k,v in self.error_ids.iteritems():
				state = self._states[k]
				values.append({'id': v, 'color': state['state'], 'root': (1 if state['root'] else 0) })


			return values


	def asJSON(self):

		payload = {'description' : "Status update", 'values' : self._buildValues() }

		return json.dumps(payload)



	def resetAllState(self):
		self._resetEverything()


	def setState(self,name,state,root=False):
		with self._locker:
			self._states[name]['state'] = state
			self._states[name]['root'] = root


	def applyScenario(self,scenario): # expects error scenario description
		with self._locker:

			if scenario.get('offline',False):
				for i in scenario['offline']:
					self._states[i]['state'] = self.STATE_OFFLINE

			if scenario.get('error',False):
				for i in scenario['error']:
					self._states[i]['state'] = self.STATE_ERROR

			if scenario.get('root',False):
				for i in scenario['root']:
					self._states[i]['root'] = True



# predefinied scenarios go here:
ScenarioBeltPlcError = { 'error': ['belt_plc'], 'root': ['belt_plc'] }

ScenarioNoLiquidError = { 'error': ['tank_plc'], 'root': ['tank_plc'] }

ScenarioForkliftObstacle = { 'error': ['forklift_plc'], 'root': ['forklift_plc'] }

ScenarioRFIDWarehouse = {'offline': ['warehouse_RFID'], 'error': ['warehouse_RFID_ping'], 'root': ['warehouse_RFID_ping'] }

ScenarioForkliftPower = {'offline' : ['forklift_plc'], 'error': ['forklift_power','forklift_plc_ping'], 'root': ['forklift_power']}

ScenarioGatewayError = {'offline' :  ['belt_dc_motor','belt_plc','pack_moving','tank_plc','forklift_plc','warehouse_RFID','gateway_power','belt_tank_power','forklift_power','warehouse_power'],
			'error' : ['gateway','belt_dc_motor_ping','belt_plc_ping','pack_moving_ping','tank_ping','forklift_plc_ping','warehouse_RFID_ping','gateway_power_sensor_ping','belt_tank_power_sensor_ping','forklift_power_sensor_ping','warehouse_power_sensor_ping'],
			'root': ['gateway']}

ScenarioGatewayPowerError = {'offline' :  ['belt_dc_motor','belt_plc','pack_moving','tank_plc','forklift_plc','warehouse_RFID','gateway_power','belt_tank_power','forklift_power','warehouse_power'],
			'error' : ['gateway','belt_dc_motor_ping','belt_plc_ping','pack_moving_ping','tank_ping','forklift_plc_ping','warehouse_RFID_ping','gateway_power_sensor_ping','belt_tank_power_sensor_ping','forklift_power_sensor_ping','warehouse_power_sensor_ping','gateway_ping'],
			'root': ['gateway','gateway_power','gateway_ping']}
