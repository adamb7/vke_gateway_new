import json
import os
import paho.mqtt.client as paho
import time
import RPi.GPIO as GPIO
try:
    from urllib.request import urlopen
except ImportError:
    
    from urllib2 import urlopen
    
import logging
import traceback

import MainLogic as logic
from MainLogic import Errors
from MainLogic import DemoErrors

import sys
import threading

#kesobb implementalni
#import LEDTest as led

import IRSensor as ir

'''
LED setup
'''

'''
Az LED inverz tulajdonsaga miatt forditva adjuk ki a labakra a jelet
'''
'''
GPIOHigh es low helyett lehetne egyszerubb valtozo
'''
'''
LED kezelo logikat kilehetne tenni kulon modulba / classba
'''
GW_POWER_ERR_GREEN = 13 
GW_POWER_ERR_RED = 19 
GW_ERR_GREEN = 5 
GW_ERR_RED = 6 

RFID_GREEN = 20 
RFID_RED = 21 

on = GPIO.LOW
off = GPIO.HIGH

GPIO.setmode(GPIO.BCM)
GPIO.setup(GW_POWER_ERR_GREEN, GPIO.OUT)
GPIO.setup(GW_POWER_ERR_RED, GPIO.OUT)
GPIO.setup(GW_ERR_GREEN, GPIO.OUT)
GPIO.setup(GW_ERR_RED, GPIO.OUT)
GPIO.setup(RFID_GREEN, GPIO.OUT)
GPIO.setup(RFID_RED, GPIO.OUT)


'''
end of LED setup
'''

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
                error_rfid_warehouse()
                convert_to_json()
            
                RFIDErrorLED()
                
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
   
'''            
kitenni a LED kezelo modulba
Komm errorhoz hasonlo mukodes van itt, akar lehetne 1 metodusba tenni
alul van a metodus ami ezt lehetove tenne "GWErrorLEDTest" neven
'''
def RFIDErrorLED(delay=0.2, error_duration = 10, hold = 2):
    GPIO.output(RFID_GREEN,off)

    GPIO.output(RFID_RED,on)
    time.sleep(hold)

    sample = time.time()
    
    while (time.time() - sample) < (error_duration - hold):
        GPIO.output(RFID_RED, on)
        time.sleep(delay)
        GPIO.output(RFID_RED, off)
        time.sleep(delay)
        
    GPIO.output(RFID_RED, off)
    GPIO.output(RFID_GREEN, on)
        
        
        
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


color = []
is_root = []

my_colors = {"belt_dc_motor": 1, "belt_plc": 2, "pack_moving": 3, "tank_plc": 4,
             "forklift_plc": 5, "warehouse_RFID": 6, "gateway_power": 7,
             "belt_tank_power": 8, "forklift_power": 9, "warehouse_power": 10,
             "gateway": 11, "gateway_ping": 12, "belt_dc_motor_ping": 13,
             "belt_plc_ping": 14, "pack_moving_ping": 15, "tank_ping": 16,
             "forklift_plc_ping": 17, "warehouse_RFID_ping": 18, "gateway_power_sensor_ping": 19,
             "belt_tank_power_sensor_ping": 20, "forklift_power_sensor_ping": 21,
             "warehouse_power_sensor_ping": 22
             }

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

#Test, egyelore semmire se hasznalandok
errors = Errors()
de = DemoErrors()

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

def initialize_colors():
    for i in range(22):
        color.append('green')
        is_root.append(0)


def convert_to_json():
    global json_str
    json_str = '{"description":' + '"Status update","values":' + '['
    for i in range(22):
        #print(color[i])
        j = i + 1
        json_str += "{" + '"' + "id" + '"' + ':' + str(j) + ','
        json_str += '"' + "color" + '"' + ':' + '"' + color[i] + '"' + ','
        json_str += '"' + "root" + '"' + ':' + str(is_root[i]) + '}'
        if i != 21:
            json_str += ','
        
    json_str += "]}"
    #print(json_str)
    client.publish("ERROR_DEMO",json_str,retain=True, qos=1)
    

# change the color of the component to newcolor
def change_color_root_error(component, newcolor, isroot):
    if not (color[my_colors[component] - 1] == 'red' and newcolor == 'yellow') and not (
            color[my_colors[component] - 1] == 'yellow' and newcolor == 'red'):
        color[my_colors[component] - 1] = newcolor
        is_root[my_colors[component] - 1] = isroot


def change_color_root_reset(component, newcolor):
    color[my_colors[component] - 1] = newcolor


def print_colors():
    for str in my_colors:
        print(my_colors[str], str, color[my_colors[str]])


def error_belt_plc():
    change_color_root_error("belt_plc", 'red', 1)


def error_no_liquid():
    change_color_root_error("tank_plc", 'red', 1)


def error_forklift_obstacle():
    change_color_root_error("forklift_plc", 'red', 1)


def error_rfid_warehouse():
    change_color_root_error("warehouse_RFID", 'yellow', 0)
    change_color_root_error("warehouse_RFID_ping", 'red', 1)


# Gateway communication error
def error_gateway():
    change_color_root_error("belt_dc_motor", 'yellow', 0)
    change_color_root_error("belt_plc", 'yellow', 0)
    change_color_root_error("pack_moving", 'yellow', 0)
    change_color_root_error("tank_plc", 'yellow', 0)
    change_color_root_error("forklift_plc", 'yellow', 0)
    change_color_root_error("warehouse_RFID", 'yellow', 0)
    change_color_root_error("gateway_power", 'yellow', 0)
    change_color_root_error("belt_tank_power", 'yellow', 0)
    change_color_root_error("forklift_power", 'yellow', 0)
    change_color_root_error("warehouse_power", 'yellow', 0)
    change_color_root_error("gateway", 'red', 1)
    # is_root[my_colors["gateway"] - 1] = 1
    change_color_root_error("belt_dc_motor_ping", 'red', 0)
    change_color_root_error("belt_plc_ping", 'red', 0)
    change_color_root_error("pack_moving_ping", 'red', 0)
    change_color_root_error("tank_ping", 'red', 0)
    change_color_root_error("forklift_plc_ping", 'red', 0)
    change_color_root_error("warehouse_RFID_ping", 'red', 0)
    change_color_root_error("gateway_power_sensor_ping", 'red', 0)
    change_color_root_error("belt_tank_power_sensor_ping", 'red', 0)
    change_color_root_error("forklift_power_sensor_ping", 'red', 0)
    change_color_root_error("warehouse_power_sensor_ping", 'red', 0)


# No power for the forklift
def error_forklift_power():
    change_color_root_error("forklift_plc", 'yellow', 0)
    change_color_root_error("forklift_power", 'red', 1)
    change_color_root_error("forklift_plc_ping", 'red', 0)


# Gateway has no power error
def error_gateway_power():
    change_color_root_error("gateway", 'yellow', 1)
    change_color_root_error("gateway_power", 'yellow', 1)
    error_gateway()
    # color[my_colors["gateway"] - 1] = 'y'
    is_root[my_colors["gateway_power"] - 1] = 1
    change_color_root_error("gateway_ping", 'red', 1)
    # color[my_colors["gateway_ping"] - 1] = 'r'
    # is_root[my_colors["gateway_ping"] - 1] = 1


def reset_error():
    change_color_root_error("belt_dc_motor", 'green', 0)
    change_color_root_error("belt_plc", 'green', 0)
    change_color_root_error("pack_moving", 'green', 0)
    change_color_root_error("tank_plc", 'green', 0)
    change_color_root_error("forklift_plc", 'green', 0)
    change_color_root_error("warehouse_RFID", 'green', 0)
    change_color_root_error("gateway_power", 'green', 0)
    change_color_root_error("belt_tank_power", 'green', 0)
    change_color_root_error("forklift_power", 'green', 0)
    change_color_root_error("warehouse_power", 'green', 0)
    change_color_root_error("gateway", 'green', 0)
    change_color_root_error("gateway_ping",'green',0)
    change_color_root_error("gateway_power", 'green', 0)
    change_color_root_error("belt_dc_motor_ping", 'green', 0)
    change_color_root_error("belt_plc_ping", 'green', 0)
    change_color_root_error("pack_moving_ping", 'green', 0)
    change_color_root_error("tank_ping", 'green', 0)
    change_color_root_error("forklift_plc_ping", 'green', 0)
    change_color_root_error("warehouse_RFID_ping", 'green', 0)
    change_color_root_error("gateway_power_sensor_ping", 'green', 0)
    change_color_root_error("belt_tank_power_sensor_ping", 'green', 0)
    change_color_root_error("forklift_power_sensor_ping", 'green', 0)
    change_color_root_error("warehouse_power_sensor_ping", 'green', 0)
    
    if gateway_power_error_running:
        error_gateway_power()
    else:
        if gateway_error_running:
            error_gateway()
        else:
            if belt_plc_error_running:
                error_belt_plc()
            if liquid_error_running:
                error_no_liquid()
            if forklift_power_error_running:
                error_forklift_power()
            if forklift_obstacle_error_running:
                error_forklift_obstacle()
            if RFID_warehouse_error_running:
                error_rfid_warehouse()
    convert_to_json()

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
    
    
    if not systemStarted:
        if msg.topic == "start_system":
            systemStarted = True
            InitLEDs()
            client.publish(carManagement, "initLED", qos=1)
            
    else:
        if msg.topic == "stop_system":
            #kell egy "clear" logika
            systemStarted = False
            ml._Init()
            #vagy megallitjuk azonnal, vagy a helyere visszuk
            client.publish(carManagement, terminate, qos=1)
            ShutDownLeds()
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
                    error_forklift_obstacle()
                    convert_to_json()
                    
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
                    error_no_liquid()
                    convert_to_json()
                    
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
                    
                    error_belt_plc()
                    convert_to_json()

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
                    
                    error_gateway()
                    
                    t = threading.Thread(target = gateway_error_led)
                    t.setDaemon(True)
                    t.start()
                    
                    convert_to_json()
                    
             
            elif msg.topic == "gateway_error_reset":
                gateway_error_running = False
                
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
                     
                error_gateway_power()

                t = threading.Thread(target = gateway_power_error_led)
                t.setDaemon(True)
                t.start()
                
                convert_to_json()       
                
            elif msg.topic == "gateway_power_error_reset":
                gateway_power_error_running = False
                
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
        error_forklift_power()
        convert_to_json()
    
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
    

'''
A kovetkezo ket metodusbol akar 1 et is lehetne csinalni
'''
def gateway_error_led(delay = 0.2, hold = 2):
    GPIO.output(GW_ERR_GREEN, off)
    
    GPIO.output(GW_ERR_RED, on)
    time.sleep(hold)
    
    while gateway_error_running:
        GPIO.output(GW_ERR_RED, on)
        time.sleep(delay)
        GPIO.output(GW_ERR_RED, off)
        time.sleep(delay)
        
    GPIO.output(GW_ERR_RED, off)
    GPIO.output(GW_ERR_GREEN, on)


def gateway_power_error_led(delay = 0.2, hold=2):
    GPIO.output(GW_POWER_ERR_GREEN, off)
      
    GPIO.output(GW_POWER_ERR_RED, on)
    time.sleep(hold)
      
    while gateway_power_error_running:
        GPIO.output(GW_POWER_ERR_RED, on)
        time.sleep(delay)
        GPIO.output(GW_POWER_ERR_RED, off)
        time.sleep(delay)
         
    GPIO.output(GW_POWER_ERR_RED, off)
    GPIO.output(GW_POWER_ERR_GREEN, on)

'''
TEST
'''
'''
Ez egy normalisan mukodo megoldas csak a "criteria" kulon classkent kell megoldani
hogy referenciakent adodjon at, mert jelenleg nem ezt teszi
Ha lesz ido ezt megirni, hogy szep legyen --> "LEDControl" ba
'''
def GWErrorLEDTest(greenLED, redLED, criteria, delay=0.2):
    
    GPIO.output(greenLED, off)
       
    while criteria:
        GPIO.output(redLED, on)
        time.sleep(delay)
        GPIO.output(redLED, off)
        time.sleep(delay)
        
    GPIO.output(redLED, off)
    GPIO.output(greenLED, on)

'''
LED -ek alaphelyzetbe allitasa
'''
def InitLEDs():
    GPIO.output(GW_POWER_ERR_RED, off)
    GPIO.output(GW_POWER_ERR_GREEN, on)
    GPIO.output(GW_ERR_RED, off)
    GPIO.output(GW_ERR_GREEN, on)
    GPIO.output(RFID_RED, off)
    GPIO.output(RFID_GREEN, on)
    

'''
LED -ek kikapcsolasa
'''
def ShutDownLeds():
    GPIO.output(GW_POWER_ERR_GREEN, off)
    GPIO.output(GW_POWER_ERR_RED, off)
    GPIO.output(GW_ERR_GREEN, off)
    GPIO.output(GW_ERR_RED, off)
    GPIO.output(RFID_RED, off)
    GPIO.output(RFID_GREEN, off)


wait_for_internet_connection()

initialize_colors()

if __name__ == '__main__':
    try:
        '''
        kene kulon setup metodus hogy ne ezt szemeteljuk tele 
        '''
        #InitLEDs()
        InitMQTT()
        client.loop_forever()
        
    except KeyboardInterrupt:
        print("Keyboard Interrupt")
        
        try:
            ShutDownLeds()
            
        except SystemExit:
            os._exit(0)
            
    finally:
        #"LEDControl" classba "destroy" metodus kezelje le
        GPIO.cleanup([GW_POWER_ERR_GREEN, GW_POWER_ERR_RED, \
                      GW_ERR_GREEN, GW_ERR_RED, RFID_GREEN, \
                      RFID_RED])
        
        convert_to_json()
