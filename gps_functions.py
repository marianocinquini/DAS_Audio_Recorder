#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 15 11:57:27 2019

@author: mariano
"""

import serial
import pynmea2
import time

def gps_msg(port_name):
    
    try:
        ser = serial.Serial(port=port_name, baudrate=4800, timeout=5)
        msg=''
        while True:
            line=ser.readline()
            line2=str(line).split('\\')
            line2=line2[0][2:]
            
            if line2.split(',')[0] == '$GPGGA':
                msg = pynmea2.parse(line2)
            elif line2.split(',')[0] == '$GPRMC':
                msg_aux=pynmea2.parse(line2)
                date_str=str(msg_aux.datestamp)
                if msg!='':
                    break
                
        ser.close()
        return msg, date_str
    
    except serial.SerialException:
        date_str='No hay puerto serie'
        return date_str

                
def find_gps_port(port_name,timeout):
    
    try:
        ser = serial.Serial(port=port_name, baudrate=4800, timeout=5)
        t1=time.time()
        while True:
            line=ser.readline()
            find_index=str(line).find('$GPGGA')
            
            
            if find_index != -1:
                break
            
            elif (time.time() - t1) >= timeout:
                break
            
        ser.close()
        return find_index
    
    except serial.SerialException:
        index = -1
        return index
