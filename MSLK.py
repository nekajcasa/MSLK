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


# =============================================================================
# class :
#
#     def __init__(self,t):
#         self.t=t
#
#     def izvajanje_meritve(self,c,n):
#         print("/////////////////////////////////////////////////////////")
#         print(f"...izvaja se cikelj {c}, MERITEV vzorca {n}...")
#         print("/////////////////////////////////////////////////////////")
#         time.sleep(self.t)
#         print("konec meritve")
# =============================================================================
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

    def __init__(self, pi):
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
        self.pi = RPi()

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
        command = "python3 "+self.pi.skripta
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

    def req(self, dtyp):
        """možne zahteva slika: "img", pozicija laserja: "loc" """
        self.pi_kamera.send(bytes(dtyp, "utf-8"))
        if dtyp == "loc":
            run = 1
            while run == 1:
                data = self.pi_kamera.recv(128)
                data = data.decode("utf-8")
                if data == "None":
                    print("Žarek ni zaznan...")
                    self.pi_kamera.send(bytes(dtyp, "utf-8"))
                else:
                    run = 0
            data = data[:-1]
            data = data[1:]
            data = np.float64(data.split(','))
            return data
        elif dtyp == "img":
            ime, data = self.image_hub.recv_image()
            self.image_hub.send_reply(b'OK')
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

    def __init__(self, kamera, ch1="cDAQ2Mod1/ao0", ch2="cDAQ2Mod1/ao1"):
        self.kamera = kamera
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
        time.sleep(0.5)
        self.premik_volt(v3, v4)
        time.sleep(0.5)
        p1 = self.kamera.req("loc")
        delta_px = np.array(p1)-np.array(p0)
        delta_zrcal = položaj_zrcal_1-položaj_zrcal_0
        k = delta_zrcal / delta_px
        print(f"konec kalibracije, k={k}")

        return k


class Scanner:

    def __init__(self, kamera, laser, meritev, položaj_zrcal, k):
        """kamera : objekt class Camera\n
        laser : objekt class LaserHead\n
        meritev : objekt class Meritev\n
        položaj zrcal : zadnji položaj zrcal v voltih v obliki np.array\n
        k : koeficient med piksli in volti za krmiljenje zrcal"""
        self.kamera = kamera
        self.laser = laser
        self.meritev = meritev
        self.položaj_zrcal = np.array([položaj_zrcal[1], položaj_zrcal[1]])
        self.k = k
        self.tarče = None

    def plotimg(self, img):
        plt.clf()
        plt.imshow(img[:, :, ::-1])
        plt.show()

    def narisi_tarce(self, img, tarče):
        """funkcija nariše tarče na sliko, tarče so podane v obliki seznama"""
        j = 1
        for i in tarče:
            start_point = (int(i[0]-10), int(i[1]-10))
            end_point = (int(i[0]+10), int(i[1]+10))
            cv2.rectangle(img, start_point, end_point,
                          (140, 225, 70), thickness=5)
            p_text = (int(i[0]+15), int(i[1]-15))
            cv2.putText(img, f"T{j}", p_text, 2, 3, (140, 225, 70))
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

    def namesto(self, cilj, max_r=5):
        """pomik na merilno mesto meritve"""
        while True:
            p0 = self.kamera.req("loc")
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
                #image = self.narisi_tarce(image, tarče)
                return img1
                break
            else:
                delta_zrcal = delta_px * self.k
                p_zrcal = list(self.položaj_zrcal)
                self.položaj_zrcal += delta_zrcal
                self.laser.premik_volt(
                    self.položaj_zrcal[0], self.položaj_zrcal[1])
                p1 = self.kamera.req("loc")
                # preverjanje položaja laserja, če je zašel v nevidnem območje
                delta_px1 = cilj-p1
                razdalja_do_cilja1 = np.sqrt(delta_px1[0]**2+delta_px1[1]**2)
                print(f"razdalja do cilja prvič {razdalja_do_cilja1}")
                while razdalja_do_cilja1 > razdalja_do_cilja*0.8:
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
                    delta_px1 = cilj-p1
                    razdalja_do_cilja1 = np.sqrt(
                        delta_px1[0]**2+delta_px1[1]**2)
                    print(f"zgrešeno {razdalja_do_cilja1}, pomika za {delta_zrcal}, na {self.položaj_zrcal}")

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
                        self.meritev.izvajanje_meritve(c, vzorec)
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


if __name__ == '__main__':
    # določanje objektov
    Pi = RPi()
    pi_kamera = Camera(Pi)
    laser = LaserHead(pi_kamera)
    meritev = Meritev(5)
    položaj_zrcal = np.array([1.7, 1.7])
    scanner = Scanner(pi_kamera, laser, meritev, položaj_zrcal, None)

    # povezovanje in aktivacija RPi
    pi_kamera.connect()
    # kalibracija laserja
    scanner.k = laser.kalibracija_basic(
        2, 2, položaj_zrcal[0], položaj_zrcal[1])
    # prikaz prve slike
    image = pi_kamera.req("img")
    scanner.plotimg(image)
    # določanje tarč
    scanner.dolocanje_tarc()
    # izvajanje pograma
    for i in range(5):
        scanner.cikelj(i+1)
    # izklaplanje
    pi_kamera.disconnect()
