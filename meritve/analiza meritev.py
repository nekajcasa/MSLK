# -*- coding: utf-8 -*-
"""
Created on Wed Aug  4 14:31:01 2021

@author: Student
"""
import numpy as np
import matplotlib.pyplot as plt
import pyEMA
from pyFRF import FRF

frekvenca, frf_gui, exc, h = np.load("meritev_kladivo_kovinska_2.npy", allow_pickle=True)
t=np.linspace(0, 1,len(exc[0,0]))

meritev=0
#['None', 'Hann', 'Hamming', 'Force',
# 'Exponential', 'Bartlett', 'Blackman', 'Kaiser']
frf= FRF(sampling_freq=1/t[1],
         exc=exc[0,meritev], resp=h[0,meritev],
         resp_type='v',
         exc_window="Force:0.1",
         resp_window="Exponential:0.1",
         frf_type="Hv")


plt.close()
fig, ax = plt.subplots(nrows=3, ncols=1, figsize=(8, 6))

ax[0].plot(t,exc[0,meritev])

ax[1].plot(t,h[0,meritev])

ax[2].plot(frf.get_f_axis(), np.abs(frf.get_FRF()),label="zdej")
ax[2].plot(frekvenca,np.abs(frf_gui[0,meritev]),label="GUI")
ax[2].set_yscale("log")
ax[2].set_xlim(0,2000)
ax[2].legend()
plt.show()

# =============================================================================

# 
# plt.plot(frf.get_f_axis(), frf.get_FRF())
# plt.yscale("log")
# plt.show()
# =============================================================================
