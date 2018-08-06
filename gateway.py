import json
import os
import paho.mqtt.client as paho
import time
from RPi import GPIO
try:
    from urllib.request import urlopen
except ImportError:
    
    from urllib2 import urlopen
    
import logging
import traceback

import MainLogic as logic

import sys
import threading

import IRSensor as ir

import ledcontrol
import faultmanagerscreen

'''
LED setup
'''

GPIO.setmode(GPIO.BCM)

ledconfig = {'gw_power': {'r': 19, 'g': 13}, 'gw': {'r': 6, 'g': 5}, 'rfid': {'g' : 20, 'r' : 21}}
lc = ledcontrol.LEDControl(ledconfig,ledcontrol.LEDAnimationOff(),True)
lc.start()

'''
Fault manager thingy setup
'''

fm = faultmanagerscreen.FaultManagerScreen()



#Jo csunya, majd szepre atirni
last_time = time.time()

'''
IR Sensing ezt hivogatja ha lat valamit
borzaszto nagy retek
'''
reset_active = False
def IRCallback():
    global last_time, reset_active
    global RFID_warehouse_error_running
     
    if reset_active:
        EndDemo()
        reset_active = False
        client.publish(carManagement, stopReset, qos=1)
        
        
    elif not RFID_warehouse_error_running and (time.time() - last_time) > 25: 
        
        if ml.GetLap() == 1:
            client.publish(carManagement, "stop", qos=1)
            RFID_warehouse_error_running = True

            if not gateway_error_running and not gateway_power_error_running:
                fm.applyScenario(faultmanagerscreen.ScenarioRFIDWarehouse)
                publish_to_faultmanager()

                lc.setAnimation('rfid',ledcontrol.LEDAnimationError())
                time.sleep(10)
                lc.setAnimation('rfid',ledcontrol.LEDAnimationGood())

                RFID_warehouse_error_running = False

                #kiirni metodusba
                #nagyon csunya majd kitalalni valamit
                if not (gateway_power_error_running or gateway_error_running \
                        or belt_plc_error_running):
                    client.publish(carManagement, start, qos=1)

                    if not (gateway_power_error_running or gateway_error_running \
                        or belt_plc_error_running):
                        reset_error()
        
        last_time = time.time()


#osszefogo setup metodusba kitenni    
ir.callback = IRCallback
ir.StartSampling()

 
'''
MQTT beallito metodus
'''
client = paho.Client()
def InitMQTT():
    global client
    
    mqtt_username = "user"
    mqtt_password = "user"
    mqtt_broker_ip = "10.3.141.3"
    port = 1883
    
    client.username_pw_set(mqtt_username, mqtt_password)
    client.connect(mqtt_broker_ip)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_publish = on_publish


'''
Ezeket kulon classba kitenni --> "DemoErrors"
'''
gateway_error_running = False
gateway_power_error_running = False
belt_plc_error_running = False
RFID_warehouse_error_running = False
forklift_power_error_running = False
forklift_obstacle_error_running = False
liquid_error_running = False

'''
Test jellegu, csak egy helyen van kiprobalva
de a lenyege kulon classba kell kitenni
'''
def IsErrorActive():
    return gateway_error_running or gateway_power_error_running \
           or belt_plc_error_running or RFID_warehouse_error_running \
           or forklift_power_error_running or forklift_obstacle_error_running \
           or liquid_error_running

def ResetAllErrors():
    global gateway_error_running, gateway_power_error_running
    global belt_plc_error_running, RFID_warehouse_error_running
    global forklift_power_error_running, forklift_obstacle_error_running
    global liquid_error_running
    
    gateway_error_running = False
    gateway_power_error_running = False
    belt_plc_error_running = False
    RFID_warehouse_error_running = False
    forklift_power_error_running = False
    forklift_obstacle_error_running = False
    liquid_error_running = False
#kene egy logika ami eldonti, hogy hatterszalon fut e vagy sem
#logging.basicConfig(filename="gateway.log",level=logging.DEBUG, \
#                    format="%(asctime)s %(message)s")

logging.basicConfig(level=logging.DEBUG, \
                    format="%(asctime)s %(message)s")


'''
String constansok
'''
carManagement = "carManagement"
positionManagement = "positionManagement"
start = "start"
stop = "stop"
startFill = "startFill"
resumeFill = "resumeFill"
stopFill = "stopFill"
startReset = "startReset"
stopReset = "stopReset"
terminate = "terminate"


ml = logic.MainLogic(checkpoints = 3,laps = 6)

'''
Eza  metodus a Fault manager server gepehez csatlakozik
Debug okok miatt a bool visszatereset nem hasznaljuk
'''
def wait_for_internet_connection(maxTry=100):
    tryCount = 0
    while tryCount < 100:
        try:
            response=urlopen('http://10.3.141.2:8081/console/',timeout=1)
            return True
        except:
            logging.info("A kapcsolodas nem sikerult a FaultManagerhez. Ujraporbalkozas...")
            tryCount += 1

    logging.info("A kapcsolodas nem sikerult a FaultManagerhez.")
    return False


def publish_to_faultmanager():
    global fm
    payload = fm.asJSON()
    client.publish("ERROR_DEMO", payload, retain=True, qos=1)


def reset_error():
    global fm

    fm.resetAllState()

    if gateway_power_error_running: # I have no idea what this part does :S
        fm.applyScenario(faultmanagerscreen.ScenarioGatewayPowerError)
    else:
        if gateway_error_running:
            fm.applyScenario(faultmanagerscreen.ScenarioGatewayError)
        else:
            if belt_plc_error_running:
                fm.applyScenario(faultmanagerscreen.ScenarioBeltPlcError)

            if liquid_error_running:
                fm.applyScenario(faultmanagerscreen.ScenarioNoLiquidError)

            if forklift_power_error_running:
                fm.applyScenario(faultmanagerscreen.ScenarioForkliftPower)

            if forklift_obstacle_error_running:
                fm.applyScenario(faultmanagerscreen.ScenarioForkliftObstacle)

            if RFID_warehouse_error_running:
                fm.applyScenario(faultmanagerscreen.ScenarioRFIDWarehouse)

    publish_to_faultmanager()

def on_connect(client, userdata, flag, rc):
    global gateway_error_running
    gateway_error_running = False
    global gateway_power_error_running
    gateway_power_error_running = False
    global belt_plc_error_running
    belt_plc_error_running = False

    print("Connected!", str(rc))

    client.subscribe("RFID_warehouse_error")
    client.subscribe("RFID_warehouse_error_reset")
    client.subscribe("gateway_error")
    client.subscribe("gateway_error_reset")
    client.subscribe("gateway_power_error")
    client.subscribe("gateway_power_error_reset")
    client.subscribe("forklift_power_error_reset")
    client.subscribe("forklift_power_error")
    client.subscribe("forklift_obstacle_error")
    client.subscribe("forklift_obstacle_error_reset")
    client.subscribe("no_liquid_error")
    client.subscribe("no_liquid_error_reset")
    client.subscribe("belt_plc_error")
    client.subscribe("belt_plc_error_reset")
    client.subscribe("start_system")
    client.subscribe("stop_system")
    client.subscribe("restart_system")

    client.subscribe(carManagement)
    client.subscribe(positionManagement)

def on_publish(client, userdata, result):
    #ide majd logolni kell rendesen
    print("\nData published: ", userdata)

#ezt majd kivenni, ha a position management mukodesbe lep
temp = 0

#test, ezt majd a classba kitenni
systemStarted = False
'''
Az MQTT rol erkezo uzenetek handlere, a main logika itt helyezkedik el
'''
# Ezt a kommentet modositottam, mert ekezetek voltak benne, es a python meghalt miatta -- Marci
def on_message(client, userdata, msg):
    print("Topic: ", msg.topic + "Message: " + msg.payload)
    
    global belt_plc_error_running
    global gateway_error_running
    global gateway_power_error_running
    global RFID_warehouse_error_running
    global forklift_power_error_running
    global forklift_obstacle_error_running
    global liquid_error_running
    
    global temp
    global systemStarted
    global reset_active
    
    global fm,lc,ml
    
    if not systemStarted:
        if msg.topic == "start_system":
            systemStarted = True
            lc.setAllAnimation(ledcontrol.LEDAnimationGood())
            client.publish(carManagement, "initLED", qos=1)
            
    else:
        if msg.topic == "stop_system":
            #kell egy "clear" logika
            systemStarted = False
            ml._Init()
            #vagy megallitjuk azonnal, vagy a helyere visszuk
            client.publish(carManagement, terminate, qos=1)
            lc.setAllAnimation(ledcontrol.LEDAnimationOff())
            #os.system('sudo shutdown -r now')
        
        #"Demo felelesztese alvo modbol", Demot meg nem inditottak el        
        #elif msg.topic == "restart_system" and not reset_active:
        elif msg.topic == "restart_system" and not ml.IsRunning():
            #ml._Init()
            ml.SetRunning(True)
            client.publish(carManagement, start, qos=1)
            reset_error()
            temp = 0
            
        elif ml.IsRunning():         
            #nem kell kikopni az errort, mert itt generaljuk        
            if msg.topic == "forklift_obstacle_error":
                forklift_obstacle_error_running = True
                      
                if not (gateway_power_error_running or gateway_error_running\
                        or belt_plc_error_running):
                    fm.applyScenario(faultmanagerscreen.ScenarioForkliftObstacle)
                    publish_to_faultmanager()
                    
            elif msg.topic == "forklift_obstacle_error_reset":
                forklift_obstacle_error_running = False
                
                if not (gateway_error_running or gateway_power_error_running\
                        or belt_plc_error_running):
                    reset_error()
                    
            elif msg.topic == "forklift_power_error_reset":
                forklift_power_error_running = False
                
                #IsConsolErrorRunning metodus a demoerror classhoz
                if not (gateway_error_running or gateway_power_error_running\
                        or belt_plc_error_running):
                    client.publish(carManagement, start, qos=1)
                    reset_error()
                    
            elif msg.topic == "no_liquid_error":
                liquid_error_running = True
                client.publish(carManagement, stop, qos=1)
                      
                if not gateway_power_error_running and not gateway_error_running:
                    fm.applyScenario(faultmanagerscreen.ScenarioNoLiquidError)
                    publish_to_faultmanager()
                    
            elif msg.topic == "no_liquid_error_reset":       
                liquid_error_running = False
                
                if not gateway_power_error_running and not gateway_error_running:
                    client.publish(carManagement, start, qos=1)
                    client.publish(carManagement, resumeFill, qos=1)
                    reset_error()
                           
            elif msg.topic == "belt_plc_error":   
                belt_plc_error_running = True

                if not gateway_error_running and not gateway_power_error_running:
                    client.publish(carManagement, stop, qos=1)
                
                    if ml.GetNext() == 1:       
                        client.publish(carManagement, stopFill, qos=1)
                    
                    fm.applyScenario(faultmanagerscreen.ScenarioBeltPlcError)
                    publish_to_faultmanager()

            elif msg.topic=="belt_plc_error_reset":
                belt_plc_error_running = False
                
                if not gateway_error_running and not gateway_power_error_running:
                    client.publish(carManagement, start, qos=1)
                    
                    if ml.GetNext() == 1:
                        client.publish(carManagement, "resumeFill", qos=1)
                    
                    reset_error()

            elif msg.topic == "gateway_error":
                gateway_error_running = True
                      
                if not (gateway_power_error_running or belt_plc_error_running):
                    client.publish(carManagement, stop, qos=1)
                
                    #valami belt check metodusba ezeket kikellene szervezni
                    if ml.GetNext() == 1:
                        client.publish(carManagement, stopFill, qos=1)
                    
                    fm.applyScenario(faultmanagerscreen.ScenarioGatewayError)
                    
                    lc.setAnimation('gw',ledcontrol.LEDAnimationError())

                    publish_to_faultmanager()
                    
             
            elif msg.topic == "gateway_error_reset":
                gateway_error_running = False
                lc.setAnimation('gw',ledcontrol.LEDAnimationGood())
                
                print(IsErrorActive())
                
                if not IsErrorActive():
                    client.publish(carManagement, start, qos=1)
                    if ml.GetNext() == 1:
                        client.publish(carManagement, resumeFill, qos=1)
                    
                    reset_error()
                    
            elif msg.topic == "gateway_power_error":
                gateway_power_error_running = True
                
                client.publish(carManagement, stop, qos=1)
                
                #valami belt check metodusba ezeket kikellene szervezni
                if ml.GetNext() == 1:
                    client.publish(carManagement, stopFill, qos=1)
                     
                fm.applyScenario(faultmanagerscreen.ScenarioGatewayPowerError)

                lc.setAnimation('gw_power',ledcontrol.LEDAnimationError())
                
                publish_to_faultmanager()       
                
            elif msg.topic == "gateway_power_error_reset":
                gateway_power_error_running = False
                lc.setAnimation('gw_power',ledcontrol.LEDAnimationGood())

                #kitenni majd a metodusba
                if not (gateway_error_running or belt_plc_error_running):
                    client.publish(carManagement, start, qos=1)
                
                    if ml.GetNext() == 1:
                        client.publish(carManagement, resumeFill, qos=1)
                    
                    
                    reset_error()
                
            elif msg.topic == carManagement:
                if msg.payload == "update":
                    #ezt majd atkell helyezni de a kocsi egyelore ezt tudja publisholni
                    ml.UpdatePosition(temp)
                    temp += 1
                    
                    #muszaj kulon szaloninditani kulonben nem kulon kuldi az mqtt uzeneteket
                    t = threading.Thread(target=ScenarioTest)
                    t.setDaemon(True)
                    t.start()
                     
                    if temp > 2:
                        temp = 0
                
                #ugytunik nem hasznaljuk mar, kiveheto
                if msg.payload == "ready":
                    pass
                    #client.publish(carManagement, start)
                
                
            elif msg.topic == positionManagement:
                
                try:
                    inputpos = int(msg.payload)
                    
                    #ml.UpdatePosition(inputpos)
                
                except:
                    traceback.print_exc()
                    logging.debug("Konvertalasi hiba, payload: %s" % msg.payload)
                    
            #ha futas kozben nyomjak a resetet
            #az IR sensorra hagytam nem a szamlalasra
            elif msg.topic == "restart_system":
                reset_active = True
                ml.SetRunning(False)
                client.publish(carManagement, startReset, qos=1)
                reset_error()
                temp = 0
    
'''
A forgatokonyv egy reszet kezeli
'''
def ScenarioTest():
    '''
    Minden korre ervenyes esetek
    ''' 
    if ml.GetNext() == 1 and ml.GetLap() < 6:
        time.sleep(2)
        client.publish(carManagement,"startFill")
             
    elif ml.GetNext() == 0:
        client.publish(carManagement,"emptyBottle")
        
    '''
    Kor specifikus esetek
    '''
    if ml.GetLap() == 3 and ml.GetNext() == 0:
        #classba kitenni
        time.sleep(8)
        client.publish(carManagement, "stopAndBlink", qos=1)
        
        forklift_power_error_running = True
        fm.applyScenario(faultmanagerscreen.ScenarioForkliftPower)
        publish_to_faultmanager()
    
    #A tank kommunikaciojanak hibaja miatt tettem ide bele
    #De ha az megoldodik, ralehet hagyatkozni a fentebb levo
    #"no_liquid_error" uzenetre
    elif ml.GetLap() == 5 and ml.GetNext() == 1:
        time.sleep(2.85)
        client.publish(carManagement, stop, qos=1)
        client.publish(carManagement, stopFill, qos=1)
        #ide majd a no liquid error cuccait
                
    elif ml.GetLap() == 5 and ml.GetNext() == 0:     
        EndDemo()
          
    

def EndDemo(delay = 6):
    time.sleep(delay)
    client.publish(carManagement, stop, qos=1)
    ml._Init()
    temp = 0
    ResetAllErrors()
    reset_error()


wait_for_internet_connection()

if __name__ == '__main__':
    try:
        '''
        kene kulon setup metodus hogy ne ezt szemeteljuk tele
        '''
        InitMQTT()
        client.loop_forever()

    except KeyboardInterrupt:
        print("Keyboard Interrupt")

        try:
            lc.setAllAnimation(ledcontrol.LEDAnimationOff())

        except SystemExit:
            os._exit(0)

    finally:
	lc.shutdown()
        fm.resetAllState()
        publish_to_faultmanager()
