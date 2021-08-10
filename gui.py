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
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        self.master.geometry("%dx%d+0+0" % (w-100, h-100))

#_________________________________Status_bar__________________________________________
        frame_info = tk.Frame(self.master, relief=tk.SUNKEN)
        frame_info.pack(fill=tk.X, side=tk.BOTTOM)
        self.stslabel = tk.Label(
            frame_info, anchor=tk.W, text="Program priprvljen. Potrebno je vspostaviti povezavo s RPi")
        self.stslabel.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(
            frame_info, orient=tk.HORIZONTAL, length=100,  mode='indeterminate')
#_________________________________Load_data___________________________________________

        self.nastavitve_file = "files/nastavitve.pkl"
        try:
            fileholder = open(nastavitve_file, "rb")
            self.nastavitve = pickle.load(fileholder)
            fileholder.close()
        except:
            self.nastavitve = {"Ux": 2.7,
                               "Uy": 1.8,
                               "Ukal": 0.3,
                               "Upomik": 0.3,
                               "hostname": "pi-kamera",
                               "port": 22,
                               "username": "pi",
                               "password": "pi",
                               "skripta": "Desktop/laserV3.py",
                               "ao0": "cDAQ10Mod1/ao0",
                               "ao1": "cDAQ10Mod1/ao1",
                               "ai0": "cDAQ10Mod3/ai0",
                               "ai1": "cDAQ10Mod3/ai1",
                               "ai2": "cDAQ10Mod3/ai3",
                               "U_max": 4,
                               "U_min": -4,
                               "las_v": 20.0,
                               "zamik laser": 0.00124,
                               "start silomer/kladivo": True,
                               "f kladivo": 2.273,
                               "f1": 4.034,
                               "f2": 9.923,
                               "osnovna frekvenca": 13107200,
                               "frekvenca vzorčenja": 4,
                               "čas": 1,
                               "vzorcev za povprečenje": 5,
                               "okno exc": 2,
                               "okno h": 2,
                               "typ": 2,
                               "file_name": "meritev",
                               "dir": "C:",
                               "število ciklov": 1}
            file = open("nastavitve.pkl", "wb")
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
        self.povezava_vspostavljena_boolean = False
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
        self.gumb_izbriši_zadnjo_tarčo = tk.Button(
            self.tab1, text="Izbriši zadnjo tarčo", command=self.izbriši_zadnjo_tarčo)
        self.gumb_izbriši_zadnjo_tarčo.grid(row=0, column=1)

        self.gumb_izbriši_vse_tarče = tk.Button(
            self.tab1, text="Izbriši vse tarče", command=self.izbriši_vse_tarče)
        self.gumb_izbriši_vse_tarče.grid(row=0, column=2)

        self.gumb_vspostavi_povezavo = tk.Button(
            self.tab1, text="Vspostavi povezavo", command=self.connect, bg="#89eb34")
        self.gumb_vspostavi_povezavo.grid(row=1, column=1)
        self.spremeni_stanje(self.gumb_vspostavi_povezavo)

        self.gumb_prekini_povezavo = tk.Button(
            self.tab1, text="Prekini povezavo", command=self.disconnect, bg="#ec123e")
        self.gumb_prekini_povezavo.grid(row=1, column=2)

        self.gumb_pretakanje_slike = tk.Button(
            self.tab1, text="Pretakanje slike \n start/stop", command=self.gh1, bg="red", fg="white")
        self.gumb_pretakanje_slike.grid(row=2, column=1, columnspan=2)

    # kontrole kalibracije
        frame_kontorla_kalibracije = tk.Frame(
            master=self.tab1, relief=tk.RAISED, borderwidth=1, width=100, height=100)
        frame_kontorla_kalibracije.grid(row=3, column=1, columnspan=2)

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
        # zadodt
        self.gumb_shrani_kal = tk.Button(
            frame_joystick, text="Shrani", bg="#eb4034")
        self.gumb_shrani_kal.grid(row=3, column=1)

    # priprava za plotanje slike iz kamere
        self.fig = Figure(figsize=(8, 6))
        self.fig.add_subplot(111)
        self.fig.tight_layout()
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab1)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, rowspan=10)
        self.fig.canvas.callbacks.connect('button_press_event', self.on_click)
#___________________________________tab_2_____________________________________________
    # Polje za nastavitev RPi
        frame_pi_nastavitve = tk.Frame(
            master=self.tab2, relief=tk.RAISED, borderwidth=1, width=100, height=100)
        frame_pi_nastavitve.grid(row=0, column=0)
        label = tk.Label(master=frame_pi_nastavitve,
                         text="Nastavitve Raspbrerry Pi")
        label.grid(row=0, column=0, columnspan=2)

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

        # pi_nast_gumb3 = tk.Button(master = frame_pi_nastavitve, text = "Prekini in vspostavi povezavo")
        # pi_nast_gumb3.grid(row=7,column=0,columnspan=3)

    # Nastavitve merilnih kartic
        frame_ni_nastavitve = tk.Frame(
            master=self.tab2, relief=tk.RAISED, borderwidth=1, width=100, height=100)
        frame_ni_nastavitve.grid(row=0, column=1)
        label = tk.Label(master=frame_ni_nastavitve,
                         text="Merilna kartica izhodni kanali")
        label.grid(row=0, column=0, columnspan=2)

        nast1_ni = tk.Label(master=frame_ni_nastavitve,
                            text="Izhodni kanal 1: ")
        nast1_ni.grid(row=1, column=0)
        self.vnos1_ni = tk.Entry(master=frame_ni_nastavitve)
        self.vnos1_ni.grid(row=1, column=1)
        self.vnos1_ni.insert(0, self.nastavitve["ao0"])

        nast2_ni = tk.Label(master=frame_ni_nastavitve,
                            text="Izhodni kanal 2: ")
        nast2_ni.grid(row=2, column=0)
        self.vnos2_ni = tk.Entry(master=frame_ni_nastavitve)
        self.vnos2_ni.grid(row=2, column=1)
        self.vnos2_ni.insert(0, self.nastavitve["ao1"])

        nast3_ni = tk.Label(master=frame_ni_nastavitve,
                            text="Vhodni kanal 1: ")
        nast3_ni.grid(row=3, column=0)
        self.vnos3_ni = tk.Entry(master=frame_ni_nastavitve)
        self.vnos3_ni.grid(row=3, column=1)
        self.vnos3_ni.insert(0, self.nastavitve["ai0"])

        nast4_ni = tk.Label(master=frame_ni_nastavitve,
                            text="Vhodni kanal 2: ")
        nast4_ni.grid(row=4, column=0)
        self.vnos4_ni = tk.Entry(master=frame_ni_nastavitve)
        self.vnos4_ni.grid(row=4, column=1)
        self.vnos4_ni.insert(0, self.nastavitve["ai1"])

        ni_nast_gumb1 = tk.Button(
            master=frame_ni_nastavitve, text="Reset to default", command=self.rtd_ni)
        ni_nast_gumb1.grid(row=5, column=0)

        ni_nast_gumb2 = tk.Button(
            master=frame_ni_nastavitve, text="Save", command=self.save_ni)
        ni_nast_gumb2.grid(row=5, column=1)
#___________________________________tab_3_____________________________________________
        # nastavitve laserja
        frame_laser_nastavitve = tk.Frame(
            master=self.tab3, relief=tk.RAISED, borderwidth=1, width=100, height=100)
        frame_laser_nastavitve.grid(row=0, column=0)

        label_laser_nastavitve = tk.Label(
            frame_laser_nastavitve, text="Nastavitve laserja")
        label_laser_nastavitve.grid(row=0, column=0, columnspan=2)

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
            frame_laser_nastavitve, text="Občutljivost [mm/s]")
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

        # nastavitve silomera/kladiva
        frame_silomer_nastavitve = tk.Frame(
            master=self.tab3, relief=tk.RAISED, borderwidth=1, width=100, height=100)
        frame_silomer_nastavitve.grid(row=1, column=0)

        label_silomer_nastavitve = tk.Label(
            frame_silomer_nastavitve, text="Nastavitve silomera / kladiva")
        label_silomer_nastavitve.grid(row=0, column=0, columnspan=2)

        self.nastavitve["start silomer/kladivo"]
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

        self.urejanje_silomer_kladivo()

        # nastavitve zajema
        frame_zajem_nastavitve = tk.Frame(
            master=self.tab3, relief=tk.RAISED, borderwidth=1)
        frame_zajem_nastavitve.grid(row=2, column=0)

        label_zajem_nastavitve = tk.Label(
            frame_zajem_nastavitve, text="Nastavitve meritev")
        label_zajem_nastavitve.grid(row=0, column=0, columnspan=2)

        label_zajem_nastavitve = tk.Label(
            frame_zajem_nastavitve, text="Frekvenca merilne kartice [Hz]:")
        label_zajem_nastavitve.grid(row=1, column=0)

        self.entry_osnovna_frekvenca = tk.Entry(frame_zajem_nastavitve)
        self.entry_osnovna_frekvenca.grid(row=1, column=1)
        self.entry_osnovna_frekvenca.insert(
            0, self.nastavitve["osnovna frekvenca"])

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
        self.variable.set(
            self.mozne_frekvence[self.nastavitve["frekvenca vzorčenja"]])

        self.om_frekvenca = tk.OptionMenu(
            frame_zajem_nastavitve, self.variable, *self.mozne_frekvence)
        self.om_frekvenca.grid(row=3, column=1)

        label_cas_meritve = tk.Label(
            frame_zajem_nastavitve, text="Čas meritve [s]")
        label_cas_meritve.grid(row=4, column=0)

        self.entry_cas_meritve = tk.Entry(master=frame_zajem_nastavitve)
        self.entry_cas_meritve.grid(row=4, column=1)
        self.entry_cas_meritve.insert(0, self.nastavitve["čas"])

        label_povprečenje = tk.Label(
            frame_zajem_nastavitve, text="Vzorcev za povprečenje")
        label_povprečenje.grid(row=5, column=0)

        self.entry_povprečenje = tk.Entry(master=frame_zajem_nastavitve)
        self.entry_povprečenje.grid(row=5, column=1)
        self.entry_povprečenje.insert(
            0, self.nastavitve["vzorcev za povprečenje"])

        # Kontrola FRF
        label_okno_exc = tk.Label(frame_zajem_nastavitve, text="Okno exc")
        label_okno_exc.grid(row=6, column=0)

        self.okna = ['None', 'Hann', 'Hamming', 'Force',
                     'Exponential', 'Bartlett', 'Blackman', 'Kaiser']

        self.variable_okno_exc = tk.StringVar(self.master)
        self.variable_okno_exc.set(self.okna[self.nastavitve["okno exc"]])

        self.om_okno_exc = tk.OptionMenu(
            frame_zajem_nastavitve, self.variable_okno_exc, *self.okna)
        self.om_okno_exc.grid(row=6, column=1)

        label_okno_h = tk.Label(frame_zajem_nastavitve, text="Okno h")
        label_okno_h.grid(row=7, column=0)

        self.variable_okno_h = tk.StringVar(self.master)
        self.variable_okno_h.set(self.okna[self.nastavitve["okno h"]])

        self.om_okno_h = tk.OptionMenu(
            frame_zajem_nastavitve, self.variable_okno_h, *self.okna)
        self.om_okno_h.grid(row=7, column=1)

        label_typ = tk.Label(frame_zajem_nastavitve, text="Typ")
        label_typ.grid(row=8, column=0)

        self.types = ['H1', 'H2', 'Hv', 'vector', 'ODS']

        self.variable_typ = tk.StringVar(self.master)
        self.variable_typ.set(self.types[self.nastavitve["typ"]])

        self.om_typ = tk.OptionMenu(
            frame_zajem_nastavitve, self.variable_typ, *self.types)
        self.om_typ.grid(row=8, column=1)

        self.var_save = tk.IntVar()
        self.cb_save_file = tk.Checkbutton(
            frame_zajem_nastavitve, text='Shranjuj podatke', variable=self.var_save, onvalue=1, offvalue=0)
        self.cb_save_file.grid(row=9, column=0, columnspan=2)

        label_ime_datoteke = tk.Label(
            frame_zajem_nastavitve, text="Ime datoteke")
        label_ime_datoteke.grid(row=10, column=0)

        self.entry_ime_datoteke = tk.Entry(master=frame_zajem_nastavitve)
        self.entry_ime_datoteke.grid(row=10, column=1)
        self.entry_ime_datoteke.insert(0, self.nastavitve["file_name"])

        button_path = tk.Button(frame_zajem_nastavitve,
                                text="Pot do datoteke", command=self.dir_path)
        button_path.grid(row=11, column=0)

        self.entry_path = tk.Entry(master=frame_zajem_nastavitve)
        self.entry_path.grid(row=11, column=1)
        self.entry_path.insert(0, self.nastavitve["dir"])

        # plotanje
        frame_tab3_plotanje = tk.Frame(
            master=self.tab3, relief=tk.RAISED, borderwidth=1)
        frame_tab3_plotanje.grid(row=0, column=1, rowspan=4)

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
            nrows=2, ncols=1, figsize=(8, 6))
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
            side=tk.BOTTOM, fill=tk.BOTH, expand=True)
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
            frame_gumbi_tab3, text="Začni meritev", command=self.gui_handler)
        self.gumb_začni_meritev.grid(row=3, column=0)

        self.gumb_prekini_meritev = tk. Button(
            frame_gumbi_tab3, text="Prekini meritev", command=self.prekini_meritev)
        self.gumb_prekini_meritev.grid(row=3, column=1)

        self.gumb_doloci_pole = tk. Button(
            frame_gumbi_tab3, text="Določi pole", command=self.doloci_pole)
        self.gumb_doloci_pole.grid(row=4, column=0)
        self.spremeni_stanje(self.gumb_doloci_pole)

        self.gumb_plotaj_lastne = tk. Button(
            frame_gumbi_tab3, text="Plotaj lastne oblike", command=self.lastne_oblike_plot)
        self.gumb_plotaj_lastne.grid(row=4, column=1)
        self.spremeni_stanje(self.gumb_plotaj_lastne)

        # Loadanje in upravljanje s ploti
        frame_upravlanje_plotov_tab3 = tk.Frame(
            master=self.tab3, relief=tk.RAISED, borderwidth=1)
        frame_upravlanje_plotov_tab3.grid(row=1, column=2)

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

        self.gumb_ciklj_prejšnji = tk.Button(
            frame_upravlanje_plotov_tab3, text="<", command=self.cikelj_nazaj)
        self.gumb_ciklj_prejšnji.grid(row=4, column=0)
        self.spremeni_stanje(self.gumb_ciklj_prejšnji)

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

        self.switch()
        # self.spremeni_stanje(self.gumb_plotaj_lastne)
# =================================Funkcije===========================================
    def connect(self):
        """funkcija skrbi za vspostavitev povezave z RPi"""
        def real_connect():

            if self.povezava_vspostavljena_boolean == False:
                self.stslabel.configure(text="Vpostavljanje povezave")
                Pi = MSLK.RPi(hostname=self.nastavitve["hostname"],
                              port=self.nastavitve["port"],
                              username=self.nastavitve["username"],
                              password=self.nastavitve["password"],
                              skripta=self.nastavitve["skripta"])
                pi_kamera = MSLK.Camera(Pi)
                laser = MSLK.LaserHead(
                    pi_kamera, ch1=self.nastavitve["ao0"], ch2=self.nastavitve["ao1"])
                meritev = MSLK.Meritev()
                položaj_zrcal = np.array([self.U_x, self.U_y])
                self.scanner = MSLK.Scanner(
                    pi_kamera, laser, meritev, položaj_zrcal, None)

                # vspostavitev povezave z RPi
                self.scanner.kamera.connect()
                # kalibracija laserske glave
                self.kalibracija_laserja()
                self.stslabel.configure(text="Povezava na RPi vspostavljena")

                self.image = self.scanner.kamera.req("img")
                self.image = self.scanner.narisi_tarce(self.image, self.tarče)
                self.imgshow()

                self.povezava_vspostavljena_boolean = True
                self.switch()
        threading.Thread(target=real_connect).start()

    def disconnect(self):
        """funkcija za prekinitev povezave z RPi"""
        if self.povezava_vspostavljena_boolean == True:
            self.scanner.kamera.disconnect()
            self.stslabel.configure(text="Povezava na RPi prekinjena")
            self.povezava_vspostavljena_boolean = False
            self.switch()
        else:
            self.stslabel.configure(text="Povezava je že prekinjena")

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

        self.kontrola_gumbov_podatkov()

        self.update_grafe([], 1, 1, self.data_freq,
                          self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def kontrola_gumbov_podatkov(self):
        """Funkcija nadoruje da se gubi za prehanjanje med različnimi podatki pravilno 
        izklapljajo in uklapljajo"""
        self.prikazan_cikelj = 1
        self.prikazano_mesto = 1
        self.text_prikazan_cikej.set(self.prikazan_cikelj)
        self.text_prikazano_mesto.set(self.prikazano_mesto)
        self.tabControltab3.select(self.tab3tab2)

        # zamrzne se vse gumbe
        if self.data_loaded == True:
            self.gumb_ciklj_prejšnji["state"] = "disabled"
            self.gumb_cikelj_nasljednji["state"] = "disabled"
            self.gumb_mesto_prejšnje["state"] = "disabled"
            self.gumb_mesto_nasljednje["state"] = "disabled"
            self.data_loaded = False

        # odmrzne se relavantne gumbe
        if self.data_ciklov > 1 and self.data_mest > 1:
            self.spremeni_stanje(self.gumb_cikelj_nasljednji)
            self.spremeni_stanje(self.gumb_mesto_nasljednje)
        elif self.data_ciklov > 1:
            self.spremeni_stanje(self.gumb_cikelj_nasljednji)
        elif self.data_mest > 1:
            self.spremeni_stanje(self.gumb_mesto_nasljednje)

        self.data_loaded = True
        self.gumb_doloci_pole["state"] = "normal"
        self.stslabel.configure(text=f"Podatki pridobljeni, določiti je potrebno pole.")

    def doloci_pole(self):
        """Odpre se novo okno v s pomočjo pyEMA kjer se določiko poli"""
        self.acc = pyEMA.Model(frf=self.data_frf[self.prikazan_cikelj-1],
                               freq=self.data_freq,
                               lower=10,
                               upper=float(self.variable.get())/2,
                               pol_order_high=60)
        self.acc.get_poles()
        self.stslabel.configure(text=f"Poli določeni, možno je plotanje lastnih oblik.")
        if self.poli_določeni == False:
            self.spremeni_stanje(self.gumb_plotaj_lastne)
        self.poli_določeni = True
        self.acc.select_poles()

    def lastne_oblike_plot(self):
        """Funkcija skrbi za plotanje lastnih oblik s pomočjo pyEMA"""
        # self.acc.print_modal_data()
        #frf_rec, modal_const = acc.get_constants(whose_poles='own', FRF_ind='all')
        self.axes_lastne_oblike.cla()
        for i in range(3):
            self.axes_lastne_oblike.plot(self.acc.normal_mode()[:, i], label=f"{i+1}. lastna oblika")
        self.axes_lastne_oblike.legend()
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
        self.spremeni_stanje(self.gumb_vspostavi_povezavo)
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
        if self.var_kladivo.get() == True:
            self.entry_silomer_faktor2['state'] = 'disabled'
            self.text_kanal_sk.set("Kanal kladiva")
            self.entry_silomer_kanal.delete(0, 'end')
            self.entry_silomer_kanal.insert(0, self.nastavitve["ai2"])
            self.text_faktor_sk.set("Faktor kladiva [mV/N]")
            self.entry_silomer_faktor1.delete(0, 'end')
            self.entry_silomer_faktor1.insert(0, self.nastavitve["f kladivo"])

        else:
            self.entry_silomer_faktor2['state'] = 'normal'
            self.text_kanal_sk.set("Kanal silomera")
            self.entry_silomer_kanal.delete(0, 'end')
            self.entry_silomer_kanal.insert(0, self.nastavitve["ai1"])
            self.text_faktor_sk.set("Faktor silomera [pC/N]")
            self.entry_silomer_faktor1.delete(0, 'end')
            self.entry_silomer_faktor1.insert(0, self.nastavitve["f1"])

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

    def cikelj_nazaj(self):
        """Prikaže se ploti prejšnega cikla"""
        if self.prikazan_cikelj == self.data_ciklov:
            self.spremeni_stanje(self.gumb_cikelj_nasljednji)

        self.prikazan_cikelj -= 1
        self.text_prikazan_cikej.set(self.prikazan_cikelj)

        if self.prikazan_cikelj == 1:
            self.spremeni_stanje(self.gumb_ciklj_prejšnji)

        self.update_grafe([], 1, 1, self.data_freq,
                          self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def cikelj_naprej(self):
        """Prikažejo se ploti naslednjega cikla"""
        if self.prikazan_cikelj == 1:
            self.spremeni_stanje(self.gumb_ciklj_prejšnji)

        self.prikazan_cikelj += 1
        self.text_prikazan_cikej.set(self.prikazan_cikelj)

        if self.prikazan_cikelj == self.data_ciklov:
            self.spremeni_stanje(self.gumb_cikelj_nasljednji)

        self.update_grafe([], 1, 1, self.data_freq,
                          self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def mesto_nazaj(self):
        """prikažejo se ploti naslednjega mesta"""
        if self.prikazano_mesto == self.data_mest:
            self.spremeni_stanje(self.gumb_mesto_nasljednje)

        self.prikazano_mesto -= 1
        self.text_prikazano_mesto.set(self.prikazano_mesto)

        if self.prikazano_mesto == 1:
            self.spremeni_stanje(self.gumb_mesto_prejšnje)

        self.update_grafe([], 1, 1, self.data_freq,
                          self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def mesto_naprej(self):
        """prikažejo se ploti prejšnega mesta"""
        if self.prikazano_mesto == 1:
            self.spremeni_stanje(self.gumb_mesto_prejšnje)

        self.prikazano_mesto += 1
        self.text_prikazano_mesto.set(self.prikazano_mesto)

        if self.prikazano_mesto == self.data_mest:
            self.spremeni_stanje(self.gumb_mesto_nasljednje)

        self.update_grafe([], 1, 1, self.data_freq,
                          self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def kalibracija_laserja(self):
        """Izvede se ponova kalibracija laseraj na podlagi vpisanih vrednosti"""
        self.scanner.k = self.scanner.laser.kalibracija_basic(
            self.U_x, self.U_y, self.U_x - float(self.entry_U_pomik.get()), self.U_y - float(self.entry_U_pomik.get()))
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])
        self.stslabel.configure(text=f"Kalibracija:{self.scanner.k}")

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
        try:
            fileholder = open(self.nastavitve_file, 'wb')
            pickle.dump(self.nastavitve, fileholder)
            fileholder.close()
            self.stslabel.configure(text="Nastavitve RPi shranjene.")

        except:
            self.stslabel.configure(
                text="NAPKA! Nastavitve RPi NISO sharanjene.")

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
        self.nastavitve["ai0"] = str(self.vnos3_ni.get())
        self.nastavitve["ai1"] = str(self.vnos4_ni.get())

        try:
            fileholder = open(self.nastavitve_file, 'wb')
            pickle.dump(self.nastavitve, fileholder)
            fileholder.close()
            self.stslabel.configure(
                text="Nastavitve merilne kartice shranjene.")

            self.scanner.laser.ch1 = self.nastavitve["ao0"]
            self.scanner.laser.ch2 = self.nastavitve["ao1"]

        except:
            self.stslabel.configure(
                text="NAPKA! Nastavitve merilne kartice NISO sharanjene.")

    def on_click(self, event):
        """Funkcija ki opazuje in določa kaj se zgodi ko kliknemo na sliko"""
        if event.inaxes is not None:
            tarča = [event.xdata, event.ydata]
            self.tarče.append(tarča)
            self.image = cv2.imread("img1_2_1.jpg")
            self.image = self.scanner.kamera.req("img")
            self.image = self.scanner.narisi_tarce(self.image, self.tarče)
            self.imgshow()
            self.stslabel.configure(text=f"Prikaz slike. Dodana tarča {len(self.tarče)}.")
        else:
            self.stslabel.configure(
                text="Clicked ouside axes bounds but inside plot window")
        print(self.tarče)

    def imgshow(self):
        """Funkcija skrbi za prikaz slike pridobljene iz RPi"""
        self.fig.clear()
        self.fig.add_subplot(111).imshow(self.image[:, :, ::-1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab1)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, rowspan=10)

    def izbriši_zadnjo_tarčo(self):
        """S seznama tarč se izbriše zadnja tarča"""
        if len(self.tarče) != 0:
            self.tarče = self.tarče[:-1]
            self.stslabel.configure(text="Tarča odstranjena")
            self.image = self.scanner.kamera.req("img")
            if len(self.tarče) != 0:
                self.image = self.scanner.narisi_tarce(self.image, self.tarče)
                self.imgshow()
                #self.fig.canvas.callbacks.connect('button_press_event', on_click)
            else:
                self.stslabel.configure(text="Vse tarče odstranjene")
                self.imgshow()

    def izbriši_vse_tarče(self):
        """pobriše se celoten seznam tarč"""
        self.tarče = []
        self.image = self.scanner.kamera.req("img")
        self.stslabel.configure(text="Vse tarče odstranjene")
        self.imgshow()

    # _______________________________Threading______________________________________
    """funkcije so namenjene temu da bi stvari lahko delovale sočasno, večino 
    jih ne deluje pravilno..."""

    def gh1(self):
        self.change_state()
        threading.Thread(target=self.zajemanje_slike).start()

    def gui_handler_grafi(self, exc, h, t, frf):
        threading.Thread(target=self.update_grafe(exc, h, t, frf)).start()

    def gui_handler(self):
        self.prekini = False
        threading.Thread(target=self.zacni_meritev()).start()

    def meritev_trenutnega_mesta(self):
        if self.var_kladivo.get() == True:
            self.meritev_trenutnega_mesta_kladivo()
        else:
            threading.Thread(target=self.meritev_trenutnega_mesta_silomer()).start()

    # ____________________________________________________________________________

    def pomik_na_nasledno_tarčo(self):
        """Funkcija pomakne laser na naslednjo tarčo v seznamu tarč"""
        self.na_tarči += 1
        i = self.na_tarči % len(self.tarče)
        cilj = self.tarče[i]
        self.image = self.scanner.namesto(cilj)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()
        self.stslabel.configure(text=f"Premik na tarčo {i+1}.")

    def pomik_na_prejšno_tarčo(self):
        """Funkcija pomakne laser na prejšnjo tarčo v seznamu tarč"""
        self.na_tarči -= 1
        i = self.na_tarči % len(self.tarče)
        cilj = self.tarče[i]
        self.image = self.scanner.namesto(cilj)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()
        self.stslabel.configure(text=f"Premik na tarčo {i+1}.")

    def update_grafe(self, t, exc, h, f, frf):
        """Posodobijo se vis grafi-- za enkrat je tako da se posodobijo samo FRF"""
        # začasno!!!!!!!
        if len(t) != 0:
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
        # fazni zamik
        self.axes_FRF[1].cla()
        self.axes_FRF[1].plot(f, np.arctan2(
            np.imag(frf), np.real(frf)))
        self.axes_FRF[1].set_title("Fazni zamik")
        self.axes_FRF[1].set_xlabel("Frekvenca [Hz]")
        self.axes_FRF[1].set_ylabel("kot [rad]")
        # self.axes_FRF[1].set_ylim(-np.pi/2,np.pi/2)
        self.axes_FRF[1].grid()

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

    def meritev_trenutnega_mesta_silomer(self):
        """Funkcija za izvajanje meritve, aktiviran je preko threading"""
        self.pridobi_zahteve_merjenja()
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

            else:
                self.exc, self.h, self.t = self.scanner.meritev.naredi_meritev()
                self.frf.add_data(self.exc, self.h)
                self.update_grafe(self.t, self.exc, self.h,
                                  self.frf.get_f_axis(), self.frf.get_FRF())

        self.update_grafe(self.t, self.exc, self.h,
                          self.frf.get_f_axis(), self.frf.get_FRF())
        print(time.time()-toc)
        if self.var_save.get() == 1:
            if self.append_to_file == False:
                file = self.entry_path.get()+"/"+self.entry_ime_datoteke.get()
                np.save(file, self.frf.get_FRF())

    

        if self.var_kladivo.get() == True:
            self.začni_zajem_kladivo()
        else:
            self.meritev_s_silomerom()

    def meritev_trenutnega_mesta_kladivo(self):
        self.pridobi_zahteve_merjenja()
        self.scanner.meritev.continuous_bool = True
        self.scanner.meritev.connect()
        self.t = np.linspace(0, self.scanner.meritev.st_vzorcev /
                             self.scanner.meritev.frekvenca, self.scanner.meritev.st_vzorcev)
        print(len(self.t))
        self.meritev_s_kladivom()
        self.triger = False
        self.serija0 = False
        self.objek_je_mirn = False

    def meritev_s_kladivom(self):
        """funkcija za pretočno zajemanje podatkov"""
        # potrebno dodat za določanje preko GUI
        triger_val = 2.2
        pogoj_mirnosti = 0.25
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
                        nazaj = int(0.01*self.scanner.meritev.frekvenca)
                        st_vzorcev = int(
                            self.scanner.meritev.frekvenca*float(self.entry_cas_meritve.get()))
                        # obrezovanje na meritev
                        self.exc = self.exc[indeks_triger -
                                            nazaj:indeks_triger-nazaj+st_vzorcev]
                        self.h = self.h[indeks_triger -
                                        nazaj:indeks_triger-nazaj+st_vzorcev]
                        # naredi se objekt frf
                        self.frf = FRF(sampling_freq=1/self.t[1],
                                       exc=self.exc,
                                       resp=self.h,
                                       resp_type='v',
                                       frf_type=self.variable_typ.get(),
                                       exc_window=self.variable_okno_exc.get(),
                                       resp_window=self.variable_okno_h.get(),
                                       n_averages=int(
                                           self.entry_povprečenje.get()),
                                       resp_delay=float(self.entry_laser_delay.get()))

                        self.update_grafe(
                            self.t, self.exc, self.h, self.frf.get_f_axis(), self.frf.get_FRF())
                        
                        #prevei še če je dvojni udarec
                        if  self.frf.is_data_ok(self.exc,self.h):
                            self.prekini = True
                            self.stslabel.configure(text="Meritev je ok.")    
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
            self.scanner.meritev.disconnect()
            self.triger = False
            self.serija0 = False
            self.objek_je_mirn = False
        else:
            self.master.after(10, self.meritev_s_kladivom)

    def zacni_meritev(self):
        """Funkcija naredi določeno število ciklov meritev, laser se pomakne do označene terče kjer se 
        izvede meritev"""
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
        for c in range(ciklov):
            frf_c = []
            for i in range(len(self.tarče)):
                cilj = self.tarče[i]
                self.image = self.scanner.namesto(cilj)
                self.image = self.scanner.kamera.req("img")
                self.image = self.scanner.narisi_tarce(self.image, self.tarče)
                self.imgshow()
                self.stslabel.configure(text=f"Izvajanje {c+1} cikla, meritev {i+1} vzorca.")
                self.meritev_trenutnega_mesta()
                frf_c.append(self.frf.get_FRF()[1:])
                if self.prekini == True:
                    break
            frf_data.append(np.array(frf_c))
            exc_data.append(self.exc)
            h_data.append(self.h)
            self.data_frf = np.array(frf_c)
            if self.prekini == True:
                break
        # seznam frekvenc za FRF
        self.data_freq = self.frf.get_f_axis()[1:]
        #frf-ji [[frfji_cikla_1],[frfji_cikla_2],[frfji_cikla_3]]
        self.data_frf = np.array(frf_data)
        # self.data_exc je [[exc_cikelj_1],[exc_cikej_2],[exc_cikelj_3]...]
        self.data_exc = exc_data
        self.data_h = h_data
        self.data_ciklov = np.shape(self.data_frf)[0]
        self.data_mest = np.shape(self.data_frf)[1]
        self.kontrola_gumbov_podatkov()

        if self.var_save.get() == 1:
            np.save(file_opend, (self.data_freq,
                                 self.data_frf))  # , self.data_exc, self.data_h))
            self.append_to_file = False

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


root = tk.Tk()
my_gui = GUI_MSLK(root)
root.mainloop()

# zapiranje povezav
my_gui.scanner.kamera.disconnect()
