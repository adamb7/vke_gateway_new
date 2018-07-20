#!/usr/bin/env python
#------------------------------------------------------
#
#		This is a program for PCF8591 Module.
#
#		Warnng! The Analog input MUST NOT be over 3.3V!
#    
#		In this script, we use a poteniometer for analog
#   input, and a LED on AO for analog output.
#
#		you can import this script to another by:
#	import PCF8591 as ADC
#	
#	ADC.Setup(Address)  # Check it by sudo i2cdetect -y -1
#	ADC.read(channal)	# Channal range from 0 to 3
#	ADC.write(Value)	# Value range from 0 to 255		
#
#------------------------------------------------------
import smbus
import time
import threading

# for RPI version 1, use "bus = smbus.SMBus(0)"
bus = smbus.SMBus(1)

#check your PCF8591 address by type in 'sudo i2cdetect -y -1' in terminal.
def setup(Addr):
	global address
	address = Addr

def read(chn): #channel
	try:
		if chn == 0:
			bus.write_byte(address,0x40)
		if chn == 1:
			bus.write_byte(address,0x41)
		if chn == 2:
			bus.write_byte(address,0x42)
		if chn == 3:
			bus.write_byte(address,0x43)
		bus.read_byte(address) # dummy read to start conversion
	except Exception, e:
		print "Address: %s" % address
		print e
	return bus.read_byte(address)

def write(val):
	try:
		temp = val # move string value to temp
		temp = int(temp) # change string to integer
		# print temp to see on terminal else comment out
		bus.write_byte_data(address, 0x40, temp)
	except Exception, e:
		print "Error: Device address: 0x%2X" % address
		print e

avgValue = -1
minValue = -1
maxValue = -1

'''
Kalibralas, ebben az esetben el kell vegezni de az autonal nem. 
csak a maxValue van hasznalatban, a tobbi kiveheto
'''
def Calibrate(length = 200): 
    global avgValue,minValue,maxValue
    
    values = []
    
    for i in xrange(length):
        values.append(read(0))
        
    avgValue = sum(values) / len(values)
    maxValue = max(values)
    #1.15
    maxValue = maxValue*1.15
    minValue = min(values)

'''
Az IR sensing logika
'''
callback = None
def Sampling(timeout=1):
    try:
        setup(0x48)
        Calibrate()
        
        i = 0
        while True:        
            if CheckValues():       
                if callback:
                    callback()
                else:
                    print("Obstacle")
            i += 1
                    
	    time.sleep(0.125)
                        
    except KeyboardInterrupt:
        print("exiting")
        return
    except IOError:        
	print("I2C bus nem elerheto!")

'''
deBounce, hirtelen felugro ertekekre
'''
def CheckValues(quantity=10):
    try:
        count = 0
        for i in xrange(quantity):
            value = read(0)
            
            #print(maxValue)
            #print(value)
            
            if value > maxValue:
                count +=1
        
        if count == quantity:
            return True
        
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        
    return False

'''
az IR sensing logikat inditja kulon szalon
'''
def StartSampling(daemon=True):
    t = threading.Thread(target=Sampling)
    t.setDaemon(daemon)
    t.start()
    



if __name__ == "__main__":
	#setup(0x48)
	#Calibrate()
	try:
            StartSampling(False)
        except KeyboardInterrupt:
            pass

	'''
	while True:
		print 'AIN0 = ', read(0)
		#print 'AIN1 = ', read(1)
		tmp = read(0)
		tmp = tmp*(255-125)/255+125 # LED won't light up below 125, so convert '0-255' to '125-255'
		write(tmp)
                #time.sleep(0.3)
        '''
