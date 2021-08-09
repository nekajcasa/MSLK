# -*- coding: utf-8 -*-
"""
Created on Thu Jul 22 09:23:32 2021

@author: Student

Program za generiranje datoteke z nastavitvami.

"""
import pickle

dictionary_data = {"Ux": 2.7,
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
                   "f kladivo":2.273,
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
pickle.dump(dictionary_data, file)
file.close()

a_file = open("nastavitve.pkl", "rb")
output = pickle.load(a_file)
print(output)
file.close()
