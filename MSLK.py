# -*- coding: utf-8 -*-
"""
Created on Tue Jul  6 13:41:43 2021

@author: Student

modulmerilni sistem laser kamera
"""

import nidaqmx
import cv2
import imagezmq
import time
import paramiko
import numpy as np
import socket
import matplotlib.pyplot as plt
import scipy.signal
import tkinter as tk
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
from matplotlib.figure import Figure
import threading
from nidaqmx.stream_writers import (AnalogSingleChannelWriter)
import pyExSi as es


class Meritev_demo:
    def __init__(self,t):
        """primer funkcije, ki izvaja meritev"""
        self.t=t

    def naredi_meritev(self):
        """izvajanje meritve"""
        time.sleep(self.t)


class Meritev:

    def __init__(self, ch_laser="",
                 ch_silomer="",
                 frekvenca=10240,
                 čas=5,
                 U_max=4,
                 U_min=-4,
                 las_v=20,
                 f1=4.034,
                 f2=9.923):
        """ch_laser : kanal laserja
           ch_silomer : kanla silomera
           frekvenca : frekvenca vzorčenja
           čas : čas vzorčenja
           U_max : maksimalna napetost laseraj
           U_min : minimalna napetost laserja
           las_v : max hitrost laserja (20,100,500) (mm/s)
           f1 : koeficient silomera
           f2 : koeficient nabojnega pretvornjka"""

        self.ch_laser = ch_laser
        self.ch_silomer = ch_silomer
        self.frekvenca = frekvenca
        self.čas = čas
        self.U_max = U_max
        self.U_min = U_min
        self.las_v = las_v
        self.f1 = f1
        self.f2 = f2
        self.st_vzorcev = int(self.frekvenca*self.čas)
        self.continuous_bool = False

    def connect(self):
        self.st_vzorcev = int(self.frekvenca*self.čas)
        self.max_val_silomer = 5000/(self.f1*self.f2)*0.98
        self.min_val_silomer = -self.max_val_silomer

        self.task = nidaqmx.Task()
         # laser
        self.task.ai_channels.add_ai_voltage_chan(
            self.ch_laser, min_val=self.U_min, max_val=self.U_max)
        # sila če je f2=0 pomeni da ni nabojnega ojačevalnka-> merimo napetost
        if self.f2 <= 0:
            # potrebno je se dodati!
            pass
        else:
            self.task.ai_channels.add_ai_force_iepe_chan(
                self.ch_silomer, sensitivity=self.f1*self.f2, min_val=self.min_val_silomer, max_val=self.max_val_silomer)
        if self.continuous_bool:
            self.task.timing.cfg_samp_clk_timing(
                self.frekvenca, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=self.st_vzorcev*3)
        else:
            self.task.timing.cfg_samp_clk_timing(
                self.frekvenca, sample_mode=nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan=self.st_vzorcev)

        self.task.start()

    def one_measurment(self):
        """funkcija vrne izmerjeno silo, pomerjen odziv (hitrost v mm/s), in čas meritve"""       
        data = self.task.read(self.st_vzorcev)
        
        exc = np.array(data[1])
        h = np.array(data[0])*self.las_v/self.U_max
        t = np.linspace(0, self.st_vzorcev/self.frekvenca, self.st_vzorcev)
        print(t[-1])
       
        return exc, h, t

    def disconnect(self):
        self.task.stop()
        self.task.close()

    def naredi_meritev(self):
        self.continuous_bool = False
        self.connect()
        exc, h, t = self.one_measurment()
        self.disconnect()

        return exc, h, t


class RPi:

    def __init__(self, hostname="pi-kamera",
                 port=22,
                 username="pi",
                 password="pi",
                 skripta="Desktop/laserV3.py"):
        """Naredi se objek, ki se mu pripiše lastnosti Raspberry pi na kaerega 
        se želimo povezati
        hostname : hostname oz ip če v Raspberry pi nimso nastavili hostname
        port : port na katerm se vspostavi povezava
        username : uporabniško ime Raspberry pi
        password : geslo za Raspberry pi
        skripta : pot + ime porgram, ki skrbi za zajem, obdelavo in pošiljanje
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.skripta = skripta


class Camera:

    def __init__(self, Pi):
        """Definira se objek kamera, ki skrbi za povezavo s kamero (RPi),
        pošiljanje slik in ostalih podatkov, tukaj se tudi definirajo lastnosi
        kamere

        !!!potrebno je dodati se stvaei ki se lahko nastavljajo kameri:
            resolucija
            kontrast,
            iso,
            shuter,
            treshold...
            !!!
        """
        self.pi = Pi

    def connect(self):
        """Povezava in vspostavitev vseh povezav med RPi in PC"""
        # ___________________________0MQ________________________________________
        # štartanje serverja za sprejemanje slik
        self.image_hub = imagezmq.ImageHub()

        # __________________________SSH_________________________________________
        # povezava na pi preko SSH in aktivacija python skripte
        # definiranje potrebnih podatkov za SSH povezavo
        host = self.pi.hostname
        port = self.pi.port
        username = self.pi.username
        password = self.pi.password
        # ukaz za zagon programa na RPi
        command = "python3 "+self.pi.skripta+" "+socket.gethostbyname(socket.gethostname())
        # povezovanje preko SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port, username, password)
        # zagon python skripte na RPi
        ssh.exec_command(command)
        # zapiranej SSH povezave
        ssh.close()

        # ___________________________socket_____________________________________
        # povezovanje s pomočjo socet za pošiljanje ukazov na RPi
        self.soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.soc.bind((socket.gethostname(), 5577))
        self.soc.listen(5)
        self.pi_kamera, address = self.soc.accept()
        print(f"povezava na {address}, je bila vspostavljena")
        #self.pi_kamera.send(bytes("192.168.137.1", "utf-8"))

    def req(self, dtyp,U_x=2,U_y=2):
        """možne zahteva slika: "img", pozicija laserja: "loc" """
        self.pi_kamera.send(bytes(dtyp, "utf-8"))
        count=0
        if dtyp == "loc":
            run = 1
            while run == 1:
                data = self.pi_kamera.recv(128)
                data = data.decode("utf-8")
                if data == "None":
                    print(f"Žarek ni zaznan...{count}")
                    self.pi_kamera.send(bytes(dtyp, "utf-8"))
                    count+=1
                    if count>5:
                        return np.array([None,None])
                else:
                    run = 0
            data = data[:-1]
            data = data[1:]
            print(data)
            data = np.float64(data.split(','))
            return data
        elif dtyp == "img" or dtyp== "msk":
            ime, data = self.image_hub.recv_image()
            self.image_hub.send_reply(b'OK')
            #print(ime)
            return data
        else:
            print("napačen zahtevek, opcije \"loc\" ali \"img\"")

    def disconnect(self):
        """Zapirane vseh odprtih povezav s RPi"""
        self.pi_kamera.send(bytes("end", "utf-8"))
        self.image_hub.zmq_socket.close()
        self.pi_kamera.close()
        self.soc.close()
        print("Povezava prekinjena.")


class LaserHead:

    def __init__(self, Kamera, ch1="cDAQ10Mod1/ao0", ch2="cDAQ10Mod1/ao1"):
        self.kamera = Kamera
        self.ch1 = ch1
        self.ch2 = ch2
        self.task = nidaqmx.Task()
        self.task.ao_channels.add_ao_voltage_chan(self.ch1)
        self.task.ao_channels.add_ao_voltage_chan(self.ch2)

    def premik_volt(self, v1, v2):
        self.task.write([v1, v2], auto_start=True)

    def kalibracija_basic(self, v1, v2, v3, v4):
        """osnvna kalibracija, narei se en pomik žarka na podlafi karerega se
        nato izračuna povezavo"""

        print("Začetek kalibracije")

        položaj_zrcal_0 = np.array([v1, v2])
        položaj_zrcal_1 = np.array([v3, v4])

        self.premik_volt(v1, v2)
        time.sleep(0.5)
        p0 = self.kamera.req("loc")
        while p0.any()==None:
            v1+=0.05
            v2+=0.05
            self.premik_volt(v1, v2)
            p0 = self.kamera.req("loc")
        time.sleep(0.5)
        self.premik_volt(v3, v4)
        time.sleep(0.5)
        p1 = self.kamera.req("loc")
        while p1.any()==None:
            v3+=0.05
            v4+=0.05
            self.premik_volt(v3, v4)
            p1 = self.kamera.req("loc")
        delta_px = np.array(p1)-np.array(p0)
        položaj_zrcal_0 = np.array([v1, v2])
        položaj_zrcal_1 = np.array([v3, v4])
        delta_zrcal = položaj_zrcal_1-položaj_zrcal_0
        self.položaj_zrcal_origen=položaj_zrcal_1
        k = delta_zrcal / delta_px
        print(f"konec kalibracije, k={k}")

        return k


class Scanner:

    def __init__(self, Kamera, Laser, Meritev, položaj_zrcal, k):
        """kamera : objekt class Camera\n
        laser : objekt class LaserHead\n
        meritev : objekt class Meritev\n
        položaj zrcal : zadnji položaj zrcal v voltih v obliki np.array\n
        k : koeficient med piksli in volti za krmiljenje zrcal"""
        self.kamera = Kamera
        self.laser = Laser
        self.meritev = Meritev
        self.položaj_zrcal = np.array([položaj_zrcal[1], položaj_zrcal[1]])
        self.k = k
        self.tarče = None

    def plotimg(self, img):
        plt.clf()
        plt.imshow(img[:, :, ::-1])
        plt.show()

    def narisi_ROI(self,img,ROI):
        if len(ROI)==2:
            cv2.rectangle(img, ROI[0], ROI[1],
                              (70, 180, 225), thickness=2)
        return img


    def narisi_tarce(self, img, tarče):
        """funkcija nariše tarče na sliko, tarče so podane v obliki seznama"""
        j = 1
        for i in tarče:
            start_point = (int(i[0]-10), int(i[1]-10))
            end_point = (int(i[0]+10), int(i[1]+10))
            cv2.rectangle(img, start_point, end_point,
                          (140, 225, 70), thickness=5)
            p_text = (int(i[0]+15), int(i[1]-15))
            cv2.putText(img, f"T{j}", p_text, 2, 1, (140, 225, 70))
            j += 1

        return img

    def dolocanje_tarc(self):
        st_tarče = 1
        run = 1
        tarče = []
        while run == 1:
            move_str = input(f'Tarča {st_tarče}:  ')
            if move_str == 'exit':
                break
            elif move_str == "k":
                print("Seznam tarč:")
                for i in tarče:
                    print(i)
                run = 0
            elif move_str == "r":
                položaj_zrcal = np.array([0.7, 0.7])
                self.k = self.laser.kalibracija_basic(
                    1, 1, položaj_zrcal[0], položaj_zrcal[1])
            elif move_str == "b":
                if len(tarče) != 0:
                    tarče = tarče[:-1]
                    st_tarče -= 1
                    image = self.kamera.req("img")
                    if len(tarče) != 0:
                        image = self.narisi_tarce(image, tarče)
                        self.plotimg(image)
                else:
                    print("Vse tarče odstranjene")
            else:
                try:
                    cilj = np.float64(move_str.split(','))
                    cilj = np.array(cilj)
                    tarče.append(cilj)
                    image = self.kamera.req("img")
                    image = self.narisi_tarce(image, tarče)
                    self.plotimg(image)
                    st_tarče += 1
                except:
                    print('Wrong data format')
        if move_str == "exit":
            self.tarče = "exit"
        self.tarče = np.array(tarče)

    def namesto(self, cilj, max_r=2):
        """pomik na merilno mesto meritve (cilj), loopi se zaključijo ko se približa cilju na max_r"""
        while True:
            p0 = self.kamera.req("loc")
            while p0.any()==None:
                self.laser.premik_volt(self.laser.položaj_zrcal_origen[0],self.laser.položaj_zrcal_origen[1])
                p0 = self.kamera.req("loc")
                if p0.any()==None:
                    self.laser.položaj_zrcal_origen[0]+=0.05
                    self.laser.položaj_zrcal_origen[1]+=0.05
            delta_px = cilj-p0
            razdalja_do_cilja = np.sqrt(delta_px[0]**2+delta_px[1]**2)
            print(f"Trenutna lokacija: {p0}\t Cilj: {cilj}\t Razdalja: {razdalja_do_cilja}")
            if razdalja_do_cilja < max_r:
                # izvajanje meritve
                print("Na mestu meritve")
                self.laser.premik_volt(self.položaj_zrcal[0], -8)
                img1 = self.kamera.req("img")
                self.laser.premik_volt(
                    self.položaj_zrcal[0], self.položaj_zrcal[1])
                return img1
                break
            else:
                delta_zrcal = delta_px * self.k
                p_zrcal = list(self.položaj_zrcal)
                self.položaj_zrcal += delta_zrcal
                self.laser.premik_volt(
                    self.položaj_zrcal[0], self.položaj_zrcal[1])
                p1 = self.kamera.req("loc")
                while p1.any()==None:
                    self.položaj_zrcal=self.položaj_zrcal*0.5
                    self.laser.premik_volt(self.položaj_zrcal[0], self.položaj_zrcal[1])
                    p1 = self.kamera.req("loc")
                # preverjanje položaja laserja, če je zašel v nevidno območje
                delta_px1 = cilj-p1
                žarek_do_cilja = np.sqrt(delta_px1[0]**2+delta_px1[1]**2)
                #print(f"razdalja do cilja prvič {razdalja_do_cilja1}")
                radij_verjetnosti=razdalja_do_cilja*0.15
                while žarek_do_cilja > radij_verjetnosti:
                    # pomeni da ne vidimo žarka sej domnevamo da ne more zgrešiti za več kot 50 pikslov
                    # ponastavimo žarek na začetni položaj
                    self.položaj_zrcal = list(p_zrcal)
                    # zato žarek premaknemo za 90% prvotno planiranega pomika
                    delta_zrcal = delta_zrcal*0.9
                    self.položaj_zrcal += delta_zrcal
                    # pomik žarka na skrajšano lokacijo
                    self.laser.premik_volt(
                        self.položaj_zrcal[0], self.položaj_zrcal[1])
                    p1 = self.kamera.req("loc")
                    while p1.any()==None:
                        self.položaj_zrcal=self.položaj_zrcal*0.5
                        self.laser.premik_volt(self.položaj_zrcal[0], self.položaj_zrcal[1])
                        p1 = self.kamera.req("loc")
                    delta_px1 = cilj-p1
                    žarek_do_cilja = np.sqrt(
                        delta_px1[0]**2+delta_px1[1]**2)
                    radij_verjetnosti=radij_verjetnosti*1.3
                    print(f"zgrešeno {žarek_do_cilja}, radij radij verjetnosti {radij_verjetnosti}")

    def cikelj(self, c):
        """funkcija premika laser od tarče do tarče, na vsaki tarči se izede
        meritev, naredi se željeno število ciklov meritev
        c : cikelj
        tarče : seznam tarč, merilnih mest \n
        r : radij (px) znatraj katerega je tarča zadeta (je izpolnjen pogoj za 
                                                         meritev)
        """
        if self.tarče != "exit":
            vzorec = 1
            # začetna slika
            self.laser.premik_volt(self.položaj_zrcal[0], -8)
            img0 = self.kamera.req("img")
            self.laser.premik_volt(
                self.položaj_zrcal[0], self.položaj_zrcal[1])
            len_c = len(self.tarče)
            i = 0
            while i < len_c:
                if np.any(self.tarče[i] < 0) or self.tarče[i, 0] >= img0.shape[1] or self.tarče[i, 0] >= img0.shape[0]:
                    i += 1
                    print(f"Tarča {i+1} izven vidnega polja, premik na tarčo {i+2}!")
                else:
                    while True:
                        cilj = self.tarče[i]
                        # pomik na mesto + slika pred meritvijo
                        img1 = self.namesto(cilj)
                        # translacija med začetkom in prvim hodom
                        translation = self.img_translation(img0, img1)
                        self.premik_tarč(translation)
                        img0 = img1
                        img1 = self.kamera.req("img")
                        # če ni prišlo do translacije med premikom se prične meritev
                        if np.sum(np.abs(translation)) == 0:
                            break
                    # meritev se izvaja dokler se ne izvede "mirna meritev"
                    while True:
                        ##########TUKAJ_SE_DODA_DUNKCIJO_MERITVE################
                        self.meritev.naredi_meritev()
                        ########################################################
                        self.laser.premik_volt(self.položaj_zrcal[0], -8)
                        # slika pred meritvijo
                        img0 = img1
                        # zajem slike po meritvi
                        img1 = self.kamera.req("img")
                        self.laser.premik_volt(
                            self.položaj_zrcal[0], self.položaj_zrcal[1])
                        translation = self.img_translation(img0, img1)
                        if np.sum(np.abs(translation)) == 0:
                            break
                        self.premik_tarč(translation)
                        img1 = self.namesto(cilj)
                    cilj = self.tarče[i]
                    # pomik na mesto + slika pred meritvijo
                    img1 = self.namesto(cilj)
                    self.premik_tarč(translation)
                    time.sleep(1)
                    img0 = img1
                    self.plotimg(self.narisi_tarce(
                        self.kamera.req("img"), self.tarče))
                    i += 1
                    vzorec += 1

    def img_translation(self, im1, im2):

        im1_gray = np.sum(im1.astype('float'), axis=2)
        im2_gray = np.sum(im2.astype('float'), axis=2)

        im1_gray -= np.mean(im1_gray)
        im2_gray -= np.mean(im2_gray)

        # calculate the correlation image; note the flipping of onw of the images
        cor = scipy.signal.fftconvolve(
            im1_gray, im2_gray[::-1, ::-1], mode='same')
        brightest = np.unravel_index(np.argmax(cor), cor.shape)

        sz = im1.shape
        translation = np.array(
            [sz[1]/2-float(brightest[1]), sz[0]/2-float(brightest[0])])
        print(f"translacija: {translation}")
        return translation

    def premik_tarč(self, translation):
        """izračuna premik slike"""
        self.tarče = self.tarče+translation

class Generator:
    
    def __init__(self,ch,freq_lower,freq_upper):
        self.ch = ch
        self.freq_lower = freq_lower # PSD lower frequency limit  [Hz]
        self.freq_upper = freq_upper # PSD upper frequency limit [Hz]
        self.frekvenca=100000# sampling frequency [Hz]
        # self.N = int(1e5) # number of data points of time signal
        # self.buffer_size = self.N
        self.cas=100 #s
        self.N=int(self.cas*self.frekvenca)
        self.st_vzorcev=int(self.frekvenca*self.cas)

         
        #klicnaje funkcije za nove signale
        
    def pripravi_signal(self):
        self.task = nidaqmx.Task()
        self.task.ao_channels.add_ao_voltage_chan(self.ch)
        self.task.timing.cfg_samp_clk_timing(self.frekvenca)
        self.task.timing.cfg_samp_clk_timing(
                self.frekvenca, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=self.st_vzorcev)
        self.stream = AnalogSingleChannelWriter(self.task.out_stream, auto_start=False)
        #generacija PSD
        self.naredi_PSD()
        self.x = es.random_gaussian(self.N, self.PSD, self.frekvenca)
        self.stream.write_many_sample(self.x)
        self.task.register_every_n_samples_transferred_from_buffer_event(self.st_vzorcev, self.callback)

    def naredi_PSD(self):
        t = np.arange(0,self.N)/self.frekvenca # time vector
        M = self.N // 2 + 1 # number of data points of frequency vector
        freq = np.arange(0, M/2-1, 1) * self.frekvenca / self.N # frequency vector
        self.PSD = es.get_psd(freq, self.freq_lower, self.freq_upper) # one-sided flat-shaped PSD   

    def callback(self, task_idx, every_n_samples_event_type, num_of_samples, callback_data):
        self.x = es.random_gaussian(self.N, self.PSD, self.frekvenca)
        self.stream.write_many_sample(self.x)


class MLSK_GUI:

    def __init__(self,Scanner):
        """odpre se GUI za določanje tarč"""
        self.tarče=[]
        self.scanner = Scanner
        self.master = tk.Tk()
        self.master.title("MSLK")
        self.master.iconbitmap("./files/logo.ico")
    # spremenljivke
        self.U_x=2    #začetna voltaža zrcala
        self.U_y=1.5  #začetna voltaža zrcala
        self.continuePlottingImg = False
        self.prekini = False

    # definiranje prostora za sliko
        self.fig, self.ax = plt.subplots(
            nrows=1, ncols=1, figsize=(10, 6))
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.master)
        self.canvas.get_tk_widget().grid(row=0, column=0, rowspan=10)
        self.fig.canvas.callbacks.connect('button_press_event', self.on_click)

        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()

    # povezava in tarče
        frame_kontrola_tarč = tk.Frame(self.master)
        frame_kontrola_tarč.grid(row=0,column=1,sticky="EW")

        self.gumb_izbriši_zadnjo_tarčo = tk.Button(
            frame_kontrola_tarč, text="Izbriši zadnjo tarčo", command=self.izbriši_zadnjo_tarčo)
        self.gumb_izbriši_zadnjo_tarčo.grid(row=0, column=0)

        self.gumb_izbriši_vse_tarče = tk.Button(
            frame_kontrola_tarč, text="Izbriši vse tarče", command=self.izbriši_vse_tarče)
        self.gumb_izbriši_vse_tarče.grid(row=0, column=1)

        self.gumb_pretakanje_slike = tk.Button(
            frame_kontrola_tarč, text="Pretakanje slike \n start/stop", command=self.gh1)
        self.gumb_pretakanje_slike.grid(row=1, column=0,columnspan=2,sticky="EW")

        self.gumb_začni_meritrv = tk.Button(frame_kontrola_tarč,text="ZAČNI MERITEV",bg="#baff82",command=self.zacni_meritev)
        self.gumb_začni_meritrv.grid(row=2,column=0,columnspan=2,sticky="EW")

        self.gumb_začni_meritrv = tk.Button(frame_kontrola_tarč,text="Prekini meritev",bg="#ff6b6b",command=self.prekini_meritev)
        self.gumb_začni_meritrv.grid(row=3,column=0,columnspan=2,sticky="EW")

    # kontrole kalibracije
        frame_kontorla_kalibracije = tk.LabelFrame(
            master=self.master, relief=tk.RAISED, borderwidth=1, text="Kalibracija laserja/kamere")
        frame_kontorla_kalibracije.grid(row=3, column=1, columnspan=2)

        label_kal_premik = tk.Label(
            frame_kontorla_kalibracije, text="Kal. premik [V]")
        label_kal_premik.grid(row=1, column=0, columnspan=2)

        self.entry_kal_premik = tk.Entry(master=frame_kontorla_kalibracije,width=6)
        self.entry_kal_premik.grid(row=1, column=2)
        self.entry_kal_premik.insert(0, 0.3)

        label_U_pomik = tk.Label(
            frame_kontorla_kalibracije, text="Delata U (pada) [V]")
        label_U_pomik.grid(row=2, column=0, columnspan=2)

        self.entry_U_pomik = tk.Entry(master=frame_kontorla_kalibracije,width=6)
        self.entry_U_pomik.grid(row=2, column=2)
        self.entry_U_pomik.insert(0, 0.1)

        frame_joystick = tk.Frame(frame_kontorla_kalibracije)
        frame_joystick.grid(row=3, column=0, columnspan=3)

        self.gumb_Ux_gor = tk.Button(
            frame_joystick, text="/\\", bg="#32a852", command=self.laser_Ux_gor)
        self.gumb_Ux_gor.grid(row=0, column=0)

        self.gumb_Ux_dol = tk.Button(
            frame_joystick, text="\\/", bg="#32a852", command=self.laser_Ux_dol)
        self.gumb_Ux_dol.grid(row=2, column=0)

        self.gumb_Uy_gor = tk.Button(
            frame_joystick, text="/\\", bg="#32a852", command=self.laser_Uy_gor)
        self.gumb_Uy_gor.grid(row=0, column=1)

        self.gumb_Uy_dol = tk.Button(
            frame_joystick, text="\\/", bg="#32a852", command=self.laser_Uy_dol)
        self.gumb_Uy_dol.grid(row=2, column=1)

        self.text_Ux = tk.StringVar()
        self.text_Ux.set(f"{self.U_x:.2f}")

        self.label_Ux = tk.Label(frame_joystick, textvariable=self.text_Ux)
        self.label_Ux.grid(row=1, column=0)

        self.text_Uy = tk.StringVar()
        self.text_Uy.set(f"{self.U_y:.2f}")

        self.label_Uy = tk.Label(frame_joystick, textvariable=self.text_Uy)
        self.label_Uy.grid(row=1, column=1)

        self.gumb_kalibriraj = tk.Button(
            frame_kontorla_kalibracije, text="Ponovno kalibriraj", bg="#eb4034", command=self.kalibracija_laserja)
        self.gumb_kalibriraj.grid(row=4, column=0,columnspan=2)
    
        self.kalibracija_laserja()

        self.master.mainloop()

        


    #____________________________________funkcije__________________________
    def gh1(self):
        self.change_state()
        threading.Thread(target=self.zajemanje_slike).start()

    def zajemanje_slike(self):
        """Konstantno zajemanje slike, funkcija je aktiviran preko threading"""
        while self.continuePlottingImg:
            self.image = self.scanner.kamera.req("img")
            self.image = self.scanner.narisi_tarce(self.image, self.tarče)
            self.imgshow()

    def change_state(self):
        """za nadzor funkcije self.zajemanje_slike"""
        if self.continuePlottingImg == True:
            self.continuePlottingImg = False
        else:
            self.continuePlottingImg = True

    def imgshow(self):
        """Funkcija skrbi za prikaz slike pridobljene iz RPi"""
        self.ax.cla()
        self.ax.imshow(self.image[:, :, ::-1])
        self.canvas.draw()
        #self.canvas.get_tk_widget().grid(row=0, column=0, rowspan=10)

    def on_click(self, event):
            """Funkcija ki opazuje in določa kaj se zgodi ko kliknemo na sliko"""
            if event.inaxes is not None:
                tarča = [event.xdata, event.ydata]
                self.tarče.append(tarča)
                self.image = cv2.imread("img1_2_1.jpg")
                self.image = self.scanner.kamera.req("img")
                self.image = self.scanner.narisi_tarce(self.image, self.tarče)
                self.imgshow()
                #self.stslabel.configure(text=f"Prikaz slike. Dodana tarča {len(self.tarče)}.")
            else:
                print("Clicked ouside axes bounds but inside plot window")
                #self.stslabel.configure(
                #    text="Clicked ouside axes bounds but inside plot window")

    def kalibracija_laserja(self):
        """Izvede se ponova kalibracija laseraj na podlagi vpisanih vrednosti"""
        self.scanner.k = self.scanner.laser.kalibracija_basic(
            self.U_x, self.U_y, self.U_x - float(self.entry_U_pomik.get()), self.U_y - float(self.entry_U_pomik.get()))
        self.scanner.položaj_zrcal = np.array([self.U_x- float(self.entry_U_pomik.get()), self.U_y - float(self.entry_U_pomik.get())])

    def laser_Ux_gor(self):
        """Sprememba poločaja zrcala na podlagi napetosti za smer x,
         POVEČANJE vrednosti"""
        self.U_x += float(self.entry_U_pomik.get())
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])
        self.text_Ux.set(f"{self.U_x:.2f}")
        self.scanner.laser.premik_volt(self.U_x, self.U_y)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()

    def laser_Ux_dol(self):
        """Sprememba poločaja zrcala na podlagi napetosti za smer x,
         ZMANŠANJE vrednosti"""
        self.U_x -= float(self.entry_U_pomik.get())
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])
        self.text_Ux.set(f"{self.U_x:.2f}")
        self.scanner.laser.premik_volt(self.U_x, self.U_y)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()

    def laser_Uy_gor(self):
        """Sprememba poločaja zrcala na podlagi napetosti za smer y,
         POVEČANJE vrednosti"""
        self.U_y += float(self.entry_U_pomik.get())
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])
        self.text_Uy.set(f"{self.U_y:.2f}")
        self.scanner.laser.premik_volt(self.U_x, self.U_y)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()

    def laser_Uy_dol(self):
        """Sprememba poločaja zrcala na podlagi napetosti za smer y,
         ZMANŠANJE vrednosti"""
        self.U_y -= float(self.entry_U_pomik.get())
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])
        self.text_Uy.set(f"{self.U_y:.2f}")
        self.scanner.laser.premik_volt(self.U_x, self.U_y)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()

    def izbriši_zadnjo_tarčo(self):
        """S seznama tarč se izbriše zadnja tarča"""
        if len(self.tarče) != 0:
            self.tarče = self.tarče[:-1]
            self.image = self.scanner.kamera.req("img")
            if len(self.tarče) != 0:
                self.image = self.scanner.narisi_tarce(self.image, self.tarče)
                self.imgshow()
                #self.fig.canvas.callbacks.connect('button_press_event', on_click)
            else:
                self.imgshow()

    def izbriši_vse_tarče(self):
        """pobriše se celoten seznam tarč"""
        self.tarče = []
        self.image = self.scanner.kamera.req("img")
        self.imgshow()
    
    def zacni_meritev(self):
        threading.Thread(target=self.real_zacni_meritev).start()

    def real_zacni_meritev(self):
        """Funkcija vodi laser do tarče do tarče in naredi meritev"""

        for i in range(len(self.tarče)):
            while True:
                self.pomik_na_tarčo(i)
                # spodnja funkcija definira kaj se dogaja ko žarek pride na mesto
                self.scanner.meritev.naredi_meritev()
                dovoljen_premik_kamere = 1
                if self.korekcija_tarč(dovoljen_premik_kamere) == False:
                    break
            if self.prekini == True:
                self.prekini = False
                break
        print("konec meritve")
    
    def prekini_meritev(self):
            """Funkcija namenjena kontroli funkcije self.zacni_meritev"""
            self.prekini = True

    def pomik_na_tarčo(self,i):
        self.korekcija_tarč()
        self.image = self.scanner.namesto(self.tarče[i])
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()

    def korekcija_tarč(self,se_dovoljen_premik=1):
        """če se zazna premik slike za več kot se_dovoljen_premik (vrednost v pikslih)
        se zgoti korekcija pozicije tarč

        ze e zgodi korekcija frne funkcija True,
        drugače pa False"""
        #prva slika
        img0=self.image
        #druga slika
        self.image=self.scanner.kamera.req("img")
        img1=self.image
        translation = self.scanner.img_translation(img0, img1)
        if np.sqrt(translation[0]**2+translation[1]**2) > se_dovoljen_premik:
            self.tarče = self.tarče+translation
            return True
        else: 
            return False

#===============================showcase===============================
if __name__ == '__main__':
    # določanje objektov
    Pi = RPi(hostname="pi-kamera",
             port=22,
             username="pi",
             password="pi",
             skripta="Desktop/laserV3.py")

    pi_kamera = Camera(Pi)
    laser = LaserHead(pi_kamera,ch1="cDAQ1Mod1/ao0", ch2="cDAQ1Mod1/ao1")
    meritev = Meritev_demo(5)
    # določitev začetnega poločaja zrcal
    položaj_zrcal = np.array([1.7, 1.7])
    scanner = Scanner(pi_kamera, laser, meritev, položaj_zrcal, None)


    # povezovanje na kamero
    pi_kamera.connect()
    #Gui za določanje tarč
    MLSK_GUI(scanner)
    # zapiranje povezav
    pi_kamera.disconnect()
