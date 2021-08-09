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


class GUI_MSLK:

    def __init__(self, master):

        self.master = master
        self.master.title("MSLK")
        self.master.iconbitmap("./files/logo.ico")
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        self.master.geometry("%dx%d+0+0" % (w-100, h-100))

        # status bar
        frame_info = tk.Frame(self.master, relief=tk.SUNKEN)
        frame_info.pack(fill=tk.X, side=tk.BOTTOM)
        self.stslabel = tk.Label(
            frame_info, anchor=tk.W, text="Program priprvljen. Potrebno je vspostaviti povezavo s RPi")
        self.stslabel.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(
            frame_info, orient=tk.HORIZONTAL, length=100,  mode='indeterminate')


##################################_Load_data_########################################

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
                               "U_max": 4,
                               "U_min": -4,
                               "las_v": 20.0,
                               "zamik laser": 0.00124,
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

#####################################################################################
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

    # definiranje zavihkov
        tabControl = ttk.Notebook(self.master)

        self.tab1 = ttk.Frame(tabControl)
        self.tab2 = ttk.Frame(tabControl)
        self.tab3 = ttk.Frame(tabControl)

        tabControl.add(self.tab1, text='Kalibracija')
        tabControl.add(self.tab2, text='Nastavitve')
        tabControl.add(self.tab3, text='Meritve')
        tabControl.pack(expand=1, fill="both")

    # tab1
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

    # tab2
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

        # tab 3
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

        # nastavitve silomera
        frame_silomer_nastavitve = tk.Frame(
            master=self.tab3, relief=tk.RAISED, borderwidth=1, width=100, height=100)
        frame_silomer_nastavitve.grid(row=1, column=0)

        label_silomer_nastavitve = tk.Label(
            frame_silomer_nastavitve, text="Nastavitve silomera")
        label_silomer_nastavitve.grid(row=0, column=0, columnspan=2)

        label_silomer_kanal = tk.Label(
            frame_silomer_nastavitve, text="Kanal silomera")
        label_silomer_kanal.grid(row=1, column=0)

        self.entry_silomer_kanal = tk.Entry(master=frame_silomer_nastavitve)
        self.entry_silomer_kanal.grid(row=1, column=1)
        self.entry_silomer_kanal.insert(0, self.nastavitve["ai1"])

        label_silomer_fakror1 = tk.Label(
            frame_silomer_nastavitve, text="Faktor silomera [pC/N]")
        label_silomer_fakror1.grid(row=2, column=0)

        self.entry_silomer_faktor1 = tk.Entry(master=frame_silomer_nastavitve)
        self.entry_silomer_faktor1.grid(row=2, column=1)
        self.entry_silomer_faktor1.insert(0, self.nastavitve["f1"])

        label_silomer_fakror2 = tk.Label(
            frame_silomer_nastavitve, text="Faktor nabojnega ojačevalnika [mV/pC]")
        label_silomer_fakror2.grid(row=3, column=0)

        self.entry_silomer_faktor2 = tk.Entry(master=frame_silomer_nastavitve)
        self.entry_silomer_faktor2.grid(row=3, column=1)
        self.entry_silomer_faktor2.insert(0, self.nastavitve["f2"])

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
            frame_gumbi_tab3, text="Meritev trenutnega mesta", command=self.metitev_trenutnega_mesta)  # moras se naredit
        self.gumb_ena_meritev.grid(row=1, column=0, columnspan=2)

        self.label_stevilo_ciklov = tk.Label(
            frame_gumbi_tab3, text='Število ciklov:')
        self.label_stevilo_ciklov.grid(row=2, column=0)

        self.entry_stevilo_ciklov = tk.Entry(frame_gumbi_tab3)
        self.entry_stevilo_ciklov.grid(row=2, column=1)
        self.entry_stevilo_ciklov.insert(0, self.nastavitve["število ciklov"])

        self.gumb_začni_meritev = tk. Button(
            frame_gumbi_tab3, text="Začni cikelj meritev", command=self.gui_handler)
        self.gumb_začni_meritev.grid(row=3, column=0)

        self.gumb_prekini_meritev = tk. Button(
            frame_gumbi_tab3, text="Prekini cikelj", command=self.prekini_meritev)
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

# ===============================Funkcije=========================================
    def connect(self):

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

                # vspostavitev povezave s RPi
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
        if self.povezava_vspostavljena_boolean == True:
            self.scanner.kamera.disconnect()
            self.stslabel.configure(text="Povezava na RPi prekinjena")
            self.povezava_vspostavljena_boolean = False
            self.switch()
        else:
            self.stslabel.configure(text="Povezava je že prekinjena")

    def izračun_možnih_frekvenc(self):
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
        file_path = tk.filedialog.askdirectory()
        self.entry_path.delete(0, 'end')
        self.entry_path.insert(0, file_path)
        self.cb_save_file.select()

    def load_file(self):
        self.loaded_data_filename = tk.filedialog.askopenfilenames(
            filetypes=(('numpy files', '*.npy'), ('All files', '*.*')))
        self.text_data_for_plot.set(self.loaded_data_filename)
        print(self.loaded_data_filename[0])
        self.data_freq, self.data_frf, self.data_exc, self.data_h = np.load(
            self.loaded_data_filename[0], allow_pickle=True)
        self.data_ciklov = np.shape(self.data_frf)[0]
        self.data_mest = np.shape(self.data_frf)[1]

        self.kontrola_gumbov_podatkov()

        self.update_grafe([], 1, 1, self.data_freq,
                          self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def kontrola_gumbov_podatkov(self):
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
    # def lastne_oblike(self):
        # frf = []
        # for i in range(len(self.tarče)):
        #     cilj = self.tarče[i]
        #     self.image = self.scanner.namesto(cilj)
        #     self.image = self.scanner.kamera.req("img")
        #     self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        #     self.imgshow()
        #     self.stslabel.configure(text=f"Meritev na {i+1}. mestu.")
        #     frf_izmerjeni = self.metitev_trenutnega_mesta()
        #     frf.append(frf_izmerjeni.get_FRF()[1:])
        #     if self.prekini == True:
        #         break
        # frf = np.array(frf)
        # freq = frf_izmerjeni.get_f_axis()[1:]

    def doloci_pole(self):
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
        # self.acc.print_modal_data()
        #frf_rec, modal_const = acc.get_constants(whose_poles='own', FRF_ind='all')
        self.axes_lastne_oblike.cla()
        for i in range(3):
            self.axes_lastne_oblike.plot(self.acc.normal_mode()[:, i], label=f"{i+1}. lastna oblika")
        self.axes_lastne_oblike.legend()
        self.stslabel.configure(text=f"Plotanje lastnih oblik končnao")
        self.tabControltab3.select(self.tab3tab3)

    def spremeni_stanje(self, b1):  # ,b2):
        if b1["state"] == "normal":
            b1["state"] = "disabled"
            #b2["text"] = "enable"
        else:
            b1["state"] = "normal"
            #b2["text"] = "disable"

    def switch(self):
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

    def laser_Ux_gor(self):
        self.U_x += float(self.entry_U_pomik.get())
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])
        self.text_Ux.set(f"{self.U_x:.2f}")
        self.scanner.laser.premik_volt(self.U_x, self.U_y)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()

    def laser_Ux_dol(self):
        self.U_x -= float(self.entry_U_pomik.get())
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])
        self.text_Ux.set(f"{self.U_x:.2f}")
        self.scanner.laser.premik_volt(self.U_x, self.U_y)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()

    def laser_Uy_gor(self):
        self.U_y += float(self.entry_U_pomik.get())
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])
        self.text_Uy.set(f"{self.U_y:.2f}")
        self.scanner.laser.premik_volt(self.U_x, self.U_y)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()

    def laser_Uy_dol(self):
        self.U_y -= float(self.entry_U_pomik.get())
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])
        self.text_Uy.set(f"{self.U_y:.2f}")
        self.scanner.laser.premik_volt(self.U_x, self.U_y)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()

    def cikelj_nazaj(self):
        if self.prikazan_cikelj == self.data_ciklov:
            self.spremeni_stanje(self.gumb_cikelj_nasljednji)

        self.prikazan_cikelj -= 1
        self.text_prikazan_cikej.set(self.prikazan_cikelj)

        if self.prikazan_cikelj == 1:
            self.spremeni_stanje(self.gumb_ciklj_prejšnji)

        self.update_grafe([], 1, 1, self.data_freq,
                          self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def cikelj_naprej(self):
        if self.prikazan_cikelj == 1:
            self.spremeni_stanje(self.gumb_ciklj_prejšnji)

        self.prikazan_cikelj += 1
        self.text_prikazan_cikej.set(self.prikazan_cikelj)

        if self.prikazan_cikelj == self.data_ciklov:
            self.spremeni_stanje(self.gumb_cikelj_nasljednji)

        self.update_grafe([], 1, 1, self.data_freq,
                          self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def mesto_nazaj(self):
        if self.prikazano_mesto == self.data_mest:
            self.spremeni_stanje(self.gumb_mesto_nasljednje)

        self.prikazano_mesto -= 1
        self.text_prikazano_mesto.set(self.prikazano_mesto)

        if self.prikazano_mesto == 1:
            self.spremeni_stanje(self.gumb_mesto_prejšnje)

        self.update_grafe([], 1, 1, self.data_freq,
                          self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def mesto_naprej(self):
        if self.prikazano_mesto == 1:
            self.spremeni_stanje(self.gumb_mesto_prejšnje)

        self.prikazano_mesto += 1
        self.text_prikazano_mesto.set(self.prikazano_mesto)

        if self.prikazano_mesto == self.data_mest:
            self.spremeni_stanje(self.gumb_mesto_nasljednje)

        self.update_grafe([], 1, 1, self.data_freq,
                          self.data_frf[self.prikazan_cikelj-1, self.prikazano_mesto-1])

    def kalibracija_laserja(self):
        self.scanner.k = self.scanner.laser.kalibracija_basic(
            self.U_x, self.U_y, self.U_x - float(self.entry_U_pomik.get()), self.U_y - float(self.entry_U_pomik.get()))
        self.scanner.položaj_zrcal = np.array([self.U_x, self.U_y])

    def gh1(self):
        self.change_state()
        threading.Thread(target=self.zajemanje_slike).start()

    def zajemanje_slike(self):
        while self.continuePlottingImg:
            self.image = self.scanner.kamera.req("img")
            self.image = self.scanner.narisi_tarce(self.image, self.tarče)
            self.imgshow()

    def change_state(self):

        if self.continuePlottingImg == True:
            self.continuePlottingImg = False
        else:
            self.continuePlottingImg = True

    def rtd_pi(self):
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
        self.fig.clear()
        self.fig.add_subplot(111).imshow(self.image[:, :, ::-1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab1)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, rowspan=10)

    def izbriši_zadnjo_tarčo(self):
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
        self.tarče = []
        self.image = self.scanner.kamera.req("img")
        self.stslabel.configure(text="Vse tarče odstranjene")
        self.imgshow()

# _______________________________Threading_______________________________________________

    def gui_handler_grafi(self, exc, h, t, frf):
        threading.Thread(target=self.update_grafe(exc, h, t, frf)).start()

    def gui_handler(self):
        self.prekini = False
        threading.Thread(target=self.zacni_meritev()).start()

    def gui_handler_zajem(self):
        threading.Thread(target=self.zajem_podatkov()).start()

    def zajem_podatkov(self):
        self.exc, self.h, self.t = self.scanner.meritev.naredi_meritev()

    def metitev_trenutnega_mesta(self):
        threading.Thread(target=self.real_meritev_trenutnega_mesta()).start()

# _______________________________Ostale funkcije________________________________________

    def pomik_na_nasledno_tarčo(self):
        self.na_tarči += 1
        i = self.na_tarči % len(self.tarče)
        cilj = self.tarče[i]
        self.image = self.scanner.namesto(cilj)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()
        self.stslabel.configure(text=f"Premik na tarčo {i+1}.")

    def pomik_na_prejšno_tarčo(self):
        self.na_tarči -= 1
        i = self.na_tarči % len(self.tarče)
        cilj = self.tarče[i]
        self.image = self.scanner.namesto(cilj)
        self.image = self.scanner.kamera.req("img")
        self.image = self.scanner.narisi_tarce(self.image, self.tarče)
        self.imgshow()
        self.stslabel.configure(text=f"Premik na tarčo {i+1}.")

    def update_grafe(self, t, exc, h, f, frf):
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

    def real_meritev_trenutnega_mesta(self):
        self.scanner.meritev.ch_laser = str(self.entry_laser_kanal.get())
        self.scanner.meritev.ch_silomer = str(self.entry_silomer_kanal.get())
        self.scanner.meritev.frekvenca = float(self.variable.get())
        self.scanner.meritev.čas = float(self.entry_cas_meritve.get())
        self.scanner.meritev.U_max = float(self.entry_laser_U_max.get())
        self.scanner.meritev.U_min = float(self.entry_laser_U_min.get())
        self.scanner.meritev.las_v = float(self.entry_laser_v.get())
        self.scanner.meritev.f1 = float(self.entry_silomer_faktor1.get())
        self.scanner.meritev.f2 = float(self.entry_silomer_faktor2.get())

        toc = time.time()
        for i in range(int(self.entry_povprečenje.get())):
            if i == 0:
                self.gui_handler_zajem()
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
                self.gui_handler_zajem()
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
    #     return frf
    # #threading.Thread(target=real_meritev_trenutnega_mesta).start()
    # with concurrent.futures.ThreadPoolExecutor() as executor:
    #     future = executor.submit(real_meritev_trenutnega_mesta)
    #     return_value = future.result()
    # return return_value

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
                self.metitev_trenutnega_mesta()
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
                                 self.data_frf, self.data_exc, self.data_h))
            self.append_to_file = False

    def prekini_meritev(self):
        self.prekini = True
        print("prekini")


root = tk.Tk()
my_gui = GUI_MSLK(root)
root.mainloop()

# zapiranje povezav
my_gui.scanner.kamera.disconnect()