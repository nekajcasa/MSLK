# -*- coding: utf-8 -*-
"""
Created on Thu Jul 22 09:23:32 2021

@author: Student

Program za generiranje datoteke z nastavitvami.

"""
import pickle

dictionary_data = {"slika/mask":True,
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

file = open("nastavitve.pkl", "wb")
pickle.dump(dictionary_data, file)
file.close()

a_file = open("nastavitve.pkl", "rb")
output = pickle.load(a_file)
print(output)
file.close()
