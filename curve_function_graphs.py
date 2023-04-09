#%%
import numpy as np 
# import matplotlib.pyplot as plt


# cc_out = 127*(np.exp( curve_amt*(cc_val/127) ) -1)  

def curve_quad(cc_val, curve_amt):
    cc_val = cc_val/127
    cc_out = 127*( cc_val + curve_amt*(cc_val - cc_val**2) )
    return cc_out



#%%
if __name__ == '__main__':

    cc_vals = np.arange(0,127,1)
    cc_outs = curve_quad(cc_vals, 1)
    plt.plot(cc_vals, cc_outs)
    plt.show()
