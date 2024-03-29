#!/usr/bin/python3
# -*- coding: utf-8 -*-

import pyaudio
import wave
import time
import datetime
from gps_functions import gps_msg
import sys
import numpy as np
import msvcrt
from scipy import signal
from queue import Queue


import matplotlib
matplotlib.use('tkagg')
import matplotlib.pyplot as plt


def callback(in_data,frame_count, time_info, status):
    q.put(in_data)

    return in_data, pyaudio.paContinue

fs=192000
duracion=3
time_window=fs*duracion   # equivalente a 3 segundos
cal_factor=1.1207
segmento_proc=np.zeros([time_window,1])

fnyq=fs/2
Deltaf=10
ruta= "C:/Users/maria/Documents/DIIV/Python/piddef 02-18 rugged_laptop/datos/"

t1=np.linspace(0,duracion-1/fs,time_window)

f=np.linspace(0,fnyq,int(fnyq/Deltaf)+1)

cant_puntos=8192
cant_overlap=cant_puntos/2
cant_fft=cant_puntos

factor_pres_ch1=206.3 - 40   # Considero la ganancia (en la banda de paso) del preamp
factor_pres_ch2=209.8 - 40


if len(sys.argv)>1:
    GPS_port_name=sys.argv[1]
else:
    GPS_port_name='COM6'

msg=gps_msg(GPS_port_name)
if msg != 'No hay puerto serie':
    estampa1 = msg[1] + '_' + str(msg[0].timestamp)[0:5]
    lat_stamp = msg[0].lat_dir + msg[0].lat[0:2] + '_' + msg[0].lat[2:4] + '_' + str(msg[0].latitude_seconds)[0:2]
    long_stamp = msg[0].lon_dir + msg[0].lon[0:3] + '_' + msg[0].lon[3:5] + '_' + str(msg[0].longitude_seconds)[0:2]
    estampa2= estampa1 + '_' + lat_stamp + '_' + long_stamp + '.wav'
else:
    estampa1=str(datetime.datetime.now())
    estampa2= estampa1[0:10]+'_'+estampa1[11:13]+'h'+estampa1[14:16]+'m' + '_noGPS'
estampa2=ruta+ estampa2

while 1:
    if input("Presione 'r' + Enter para comenzar a grabar; luego 's' para detener: ") == "r":
        ch_query=input("Elija canal para mostrar (1 o 2 + Enter): ")
        if ch_query=="1":
            sens_ch1=input('Seleccione sensibilidad del hidrófono ([Enter] para sensibilidad por defecto del hid. de 20m): ')
            if sens_ch1 != '':
                factor_pres=np.double(sens_ch1) 
            else:
                factor_pres=factor_pres_ch1
            ch=0
            break
        elif ch_query == "2":    
            sens_ch2=input('Seleccione sensibilidad del hidrófono ([Enter] para sensibilidad por defecto del hid. de 50m): ')
            if sens_ch2 != '':
                factor_pres=np.double(sens_ch2) 
            else:
                factor_pres=factor_pres_ch2
            ch=1
            break

etiqueta=input('Ingrese una etiqueta para el archivo ([Enter] para continuar): ')
estampa2=estampa2 + '_'+ etiqueta + '.wav'

factor_amp=10**(factor_pres/20)

plt.ion()
plt.style.use('dark_background')
fig=plt.figure(constrained_layout=False)
gs=fig.add_gridspec(2,4)
p1=fig.add_subplot(gs[0,0:2])
p1.set_title('Señal temporal')
p2=fig.add_subplot(gs[1,0:2])
p2.set_title('Espectrograma')
p3=fig.add_subplot(gs[0:,2:])
p3.set_title('PSD Welch Estimator')
p2.set_yscale("log")
p3.set_xscale("log")

f, t, Sxx = signal.spectrogram(segmento_proc[:,0], fs, 
                                           nperseg=cant_puntos,
                                           noverlap=0,
                                           nfft=cant_fft)

f_welch, Pxx = signal.welch(segmento_proc[-192000:,0], fs=192000, 
                                            nperseg=int(cant_puntos/4),
                                            noverlap=0)
                                            
xdata1=np.linspace(0,3,3000)                            
ydata1_aux=segmento_proc[range(0,len(segmento_proc[:,0]),192),0]

curva1,=p1.plot(xdata1,ydata1_aux)
curva2=p2.pcolorfast(t,f,10*np.log10(Sxx+1e-30), vmin=-125, vmax=-30)
curva3,=p3.plot(f_welch,Pxx)

p1.set_ylim(-0.1, 0.1)
p2.set_ylim(10,96e3)
p3.set_ylim(-150 + factor_pres, -20 + factor_pres)

bg=fig.canvas.copy_from_bbox(fig.bbox)
print(fig.canvas.supports_blit)

q=Queue(maxsize=100)

pa = pyaudio.PyAudio()
stream = pa.open(format=pyaudio.paInt32,
                 channels=2,
                 rate=fs,
                 input=True,
                 frames_per_buffer=cant_puntos,
                 input_device_index=1,
                 stream_callback = callback)
                 

wf=wave.open(estampa2, 'wb')

wf.setnchannels(2)
wf.setsampwidth(4)
wf.setframerate(fs)
    
stream.start_stream()

time.sleep(0.5)

   
done=False
while not done:
#       
    t1=time.perf_counter()
    # time.sleep(0.01)
    if msvcrt.kbhit():
        tecla=msvcrt.getch()
        if tecla == b's':
            
            print('Saliendo!')
            stream.stop_stream()
            pa.terminate()
            done = True
    
    segmento=np.empty([1,1])
    print(q.qsize())
    
    while q.empty() == False:

        aux=q.get()
        wf.writeframes(aux)
        segmento=np.append(segmento, np.frombuffer(aux, dtype=np.int32)/2**31*cal_factor)

    print(segmento.shape)  
    segmento=segmento[1:]
            
    
    segmento=segmento.reshape(int(segmento.shape[0]/2),2)
    segmento_proc[0:-segmento.shape[0]]=segmento_proc[segmento.shape[0]:]       
    segmento_proc[-segmento.shape[0]:,0]=segmento[:,ch]
    ydata1=segmento_proc[:,0]*factor_amp
#        ydata1=segmento
    
#        
    
      
    f_aux, t_aux, Sxx_aux = signal.spectrogram(segmento[:,ch], fs, 
                                    nperseg=cant_puntos,#nperseg=int(segmento_proc.shape[0]/20),
                                    noverlap=0,#noverlap=int(segmento_proc.shape[0]/20*4/5),
                                    nfft=cant_fft)#nfft=int(segmento_proc.shape[0]/20))
    
    
    
    Sxx=np.roll(Sxx,-Sxx_aux.shape[1],1)
    Sxx[:,-Sxx_aux.shape[1]:]=Sxx_aux
#        
    
    
    t2=time.perf_counter()
    f_welch, Pxx = signal.welch(segmento_proc[-int(cant_puntos*20):,0], fs=192000, 
                                        nperseg=int(cant_puntos),
                                        noverlap=0)
    
    
    ydata3=10*np.log10(Pxx)+factor_pres
    
    
    
#        print(cantframes-pos) 
    
    ydata1_aux=ydata1[range(0,len(ydata1),192)]
    
    fig.canvas.restore_region(bg)
    
    curva1.set_ydata(ydata1_aux)

    curva1.set_xdata(np.linspace(0,3,3000))
    
    # curva1.set_ydata(ydata1[range(0,len(ydata1),3*192)])
    p1.set_ylim(ydata1.min()*1.2, ydata1.max()*1.2)
    # p1.draw_artist(curva1)
    curva2.set_array(10*np.log10(Sxx+1e-30))
    
    curva3.set_xdata(f_welch)
    curva3.set_ydata(ydata3)
    

    # print(time.perf_counter()-t1) 

    
    fig.canvas.blit(fig.bbox)
##        fig.canvas.blit(p2.bbox)
    # print(time.perf_counter()-t1)
##        fig.canvas.blit(p3.bbox)
    t2=time.perf_counter()
##    fig.canvas.update()
    # plt.pause(0.04)
    fig.canvas.flush_events()
#        print(recfile2.chunk)
   
    
    print((time.perf_counter()-t1)) 
        
##        print(pos)

wf.close()










        
    
