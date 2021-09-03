import tkinter as tk
from tkinter import ttk
import MSLK
import numpy as np
from matplotlib.backends.backend_tkagg import (
    FigureCanvasTkAgg, NavigationToolbar2Tk)
#from matplotlib.backend_bases import key_press_handler
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import cv2
import pickle
import threading
from pyFRF import FRF
import pyEMA
import time
import concurrent.futures
import winsound


class GUI_MSLK:

    def __init__(self, master):

        self.master = master
        self.master.title("MSLK")
        self.master.iconbitmap("./files/logo.ico")
        # w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        # self.master.geometry("%dx%d+0+0" % (w-100, h-50))

#_________________________________Status_bar__________________________________________
        frame_info = tk.Frame(self.master, relief=tk.SUNKEN)
        frame_info.pack(fill=tk.X, side=tk.BOTTOM)
        self.stslabel = tk.Label(
            frame_info, anchor=tk.W, text="Program priprvljen. Potrebno je vzpostaviti povezavo s RPi")
        self.stslabel.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(
            frame_info, orient=tk.HORIZONTAL, length=100,  mode='indeterminate')
#_________________________________Load_data___________________________________________
        self.backup = {"slika/mask":True,
                   "iso":100,
                   "shutter speed":20000,
                   "th": 175,  
                   "Ux": 2.7,
                   "Uy": 2.0,
                   "Ukal": 0.3,
                   "Upomik": 0.3,
                   "hostname": "pi-kamera",
                   "port": 22,
                   "username": "pi",
                   "password": "pi",
                   "skripta": "Desktop/RPi_MSLK.py",
                   "ao0": "cDAQ10Mod1/ao0",
                   "ao1": "cDAQ10Mod1/ao1",
                   "ao2": "cDAQ10Mod4/ao0",
                   "ai0": "cDAQ10Mod3/ai0",
                   "ai1": "cDAQ10Mod3/ai1",
                   "ai2": "cDAQ10Mod3/ai3",
                   "U_max": 4,
                   "U_min": -4,
                   "las_v": 100.0,
                   "zamik laser": 0.00124,
                   "start silomer/kladivo": True,
                   "f kladivo":2.273,
                   "f1": 4.034,
                   "f2": 9.923,
                   "kladivo k. mirnosti":0.1,
                   "trigger value":3.0,
                   "pred trigger":0.01,
                   "osnovna frekvenca silomer": 13107200,
                   "frekvenca vzorčenja silomer": 0,
                   "čas silomer": 1,
                   "vzorcev za povprečenje silomer": 5,
                   "okno exc silomer": 2,
                   "value exc silomer":0.1,
                   "okno h silomer": 2,
                   "value h silomer": 0.1,
                   "typ silomer": 2,
                   "osnovna frekvenca kladivo": 13107200,
                   "frekvenca vzorčenja kladivo": 0,
                   "čas kladivo": 1,
                   "vzorcev za povprečenje kladivo": 1,
                   "okno exc kladivo": 3,
                   "value exc kladivo": 0.2,
                   "okno h kladivo": 4,
                   "value h kladivo":0.1,
                   "typ kladivo": 2,
                   "file_name": "meritev",
                   "dir": "C:",
                   "gen_on":True,
                   "low_f":50,
                   "upper_f":5000,
                   "število ciklov": 1}

        self.nastavitve_file = "files/nastavitve.pkl"
        try:
            fileholder = open(self.nastavitve_file, "rb")
            self.nastavitve = pickle.load(fileholder)
            fileholder.close()
        except:
            self.nastavitve = dict(self.backup)
            file = open("files/nastavitve.pkl", "wb")
            pickle.dump(self.nastavitve, file)
            file.close()
#_________________________________Konstante___________________________________________

    # definiranje konstant
        self.U_x = self.nastavitve["Ux"]
        self.U_y = self.nastavitve["Uy"]
        self.tarče = []
        self.continuePlottingImg = False
        self.prekini = False
        self.na_tarči = -1
        self.append_to_file = False
        self.povezava_vzpostavljena_boolean = False
        self.data_freq = None
        self.data_frf = None
        self.data_loaded = False
        self.poli_določeni = False
        self.prikazan_cikelj = 1
        self.prikazano_mesto = 1
        self.load_bar_stop = False
        self.objek_je_mirn = False
        self.serija0 = False
        self.triger = False
        self.tocke_ROI=-1
        self.ROI_kordinate=[]
        self.ena_metirev=True
#____________________________Definicija_zavihkov______________________________________

        tabControl = ttk.Notebook(self.master)

        self.tab1 = ttk.Frame(tabControl)
        self.tab2 = ttk.Frame(tabControl)
        self.tab3 = ttk.Frame(tabControl)

        tabControl.add(self.tab1, text='Kalibracija')
        tabControl.add(self.tab2, text='Nastavitve')
        tabControl.add(self.tab3, text='Meritve')
        tabControl.pack(expand=1, fill="both")
#___________________________________tab_1_____________________________________________
    #povezava in tarče
        frame_povezava_tarče = tk.Frame(self.tab1)
        frame_povezava_tarče.grid(row=0,column=1)

        self.gumb_izbriši_zadnjo_tarčo = tk.Button(
            frame_povezava_tarče, text="Izbriši zadnjo tarčo", command=self.izbriši_zadnjo_tarčo)
        self.gumb_izbriši_zadnjo_tarčo.grid(row=0, column=0)

        self.gumb_izbriši_vse_tarče = tk.Button(
            frame_povezava_tarče, text="Izbriši vse tarče", command=self.izbriši_vse_tarče)
        self.gumb_izbriši_vse_tarče.grid(row=0, column=1)

        self.gumb_vzpostavi_povezavo = tk.Button(
            frame_povezava_tarče, text="Vzpostavi povezavo", command=self.connect, bg="#89eb34")
        self.gumb_vzpostavi_povezavo.grid(row=1, column=0)
        self.spremeni_stanje(self.gumb_vzpostavi_povezavo)

        self.gumb_prekini_povezavo = tk.Button(
            frame_povezava_tarče, text="Prekini povezavo", command=self.disconnect, bg="#ec123e")
        self.gumb_prekini_povezavo.grid(row=1, column=1)

        frame_nastavitve_slike = tk.Frame(self.tab1)
        frame_nastavitve_slike.grid(row=2,column=1)

        self.gumb_pretakanje_slike = tk.Button(
            frame_nastavitve_slike, text="Pretakanje slike \n start/stop", command=self.gh1, bg="red", fg="white")
        self.gumb_pretakanje_slike.grid(row=0, column=0,rowspan=2)

        self.var_img = tk.BooleanVar()
        self.var_img.set(self.nastavitve["slika/mask"])
        self.cb_slika = tk.Checkbutton(frame_nastavitve_slike, text='Slika', variable=self.var_img, command=self.izbran_img)
        self.cb_slika.grid(row=0, column=1)

        self.var_mask = tk.BooleanVar()
        self.var_mask.set(not self.nastavitve["slika/mask"])
        self.cb_mask = tk.Checkbutton(frame_nastavitve_slike, text='Mask', variable=self.var_mask, command=self.izbran_mask)
        self.cb_mask.grid(row=1, column=1)

        label_iso = tk.Label(frame_nastavitve_slike,text="ISO kamere")
        label_iso.grid(row=2,column=0)

        self.entry_iso = tk.Entry(frame_nastavitve_slike)
        self.entry_iso.grid(row=2,column=1)
        self.entry_iso.insert(0,self.nastavitve["iso"])

        label_shutter_speed = tk.Label(frame_nastavitve_slike,text="Shutter speed (\u03BCs)")
        label_shutter_speed.grid(row=3,column=0)

        self.entry_shutter_speed = tk.Entry(frame_nastavitve_slike)
        self.entry_shutter_speed.grid(row=3,column=1)
        self.entry_shutter_speed.insert(0,self.nastavitve["shutter speed"])

        label_threshold = tk.Label(frame_nastavitve_slike,text="Threshold")
        label_threshold.grid(row=4,column=0)

        self.entry_threshold = tk.Entry(frame_nastavitve_slike)
        self.entry_threshold.grid(row=4,column=1)
        self.entry_threshold.insert(0,self.nastavitve["th"])

        gumb_posliji_nast_kamere = tk.Button(frame_nastavitve_slike,text="Pošlji nastavitve kamere",command=self.poslji_nast_kamere)
        gumb_posliji_nast_kamere.grid(row=5,column=0,columnspan=2,sticky="EW")

        gumn_rtd_slika = tk.Button(
            master=frame_nastavitve_slike, text="Reset to default", command=self.rtd_nast_slike)
        gumn_rtd_slika.grid(row=6, column=0,sticky="EW")

        gumb_save_slika = tk.Button(
            master=frame_nastavitve_slike, text="Save", command=self.save_nast_slike)
        gumb_save_slika.grid(row=6, column=1,sticky="EW")

        self.gumb_ROI = tk.Button(
            self.tab1, text="ROI", command=self.ROI, bg="#88b5fc")#, fg="white")
        self.gumb_ROI.grid(row=3, column=1, columnspan=2)

    # kontrole kalibracije
        frame_kontorla_kalibracije = tk.Frame(
            master=self.tab1, relief=tk.RAISED, borderwidth=1, width=100, height=100)
        frame_kontorla_kalibracije.grid(row=4, column=1, columnspan=2)

        label_kontrola_kalibracije = tk.Label(
            frame_kontorla_kalibracije, text="Kalibracija laserja/kamere")
        label_kontrola_kalibracije.grid(row=0, column=0, columnspan=3)

        label_kal_premik = tk.Label(
            frame_kontorla_kalibracije, text="Kal. premik [V]")
        label_kal_premik.grid(row=1, column=0, columnspan=2)

        self.entry_kal_premik = tk.Entry(master=frame_kontorla_kalibracije)
        self.entry_kal_premik.grid(row=1, column=2)
        self.entry_kal_premik.insert(0, self.nastavitve["Ukal"])

        label_U_pomik = tk.Label(
            frame_kontorla_kalibracije, text="Delata U (pada) [V]")
        label_U_pomik.grid(row=2, column=0, columnspan=2)

        self.entry_U_pomik = tk.Entry(master=frame_kontorla_kalibracije)
        self.entry_U_pomik.grid(row=2, column=2)
        self.entry_U_pomik.insert(0, self.nastavitve["Upomik"])

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
            frame_joystick, text="kalibriraj", bg="#eb4034", command=self.kalibracija_laserja)
        self.gumb_kalibriraj.grid(row=3, column=0)
        
        self.gumb_shrani_kal = tk.Button(
            frame_joystick, text="Shrani", bg="#eb4034", command=self.save_kaibracija)
        self.gumb_shrani_kal.grid(row=3, column=1)

    # priprava za plotanje slike iz kamere
        self.fig, self.ax = plt.subplots(
            nrows=1, ncols=1, figsize=(10, 6))
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab1)
        self.canvas.get_tk_widget().grid(row=0, column=0, rowspan=10)
        self.fig.canvas.callbacks.connect('button_press_event', self.on_click)
#___________________________________tab_2_____________________________________________
    # Polje za nastavitev RPi
        frame_pi_nastavitve = tk.LabelFrame(
            master=self.tab2, relief=tk.RAISED, borderwidth=1, text="Nastavitve Raspbrerry Pi")
        frame_pi_nastavitve.grid(row=0, column=0,sticky="NSEW")

        nast1 = tk.Label(master=frame_pi_nastavitve, text="Hostname: ")
        nast1.grid(row=1, column=0)
        self.vnos1 = tk.Entry(master=frame_pi_nastavitve)
        self.vnos1.grid(row=1, column=1)
        self.vnos1.insert(0, self.nastavitve["hostname"])

        nast2 = tk.Label(master=frame_pi_nastavitve, text="Port: ")
        nast2.grid(row=2, column=0)
        self.vnos2 = tk.Entry(master=frame_pi_nastavitve)
        self.vnos2.grid(row=2, column=1)
        self.vnos2.insert(0, self.nastavitve["port"])

        nast3 = tk.Label(master=frame_pi_nastavitve, text="Username")
        nast3.grid(row=3, column=0)
        self.vnos3 = tk.Entry(master=frame_pi_nastavitve)
        self.vnos3.grid(row=3, column=1)
        self.vnos3.insert(0, self.nastavitve["username"])

        nast4 = tk.Label(master=frame_pi_nastavitve, text="Password")
        nast4.grid(row=4, column=0)
        self.vnos4 = tk.Entry(master=frame_pi_nastavitve)
        self.vnos4.grid(row=4, column=1)
        self.vnos4.insert(0, self.nastavitve["password"])

        nast5 = tk.Label(master=frame_pi_nastavitve, text="Skripta")
        nast5.grid(row=5, column=0)
        self.vnos5 = tk.Entry(master=frame_pi_nastavitve)
        self.vnos5.grid(row=5, column=1)
        self.vnos5.insert(0, self.nastavitve["skripta"])

        pi_nast_gumb1 = tk.Button(
            master=frame_pi_nastavitve, text="Reset to default", command=self.rtd_pi)
        pi_nast_gumb1.grid(row=6, column=0)

        pi_nast_gumb2 = tk.Button(
            master=frame_pi_nastavitve, text="Save", command=self.save_pi)
        pi_nast_gumb2.grid(row=6, column=1)

    # Nastavitve merilnih kartic
        frame_ni_nastavitve = tk.LabelFrame(
            master=self.tab2, relief=tk.RAISED, borderwidth=1, text="Merilna kartica izhodni kanali")
        frame_ni_nastavitve.grid(row=1, column=0,sticky="NSEW")
        # label = tk.Label(master=frame_ni_nastavitve,
        #                  text="Merilna kartica izhodni kanali")
        # label.grid(row=0, column=0, columnspan=2)

        nast1_ni = tk.Label(master=frame_ni_nastavitve,
                            text="Izhodni kanal x: ")
        nast1_ni.grid(row=1, column=0)
        self.vnos1_ni = tk.Entry(master=frame_ni_nastavitve)
        self.vnos1_ni.grid(row=1, column=1)
        self.vnos1_ni.insert(0, self.nastavitve["ao0"])

        nast2_ni = tk.Label(master=frame_ni_nastavitve,
                            text="Izhodni kanal y: ")
        nast2_ni.grid(row=2, column=0)
        self.vnos2_ni = tk.Entry(master=frame_ni_nastavitve)
        self.vnos2_ni.grid(row=2, column=1)
        self.vnos2_ni.insert(0, self.nastavitve["ao1"])

        nast3_ni = tk.Label(master=frame_ni_nastavitve,
                            text="Izhod generator signala: ")
        nast3_ni.grid(row=3, column=0)
        self.vnos3_ni = tk.Entry(master=frame_ni_nastavitve)
        self.vnos3_ni.grid(row=3, column=1)
        self.vnos3_ni.insert(0, self.nastavitve["ao2"])

        ni_nast_gumb1 = tk.Button(
            master=frame_ni_nastavitve, text="Reset to default", command=self.rtd_ni)
        ni_nast_gumb1.grid(row=5, column=0)

        ni_nast_gumb2 = tk.Button(
            master=frame_ni_nastavitve, text="Save", command=self.save_ni)
        ni_nast_gumb2.grid(row=5, column=1)
    # nastavitve laserja
        frame_laser_nastavitve = tk.LabelFrame(
            master=self.tab2, relief=tk.RAISED, borderwidth=1,text="Nastavitve laserja")
        frame_laser_nastavitve.grid(row=0, column=1,sticky="NSEW")

        label_laser_kanal = tk.Label(
            frame_laser_nastavitve, text="Kanal laserja")
        label_laser_kanal.grid(row=1, column=0)

        self.entry_laser_kanal = tk.Entry(master=frame_laser_nastavitve)
        self.entry_laser_kanal.grid(row=1, column=1)
        self.entry_laser_kanal.insert(0, self.nastavitve["ai0"])

        label_laser_U_max = tk.Label(
            frame_laser_nastavitve, text="Napetost max [V]")
        label_laser_U_max.grid(row=2, column=0)

        self.entry_laser_U_max = tk.Entry(master=frame_laser_nastavitve)
        self.entry_laser_U_max.grid(row=2, column=1)
        self.entry_laser_U_max.insert(0, self.nastavitve["U_max"])

        label_laser_U_min = tk.Label(
            frame_laser_nastavitve, text="Napetost min [V]")
        label_laser_U_min.grid(row=3, column=0)

        self.entry_laser_U_min = tk.Entry(master=frame_laser_nastavitve)
        self.entry_laser_U_min.grid(row=3, column=1)
        self.entry_laser_U_min.insert(0, self.nastavitve["U_min"])

        label_laser_v = tk.Label(
            frame_laser_nastavitve, text="Merilno območje [mm/s]")
        label_laser_v.grid(row=4, column=0)

        self.entry_laser_v = tk.Entry(master=frame_laser_nastavitve)
        self.entry_laser_v.grid(row=4, column=1)
        self.entry_laser_v.insert(0, self.nastavitve["las_v"])

        label_laser_delay = tk.Label(
            frame_laser_nastavitve, text="Časovni zamik laserja [s]")
        label_laser_delay.grid(row=5, column=0)

        self.entry_laser_delay = tk.Entry(master=frame_laser_nastavitve)
        self.entry_laser_delay.grid(row=5, column=1)
        self.entry_laser_delay.insert(0, self.nastavitve["zamik laser"])

        gumb_rtd_laser = tk.Button(
            frame_laser_nastavitve, text="Reset to default",command=self.rtd_laser)
        gumb_rtd_laser.grid(row=6, column=0)

        gumb_seve_laser = tk.Button(
            frame_laser_nastavitve, text="Save",command=self.save_laser)
        gumb_seve_laser.grid(row=6, column=1)

    # nastavitve silomera/kladiva
        frame_silomer_nastavitve = tk.LabelFrame(
            master=self.tab2, relief=tk.RAISED, borderwidth=1,text="Nastavitve silomera/kladiva")
        frame_silomer_nastavitve.grid(row=1, column=1,sticky="NSEW")

        self.var_silomer = tk.BooleanVar()
        self.var_silomer.set(self.nastavitve["start silomer/kladivo"])
        self.cb_silomer = tk.Checkbutton(
            frame_silomer_nastavitve, text='Silomer', variable=self.var_silomer, command=self.izbran_silomer)
        self.cb_silomer.grid(row=1, column=0)
        self.cb_silomer.select()

        self.var_kladivo = tk.BooleanVar()
        self.var_kladivo.set(not self.nastavitve["start silomer/kladivo"])
        self.cb_kladivo = tk.Checkbutton(
            frame_silomer_nastavitve, text='Kladivo', variable=self.var_kladivo, command=self.izbrano_kladivo)
        self.cb_kladivo.grid(row=1, column=1)

        self.text_kanal_sk = tk.StringVar()
        self.text_kanal_sk.set("Kanal silomera")
        label_silomer_kanal = tk.Label(
            frame_silomer_nastavitve, textvariable=self.text_kanal_sk)
        label_silomer_kanal.grid(row=2, column=0)

        self.entry_silomer_kanal = tk.Entry(master=frame_silomer_nastavitve)
        self.entry_silomer_kanal.grid(row=2, column=1)
        self.entry_silomer_kanal.insert(0, self.nastavitve["ai1"])

        self.text_faktor_sk = tk.StringVar()
        self.text_faktor_sk.set("Faktor silomera [pC/N]")
        label_silomer_fakror1 = tk.Label(
            frame_silomer_nastavitve, textvariable=self.text_faktor_sk)
        label_silomer_fakror1.grid(row=3, column=0)

        self.entry_silomer_faktor1 = tk.Entry(master=frame_silomer_nastavitve)
        self.entry_silomer_faktor1.grid(row=3, column=1)
        self.entry_silomer_faktor1.insert(0, self.nastavitve["f1"])

        label_silomer_fakror2 = tk.Label(
            frame_silomer_nastavitve, text="Faktor nabojnega ojačevalnika [mV/pC]")
        label_silomer_fakror2.grid(row=4, column=0)

        self.entry_silomer_faktor2 = tk.Entry(master=frame_silomer_nastavitve)
        self.entry_silomer_faktor2.grid(row=4, column=1)
        self.entry_silomer_faktor2.insert(0, self.nastavitve["f2"])

        #faktor mirnosti predstavlja procent merilnega območja znotraj katerega
        #mora biti max raspon izmerjenih hitrosti da se objekt smatra za mirnega
        label_kriterij_mirnosti = tk.Label(frame_silomer_nastavitve,text="Faktor mirnosti:")
        label_kriterij_mirnosti.grid(row=5,column=0)

        self.entry_kriterij_mirnosti = tk.Entry(frame_silomer_nastavitve)
        self.entry_kriterij_mirnosti.grid(row=5,column=1)
        self.entry_kriterij_mirnosti.insert(0,self.nastavitve["kladivo k. mirnosti"])

        label_trigger_value = tk.Label(frame_silomer_nastavitve,text="Trigger value")
        label_trigger_value.grid(row=6,column=0)

        self.entry_trigger_value = tk.Entry(frame_silomer_nastavitve)
        self.entry_trigger_value.grid(row=6,column=1)
        self.entry_trigger_value.insert(0,self.nastavitve["trigger value"])

        label_pred_trigger = tk.Label(frame_silomer_nastavitve,text="Dolžina meritve pred trigger (s)")
        label_pred_trigger.grid(row=7,column=0)

        self.entry_pred_trigger = tk.Entry(frame_silomer_nastavitve)
        self.entry_pred_trigger.grid(row=7,column=1)
        self.entry_pred_trigger.insert(0, self.nastavitve["pred trigger"])

        gumb_rtd_silomer_kladivo = tk.Button(
            frame_silomer_nastavitve, text="Reset to default",command=self.rtd_silomer_kladivo)
        gumb_rtd_silomer_kladivo.grid(row=8, column=0)

        gumb_seve_silomer_kladivo = tk.Button(
            frame_silomer_nastavitve, text="Save",command=self.save_silomer_kladivo)
        gumb_seve_silomer_kladivo.grid(row=8, column=1)

    # nastavitve zajema
        frame_zajem_nastavitve = tk.LabelFrame(
            master=self.tab2, relief=tk.RAISED, borderwidth=1,text="Nastavitve meritev")
        frame_zajem_nastavitve.grid(row=0, column=2,rowspan=2)

        # label_zajem_nastavitve = tk.Label(
        #     frame_zajem_nastavitve, text="Nastavitve meritev")
        # label_zajem_nastavitve.grid(row=0, column=0, columnspan=2)

        label_zajem_nastavitve = tk.Label(
            frame_zajem_nastavitve, text="Frekvenca merilne kartice [Hz]:")
        label_zajem_nastavitve.grid(row=1, column=0)

        self.entry_osnovna_frekvenca = tk.Entry(frame_zajem_nastavitve)
        self.entry_osnovna_frekvenca.grid(row=1, column=1)

        self.gumb_izračunaj_frekvence = tk.Button(
            frame_zajem_nastavitve, text="Izračunaj frekvence", command=self.izračun_možnih_frekvenc)
        self.gumb_izračunaj_frekvence.grid(row=2, column=0, columnspan=2)

        label_frekvenca_vzorcenja = tk.Label(
            frame_zajem_nastavitve, text="Frekvenca vzorčenja [Hz]")
        label_frekvenca_vzorcenja.grid(row=3, column=0)

        self.mozne_frekvence = ["51200.0",
                                "25600.0",
                                "17066.666666666668",
                                "12800.0",
                                "10240.0",
                                "8533.333333333334",
                                "7314.285714285715",
                                "6400.0",
                                "5688.888888888889",
                                "5120.0",
                                "4654.545454545455",
                                "4266.666666666667",
                                "3938.4615384615386",
                                "3657.1428571428573",
                                "3413.3333333333335",
                                "3200.0",
                                "3011.764705882353",
                                "2844.4444444444443",
                                "2694.7368421052633",
                                "2560.0",
                                "2438.095238095238",
                                "2327.2727272727275",
                                "2226.086956521739",
                                "2133.3333333333335",
                                "2048.0",
                                "1969.2307692307693",
                                "1896.2962962962963",
                                "1828.5714285714287",
                                "1765.5172413793102",
                                "1706.6666666666667",
                                "1651.6129032258063"]

        self.variable = tk.StringVar(self.master)

        self.om_frekvenca = tk.OptionMenu(
            frame_zajem_nastavitve, self.variable, *self.mozne_frekvence)
        self.om_frekvenca.grid(row=3, column=1)

        label_cas_meritve = tk.Label(
            frame_zajem_nastavitve, text="Čas meritve [s]")
        label_cas_meritve.grid(row=4, column=0)

        self.entry_cas_meritve = tk.Entry(master=frame_zajem_nastavitve)
        self.entry_cas_meritve.grid(row=4, column=1)

        label_povprečenje = tk.Label(
            frame_zajem_nastavitve, text="Vzorcev za povprečenje")
        label_povprečenje.grid(row=5, column=0)

        self.entry_povprečenje = tk.Entry(master=frame_zajem_nastavitve)
        self.entry_povprečenje.grid(row=5, column=1)

        # Kontrola FRF
        label_okno_exc = tk.Label(frame_zajem_nastavitve, text="Okno exc")
        label_okno_exc.grid(row=6, column=0)

        self.okna = ['None', 'Hann', 'Hamming', 'Force',
                     'Exponential', 'Bartlett', 'Blackman', 'Kaiser']

        self.variable_okno_exc = tk.StringVar(self.master)
        

        self.om_okno_exc = tk.OptionMenu(
            frame_zajem_nastavitve, self.variable_okno_exc, *self.okna)
        self.om_okno_exc.grid(row=6, column=1)

        label_okno_exc_value = tk.Label(frame_zajem_nastavitve,text="Vrednost za okno exc")
        label_okno_exc_value.grid(row=7,column=0)

        self.entry_okno_exc_value = tk.Entry(frame_zajem_nastavitve)
        self.entry_okno_exc_value.grid(row=7,column=1)

        label_okno_h = tk.Label(frame_zajem_nastavitve, text="Okno h")
        label_okno_h.grid(row=8, column=0)

        self.variable_okno_h = tk.StringVar(self.master)


        self.om_okno_h = tk.OptionMenu(
            frame_zajem_nastavitve, self.variable_okno_h, *self.okna)
        self.om_okno_h.grid(row=8, column=1)

        label_okno_h_value = tk.Label(frame_zajem_nastavitve,text="Vrednost za okno h")
        label_okno_h_value.grid(row=9,column=0)

        self.entry_okno_h_value = tk.Entry(frame_zajem_nastavitve)
        self.entry_okno_h_value.grid(row=9,column=1)

        label_typ = tk.Label(frame_zajem_nastavitve, text="Typ")
        label_typ.grid(row=10, column=0)

        self.types = ['H1', 'H2', 'Hv', 'vector', 'ODS']

        self.variable_typ = tk.StringVar(self.master)
        

        self.om_typ = tk.OptionMenu(
            frame_zajem_nastavitve, self.variable_typ, *self.types)
        self.om_typ.grid(row=10, column=1)

        self.var_save = tk.IntVar()
        self.cb_save_file = tk.Checkbutton(
            frame_zajem_nastavitve, text='Shranjuj podatke', variable=self.var_save, onvalue=1, offvalue=0)
        self.cb_save_file.grid(row=11, column=0, columnspan=2)

        label_ime_datoteke = tk.Label(
            frame_zajem_nastavitve, text="Ime datoteke")
        label_ime_datoteke.grid(row=12, column=0)

        self.entry_ime_datoteke = tk.Entry(master=frame_zajem_nastavitve)
        self.entry_ime_datoteke.grid(row=12, column=1)
        self.entry_ime_datoteke.insert(0, self.nastavitve["file_name"])

        button_path = tk.Button(frame_zajem_nastavitve,
                                text="Pot do datoteke", command=self.dir_path)
        button_path.grid(row=13, column=0)

        self.entry_path = tk.Entry(master=frame_zajem_nastavitve)
        self.entry_path.grid(row=13, column=1)
        self.entry_path.insert(0, self.nastavitve["dir"])

        gumb_rtd_zajem = tk.Button(
            frame_zajem_nastavitve, text="Reset to default",command=self.rtd_zajem)
        gumb_rtd_zajem.grid(row=14, column=0)

        gumb_seve_zajem = tk.Button(
            frame_zajem_nastavitve, text="Save",command=self.save_zajem)
        gumb_seve_zajem.grid(row=14, column=1)

    #nastavitve generatorja
        frame_generator_nastavitve = tk.LabelFrame(
            master=self.tab2, relief=tk.RAISED, borderwidth=1,text="Nastavitve generatorja")
        frame_generator_nastavitve.grid(row=0, column=3,sticky="NSEW")
        self.var_generator = tk.BooleanVar()
        self.var_generator.set(self.nastavitve["gen_on"])
        self.cb_generator = tk.Checkbutton(
            frame_generator_nastavitve, text='Generiraj signal', variable=self.var_generator)
        self.cb_generator.grid(row=1, column=0, columnspan=2)
        #self.cb_generator.select()

        label_freq_lower = tk.Label(frame_generator_nastavitve,text="Spodnja frekvenca vzbujanja")
        label_freq_lower.grid(row=2,column=0)

        self.entry_freq_lower = tk.Entry(frame_generator_nastavitve)
        self.entry_freq_lower.grid(row=2,column=1)
        self.entry_freq_lower.insert(0, self.nastavitve["low_f"])

        label_freq_upper = tk.Label(frame_generator_nastavitve,text="Zgornja frekvenca vzbujanja")
        label_freq_upper.grid(row=3,column=0)

        self.entry_freq_upper = tk.Entry(frame_generator_nastavitve)
        self.entry_freq_upper.grid(row=3,column=1)
        self.entry_freq_upper.insert(0, self.nastavitve["upper_f"])

        gumb_rtd_generator = tk.Button(
            frame_generator_nastavitve, text="Reset to default",command=self.rtd_generator)
        gumb_rtd_generator.grid(row=4, column=0)

        gumb_seve_generator = tk.Button(
            frame_generator_nastavitve, text="Save",command=self.save_generator)
        gumb_seve_generator.grid(row=4, column=1)

        self.urejanje_silomer_kladivo()
#___________________________________tab_3_____________________________________________

    # plotanje
        frame_tab3_plotanje = tk.Frame(
            master=self.tab3, relief=tk.RAISED, borderwidth=1)
        frame_tab3_plotanje.grid(row=0, column=1, rowspan=4, sticky='EWNS')

        self.tabControltab3 = ttk.Notebook(frame_tab3_plotanje)

        self.tab3tab1 = ttk.Frame(self.tabControltab3)
        self.tab3tab2 = ttk.Frame(self.tabControltab3)
        self.tab3tab3 = ttk.Frame(self.tabControltab3)

        self.tabControltab3.add(self.tab3tab1, text='Zajeti signali')
        self.tabControltab3.add(self.tab3tab2, text='FRF')
        self.tabControltab3.add(self.tab3tab3, text='MA')
        self.tabControltab3.pack(expand=1, fill="both")

        # tab3->tab1 meritve
        self.fig_meritev, self.axes_meritev = plt.subplots(
            nrows=2, ncols=1, figsize=(10, 6))
        # laser
        self.axes_meritev[0].set_title("Laser")
        self.axes_meritev[0].set_xlabel("Čas [s]")
        self.axes_meritev[0].set_ylabel("Hitreost [mm/s]")
        self.axes_meritev[0].grid()

        # silomer
        self.axes_meritev[1].set_title("Silomer")
        self.axes_meritev[1].set_xlabel("Čas [s]")
        self.axes_meritev[1].set_ylabel("Sila [N]")
        self.axes_meritev[1].grid()

        self.fig_meritev.tight_layout()

        self.graph_meritve = FigureCanvasTkAgg(
            self.fig_meritev, master=self.tab3tab1)
        self.graph_meritve.get_tk_widget().pack(
            side=tk.BOTTOM, fill=tk.BOTH, expand=1)
        # self.graph_meritve.draw()

        self.meritve_toolbar = NavigationToolbar2Tk(
            self.graph_meritve, self.tab3tab1)
        self.meritve_toolbar.update()
        self.graph_meritve._tkcanvas.pack(
            side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # tab3->tab2 FRF
        self.fig_FRF, self.axes_FRF = plt.subplots(
            nrows=2, ncols=1, figsize=(8, 6))
        # FRF
        self.axes_FRF[0].set_title("FRF")
        self.axes_FRF[0].set_xlabel("Frekvenca [Hz]")
        self.axes_FRF[0].set_ylabel("(mm/s)/N")
        self.axes_FRF[0].grid()

        # kotni zamik
        self.axes_FRF[1].set_title("Fazni zamik")
        self.axes_FRF[1].set_xlabel("Frekvenca [Hz]")
        self.axes_FRF[1].set_ylabel("kot")
        self.axes_FRF[1].grid()

        self.fig_FRF.tight_layout()

        self.graph_FRF = FigureCanvasTkAgg(self.fig_FRF, master=self.tab3tab2)
        self.graph_FRF.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.FRF_toolbar = NavigationToolbar2Tk(self.graph_FRF, self.tab3tab2)
        self.FRF_toolbar.update()
        self.graph_FRF._tkcanvas.pack(
            side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # tab3->tab3 modalna analiza
        self.fig_lastne_oblike, self.axes_lastne_oblike = plt.subplots(
            figsize=(8, 6))
        # lasatne oblike
        self.axes_lastne_oblike.set_title("Lastne oblike")
        self.fig_lastne_oblike.tight_layout()

        self.graph_lastne_oblike = FigureCanvasTkAgg(
            self.fig_lastne_oblike, master=self.tab3tab3)
        self.graph_lastne_oblike.get_tk_widget().pack(
            side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        self.lastne_oblike_toolbar = NavigationToolbar2Tk(
            self.graph_lastne_oblike, self.tab3tab3)
        self.lastne_oblike_toolbar.update()
        self.graph_lastne_oblike._tkcanvas.pack(
            side=tk.BOTTOM, fill=tk.BOTH, expand=True)

    # Kontrole za začetek merive
        frame_gumbi_tab3 = tk.Frame(
            master=self.tab3, relief=tk.RAISED, borderwidth=1)
        frame_gumbi_tab3.grid(row=0, column=2)

        self.gumb_prejšnja = tk. Button(frame_gumbi_tab3, text="Pomik na prejšnjo tarčo",
                                        command=self.pomik_na_prejšno_tarčo)  # moras se naredit funkcijo
        self.gumb_prejšnja.grid(row=0, column=0)

        self.gumb_nasledna = tk. Button(frame_gumbi_tab3, text="Pomik na naslednjo tarčo",
                                        command=self.pomik_na_nasledno_tarčo)  # moras se naredit funkcijo
        self.gumb_nasledna.grid(row=0, column=1)

        self.gumb_ena_meritev = tk. Button(
            frame_gumbi_tab3, text="Meritev trenutnega mesta", command=self.meritev_trenutnega_mesta)  # moras se naredit
        self.gumb_ena_meritev.grid(row=1, column=0, columnspan=2)

        self.label_stevilo_ciklov = tk.Label(
            frame_gumbi_tab3, text='Število ciklov:')
        self.label_stevilo_ciklov.grid(row=2, column=0)

        self.entry_stevilo_ciklov = tk.Entry(frame_gumbi_tab3)
        self.entry_stevilo_ciklov.grid(row=2, column=1)
        self.entry_stevilo_ciklov.insert(0, self.nastavitve["število ciklov"])

        self.gumb_začni_meritev = tk. Button(
            frame_gumbi_tab3, text="Začni meritev", command=self.zacni_meritev,bg="#89eb34")
        self.gumb_začni_meritev.grid(row=3, column=0)

        self.gumb_prekini_meritev = tk. Button(
            frame_gumbi_tab3, text="Prekini meritev", command=self.prekini_meritev)
        self.gumb_prekini_meritev.grid(row=3, column=1)

        frame_lastne = tk.Frame(self.tab3, relief=tk.RAISED, borderwidth=1)
        frame_lastne.grid(row=1,column=2)

        self.gumb_doloci_pole = tk. Button(
            frame_lastne, text="Določi pole", command=self.doloci_pole)
        self.gumb_doloci_pole.grid(row=0, column=0,columnspan=2)
        self.spremeni_stanje(self.gumb_doloci_pole)

        label_st_lastnih=tk.Label(frame_lastne,text="Stevilo prikazanih lastnih oblik")
        label_st_lastnih.grid(row=1,column=0)

        self.entry_st_lastnih = tk.Entry(frame_lastne)
        self.entry_st_lastnih.grid(row=1,column=1)
        self.entry_st_lastnih.insert(0,"3")

        self.gumb_plotaj_lastne = tk. Button(
            frame_lastne, text="Lastne oblike", command=self.lastne_oblike_plot)
        self.gumb_plotaj_lastne.grid(row=2, column=0,columnspan=2)
        self.spremeni_stanje(self.gumb_plotaj_lastne)

    # Loadanje in upravljanje s ploti
        frame_upravlanje_plotov_tab3 = tk.Frame(
            master=self.tab3, relief=tk.RAISED, borderwidth=1)
        frame_upravlanje_plotov_tab3.grid(row=2, column=2)

        label_upravljanje_plotov = tk.Label(
            frame_upravlanje_plotov_tab3, text="Izbira podatkov")
        label_upravljanje_plotov.grid(row=0, column=0, columnspan=3)

        self.gumb_naloži_datoteko = tk.Button(
            frame_upravlanje_plotov_tab3, text="Naloži datoteko", command=self.load_file)
        self.gumb_naloži_datoteko.grid(row=1, column=0, columnspan=3)

        self.text_data_for_plot = tk.StringVar()
        self.text_data_for_plot.set("Bere se iz zadnje meritve.")

        self.entry_data_for_plot = tk.Entry(
            frame_upravlanje_plotov_tab3, textvariable=self.text_data_for_plot)
        self.entry_data_for_plot.grid(row=2, column=0, columnspan=3)

        label_cikelj = tk.Label(
            frame_upravlanje_plotov_tab3, text="Trenutno prikazan cikelj:")
        label_cikelj.grid(row=3, column=0, columnspan=3)

        self.gumb_cikelj_prejšnji = tk.Button(
            frame_upravlanje_plotov_tab3, text="<", command=self.cikelj_nazaj)
        self.gumb_cikelj_prejšnji.grid(row=4, column=0)
        self.spremeni_stanje(self.gumb_cikelj_prejšnji)

        self.text_prikazan_cikej = tk.StringVar()
        self.text_prikazan_cikej.set(self.prikazan_cikelj)

        label_trenutni_cikelj = tk.Label(
            frame_upravlanje_plotov_tab3, textvariable=self.text_prikazan_cikej)
        label_trenutni_cikelj.grid(row=4, column=1)

        self.gumb_cikelj_nasljednji = tk.Button(
            frame_upravlanje_plotov_tab3, text=">", command=self.cikelj_naprej)
        self.gumb_cikelj_nasljednji.grid(row=4, column=2)
        self.spremeni_stanje(self.gumb_cikelj_nasljednji)

        label_mesto = tk.Label(frame_upravlanje_plotov_tab3,
                               text="Trenutno prikazan mesto:")
        label_mesto.grid(row=5, column=0, columnspan=3)

        self.gumb_mesto_prejšnje = tk.Button(
            frame_upravlanje_plotov_tab3, text="<", command=self.mesto_nazaj)
        self.gumb_mesto_prejšnje.grid(row=6, column=0)
        self.spremeni_stanje(self.gumb_mesto_prejšnje)

        self.text_prikazano_mesto = tk.StringVar()
        self.text_prikazano_mesto.set(self.prikazano_mesto)

        label_trenutno_mesto = tk.Label(
            frame_upravlanje_plotov_tab3, textvariable=self.text_prikazano_mesto)
        label_trenutno_mesto.grid(row=6, column=1)

        self.gumb_mesto_nasljednje = tk.Button(
            frame_upravlanje_plotov_tab3, text=">", command=self.mesto_naprej)
        self.gumb_mesto_nasljednje.grid(row=6, column=2)
        self.spremeni_stanje(self.gumb_mesto_nasljednje)

        label_skala = tk.Label(frame_upravlanje_plotov_tab3,text="Upravljanje x osi FRF")
        label_skala.grid(row=7,column=0,columnspan=3)

        label_skala_do = tk.Label(frame_upravlanje_plotov_tab3,text="od")
        label_skala_do.grid(row=8,column=0)

        self.entry_skala_min = tk.Entry(frame_upravlanje_plotov_tab3)
        self.entry_skala_min.grid(row=8,column=1)
        self.entry_skala_min.insert(0,"0")

        label_skala_do = tk.Label(frame_upravlanje_plotov_tab3,text="do")
        label_skala_do.grid(row=9,column=0)

        self.entry_skala_max = tk.Entry(frame_upravlanje_plotov_tab3)
        self.entry_skala_max.grid(row=9,column=1,sticky="WE")
        self.entry_skala_max.insert(0, int(float(self.variable.get())/5))

        self.switch()
# =================================Funkcije===========================================
    def connect(self):
        """funkcija skrbi za vzpostavitev povezave z RPi"""
        def real_connect():

            if self.povezava_vzpostavljena_boolean == False:
                self.stslabel.configure(text="Vpostavljanje povezave")
                Pi = MSLK.RPi(hostname=self.vnos1.get(),
                              port=self.vnos2.get(),
                              username=self.vnos3.get(),
                              password=self.vnos4.get(),
                              skripta=self.vnos5.get())
                pi_kamera = MSLK.Camera(Pi)
                laser = MSLK.LaserHead(
                    pi_kamera, ch1=self.vnos1_ni.get(), ch2=self.vnos2_ni.get())
                meritev = MSLK.Meritev()
                položaj_zrcal = np.array([self.U_x, self.U_y])
                self.scanner = MSLK.Scanner(
                    pi_kamera, laser, meritev, položaj_zrcal, None)
                if self.var_generator.get():
                    self.generator_signalov = MSLK.Generator(self.vnos3_ni.get(),int(self.entry_freq_lower.get()),int(self.entry_freq_upper.get()))



                # vzpostavitev povezave z RPi
                self.scanner.kamera.connect()
                # kalibracija laserske glave
                self.kalibracija_laserja()
                self.stslabel.configure(text="Povezava na RPi vzpostavljena")

                self.image = self.scanner.kamera.req("img")
                self.image = self.scanner.narisi_tarce(self.image, self.tarče)
                self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
                self.imgshow()

                self.povezava_vzpostavljena_boolean = True
                self.switch()
        threading.Thread(target=real_connect).start()

    def disconnect(self):
        """funkcija za prekinitev povezave z RPi in ponastvitev konstant"""
        if self.povezava_vzpostavljena_boolean == True:
            self.scanner.kamera.disconnect()
            self.stslabel.configure(text="Povezava na RPi prekinjena")
            self.povezava_vzpostavljena_boolean = False
            self.switch()
        else:
            self.stslabel.configure(text="Povezava je že prekinjena")
        
        self.U_x = self.nastavitve["Ux"]
        self.U_y = self.nastavitve["Uy"]
        self.tarče = []
        self.continuePlottingImg = False
        self.prekini = False
        self.na_tarči = -1
        self.append_to_file = False
        self.povezava_vzpostavljena_boolean = False
        self.data_freq = None
        self.data_frf = None
        self.data_loaded = False
        self.poli_določeni = False
        self.prikazan_cikelj = 1
        self.prikazano_mesto = 1
        self.load_bar_stop = False
        self.objek_je_mirn = False
        self.serija0 = False
        self.triger = False
        self.tocke_ROI=-1
        self.ROI_kordinate=[]
        self.ena_metirev=True

    def generator_update(self):
        self.generator_signalov.freq_lower=int(self.entry_freq_lower.get())
        self.generator_signalov.freq_upper=int(self.entry_freq_upper.get())

    def ROI(self):
        self.tocke_ROI=0
        self.ROI_kordinate=[]
        self.stslabel.configure(text="Izbira ROI")

    def izračun_možnih_frekvenc(self):
        """Funkcija izračuna možne frekvence vzorčenja in jih ponudi uporabniku"""
        osnovna = float(self.entry_osnovna_frekvenca.get())
        seznam_frekvenc = []
        for i in range(31):
            f = str(osnovna/(256*(i+1)))
            seznam_frekvenc.append(f)
        self.mozne_frekvence = list(seznam_frekvenc)
        print(self.mozne_frekvence)
        self.om_frekvenca['menu'].delete(0, 'end')
        for choice in self.mozne_frekvence:
            self.om_frekvenca['menu'].add_command(
                label=choice, command=tk._setit(self.variable, choice))

    def dir_path(self):
        """funkcija za opdianje okna kjer uporabnik določi poto do mape
        kjer se bo shranjevale meritve"""

        file_path = tk.filedialog.askdirectory()
        self.entry_path.delete(0, 'end')
        self.entry_path.insert(0, file_path)
        self.cb_save_file.select()

    def load_file(self):
        """Odpre se okno kjer lahko uporabnik izbere shranjene meritve za pregled in
        nadalno obdelavo"""

        self.loaded_data_filename = tk.filedialog.askopenfilenames(
            filetypes=(('numpy files', '*.npy'), ('All files', '*.*')))
        self.text_data_for_plot.set(self.loaded_data_filename)
        # spodaj odstrani naredi nove podatke
        print(self.loaded_data_filename[0])
        self.data_freq, self.data_frf, self.data_exc, self.data_h = np.load(
            self.loaded_data_filename[0], allow_pickle=True)
        self.data_ciklov = np.shape(self.data_frf)[0]
        self.data_mest = np.shape(self.data_frf)[1]

        self.prikazan_cikelj = 1
        self.prikazano_mesto = 1
        self.kontrola_gumbov_podatkov()

        self.update_grafe(np.linspace(0, 1,len(self.data_exc[0,0])),
                            self.data_exc[self.prikazan_cikelj-1, self.prikazano_mesto-1],
                            self.data_h[self.prikazan_cikelj-1, self.prikazano_mesto-1],
                            self.data_freq,
                            self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def kontrola_gumbov_podatkov(self):
        """Funkcija nadoruje da se gubi za prehanjanje med različnimi podatki pravilno 
        izklapljajo in uklapljajo"""
        self.text_prikazan_cikej.set(self.prikazan_cikelj)
        self.text_prikazano_mesto.set(self.prikazano_mesto)
        self.tabControltab3.select(self.tab3tab2)

        self.gumb_cikelj_prejšnji["state"] = "normal"
        self.gumb_cikelj_nasljednji["state"] = "normal"
        self.gumb_mesto_prejšnje["state"] = "normal"
        self.gumb_mesto_nasljednje["state"] = "normal"

        if self.data_ciklov==1:
            self.gumb_cikelj_prejšnji["state"] = "disabled"
            self.gumb_cikelj_nasljednji["state"] = "disabled"
            if self.prikazano_mesto==self.data_mest:
                self.gumb_mesto_prejšnje["state"] = "normal"
                self.gumb_mesto_nasljednje["state"] = "disabled"
            elif self.prikazano_mesto==1:
                self.gumb_mesto_prejšnje["state"] = "disabled"
                self.gumb_mesto_nasljednje["state"] = "normal"
            else:
                self.gumb_mesto_prejšnje["state"] = "normal"
                self.gumb_mesto_nasljednje["state"] = "normal"
        elif self.data_mest==1:
                self.gumb_mesto_prejšnje["state"] = "disabled"
                self.gumb_mesto_nasljednje["state"] = "disabled"
                if self.prikazan_cikelj==1:
                    self.gumb_cikelj_prejšnji["state"] = "disabled"
                    self.gumb_cikelj_nasljednji["state"] = "normal"
                elif self.prikazan_cikelj==self.data_ciklov:
                    self.gumb_cikelj_prejšnji["state"] = "normal"
                    self.gumb_cikelj_nasljednji["state"] = "disabled"
        elif self.prikazan_cikelj==1:
            self.gumb_cikelj_prejšnji["state"] = "disabled"
            self.gumb_cikelj_nasljednji["state"] = "normal"
            if self.prikazano_mesto==1:
                self.gumb_mesto_prejšnje["state"] = "disabled"
                self.gumb_mesto_nasljednje["state"] = "normal"
            elif self.prikazano_mesto==self.data_mest:
                self.gumb_mesto_prejšnje["state"] = "normal"
                self.gumb_mesto_nasljednje["state"] = "disabled"
            else:
                self.gumb_mesto_prejšnje["state"] = "normal"
                self.gumb_mesto_nasljednje["state"] = "normal"
        elif self.prikazan_cikelj==self.data_ciklov:
            self.gumb_cikelj_prejšnji["state"] = "normal"
            self.gumb_cikelj_nasljednji["state"] = "disabled"
            if self.prikazano_mesto==1:
                self.gumb_mesto_prejšnje["state"] = "disabled"
                self.gumb_mesto_nasljednje["state"] = "normal"
            elif self.prikazano_mesto==self.data_mest:
                self.gumb_mesto_prejšnje["state"] = "normal"
                self.gumb_mesto_nasljednje["state"] = "disabled"
            else:
                self.gumb_mesto_prejšnje["state"] = "normal"
                self.gumb_mesto_nasljednje["state"] = "normal"
        else:
            self.gumb_cikelj_prejšnji["state"] = "normal"
            self.gumb_cikelj_nasljednji["state"] = "normal"
            if self.prikazano_mesto==1:
                self.gumb_mesto_prejšnje["state"] = "disabled"
                self.gumb_mesto_nasljednje["state"] = "normal"
            elif self.prikazano_mesto==self.data_mest:
                self.gumb_mesto_prejšnje["state"] = "normal"
                self.gumb_mesto_nasljednje["state"] = "disabled"
            else:
                self.gumb_mesto_prejšnje["state"] = "normal"
                self.gumb_mesto_nasljednje["state"] = "normal"

        self.data_loaded = True
        self.gumb_doloci_pole["state"] = "normal"
        self.stslabel.configure(text=f"Podatki pridobljeni, določiti je potrebno pole.")

    def doloci_pole(self):
        """Odpre se novo okno v s pomočjo pyEMA kjer se določiko poli"""
        self.acc = pyEMA.Model(frf=self.data_frf[self.prikazan_cikelj-1],
                               freq=self.data_freq,
                               lower=int(self.entry_skala_min.get()),
                               upper=int(self.entry_skala_max.get()),
                               pol_order_high=60)
        self.acc.get_poles()
        self.stslabel.configure(text=f"Poli določeni, možno je plotanje lastnih oblik.")
        self.gumb_plotaj_lastne["state"] = "normal"
        self.poli_določeni = True
        self.acc.select_poles()

    def lastne_oblike_plot(self):
        """Funkcija skrbi za plotanje lastnih oblik s pomočjo pyEMA"""
        # self.acc.print_modal_data()
        #frf_rec, modal_const = acc.get_constants(whose_poles='own', FRF_ind='all')
        self.axes_lastne_oblike.cla()
        tarče=np.array(self.tarče)
        plotaj_st_lastnih=int(self.entry_st_lastnih.get())
        if plotaj_st_lastnih>len(self.acc.normal_mode()):
            plotaj_st_lastnih=len(self.acc.normal_mode())
        for i in range(plotaj_st_lastnih):
            if len(self.tarče)!=len(self.acc.normal_mode()[:, i]):
                self.axes_lastne_oblike.plot(self.acc.normal_mode()[:, i], label=f"{i+1}. lastna oblika")
            else:
                self.axes_lastne_oblike.plot(tarče[:,0],self.acc.normal_mode()[:, i], label=f"{i+1}. lastna oblika")
        self.axes_lastne_oblike.legend()
        self.graph_lastne_oblike.draw()
        self.stslabel.configure(text=f"Plotanje lastnih oblik končnao")
        self.tabControltab3.select(self.tab3tab3)

    def spremeni_stanje(self, b1):  # ,b2):
        """Funkcija spremeni stanje gumba b1 iz aktivnega v neaktivnega oz obratno"""
        if b1["state"] == "normal":
            b1["state"] = "disabled"
            #b2["text"] = "enable"
        else:
            b1["state"] = "normal"
            #b2["text"] = "disable"

    def switch(self):
        """Funkcija zbira vse gumbe ki ob določenih dogodkih spremenijo
         stanje aktivno/ne aktnivo"""
        # tab1
        self.spremeni_stanje(self.gumb_vzpostavi_povezavo)
        self.spremeni_stanje(self.gumb_prekini_povezavo)
        self.spremeni_stanje(self.gumb_izbriši_zadnjo_tarčo)
        self.spremeni_stanje(self.gumb_izbriši_vse_tarče)
        self.spremeni_stanje(self.gumb_pretakanje_slike)
        self.spremeni_stanje(self.gumb_Ux_gor)
        self.spremeni_stanje(self.gumb_Ux_dol)
        self.spremeni_stanje(self.gumb_Uy_gor)
        self.spremeni_stanje(self.gumb_Uy_dol)
        self.spremeni_stanje(self.gumb_kalibriraj)
        self.spremeni_stanje(self.gumb_shrani_kal)

        # tab3
        self.spremeni_stanje(self.gumb_prejšnja)
        self.spremeni_stanje(self.gumb_nasledna)
        self.spremeni_stanje(self.gumb_ena_meritev)
        self.spremeni_stanje(self.gumb_začni_meritev)
        self.spremeni_stanje(self.gumb_prekini_meritev)
        if self.data_loaded == True:
            self.spremeni_stanje(self.gumb_doloci_pole)
        if self.poli_določeni == True:
            self.spremeni_stanje(self.gumb_plotaj_lastne)

    def izbran_img(self):
        if self.var_img.get() == True:
            self.var_mask.set(False)
        else:
            self.var_mask.set(True)

    def izbran_mask(self):
        if self.var_mask.get() == True:
            self.var_img.set(False)
        else:
            self.var_img.set(True)

    def izbrano_kladivo(self):
        if self.var_kladivo.get() == True:
            self.var_silomer.set(False)
        else:
            self.var_silomer.set(True)
        self.urejanje_silomer_kladivo()

    def izbran_silomer(self):
        if self.var_silomer.get() == True:
            self.var_kladivo.set(False)
        else:
            self.var_kladivo.set(True)
        self.urejanje_silomer_kladivo()

    def urejanje_silomer_kladivo(self):
        """aktivacija in deaktivacija ustreznih oken glede na to s čim se miri"""
        if self.var_kladivo.get():
            self.entry_silomer_faktor2['state'] = 'disabled'
            self.entry_kriterij_mirnosti['state'] = 'normal'
            self.entry_trigger_value['state'] = 'normal'
            self.entry_pred_trigger['state'] = 'normal'
            
 
            self.text_kanal_sk.set("Kanal kladiva")
            self.entry_silomer_kanal.delete(0, 'end')
            self.entry_silomer_kanal.insert(0, self.nastavitve["ai2"])
            self.text_faktor_sk.set("Faktor kladiva [mV/N]")
            self.entry_silomer_faktor1.delete(0, 'end')
            self.entry_silomer_faktor1.insert(0, self.nastavitve["f kladivo"])

            self.entry_osnovna_frekvenca.delete(0,"end")
            self.entry_osnovna_frekvenca.insert(
                0, self.nastavitve["osnovna frekvenca kladivo"])
            self.variable.set(
                self.mozne_frekvence[self.nastavitve["frekvenca vzorčenja kladivo"]])
            self.entry_cas_meritve.delete(0,"end")
            self.entry_cas_meritve.insert(0, self.nastavitve["čas kladivo"])
            self.entry_povprečenje.delete(0,"end")
            self.entry_povprečenje.insert(0, 
                self.nastavitve["vzorcev za povprečenje kladivo"])
            self.entry_povprečenje["state"] = "disabled"
            self.variable_okno_exc.set(self.okna[self.nastavitve["okno exc kladivo"]])
            self.entry_okno_exc_value.delete(0,"end")
            self.entry_okno_exc_value.insert(0,self.nastavitve["value exc kladivo"])
            self.variable_okno_h.set(self.okna[self.nastavitve["okno h kladivo"]])
            self.entry_okno_h_value.delete(0,"end")
            self.entry_okno_h_value.insert(0,self.nastavitve["value h kladivo"])
            self.variable_typ.set(self.types[self.nastavitve["typ kladivo"]])

        else:
            self.entry_silomer_faktor2['state'] = 'normal'
            self.entry_kriterij_mirnosti['state'] = 'disabled'
            self.entry_trigger_value['state'] = 'disabled'
            self.entry_pred_trigger['state'] = 'disabled'
            self.entry_povprečenje["state"] = "normal"

            self.text_kanal_sk.set("Kanal silomera")
            self.entry_silomer_kanal.delete(0, 'end')
            self.entry_silomer_kanal.insert(0, self.nastavitve["ai1"])
            self.text_faktor_sk.set("Faktor silomera [pC/N]")
            self.entry_silomer_faktor1.delete(0, 'end')
            self.entry_silomer_faktor1.insert(0, self.nastavitve["f1"])

            self.entry_osnovna_frekvenca.delete(0,"end")
            self.entry_osnovna_frekvenca.insert(
                0, self.nastavitve["osnovna frekvenca silomer"])
            self.variable.set(
                self.mozne_frekvence[self.nastavitve["frekvenca vzorčenja silomer"]])
            self.entry_cas_meritve.delete(0,"end")
            self.entry_cas_meritve.insert(0, self.nastavitve["čas silomer"])
            self.entry_povprečenje.delete(0,"end")
            self.entry_povprečenje.insert(0, 
                self.nastavitve["vzorcev za povprečenje silomer"])
            self.variable_okno_exc.set(self.okna[self.nastavitve["okno exc silomer"]])
            self.entry_okno_exc_value.delete(0,"end")
            self.entry_okno_exc_value.insert(0,self.nastavitve["value exc silomer"])
            self.variable_okno_h.set(self.okna[self.nastavitve["okno h silomer"]])
            self.entry_okno_h_value.delete(0,"end")
            self.entry_okno_h_value.insert(0,self.nastavitve["value h silomer"])
            self.variable_typ.set(self.types[self.nastavitve["typ silomer"]])

    def poslji_nast_kamere(self):
        iso = int(self.entry_iso.get())
        if iso<0:
            iso=0
        iso = str(iso)
        shs = int(self.entry_shutter_speed.get())
        if shs<1000:
            shs=1000
        shs = str(shs)
        thr = int(self.entry_threshold.get())
        if thr<0:
            thr=0
        elif thr>255:
            thr=255
        thr = str(thr)
        nst = "nst,"+iso+":"+shs+":"+thr
        self.scanner.kamera.pi_kamera.send(bytes(nst, "utf-8"))

    def laser_Ux_gor(self):
        """Sprememba poločaja zrcala na podlagi napetosti za smer x,
         POVEČANJE vrednosti"""
        self.U_x += float(self.entry_U_pomik.get())
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])
        self.text_Ux.set(f"{self.U_x:.2f}")
        self.scanner.laser.premik_volt(self.U_x, self.U_y)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
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
        self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
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
        self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
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
        self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
        self.imgshow()

    def cikelj_nazaj(self):
        """Prikaže se ploti prejšnega cikla"""
        if self.prikazan_cikelj == self.data_ciklov:
            self.spremeni_stanje(self.gumb_cikelj_nasljednji)

        self.prikazan_cikelj -= 1
        self.text_prikazan_cikej.set(self.prikazan_cikelj)

        if self.prikazan_cikelj == 1:
            self.spremeni_stanje(self.gumb_cikelj_prejšnji)

        self.update_grafe(np.linspace(0, 1,len(self.data_exc[0,0])),
                            self.data_exc[self.prikazan_cikelj-1, self.prikazano_mesto-1],
                            self.data_h[self.prikazan_cikelj-1, self.prikazano_mesto-1],
                            self.data_freq,
                            self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def cikelj_naprej(self):
        """Prikažejo se ploti naslednjega cikla"""
        if self.prikazan_cikelj == 1:
            self.spremeni_stanje(self.gumb_cikelj_prejšnji)

        self.prikazan_cikelj += 1
        self.text_prikazan_cikej.set(self.prikazan_cikelj)

        if self.prikazan_cikelj == self.data_ciklov:
            self.spremeni_stanje(self.gumb_cikelj_nasljednji)

        self.update_grafe(np.linspace(0, 1,len(self.data_exc[0,0])),
                            self.data_exc[self.prikazan_cikelj-1, self.prikazano_mesto-1],
                            self.data_h[self.prikazan_cikelj-1, self.prikazano_mesto-1],
                            self.data_freq,
                            self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def mesto_nazaj(self):
        """prikažejo se ploti naslednjega mesta"""
        if self.prikazano_mesto == self.data_mest:
            self.spremeni_stanje(self.gumb_mesto_nasljednje)

        self.prikazano_mesto -= 1
        self.text_prikazano_mesto.set(self.prikazano_mesto)

        if self.prikazano_mesto == 1:
            self.spremeni_stanje(self.gumb_mesto_prejšnje)

        self.update_grafe(np.linspace(0, 1,len(self.data_exc[0,0])),
                            self.data_exc[self.prikazan_cikelj-1, self.prikazano_mesto-1],
                            self.data_h[self.prikazan_cikelj-1, self.prikazano_mesto-1],
                            self.data_freq,
                            self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def mesto_naprej(self):
        """prikažejo se ploti prejšnega mesta"""
        if self.prikazano_mesto == 1:
            self.spremeni_stanje(self.gumb_mesto_prejšnje)

        self.prikazano_mesto += 1
        self.text_prikazano_mesto.set(self.prikazano_mesto)

        if self.prikazano_mesto == self.data_mest:
            self.spremeni_stanje(self.gumb_mesto_nasljednje)

        self.update_grafe(np.linspace(0, 1,len(self.data_exc[0,0])),
                            self.data_exc[self.prikazan_cikelj-1, self.prikazano_mesto-1],
                            self.data_h[self.prikazan_cikelj-1, self.prikazano_mesto-1],
                            self.data_freq,
                            self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def kalibracija_laserja(self):
        """Izvede se ponova kalibracija laseraj na podlagi vpisanih vrednosti"""
        self.scanner.k = self.scanner.laser.kalibracija_basic(
            self.U_x, self.U_y, self.U_x - float(self.entry_U_pomik.get()), self.U_y - float(self.entry_U_pomik.get()))
        self.scanner.položaj_zrcal = np.array([self.U_x- float(self.entry_U_pomik.get()), self.U_y - float(self.entry_U_pomik.get())])
        self.stslabel.configure(text=f"Kalibracija:{self.scanner.k}")

    def zajemanje_slike(self):
        """Konstantno zajemanje slike, funkcija je aktiviran preko threading"""
        while self.continuePlottingImg:
            if self.var_img.get():
                self.image = self.scanner.kamera.req("img")
            else:
                self.image = self.scanner.kamera.req("msk")
            self.image = self.scanner.narisi_tarce(self.image, self.tarče)
            self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
            self.imgshow()

    def change_state(self):
        """za nadzor funkcije self.zajemanje_slike"""
        if self.continuePlottingImg == True:
            self.continuePlottingImg = False
        else:
            self.continuePlottingImg = True

    def shrani_nastavitve(self):
        try:
            fileholder = open(self.nastavitve_file, 'wb')
            pickle.dump(self.nastavitve, fileholder)
            fileholder.close()
            self.stslabel.configure(text="Nastavitve shranjene.")

        except:
            self.stslabel.configure(
                text="NAPKA! Nastavitve NISO sharanjene.")

    def rtd_nast_slike(self):
        self.entry_iso.delete(0,"end")
        self.entry_iso.insert(0,self.backup["iso"])
        self.entry_shutter_speed.delete(0,"end")
        self.entry_shutter_speed.insert(0,self.backup["shutter speed"])
        self.entry_threshold.delete(0,"end")
        self.entry_threshold.insert(0,self.backup["th"])
        self.save_nast_slike()

    def save_nast_slike(self):
        self.nastavitve["iso"] = int(self.entry_iso.get())
        self.nastavitve["shutter speed"] = int(self.entry_shutter_speed.get())
        self.nastavitve["th"] = int(self.entry_threshold.get())
        self.shrani_nastavitve()

    def save_kaibracija(self):
        self.nastavitve["Ux"] = self.U_x
        self.nastavitve["Uy"] = self.U_y
        self.nastavitve["Ukal"] = float(self.entry_kal_premik.get())
        self.nastavitve["Upomik"] = float(self.entry_U_pomik.get())

        self.shrani_nastavitve()

    def rtd_laser(self):
        self.entry_laser_kanal.delete(0,"end")
        self.entry_laser_kanal.insert(0,self.backup["ai0"])
        self.entry_laser_U_max.delete(0,"end")
        self.entry_laser_U_max.insert(0,self.backup["U_max"])
        self.entry_laser_U_min.delete(0,"end")
        self.entry_laser_U_min.insert(0,self.backup["U_min"])
        self.entry_laser_v.delete(0,"end")
        self.entry_laser_v.insert(0,self.backup["las_v"])
        self.entry_laser_delay.delete(0,"end")
        self.entry_laser_delay.insert(0,self.backup["zamik laser"])

        self.save_laser()

    def save_laser(self):
        self.nastavitve["ai0"] = self.entry_laser_kanal.get()
        self.nastavitve["U_max"] = float(self.entry_laser_U_max.get())
        self.nastavitve["U_min"] = float(self.entry_laser_U_min.get())
        self.nastavitve["las_v"] = float(self.entry_laser_v.get())
        self.nastavitve["zamik laser"] = float(self.entry_laser_delay.get())
        self.shrani_nastavitve()

    def rtd_silomer_kladivo(self):
        if self.var_silomer.get():
            self.entry_silomer_kanal.delete(0,"end")
            self.entry_silomer_kanal.insert(0,self.backup["ai1"])
            self.entry_silomer_faktor1.delete(0,"end")
            self.entry_silomer_faktor1.insert(0,self.backup["f1"])
            self.entry_silomer_faktor2.delete(0,"end")
            self.entry_silomer_faktor2.insert(0,self.backup["f2"])
        else:
            self.entry_silomer_kanal.delete(0,"end")
            self.entry_silomer_kanal.insert(0,self.backup["ai2"])
            self.entry_silomer_faktor1.delete(0,"end")
            self.entry_silomer_faktor1.insert(0,self.backup["f kladivo"])
            self.entry_kriterij_mirnosti.delete(0,"end")
            self.entry_kriterij_mirnosti.insert(0,self.backup["kladivo k. mirnosti"])
            self.entry_trigger_value.delete(0,"end")
            self.entry_trigger_value.insert(0,self.backup["trigger value"])
            self.entry_pred_trigger.delete(0,"end")
            self.entry_pred_trigger.insert(0,self.backup["pred trigger"])
        self.save_silomer_kladivo()

    def save_silomer_kladivo(self):
        if self.var_silomer.get():
            self.nastavitve["ai1"]=self.entry_silomer_kanal.get()
            self.nastavitve["f1"]=float(self.entry_silomer_faktor1.get())
            self.nastavitve["f2"]=float(self.entry_silomer_faktor2.get())
        else:
            self.nastavitve["ai2"]=self.entry_silomer_kanal.get()
            self.nastavitve["f kladivo"]=float(self.entry_silomer_faktor1.get())
            self.nastavitve["kladivo k. mirnosti"]= float(self.entry_kriterij_mirnosti.get())
            self.nastavitve["trigger value"] = float(self.entry_trigger_value.get())
            self.nastavitve["pred trigger"] = float(self.entry_pred_trigger.get())
            self.nastavitve["trigger value"] = float(self.entry_trigger_value.get())

        self.shrani_nastavitve()

    def rtd_generator(self):
        self.entry_freq_lower.delete(0,"end")
        self.entry_freq_lower.insert(0,self.backup["low_f"])
        self.entry_freq_upper.delete(0,"end")
        self.entry_freq_upper.insert(0,self.backup["upper_f"])
        self.var_silomer.set(self.backup["gen_on"])
        self.save_generator()

    def save_generator(self):
        self.nastavitve["gen_f"]=self.var_generator.get()
        self.nastavitve["low_f"]=int(self.entry_freq_lower.get())
        self.nastavitve["upper_f"]=int(self.entry_freq_upper.get())
        self.shrani_nastavitve()

    def rtd_zajem(self):
        if self.var_silomer.get():
            self.entry_osnovna_frekvenca.delete(0,"end")
            self.entry_osnovna_frekvenca.insert(0,self.backup["osnovna frekvenca silomer"])
            self.entry_cas_meritve.delete(0,"end")
            self.entry_cas_meritve.insert(0,self.backup["čas silomer"])
            self.entry_povprečenje.delete(0,"end")
            self.entry_povprečenje.insert(0,self.backup["vzorcev za povprečenje silomer"])
            self.entry_okno_exc_value.delete(0,"end")
            self.entry_okno_exc_value.insert(0,self.backup["value exc silomer"])
            self.entry_okno_h_value.delete(0,"end")
            self.entry_okno_h_value.insert(0,self.backup["value h silomer"])
        else:
            self.entry_osnovna_frekvenca.delete(0,"end")
            self.entry_osnovna_frekvenca.insert(0,self.backup["osnovna frekvenca kladivo"])
            self.entry_cas_meritve.delete(0,"end")
            self.entry_cas_meritve.insert(0,self.backup["čas kladivo"])
            self.entry_povprečenje.delete(0,"end")
            self.entry_povprečenje.insert(0,self.backup["vzorcev za povprečenje kladivo"])
            self.entry_okno_exc_value.delete(0,"end")
            self.entry_okno_exc_value.insert(0,self.backup["value exc kladivo"])
            self.entry_okno_h_value.delete(0,"end")
            self.entry_okno_h_value.insert(0,self.backup["value h kladivo"])
        self.entry_ime_datoteke.delete(0,"end")
        self.entry_ime_datoteke.insert(0,self.backup["file_name"])
        self.entry_path.delete(0,"end")
        self.entry_path.insert(0,self.backup["dir"])
        self.save_zajem()

    def save_zajem(self):
        if self.var_silomer.get():
            self.nastavitve["osnovna frekvenca silomer"] = int(self.entry_osnovna_frekvenca.get())
            self.nastavitve["frekvenca vzorčenja silomer"] = self.mozne_frekvence.index(self.variable.get())
            self.nastavitve["čas silomer"] = float(self.entry_cas_meritve.get())
            self.nastavitve["vzorcev za povprečenje silomer"] = int(self.entry_povprečenje.get())
            self.nastavitve["okno exc silomer"] = self.okna.index(self.variable_okno_exc.get())
            self.nastavitve["value exc silomer"] = float(self.entry_okno_exc_value.get())
            self.nastavitve["okno h silomer"] = self.okna.index(self.variable_okno_h.get())
            self.nastavitve["value h silomer"] = float(self.entry_okno_h_value.get())
        else:
            self.nastavitve["osnovna frekvenca kladivo"] = int(self.entry_osnovna_frekvenca.get())
            self.nastavitve["frekvenca vzorčenja kladivo"] = self.mozne_frekvence.index(self.variable.get())
            self.nastavitve["čas kladivo"] = float(self.entry_cas_meritve.get())
            self.nastavitve["vzorcev za povprečenje kladivo"]= int(self.entry_povprečenje.get())
            self.nastavitve["okno exc kladivo"] = self.okna.index(self.variable_okno_exc.get())
            self.nastavitve["value exc kladivo"]= float(self.entry_okno_exc_value.get())
            self.nastavitve["okno h kladivo"] = self.okna.index(self.variable_okno_h.get())
            self.nastavitve["value h kladivo"]=float(self.entry_okno_h_value.get())
        self.nastavitve["file_name"]=self.entry_ime_datoteke.get()
        self.nastavitve["dir"]=self.entry_path.get()
        self.shrani_nastavitve()

    def rtd_pi(self):
        """Naložijo se prvotni podatki za RPi"""
        self.vnos1.delete(0, "end")
        self.vnos2.delete(0, "end")
        self.vnos3.delete(0, "end")
        self.vnos4.delete(0, "end")
        self.vnos5.delete(0, "end")

        self.vnos1.insert(0, self.nastavitve["hostname"])
        self.vnos2.insert(0, self.nastavitve["port"])
        self.vnos3.insert(0, self.nastavitve["username"])
        self.vnos4.insert(0, self.nastavitve["password"])
        self.vnos5.insert(0, self.nastavitve["skripta"])
        self.save_pi()
        self.stslabel.configure(text="Nastavitve RPi ponastavljene.")

    def save_pi(self):
        """Shranjevanje podatkov za RPi v datoteko"""
        self.nastavitve["hostname"] = str(self.vnos1.get())
        self.nastavitve["port"] = int(self.vnos2.get())
        self.nastavitve["username"] = str(self.vnos3.get())
        self.nastavitve["password"] = str(self.vnos4.get())
        self.nastavitve["skripta"] = str(self.vnos5.get())
        self.shrani_nastavitve()

    def rtd_ni(self):
        """Naložijo se prvotni podatki za merilne kartice"""
        self.vnos1_ni.delete(0, "end")
        self.vnos2_ni.delete(0, "end")
        self.vnos3_ni.delete(0, "end")
        self.vnos4_ni.delete(0, "end")

        self.vnos1_ni.insert(0, self.nastavitve["ao0"])
        self.vnos2_ni.insert(0, self.nastavitve["ao1"])
        self.vnos3_ni.insert(0, self.nastavitve["ai0"])
        self.vnos3_ni.insert(0, self.nastavitve["ai1"])

        self.save_ni()

        self.stslabel.configure(
            text="Nastavitve merilne kartice ponastavljene.")

    def save_ni(self):
        """shranjevanje podatkov merilnih kartic v datoteko"""
        self.nastavitve["ao0"] = str(self.vnos1_ni.get())
        self.nastavitve["ao1"] = str(self.vnos2_ni.get())
        self.nastavitve["ao2"] = str(self.vnos3_ni.get())

        self.shrani_nastavitve()

    def on_click(self, event):
        """Funkcija ki opazuje in določa kaj se zgodi ko kliknemo na sliko"""
        if self.continuePlottingImg==False:
            if event.inaxes is not None:
                tarča = [event.xdata, event.ydata]
                if self.tocke_ROI==-1:
                    self.tarče.append(tarča)
                    self.image = self.scanner.kamera.req("img")
                    self.image = self.scanner.narisi_tarce(self.image, self.tarče)
                    self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
                    self.imgshow()
                    self.stslabel.configure(text=f"Prikaz slike. Dodana tarča {len(self.tarče)}.")
                else:
                    self.ROI_kordinate.append(tarča)
                    self.stslabel.configure(text=f"Prikaz slike. Dodana ROI točka {len(self.ROI_kordinate)}.")
                    if len(self.ROI_kordinate)==2:
                        self.ROI_kordinate=[[int(self.ROI_kordinate[0][0]),int(self.ROI_kordinate[0][1])],
                                            [int(self.ROI_kordinate[1][0]),int(self.ROI_kordinate[1][1])]]
                        x1=str(min(self.ROI_kordinate[0][0],self.ROI_kordinate[1][0]))
                        y1=str(min(self.ROI_kordinate[0][1],self.ROI_kordinate[1][1]))
                        x2=str(max(self.ROI_kordinate[0][0],self.ROI_kordinate[1][0]))
                        y2=str(max(self.ROI_kordinate[0][1],self.ROI_kordinate[1][1]))
                        ROI="roi,"+x1+":"+y1+":"+x2+":"+y2
                        print(ROI)
                        self.scanner.kamera.pi_kamera.send(bytes(ROI, "utf-8"))
                        self.tocke_ROI=-1
                    self.image = self.scanner.kamera.req("img")
                    self.image = self.scanner.narisi_tarce(self.image, self.tarče)
                    self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
                    self.imgshow()
            else:
                self.stslabel.configure(
                    text="Clicked ouside axes bounds but inside plot window")
        else:
            self.stslabel.configure(
                    text="Za dolločitev tarče je potrebno izklopiti pretakanje slike")

    def imgshow(self):
        """Funkcija skrbi za prikaz slike pridobljene iz RPi"""
        self.ax.cla()
        if len(np.shape(self.image))>2:
            self.ax.imshow(self.image[:, :, ::-1])
        else:
            self.ax.imshow(self.image,cmap='Greys_r')
        self.canvas.draw()

    def izbriši_zadnjo_tarčo(self):
        """S seznama tarč se izbriše zadnja tarča"""
        if len(self.tarče) != 0:
            self.tarče = self.tarče[:-1]
            self.stslabel.configure(text="Tarča odstranjena")
            self.image = self.scanner.kamera.req("img")
            if len(self.tarče) != 0:
                self.image = self.scanner.narisi_tarce(self.image, self.tarče)
                self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
                self.imgshow()
                #self.fig.canvas.callbacks.connect('button_press_event', on_click)
            else:
                self.stslabel.configure(text="Vse tarče odstranjene")
                self.imgshow()

    def izbriši_vse_tarče(self):
        """pobriše se celoten seznam tarč"""
        self.tarče = []
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
        self.stslabel.configure(text="Vse tarče odstranjene")
        self.imgshow()

    # _______________________________Threading______________________________________
    """funkcije so namenjene temu da bi stvari lahko delovale sočasno."""

    def gh1(self):
        self.change_state()
        threading.Thread(target=self.zajemanje_slike).start()

    def zacni_meritev(self):
        threading.Thread(target=self.real_zacni_meritev).start()

    # ____________________________________________________________________________
    def korekcija_tarč(self,se_dovoljen_premik=1):
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

    def pomik_na_tarčo(self,i):
        self.korekcija_tarč()
        self.image = self.scanner.namesto(self.tarče[i])
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.image = self.scanner.narisi_ROI(self.image, self.ROI_kordinate)
        self.imgshow()

    def pomik_na_nasledno_tarčo(self):
        """Funkcija pomakne laser na naslednjo tarčo v seznamu tarč"""
        if len(self.tarče)>0:
            self.na_tarči += 1
            i = self.na_tarči % len(self.tarče)
            self.pomik_na_tarčo(i)
            self.stslabel.configure(text=f"Premik na tarčo {i+1}.")
        else:
            self.stslabel.configure(text=f"Izbrana ni nobena tarča.")

    def pomik_na_prejšno_tarčo(self):
        """Funkcija pomakne laser na prejšnjo tarčo v seznamu tarč"""
        if len(self.tarče)>0:
            self.na_tarči -= 1
            i = self.na_tarči % len(self.tarče)
            self.pomik_na_tarčo(i)
            self.stslabel.configure(text=f"Premik na tarčo {i+1}.")
        else:
            self.stslabel.configure(text=f"Izbrana ni nobena tarča.")

    def update_grafe(self, t, exc, h, f, frf):
        """Posodobijo se vis grafi-- za enkrat je tako da se posodobijo samo FRF"""
        

        # plotanje za laser
        self.axes_meritev[0].cla()
        self.axes_meritev[0].plot(t, h)
        self.axes_meritev[0].set_title("Laser")
        self.axes_meritev[0].set_xlabel("Čas [s]")
        self.axes_meritev[0].set_ylabel("Hitreost [mm/s]")
        self.axes_meritev[0].grid()
        # plotanje za silomer
        self.axes_meritev[1].cla()
        self.axes_meritev[1].plot(t, exc)
        self.axes_meritev[1].set_title("Silomer")
        self.axes_meritev[1].set_xlabel("Čas [s]")
        self.axes_meritev[1].set_ylabel("Sila [N]")
        self.axes_meritev[1].grid()

        self.graph_meritve.draw()

        # FRF
        self.axes_FRF[0].cla()
        self.axes_FRF[0].plot(f, np.abs(frf))
        self.axes_FRF[0].set_title("FRF")
        self.axes_FRF[0].set_xlabel("Frekvenca [Hz]")
        self.axes_FRF[0].set_ylabel("(mm/s)/N")
        self.axes_FRF[0].set_yscale("log")
        self.axes_FRF[0].grid()
        self.axes_FRF[0].set_xlim(int(self.entry_skala_min.get()),int(self.entry_skala_max.get()))
        # fazni zamik
        self.axes_FRF[1].cla()
        self.axes_FRF[1].plot(f, np.arctan2(
            np.imag(frf), np.real(frf)))
        self.axes_FRF[1].set_title("Fazni zamik")
        self.axes_FRF[1].set_xlabel("Frekvenca [Hz]")
        self.axes_FRF[1].set_ylabel("kot [rad]")
        # self.axes_FRF[1].set_ylim(-np.pi/2,np.pi/2)
        self.axes_FRF[1].grid()
        self.axes_FRF[1].set_xlim(int(self.entry_skala_min.get()),int(self.entry_skala_max.get()))

        self.graph_FRF.draw()

    def pridobi_zahteve_merjenja(self):
        self.scanner.meritev.ch_laser = str(self.entry_laser_kanal.get())
        self.scanner.meritev.ch_silomer = str(self.entry_silomer_kanal.get())
        self.scanner.meritev.frekvenca = float(self.variable.get())
        self.scanner.meritev.čas = float(self.entry_cas_meritve.get())
        self.scanner.meritev.U_max = float(self.entry_laser_U_max.get())
        self.scanner.meritev.U_min = float(self.entry_laser_U_min.get())
        self.scanner.meritev.las_v = float(self.entry_laser_v.get())
        self.scanner.meritev.f1 = float(self.entry_silomer_faktor1.get())
        if self.var_kladivo.get() == True:
            self.scanner.meritev.f2 = 1.0
        else:
            self.scanner.meritev.f2 = float(self.entry_silomer_faktor2.get())

#______________________Funkcije_vezane_na_pridobivanje_meritev____________________
    def naredi_okna(self):
        self.okno_exc=self.variable_okno_exc.get()
        if self.okno_exc!=None:
            self.okno_exc=self.okno_exc+":"+self.entry_okno_exc_value.get()
        
        self.okno_h=self.variable_okno_h.get()
        if self.okno_h!=None:
            self.okno_h=self.okno_h+":"+self.entry_okno_h_value.get()

    def meritev_trenutnega_mesta(self):
        self.prekini = False
        if self.var_kladivo.get() == True:
            self.meritev_trenutnega_mesta_kladivo()
        else:
            self.meritev_trenutnega_mesta_silomer()

    def meritev_trenutnega_mesta_silomer(self):
        self.pridobi_zahteve_merjenja()
        self.t = np.linspace(0, self.scanner.meritev.st_vzorcev /
                             self.scanner.meritev.frekvenca, self.scanner.meritev.st_vzorcev)
        self.thread_meritev_silomer=threading.Thread(target=self.meritev_s_silomerom)
        self.thread_meritev_silomer.start()

    def meritev_s_silomerom(self):
        """Funkcija za izvajanje meritve, aktiviran je preko threading"""
        if self.ena_metirev and self.var_generator.get():
            self.generator_update()
            self.generator_signalov.pripravi_signal()
            self.generator_signalov.task.start()
            time.sleep(5)
        toc = time.time()
        for i in range(int(self.entry_povprečenje.get())):
            if i == 0:
                self.exc, self.h, self.t = self.scanner.meritev.naredi_meritev()
                self.frf = FRF(sampling_freq=1/self.t[1],
                               exc=self.exc,
                               resp=self.h,
                               resp_type='v',
                               frf_type=self.variable_typ.get(),
                               exc_window=self.variable_okno_exc.get(),
                               resp_window=self.variable_okno_h.get(),
                               n_averages=int(self.entry_povprečenje.get()),
                               resp_delay=float(self.entry_laser_delay.get()))

                self.update_grafe(self.t, self.exc, self.h,
                                  self.frf.get_f_axis(), self.frf.get_FRF())
                self.tabControltab3.select(self.tab3tab2)

            else:
                self.exc, self.h, self.t = self.scanner.meritev.naredi_meritev()
                self.frf.add_data(self.exc, self.h)
                self.update_grafe(self.t, self.exc, self.h,
                                  self.frf.get_f_axis(), self.frf.get_FRF())
                self.tabControltab3.select(self.tab3tab2)

            if self.prekini:
                self.stslabel.configure(text="Meritev prekinjena")
                if self.ena_metirev:
                    self.prekini = False
                break
        
        self.update_grafe(self.t, self.exc, self.h,
                          self.frf.get_f_axis(), self.frf.get_FRF())
        self.tabControltab3.select(self.tab3tab2)
        print(time.time()-toc)
        if self.var_save.get() == 1:
            if self.append_to_file == False:
                file = self.entry_path.get()+"/"+self.entry_ime_datoteke.get()
                np.save(file, self.frf.get_FRF())
        if self.ena_metirev and self.var_generator.get():
            self.generator_signalov.task.close()
            
    def meritev_trenutnega_mesta_kladivo(self):
        self.pridobi_zahteve_merjenja()
        self.scanner.meritev.continuous_bool = True
        self.scanner.meritev.connect()
        self.t = np.linspace(0, self.scanner.meritev.st_vzorcev /
                             self.scanner.meritev.frekvenca, self.scanner.meritev.st_vzorcev)
        self.triger = False
        self.serija0 = False
        self.objek_je_mirn = False
        #self.result_available = threading.Event()
        self.thread_meritev_kladivo=threading.Thread(target=self.meritev_s_kladivom)
        self.thread_meritev_kladivo.start()

    def meritev_s_kladivom(self):
        """funkcija za pretočno zajemanje podatkov"""
        
        while True:
            triger_val = float(self.entry_trigger_value.get())
            pogoj_mirnosti = float(self.entry_kriterij_mirnosti.get())
            pred_trigger = float(self.entry_pred_trigger.get())
            abs_v = float(self.entry_laser_v.get())

            if self.objek_je_mirn == False:
                samplesAvailable = self.scanner.meritev.task._in_stream.avail_samp_per_chan
                if(samplesAvailable >= self.scanner.meritev.st_vzorcev):
                    data = self.scanner.meritev.task.read(
                        self.scanner.meritev.st_vzorcev)
                    self.exc = np.array(data[1])
                    self.h = np.array(
                        data[0])*self.scanner.meritev.las_v/self.scanner.meritev.U_max
                    self.update_grafe(self.t, self.exc, self.h, 1, 1)
                    self.tabControltab3.select(self.tab3tab1)
                    # shranjevanje za serijo-1
                    self.exc_m1 = np.array(self.exc)
                    self.h_m1 = np.array(self.h)
                    v_max = np.max(self.h)
                    v_min = np.min(self.h)
                    abs_v = v_max-v_min
                    self.stslabel.configure(text=f"Objekt se mora umiriti. Trenutno max razlika hitrosti {abs_v}")

            # določanje ali je objekt dovolj miren
            if abs_v <= pogoj_mirnosti*float(self.entry_laser_v.get()) or self.objek_je_mirn:

                # zapiska samo prvič ko zazna da je objekt dovolj miren
                if self.objek_je_mirn == False:
                    self.beep_pripravljen_za_meritev()
                    self.objek_je_mirn = True
                    self.stslabel.configure(text="Objekt je dovolj miren za udarec")

                # pobiranje podatkov iz kartice serija0
                samplesAvailable = self.scanner.meritev.task._in_stream.avail_samp_per_chan
                if(samplesAvailable >= self.scanner.meritev.st_vzorcev):
                    data = self.scanner.meritev.task.read(
                        self.scanner.meritev.st_vzorcev)
                    self.exc = np.array(data[1])
                    self.h = np.array(
                        data[0])*self.scanner.meritev.las_v/self.scanner.meritev.U_max
                    self.update_grafe(self.t, self.exc, self.h, 1, 1)
                    self.tabControltab3.select(self.tab3tab1)

                    # ko je enkrat sprožen da je sprožen celotn loop
                    if np.max(self.exc) > triger_val:
                        self.triger = True

                    if self.triger:
                        #Če serija0 še in zabeležena jo zabeleži drugače, naredi meritev in frf
                        if self.serija0==False:
                            self.exc0 = np.concatenate((self.exc_m1, self.exc), axis=None)
                            self.h0 = np.concatenate((self.h_m1, self.h), axis=None)
                            self.serija0=True
                        else:
                            #serija0 je bila za beležena potrebno je posneti še serijo 1
                            self.exc = np.concatenate((self.exc0, self.exc), axis=None)
                            self.h = np.concatenate((self.h0, self.h), axis=None)
                            # nadalna obdelava - iskanje kje je bil sprožen triger
                            indeks_triger = np.argmax(self.exc > float(triger_val))
                            # vračanje nazaj od sprožitve 0.01s
                            nazaj = int(pred_trigger*self.scanner.meritev.frekvenca)
                            st_vzorcev = int(
                                self.scanner.meritev.frekvenca*float(self.entry_cas_meritve.get()))
                            # obrezovanje na meritev
                            self.exc = self.exc[indeks_triger -
                                                nazaj:indeks_triger-nazaj+st_vzorcev]
                            self.h = self.h[indeks_triger -
                                            nazaj:indeks_triger-nazaj+st_vzorcev]
                            # naredi se objekt frf
                            self.naredi_okna()
                            self.frf = FRF(sampling_freq=1/self.t[1],
                                           exc=self.exc,
                                           resp=self.h,
                                           resp_type='v',
                                           frf_type=self.variable_typ.get(),
                                           exc_window=self.okno_exc,
                                           resp_window=self.okno_h,
                                           n_averages=int(
                                               self.entry_povprečenje.get()),
                                           resp_delay=float(self.entry_laser_delay.get()))
                            self.update_grafe(
                                self.t, self.exc, self.h, self.frf.get_f_axis(), self.frf.get_FRF())
                            self.tabControltab3.select(self.tab3tab2)
                            #prevei še če je dvojni udarec
                            if  self.frf.is_data_ok(self.exc,self.h):
                                self.prekini = True
                                self.stslabel.configure(text="Meritev je ok.")
                                if self.var_save.get() == 1:
                                    if self.append_to_file == False:
                                        file = self.entry_path.get()+"/"+self.entry_ime_datoteke.get()
                                        np.save(file, self.frf.get_FRF())    
                            else:
                                self.beep_double()
                                self.stslabel.configure(text="Meritev ni dobra.")
                            self.triger = False
                            self.serija0 = False
                            self.objek_je_mirn = False

                    else:
                        #če triger ni sprožen shrani serijo kot m1 (beri kot -1)
                        self.exc_m1 = np.array(self.exc)
                        self.h_m1 = np.array(self.h)
                        

            if self.prekini:
                self.stslabel.configure(text="Meritev prekinjena")
                if self.ena_metirev:
                    self.prekini = False
                break

        #počaka se še da se objek umiri predno se premakne na naslednjo pozicijo
        while True:
            pogoj_mirnosti = float(self.entry_kriterij_mirnosti.get())
            abs_v = float(self.entry_laser_v.get())

            if self.objek_je_mirn == False:
                samplesAvailable = self.scanner.meritev.task._in_stream.avail_samp_per_chan
                if(samplesAvailable >= self.scanner.meritev.st_vzorcev):
                    data = self.scanner.meritev.task.read(
                        self.scanner.meritev.st_vzorcev)
                    h = np.array(
                        data[0])*self.scanner.meritev.las_v/self.scanner.meritev.U_max
                    abs_v = np.max(h)-np.min(h)
                    self.stslabel.configure(text=f"Objekt se mora umiriti. Pred premikom na naslednje mesto.")

            # določanje ali je objekt dovolj miren
            if abs_v <= 1.5*pogoj_mirnosti*float(self.entry_laser_v.get()) or self.objek_je_mirn:
                self.scanner.meritev.disconnect()
                break
            
    def real_zacni_meritev(self):
        """Funkcija naredi določeno število ciklov meritev, laser se pomakne do označene terče kjer se 
        izvede meritev"""

        if self.var_silomer.get() and self.var_generator.get():
            self.generator_update()
            self.generator_signalov.pripravi_signal()
            self.generator_signalov.task.start()
            time.sleep(5)
            self.ena_metirev=False
        if self.var_save.get() == 1:
            self.append_to_file = True
            file = self.entry_path.get()+"/"+self.entry_ime_datoteke.get()+".npy"
            file_opend = open(file, 'wb')

        try:
            ciklov = self.entry_stevilo_ciklov.get()
            ciklov = int(ciklov)
            self.stslabel.configure(text=f"Izvajanje {ciklov} ciklov")
        except:
            ciklov = 1
        frf_data = []
        exc_data = []
        h_data = []
        self.prikazan_cikelj=0
        for c in range(ciklov):
            self.prikazan_cikelj+=1
            self.text_prikazan_cikej.set(self.prikazan_cikelj)
            frf_cikla = []
            exc_cikla = []
            h_cikla = []
            self.prikazano_mesto=0
            for i in range(len(self.tarče)):
                self.prikazano_mesto+=1
                self.text_prikazano_mesto.set(self.prikazano_mesto)
                self.stslabel.configure(text=f"Izvajanje {c+1} cikla, meritev {i+1} vzorca.")
                while True:
                    self.pomik_na_tarčo(i)
                    self.meritev_trenutnega_mesta()
                    dp=1
                    if self.var_kladivo.get():
                        dp=5
                        self.thread_meritev_kladivo.join()
                    else:
                        self.thread_meritev_silomer.join()
                    if self.korekcija_tarč(dp)==False:
                        break
                frf_cikla.append(self.frf.get_FRF()[1:])
                exc_cikla.append(self.exc)
                h_cikla.append(self.h)
                if self.prekini == True:
                    break
            frf_data.append(frf_cikla)
            exc_data.append(np.array(exc_cikla))
            h_data.append(np.array(h_cikla))
            if self.prekini == True:
                break
        # seznam frekvenc za FRF
        self.data_freq = self.frf.get_f_axis()[1:]
        #frf-ji [[frfji_cikla_1],[frfji_cikla_2],[frfji_cikla_3]]
        self.data_frf = np.array(frf_data)
        # self.data_exc je [[exc_cikelj_1],[exc_cikej_2],[exc_cikelj_3]...]
        self.data_exc = np.array(exc_data)
        # enako kakor za exc
        self.data_h = np.array(h_data)
        self.data_ciklov = np.shape(self.data_frf)[0]
        self.data_mest = np.shape(self.data_frf)[1]
        self.kontrola_gumbov_podatkov()
        print(np.shape(frf_data),np.shape(frf_cikla))
        if self.var_save.get() == 1:
            np.save(file_opend, (self.data_freq,
                                 self.data_frf, self.data_exc, self.data_h))
            self.append_to_file = False
        if self.var_silomer.get() and self.var_generator.get():
            self.generator_signalov.task.close()
            self.ena_metirev=True

    def prekini_meritev(self):
        """Funkcija namenjena kontroli funkcije self.zacni_meritev"""
        self.prekini = True
        print("prekini")

# ________________________________Beeps__________________________________________
    def beep_pripravljen_za_meritev(self):
        frequency1 = 2500  # Set Frequency To 2500 Hertz
        duration1 = 400  # Set Duration To 1000 ms == 1 second
        frequency2 = 6000  # Set Frequency To 2500 Hertz
        duration2 = 200  # Set Duration To 1000 ms == 1 second
        winsound.Beep(frequency1, duration1)
        winsound.Beep(frequency2, duration2)

    def beep_double(self):
        frequency1 = 3000  # Set Frequency To 2500 Hertz
        duration1 = 200  # Set Duration To 1000 ms == 1 second
        frequency2 = 1500  # Set Frequency To 2500 Hertz
        duration2 = 600  # Set Duration To 1000 ms == 1 second
        winsound.Beep(frequency1, duration1)
        winsound.Beep(frequency2, duration2)

    def beep_start(self):
        frequency = 1900
        duration = 250
        winsound.Beep(frequency, duration)
        winsound.Beep(frequency, duration)

if __name__ == '__main__':
    root = tk.Tk()
    my_gui = GUI_MSLK(root)
    root.mainloop()

    # zapiranje povezav
    my_gui.scanner.kamera.disconnect()
