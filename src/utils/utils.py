import numpy as np
import signal as sig
import pandas as pd

def rms(signal:np.ndarray, window:int = 500, stride:int = 100, fs:int = 5120):
  """
  Function that calculates RMS of input signal

  return rms_df: pd.DataFrame - with columns from columns_emg
  """

  rms_i = signal ** 2
  rms_i = np.sqrt(rms_i.rolling(int(window/1000*fs)).mean())

  return rms_i


def zc(signal:np.ndarray, threshold:float = 0.1, window:float = 500, stride:float = 100, fs:int = 5120):
  """
  Funcion that calculates zero crossing in signal from positive to negative and from negative to positive

  return zero_crosses_df: pd.DataFrame - of columns from columns_emg
  """

  tsed = signal[(signal > threshold) | (signal < -threshold)]
  s3= np.sign(tsed)  
  s3[s3==0] = -1     # replace zeros with -1  
  zcs = len(np.where(np.diff(s3))[0])   

  return zcs 


def find_threshold(signal:pd.DataFrame, columns_emg:list = ['EMG_8', 'EMG_9'], column_gesture:str = 'TRAJ_GT', idle_gesture_id:int = 0):
  """
  Function that calculates the threshold of given gesture id
  """
  thresholds = {}
  for ch in columns_emg:
    ts_ch = signal[signal[column_gesture] == idle_gesture_id][ch].abs().mean()
    thresholds[ch] = ts_ch

  thresholds_df = pd.DataFrame(thresholds)

  return thresholds_df 


def filter_emg(signal:np.ndarray, fs:int = 500, Rs:int = 50, notch:bool = True):
  """
  Function that filters movements and network noise
  """

  width = 4 / (0.5 * fs)
  cutoff = 15
  numtaps, beta = sig.kaiserord(ripple=Rs, width=width)
  # high pass from 0 to cutoff
  w = sig.firwin(numtaps=numtaps+1, cutoff=cutoff, window=('kaiser', beta), pass_zero='highpass', fs=fs)
  
  signal_filtered = sig.lfilter(w, 1, signal)
  signal_filtered_zero_ph = sig.filtfilt(w, 1, signal)

  if notch == True:
    b, a = sig.iirnotch(50, 10, fs)
    signal_filtered = sig.lfilter(b, a, signal_filtered)
    signal_filtered_zero_ph = sig.filtfilt(b, a, signal_filtered_zero_ph)

  return signal_filtered, signal_filtered_zero_ph


def subsample_emg(signal_filtered:np.ndarray, fs:int = 500, r:int = 3, Rs:int = 30):
  """
  Subsampling signal
  """

  sampled_sig = signal_filtered[::r]
  width = 20 / (fs/2)
  numtaps, beta = sig.kaiserord(ripple=Rs, width=width)
  w = sig.firwin(numtaps, (fs/r) / (fs/2), window=('kaiser', beta))
  sampled_sig = sig.lfilter(w, 1, sampled_sig)

  return sampled_sig


def filter_force(signal, fs):
  """
  Filter network noises
  """
  signal_filtered = sig.medfilt(signal)

  return signal_filtered, signal_filtered


def norm_emg(signal: np.ndarray, norm_coeff: int):
  """
  Normalize signal 
  """
  
  norm_sig =  signal / norm_coeff

  return norm_sig