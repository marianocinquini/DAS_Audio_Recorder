#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import pyaudio
import wave
import time
import datetime
from gps_functions import gps_msg
import sys
import numpy as np
import msvcrt
from scipy import signal
from scipy.interpolate import interp1d
from queue import Queue


import matplotlib
matplotlib.use('tkagg')
import matplotlib.pyplot as plt


def callback(in_data,frame_count, time_info, status):
    q.put(in_data)
    
    return in_data, pyaudio.paContinue


def on_key(event):
    global ch, p1, curva2, p3, fig, factor_amp, factor_pres
    if event.key == 't':
        
        if ch==0:
            ch=1
            factor_amp=10**(factor_pres_ch2/20)
            factor_pres = factor_pres_ch2
            fig.suptitle('Canal activo: CH' + str(ch+1))
            p3.set_ylim(-150 + factor_pres - preamp_sens*preamp_sens_ok, -20 + factor_pres - preamp_sens*preamp_sens_ok)
            curva2.set_clim(-150 + factor_pres - preamp_sens*preamp_sens_ok, -20 + factor_pres - preamp_sens*preamp_sens_ok)
        else:
            ch=0
            factor_amp=10**(factor_pres_ch1/20)
            factor_pres = factor_pres_ch1
            fig.suptitle('Canal activo: CH' + str(ch+1))
            p3.set_ylim(-150 + factor_pres - preamp_sens*preamp_sens_ok, -20 + factor_pres - preamp_sens*preamp_sens_ok)
            curva2.set_clim(-150 + factor_pres - preamp_sens*preamp_sens_ok, -20 + factor_pres - preamp_sens*preamp_sens_ok)
        fig.canvas.draw()
            
 
    
    

fs=192000
duracion=3
time_window=fs*duracion   # equivalente a 3 segundos
cal_factor=1.1207
f_preamp = 100
segmento_proc=np.zeros([time_window,1])

fnyq=fs/2
Deltaf=10
ruta= "C:/Users/Experimentales/Documents/Python Scripts/piddef 02-18/datos/"


preamp_resp=np.loadtxt('preamp2_gain.txt')
preamp_resp=np.append(preamp_resp, [[0, 1e-30]], 0)
func_interp_preamp=interp1d(preamp_resp[:,0], preamp_resp[:,1])


t1=np.linspace(0,duracion-1/fs,time_window)

f=np.linspace(0,fnyq,int(fnyq/Deltaf)+1)

cant_puntos=2**14
cant_overlap=cant_puntos/2
cant_fft=cant_puntos


factor_pres_ch1_default=210.15   # Sens hid de 50m calibrado el 30/11/21
factor_pres_ch2_default=206.64   # Sens hid de 20m calibrado el 30/11/21

factor_pres_ch1=factor_pres_ch1_default
factor_pres_ch2=factor_pres_ch2_default


preamp_sens = 40
ch=0


if len(sys.argv)>1:
    GPS_port_name=sys.argv[1]
else:
    GPS_port_name='COM6'


while 1:
    # Opción principal: comenzar a grabar
    main_option=input("Presione 'r' + Enter para comenzar a grabar y luego 'q' para detener, o 'exit' + Enter para salir: ")
    if main_option == "exit":
        break
    elif main_option == 'r':

        # # Elección de canal
        # while 1:
        #     ch_query=input("Elija canal para mostrar (1 o 2 + Enter): ")
        #     query_list=['1', '2']
        #     try:
        #         query_index=query_list.index(ch_query)
        #         if query_list[query_index] == '1':
        #             ch = 0
                    
        #         else:
        #             ch = 1
                    
        #         break
        #     except ValueError:
        #         print('Dale, papi, tocá una opción válida')

        
        # Elección de sensibilidades de hidrófono conectado a ch1
        while 1:
            sens_ch1=input('Seleccione sensibilidad del hidrófono ([Enter] para sens. por defecto del hidrófono del CH1): ')
            if sens_ch1 != '':
                try:
                    factor_pres_ch1=np.double(sens_ch1)
                    break
                except ValueError:
                    print('Dale, papi, tocá una opción válida')
            else:
                factor_pres_ch1=factor_pres_ch1_default
            break

        # Elección de sensibilidad del hidrófon conectado a ch2
        while 1:
            sens_ch2=input('Seleccione sensibilidad del hidrófono ([Enter] para sens. por defecto del hidrófono del CH2): ')
            if sens_ch2 != '':
                try:
                    factor_pres_ch2=np.double(sens_ch2)
                    break
                except ValueError:
                    print('Dale, papi, tocá una opción válida')
            else:
                factor_pres_ch2=factor_pres_ch2_default
            break

        # Elección del descontado de resp. en frec. de los preamps
        while 1:
            preamp_resp_query = input("¿Desea descontar la resp en frec. del preamp (con LF cut-off)? (y/n + [Enter] o [Enter] para 'Y' por defecto):")
            if preamp_resp_query!='':
                query_list=['y', 'n']
                try:
                    query_index=query_list.index(preamp_resp_query)
                    if query_list[query_index] == 'y':
                        preamp_sens_ok = 1
                    else:
                        preamp_sens_ok = 0
                    break
                except ValueError:
                    print('Dale, papi, tocá una opción válida')
            else:
                preamp_sens_ok = 1
                break

        etiqueta=input('Ingrese una etiqueta para el archivo ([Enter] para continuar): ')
       
        msg=gps_msg(GPS_port_name)
        if msg != 'No hay puerto serie':
            estampa_time=str(msg[0].timestamp)
            estampa1 = msg[1] + '_' + estampa_time[0:2] + 'h' + estampa_time[3:5] + 'm' + estampa_time[6:8] + 's'
            lat_stamp = msg[0].lat_dir + msg[0].lat[0:2] + '_' + msg[0].lat[2:4] + '_' + str(msg[0].latitude_seconds)[0:2]
            long_stamp = msg[0].lon_dir + msg[0].lon[0:3] + '_' + msg[0].lon[3:5] + '_' + str(msg[0].longitude_seconds)[0:2]
            
            estampa2= estampa1 + '_' + lat_stamp + '_' + long_stamp
        else:
            estampa1=str(datetime.datetime.now())
            estampa2= estampa1[0:10]+'_'+estampa1[11:13]+'h'+estampa1[14:16]+'m' + estampa1[17:19] + 's' + '_noGPS'
        
        estampa3=ruta + estampa2 + '_'+ etiqueta + '.wav'
              

        plt.ion()
        plt.style.use('dark_background')
        fig=plt.figure(constrained_layout=False)
        fig.suptitle('Canal activo: CH' + str(ch+1))
        gs=fig.add_gridspec(2,4)
        p1=fig.add_subplot(gs[0,0:2])
        p1.set_title('Señal temporal')
        p2=fig.add_subplot(gs[1,0:2])
        p2.set_title('Espectrograma')
        p3=fig.add_subplot(gs[0:,2:])
        p3.set_title('PSD Welch Estimator')
        p2.set_yscale("log")
        p3.set_xscale("log")
        fig.canvas.mpl_connect('key_press_event', on_key)

        f, t, Sxx = signal.spectrogram(segmento_proc[:,0], fs, 
                                                   nperseg=cant_puntos,
                                                   noverlap=0,
                                                   nfft=cant_fft)

        f_welch, Pxx = signal.welch(segmento_proc[-192000:,0], fs=192000, 
                                                    nperseg=int(cant_puntos/4),
                                                    noverlap=0)
        

        if ch==0:
            factor_amp=10**(factor_pres_ch1/20)
            factor_pres = factor_pres_ch1
        else:
            factor_amp=10**(factor_pres_ch2/20)
            factor_pres = factor_pres_ch2


                                            
        xdata1=np.linspace(0,3,3000)                            
        ydata1_aux=segmento_proc[range(0,len(segmento_proc[:,0]),192),0]
        
        espectro_min=-150 + factor_pres - preamp_sens*preamp_sens_ok
        espectro_max=-20 + factor_pres - preamp_sens*preamp_sens_ok
        
        curva1,=p1.plot(xdata1,ydata1_aux)
        curva2=p2.pcolorfast(t,f,10*np.log10(Sxx+1e-30), vmin=espectro_min, vmax=espectro_max)
        curva3,=p3.plot(f_welch,Pxx)
        
        
        
            

        p1.set_ylim(-0.1, 0.1)
        p2.set_ylim(10,96e3)
        p3.set_ylim(-150 + factor_pres - preamp_sens*preamp_sens_ok, -20 + factor_pres - preamp_sens*preamp_sens_ok)
        p3.set_xlim(1, 96000)
        

        bg=fig.canvas.copy_from_bbox(fig.bbox)
        
        
        mng = plt.get_current_fig_manager()
        mng.window.state("zoomed")
        
        
        # print(fig.canvas.supports_blit)

        q=Queue(maxsize=100)

        pa = pyaudio.PyAudio()
        stream = pa.open(format=pyaudio.paInt32,
                         channels=2,
                         rate=fs,
                         input=True,
                         frames_per_buffer=cant_puntos,
                         input_device_index=1,
                         stream_callback = callback)
                         

        wf=wave.open(estampa3, 'wb')

        wf.setnchannels(2)
        wf.setsampwidth(4)
        wf.setframerate(fs)
            
        stream.start_stream()
        
        time.sleep(0.8)

        print('Iniciando adquisiciòn...')   
        # done=False
        while 1:
        #
	

        
            # t1=time.perf_counter()
            # time.sleep(0.01)
            if not plt.get_fignums():
                break
                
            

                   # ydata1=segmento_proc[:,0]*0
                   # ydata3=10*np.log10(Pxx*0+1e-30)

#                    curva1.set_ydata(ydata1)
#                    curva2.set_array(10*np.log10(Sxx*0+1e-30))
#                    curva3.set_ydata(ydata3)
#                    fig.canvas.blit(fig.bbox)
#                    fig.canvas.flush_events()
            
            segmento=np.empty([1,1])
            # print(q.qsize())
            
            while q.empty() == False:

                aux=q.get()
                wf.writeframes(aux)
                segmento=np.append(segmento, np.frombuffer(aux, dtype=np.int32)/2**31*cal_factor)

            # print(segmento.shape)  
            segmento=segmento[1:]
                    
            
            segmento=segmento.reshape(int(segmento.shape[0]/2),2)
            segmento_proc[0:-segmento.shape[0]]=segmento_proc[segmento.shape[0]:]       
            segmento_proc[-segmento.shape[0]:,0]=segmento[:,ch]
            ydata1=segmento_proc[:,0]*factor_amp*10**(-preamp_sens*preamp_sens_ok/20)
        #        ydata1=segmento
            
        #        
            
              
            f_aux, t_aux, Sxx_aux = signal.spectrogram(segmento[:,ch], fs,
            				    window='blackman',
                                            nperseg=int(cant_puntos/2),#nperseg=int(segmento_proc.shape[0]/20),
                                            noverlap=0,
                                            nfft=cant_fft)
            

                  
            
            Sxx=np.roll(Sxx,-Sxx_aux.shape[1],1)
            Sxx[:,-Sxx_aux.shape[1]:]=Sxx_aux
            # np.tile((func_interp_preamp(f_aux))**(-2*preamp_sens_ok),(Sxx_aux.shape[1],1)).transpose()       

            
            t2=time.perf_counter()
            f_welch, Pxx = signal.welch(segmento_proc[-192000:,0], fs=192000, 
                                                window='blackman',
                                                nperseg=2**16,
                                                noverlap=2**15)
            
            
            ydata3=10*np.log10(Pxx)+factor_pres-(20*np.log10(func_interp_preamp(f_welch))*preamp_sens_ok)
            
            
            
        #        print(cantframes-pos) 
            
            ydata1_aux=ydata1[range(0,len(ydata1),192)]
            
            fig.canvas.restore_region(bg)
            
            curva1.set_ydata(ydata1_aux)

            curva1.set_xdata(np.linspace(0,3,3000))
            
            # curva1.set_ydata(ydata1[range(0,len(ydata1),3*192)])
            p1.set_ylim(ydata1.min()*1.2, ydata1.max()*1.2)
            # 
            # p3.plot(f_welch,Pxx)
            # p1.draw_artist(curva1)
            fig.suptitle('Canal activo: CH' + str(ch+1) + '  -  RMS: ' + str(ydata1.std()))
            
            # preamp_gain_para_Sxx=np.tile(20*np.log10(func_interp_preamp(f))*preamp_sens_ok,)
            curva2.set_array(10*np.log10(Sxx*factor_amp**2*10**(-preamp_sens*preamp_sens_ok/10)+1e-30))
            
            curva3.set_xdata(f_welch)
            curva3.set_ydata(ydata3)
            

            # print(time.perf_counter()-t1) 

            
            fig.canvas.blit(fig.bbox)
        ##        fig.canvas.blit(p2.bbox)
            # print(time.perf_counter()-t1)
        ##        fig.canvas.blit(p3.bbox)
            t2=time.perf_counter()
            # fig.canvas.update()
            # plt.pause(0.04)
            fig.canvas.flush_events()
        #        print(recfile2.chunk)
           
            
            # print((time.perf_counter()-t1)) 
                
        ##        print(pos)

        wf.close()
        print('Adquisión detenida')
        os.system('cls')










        
    
