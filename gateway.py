#!/usr/bin/env python2

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
import configloader


# first
gatewayconfig = configloader.ConfigLoader("/etc/gatewayconfig.json") # any exception this function throws should kill the program


'''
LED setup
'''

GPIO.setmode(GPIO.BCM)

lc = ledcontrol.LEDControl(gatewayconfig.getLedconfig(), ledcontrol.LEDAnimationOff(), gatewayconfig.getLedInversion())
lc.start()

'''
Fault manager thingy setup
'''

fm = faultmanagerscreen.FaultManagerScreen()






#Jo csunya, majd szepre atirni
last_time = time.time()

# ez arra van, hogy bizonyos szalak blokkoljanak, ha a pause aktiv, de csak akkor amikor kell
pause_event = threading.Event() # tessek odafigyelni, hogy nem minden szal szereti, ha blokkolva van, de ennek van egy isSet method-ja is
pause_event.set() # not blocking by default

systemStarted = False
reset_active = False


'''
IR Sensing ezt hivogatja ha lat valamit
borzaszto nagy retek
'''
def IRCallback(): # egyszerre csak egy peldany fut belole, nem hiv meg parhuzamosan tobbet az IR szenzor
    global last_time, reset_active
    global RFID_warehouse_error_running
    global pause_event

    print("IR event triggered")

    if reset_active: # szoval, ha active a reset, es vissza ert a helyere
        print("reset sequence done")
        EndDemo(3.5) # blocking
        reset_active = False # a reset flaget hozza helyre
        if systemStarted:
            client.publish(carManagement, stopReset, qos=1) # a reset flag-et az auton is billentse be ??


    elif not RFID_warehouse_error_running and (time.time() - last_time) > 15:

        if ml.GetLap() == 1:
            client.publish(carManagement, "stop", qos=1)
            RFID_warehouse_error_running = True

            if not gateway_error_running and not gateway_power_error_running:
                fm.applyScenario(faultmanagerscreen.ScenarioRFIDWarehouse)
                publish_to_faultmanager(fm)

                lc.setAnimation('rfid',ledcontrol.LEDAnimationError())
                for i in range(100): # 10mp
                    time.sleep(0.1)

                    if (not systemStarted) or reset_active: # ha system shutdown vagy reset event erkezett kozben
                        return

                pause_event.wait()

                if (not systemStarted) or reset_active: # hs system shutdown vagy reset event erkezett kozben
                    return

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
    while tryCount < maxTry:
        try:
            response=urlopen('http://10.3.141.2:8081/console/',timeout=1)
            return True

        except KeyboardInterrupt:
            raise # ezt tovabbdobjuk, kulonben nem lehet leloni a programot

        except:
            logging.info("A kapcsolodas nem sikerult a FaultManagerhez. Ujraporbalkozas...")
            tryCount += 1
            time.sleep(2)

    logging.info("A kapcsolodas nem sikerult a FaultManagerhez.")
    return False


def publish_to_faultmanager(_fm): # from faultmanagerscreen object
    payload = _fm.asJSON()
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

    publish_to_faultmanager(fm)


def shutdown_system(): # called by timer
	print("Shutting down system...")
	os.system('systemctl poweroff')


shutdown_timer = None


def on_connect(client, userdata, flag, rc):
    global gateway_error_running # what are those doing here? :S
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
    client.subscribe("console") # pause channel

    client.subscribe(carManagement)
    client.subscribe(positionManagement)

def on_publish(client, userdata, mid):
    #ide majd logolni kell rendesen
    print("Message published: " + str(mid))

#ezt majd kivenni, ha a position management mukodesbe lep # Kiraly, de amugy mi ez? # asszem megfejtettem...
temp = 0


'''
Az MQTT rol erkezo uzenetek handlere, a main logika itt helyezkedik el
'''
# Ezt a kommentet modositottam, mert ekezetek voltak benne, es a python meghalt miatta -- Marci
def on_message(client, userdata, msg):
    print("Topic: " + msg.topic + "  Message: " + msg.payload)
    
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

    global shutdown_timer


    
    if not systemStarted:
        if msg.topic == "start_system":

            if shutdown_timer:
                shutdown_timer.cancel() # cancel shutting down
                print("System shutdown canceled")

            systemStarted = True
            lc.setAllAnimation(ledcontrol.LEDAnimationGood())
            client.publish(carManagement, "initLED", qos=1)
            pause_event.set() # ha esetleg valahogy netalantan ez bebugolt volna clear allapotban, akkor reseteljuk, mert kulonben nem indul a demo

    else:
        if msg.topic == "stop_system":
            #kell egy "clear" logika
            systemStarted = False
            ml._Init()
            #vagy megallitjuk azonnal, vagy a helyere visszuk
            client.publish(carManagement, terminate, qos=1)
            lc.setAllAnimation(ledcontrol.LEDAnimationOff())

            ResetAllErrors() # internal flags
            reset_error() # faultmanager board according to internal flags and publishses it
            reset_active = False # ha reset kozben csaptunk ra a stop_system-re, akkor kovetkezo inditasnal egy ilyen fel-reset-fel-nem-reset allapot keletkezett, ezt fixalja ez a sor
            pause_event.set() # unblocking stuff, this should be reseted on system stop as well


            shutdown_timer = threading.Timer(15,shutdown_system) # start system shutdown timer
            shutdown_timer.start()
            print("System shutdown in 15s! Use start_system to cancel.")


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
                    publish_to_faultmanager(fm)
                    
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
                    publish_to_faultmanager(fm)
                    
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
                    publish_to_faultmanager(fm)

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

                    publish_to_faultmanager(fm)
                    
             
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
                
                publish_to_faultmanager(fm)       
                
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
                if msg.payload == "update": # ilyent akkor kapunk, ha az auto at haladt egy meroleges vonalon
                    #ezt majd atkell helyezni de a kocsi egyelore ezt tudja publisholni
                    ml.UpdatePosition(temp)
                    temp += 1

                    #muszaj kulon szaloninditani kulonben nem kulon kuldi az mqtt uzeneteket
                    t = threading.Thread(target=ScenarioTest)
                    t.setDaemon(True)
                    t.start()

                    if temp > 2: # 0,1,2
                        temp = 0

                #ugytunik nem hasznaljuk mar, kiveheto
                if msg.payload == "ready":
                    pass
                    #client.publish(carManagement, start)
                
                
            elif msg.topic == positionManagement:
                
                try:
                    inputpos = int(msg.payload)

                    #ml.UpdatePosition(input)

                except ValueError: # ha sima except van it, akkor a KeyboardInterrupt-ot is elkapja
                    traceback.print_exc()
                    logging.debug("Konvertalasi hiba, payload: %s" % msg.payload)
                    
            #ha futas kozben nyomjak a resetet
            #az IR sensorra hagytam nem a szamlalasra
            elif msg.topic == "restart_system":
                reset_active = True
                ml.SetRunning(False)
                client.publish(carManagement, startReset, qos=1)
                ResetAllErrors() # internal flags
                reset_error() # fault manager screen
                lc.setAllAnimation(ledcontrol.LEDAnimationGood()) # ledek
                temp = 0

            elif msg.topic == "console":

                if msg.payload == "stop":
                    client.publish(carManagement, "pause", qos=1)
       	            pause_event.clear() # stuff will be blocked

                elif msg.payload == "start":
                    client.publish(carManagement, "unpause", qos=1)
                    pause_event.set() # unblocking stuff


'''
A forgatokonyv egy reszet kezeli
'''
def ScenarioTest():
    '''
    Minden korre ervenyes esetek
    '''
    if ml.GetNext() == 1 and ml.GetLap() < 6: # toltes indito
        time.sleep(2)

	if reset_active or (not systemStarted): # ha a 2mp varakozas alatt lett volna egy reset vagy system_stop
            return

        client.publish(carManagement,"startFill")

    elif ml.GetNext() == 0: # empty indito

	if reset_active or (not systemStarted): # ha lett volna egy reset vagy system_stop
            return

        client.publish(carManagement,"emptyBottle")

    '''
    Kor specifikus esetek
    '''
    if ml.GetLap() == 2 and ml.GetNext() == 0: # power error - mivel az uj kor a futoszalag elejen kezdodik, ezert a '3'-as kor valojaban a 2-es kor
        #classba kitenni
        for i in range(100): # 8 sec
            time.sleep(0.08)

            pause_event.wait() # ha pause van alljon meg a timer is

            if reset_active or (not systemStarted): # ha ez alatt a magic 8mp varakozas alatt valami lenne
                return


        client.publish(carManagement, "stopAndBlink", qos=1)

        forklift_power_error_running = True
        fm.applyScenario(faultmanagerscreen.ScenarioForkliftPower)
        publish_to_faultmanager(fm)

    #A tank kommunikaciojanak hibaja miatt tettem ide bele
    #De ha az megoldodik, ralehet hagyatkozni a fentebb levo
    #"no_liquid_error" uzenetre
    elif ml.GetLap() == 5 and ml.GetNext() == 1: # no liquid error


        for i in range(100): # ez azert van igy, mert pause-re az auto megall, ha a no liquid error ezt nem respecteli, akkor el fog csuszni es unpause alatt a kor elejen all majd meg
            time.sleep(2.85/100)

            pause_event.wait()

            if reset_active or (not systemStarted): # ha a varakozas alatt tortent volna egy reset, vagy system_stop
                return


        client.publish(carManagement, stop, qos=1)
        client.publish(carManagement, stopFill, qos=1)
        #ide majd a no liquid error cuccait

    elif ml.GetLap() == 5 and ml.GetNext() == 0:
        EndDemo()


def EndDemo(delay = 6, resolution=0.05): # ez var 6mp-t, megallitja az autot, es resetel mindent

    delay_remaining = delay

    while delay_remaining > 0:
        time.sleep(resolution) # ha pause van akkor tobbet is kell varnia... a pause az auto reszerol le van kezelve megallassal, szoval itt csak a sleep-et ehhez igazitjuk
        if pause_event.isSet(): # not set -> blocking, ide amugy eredetileg a pause_event.wait kellene, mert akkor nem kellene szprakozni.... viszont akkor be lehetne bugoltatni a system started-et, mivel nem csekkolna kozben arra, hogy kozben kapott-e stop_system-et
        	delay_remaining -= resolution

        if not systemStarted: # elofordulhat, hogy ebben a 6 masodpercben kapunk egy stop_system-et, ebben az esetben a gateway elkuldene az autonak, a dolgokat, meg akkor is ha nem kellene
            return

    client.publish(carManagement, stop, qos=1)
    ml._Init() # main logic reset
    temp = 0
    ResetAllErrors() # internal flags
    reset_error() # fault manager screen


wait_for_internet_connection() # http csatlakozast probal

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
        publish_to_faultmanager(fm)
