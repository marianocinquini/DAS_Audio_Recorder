#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''recorder.py
Provides WAV recording functionality via two approaches:

Blocking mode (record for a set duration):
>>> rec = Recorder(channels=2)
>>> with rec.open('blocking.wav', 'wb') as recfile:
...     recfile.record(duration=5.0)

Non-blocking mode (start and stop recording):
>>> rec = Recorder(channels=2)
>>> with rec.open('nonblocking.wav', 'wb') as recfile2:
...     recfile2.start_recording()
...     time.sleep(5.0)
...     recfile2.stop_recording()
'''
import pyaudio
import wave
import time
import datetime
from gps_functions import gps_msg
import sys
import numpy as np
import msvcrt
from scipy import signal
import matplotlib.pyplot as plt

import matplotlib
matplotlib.use('qt5agg')



audioframes=10000      # equivalente a 0.1 segundo
time_window=192000*3   # equivalente a 3 segundos
duracion=3
cal_factor=1.1207
segmento_proc=np.zeros([time_window,1])
fs=192000
fnyq=fs/2
Deltaf=10
ruta= "C:/Users/Experimentales/Documents/Python Scripts/piddef 02-18/datos"

t1=np.linspace(0,duracion-1/fs,time_window)

f=np.linspace(0,fnyq,int(fnyq/Deltaf)+1)

cant_puntos=8192
cant_overlap=cant_puntos/2
cant_fft=cant_puntos
factor_pres_ch1=206.3 - 40   # Considero la ganancia (en la banda de paso) del preamp
factor_pres_ch2=209.8 - 40




class Recorder(object):
    '''A recorder class for recording audio to a WAV file.
    Records in mono by default.
    '''

    def __init__(self, channels=2, rate=fs, frames_per_buffer=cant_puntos):
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer

    def open(self, fname, mode='wb'):
        return RecordingFile(fname, mode, self.channels, self.rate,
                            self.frames_per_buffer)

class RecordingFile(object):
    def __init__(self, fname, mode, channels, 
                rate, frames_per_buffer):
        self.fname = fname
        self.mode = mode
        self.channels = channels
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self._pa = pyaudio.PyAudio()
        self.wavefile = self._prepare_file(self.fname, self.mode)
        self._stream = None

    def __enter__(self):
        return self

    def __exit__(self, exception, value, traceback):
        self.close()

    def record(self, duration):
        # Use a stream with no callback function in blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt32,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        frames_per_buffer=self.frames_per_buffer,
                                        input_device_index=1)
#        for _ in range(int(self.rate / self.frames_per_buffer * duration)):
#            audio = self._stream.read(self.frames_per_buffer)
#            self.wavefile.writeframes(audio)
        return None

    def get_data(self):
        audio = self._stream.read(self.frames_per_buffer)
        self.wavefile.writeframes(audio)
        
        return audio

    def start_recording(self):
        # Use a stream with a callback in non-blocking mode
        self._stream = self._pa.open(format=pyaudio.paInt32,
                                        channels=self.channels,
                                        rate=self.rate,
                                        input=True,
                                        frames_per_buffer=self.frames_per_buffer,
                                        input_device_index=1,
                                        stream_callback=self.get_callback())
        self._stream.start_stream()
        return self

    def stop_recording(self):
        self._stream.stop_stream()
        return self

    def get_callback(self):
        def callback(in_data, frame_count, time_info, status):
            self.wavefile.writeframes(in_data)
                    
            
            return in_data, pyaudio.paContinue
        return callback


    def close(self):
        self._stream.close()
        self._pa.terminate()
        self.wavefile.close()

    def _prepare_file(self, fname, mode='wb'):
        wavefile = wave.open(fname, mode)
        wavefile.setnchannels(self.channels)
        wavefile.setsampwidth(self._pa.get_sample_size(pyaudio.paInt32))
        wavefile.setframerate(self.rate)
        return wavefile





rec = Recorder(channels=2)

if len(sys.argv)>1:
    GPS_port_name=sys.argv[1]
else:
    GPS_port_name='/dev/ttyUSB1'

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
                                           noverlap=cant_overlap,
                                           nfft=cant_fft)

f_welch, Pxx = signal.welch(segmento_proc[-192000:,0], fs=192000, 
                                            nperseg=16384,
                                            noverlap=0)
                                            
                            

curva1,=p1.plot(t1,segmento_proc)
curva2=p2.pcolorfast(t,f,10*np.log10(Sxx), vmin=-125, vmax=-30)
curva3,=p3.plot(f_welch,Pxx)

p1.set_ylim(-0.01, 0.01)
p1.grid
p2.set_ylim(10,96e3)
p3.set_ylim(-150 + factor_pres, -20 + factor_pres)

mng = plt.get_current_fig_manager()
mng.window.showMaximized()
#fig.canvas.draw()
bg = fig.canvas.copy_from_bbox(fig.bbox)


with rec.open(estampa2, 'wb') as recfile2:
        
#    pg.QtGui.QApplication.processEvents()
    recfile2.start_recording()      
    pos=0
    m=0
    time.sleep(0.2)
    
        
    proc=wave.open(estampa2,'rb')
    
#    recfile2.stop_recording()
##   recfile2.record(1)
    done=False
    while not done:
#        
        if msvcrt.kbhit():
            tecla=msvcrt.getch()
            if tecla == b's':
                
                print('Saliendo!')
                recfile2.stop_recording()
                proc.close()
                done = True
#            
        t1=time.perf_counter()
##        audio=recfile2.get_data()
        proc=wave.open(estampa2,'rb')  
        proc.setpos(pos)
        cantframes=proc.getnframes()
##        print(cantframes-pos)
        segmento=np.frombuffer(proc.readframes(cantframes-pos), dtype=np.int32)/2**31*cal_factor
        
        
        
##        segmento=np.frombuffer(audio, dtype=np.int32)/2**31*cal_factor
        
        
        segmento=segmento.reshape(int(segmento.shape[0]/2),2)
        segmento_proc[0:-segmento.shape[0]]=segmento_proc[segmento.shape[0]:]       
        segmento_proc[-segmento.shape[0]:,0]=segmento[:,ch]
        ydata1=segmento_proc[:,0]*factor_amp
#        ydata1=segmento
        
#        
        
          
        f_aux, t_aux, Sxx_aux = signal.spectrogram(segmento[:,ch], fs, 
                                       nperseg=cant_puntos,#nperseg=int(segmento_proc.shape[0]/20),
                                       noverlap=cant_overlap,#noverlap=int(segmento_proc.shape[0]/20*4/5),
                                       nfft=cant_fft)#nfft=int(segmento_proc.shape[0]/20))
        
        
        
        Sxx=np.roll(Sxx,-Sxx_aux.shape[1],1)
        Sxx[:,-Sxx_aux.shape[1]:]=Sxx_aux
#        
        
        
        t2=time.perf_counter()
        f_welch, Pxx = signal.welch(segmento_proc[-192000:,0], fs=192000, 
                                            nperseg=16384,
                                            noverlap=0)
        
        
        ydata3=10*np.log10(Pxx)+factor_pres
        
        
        
#        print(cantframes-pos) 
        
        
        curva1.set_xdata(np.linspace(0,3,1000))
        curva1.set_ydata(ydata1[range(0,len(ydata1),3*192)])
        p1.set_ylim(ydata1.min()*1.2, ydata1.max()*1.2)
        curva2.set_array(10*np.log10(Sxx))
        curva3.set_ydata(ydata3)
##        print(time.perf_counter()-t1) 

        fig.canvas.restore_region(bg)
        fig.canvas.blit(fig.bbox)
        #fig.canvas.blit(p2.bbox)
##        print(time.perf_counter()-t1)
        #fig.canvas.blit(p3.bbox)
#        fig.canvas.update()
        

        fig.canvas.flush_events()
#        print(recfile2.chunk)
       
##        print(time.perf_counter()-t1) 
        pos=proc.tell()
##        print(pos)


    
    









        
    
