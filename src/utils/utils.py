import numpy as np
import signal as sig
import pandas as pd

def rms(signal:pd.DataFrame, window:int = 500, stride:int = 100, fs:int = 5120, columns_emg:list = ['EMG_20']):
  """
  Function that calculates RMS of input signals

  return rms_df: pd.DataFrame - with columns from columns_emg
  """

  t = np.arange(len(signal)) / fs
  signal['t'] = t
  rms = {}
  for ch in columns_emg:
    ch_signal = signal[ch]

    rms_i = ch_signal ** 2
    rms_i = np.sqrt(rms_i.rolling(int(window/1000*fs)).mean())

    rms[ch] = rms_i

  rms_df = pd.DataFrame(data=rms)

  return rms_df


def zc(signal:pd.DataFrame, threshold:float = 0.1, window:float = 500, stride:float = 100, fs:int = 5120, columns_emg:list = ['EMG_20']):
  """
  Funcion that calculates zero crossing in signal from positive to negative and from negative to positive

  return zero_crosses_df: pd.DataFrame - of columns from columns_emg
  """
  zero_crosses = {}
  for ch in columns_emg:
    ch_val = signal[ch].values
    tsed = ch_val[(ch_val > threshold) | (ch_val < -threshold)]
    s3= np.sign(tsed)  
    s3[s3==0] = -1     # replace zeros with -1  
    zcs = len(np.where(np.diff(s3))[0])   

    zero_crosses[ch] = zcs
  # return signal[columns_emg].iloc[int(window/1000*fs)::int(stride/1000*fs)]
  zero_crosses_df = pd.DataFrame(data=zero_crosses)

  return zero_crosses_df 


def find_threshold(signal, columns_emg=['EMG_8', 'EMG_9'], column_gesture='TRAJ_GT', idle_gesture_id = 0):
  thresholds = {}
  for ch in columns_emg:
    ts_ch = signal[signal[column_gesture] == idle_gesture_id][ch].abs().mean()
    thresholds[ch] = ts_ch

  return thresholds 


def filter_emg(signal, fs=500, Rs=50, notch=True):
  width = 4 / (0.5 * fs)
  cutoff = 15
  numtaps, beta = sig.kaiserord(ripple=Rs, width=width)
  # high pass from 0 to cutoff
  w = sig.firwin(numtaps=numtaps+1, cutoff=cutoff, window=('kaiser', beta), pass_zero='highpass', fs=fs)
  
  signal_filtered = sig.lfilter(w, 1, signal)
  signal_filtered_zero_ph = sig.filtfilt(w, 1, signal)

  # usuniecie zaklocen sieciowych 50Hz pasmozaporowym 30-70
  if notch == True:
    # ord, wn = sig.ellipord(wp=[1/(fs/2), 230/(fs/2)], ws=[30/(fs/2), 70/(fs/2)], gpass=3, gstop=20)
    b, a = sig.iirnotch(50, 10, fs)
    signal_filtered = sig.lfilter(b, a, signal_filtered)
    signal_filtered_zero_ph = sig.filtfilt(b, a, signal_filtered_zero_ph)

  return signal_filtered, signal_filtered_zero_ph


def subsample_emg(signal_filtered, fs=500, r=3, Rs=30):
  sampled_sig = signal_filtered[::r]
  width = 20 / (fs/2)
  numtaps, beta = sig.kaiserord(ripple=Rs, width=width)
  w = sig.firwin(numtaps, (fs/r) / (fs/2), window=('kaiser', beta))
  sampled_sig = sig.lfilter(w, 1, sampled_sig)

  return sampled_sig


def filter_force(signal, fs):
  signal_filtered = sig.medfilt(signal)
  return signal_filtered, signal_filtered


def norm_emg(signal, norm_coeffs: dict, columns_emg=['EMG_8', 'EMG_9']):
  norm_sigs = {}
  for ch in columns_emg:
    ch_signal = signal[ch]
    norm_sig =  ch_signal / norm_coeffs[ch]
    norm_sigs[ch] = norm_sig

  return norm_sigs