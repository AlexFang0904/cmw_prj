#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 1p4, 3, 5, 10, 15, 20
LTE_BW_SUPPORT={
    1: (0,0,1,1,1,1), 
    2: (1,1,1,1,1,1), 
    3: (1,1,1,1,1,1), 
    4: (1,1,1,1,1,1), 
    5: (1,1,1,1,0,0), 
    6: (0,0,1,1,0,0), 
    7: (0,0,1,1,1,1), 
    8: (1,1,1,1,0,0), 
    9: (0,0,1,1,1,1), 
    10: (0,0,1,1,1,1),
    11: (0,0,1,1,0,0),
    12: (1,1,1,1,0,0),
    13: (0,0,1,1,0,0),
    14: (0,0,1,1,0,0),
    17: (0,0,1,1,0,0),
    18: (0,0,1,1,1,0),
    19: (0,0,1,1,1,0),
    20: (0,0,1,1,1,1),
    21: (0,0,1,1,1,0),
    22: (0,0,1,1,1,1),
    23: (1,1,1,1,1,1),
    24: (0,0,1,1,0,0),
    25: (1,1,1,1,1,1),
    26: (1,1,1,1,1,0),
    27: (1,1,1,1,0,0),
    28: (0,1,1,1,1,1),
    30: (0,0,1,1,0,0),
    33: (0,0,1,1,1,1),
    34: (0,0,1,1,1,0),
    35: (1,1,1,1,1,1),
    36: (1,1,1,1,1,1),
    37: (0,0,1,1,1,1),
    38: (0,0,1,1,1,1),
    39: (0,0,1,1,1,1),
    40: (0,0,1,1,1,1),
    41: (0,0,1,1,1,1),
    42: (0,0,1,1,1,1),
    43: (0,0,1,1,1,1),
    44: (0,1,1,1,1,1),
    45: (0,0,1,1,1,1),
}

# UL_freq, UL_ch, DL_freq, DL_ch
LTE_UL_DL={
    1: (1920,1980,2110,2170,18000,18599,0,599),
    2: (1850,1910,1930,1990,18600,19199,600,1199),
    3: (1710,1785,1805,1880,19200,19949,1200,1949),
    4: (1710,1755,2110,2155,19950,20399,1950,2399),
    5: (824,849,869,894,20400,20649,2400,2649),
    6: (830,840,875,885,20650,20749,2650,2749),
    7: (2500,2570,2620,2690,20750,21449,2750,3449),
    8: (880,915,925,960,21450,21799,3450,3799),
    9: (1749.9,1784.9,1844.9,1879.9,21800,22149,3800,4149),
    10: (1710,1770,2110,2170,22150,22749,4150,4749),
    11: (1427.9,1447.9,1475.9,1495.9,22750,22949,4750,4949),
    12: (699,716,729,746,23010,23179,5010,5179),
    13: (777,787,746,756,23180,23279,5180,5279),
    14: (788,798,758,768,23280,23379,5280,5379),
    17: (704,716,734,746,23730,23849,5730,5849),
    18: (815,830,860,875,23850,23999,5850,5999),
    19: (830,845,875,890,24000,24149,6000,6149),
    20: (832,862,791,821,24150,24449,6150,6449),
    21: (1447.9,1462.9,1495.9,1510.9,24450,24599,6450,6599),
    22: (3410,3490,3510,3590,24600,25399,6600,7399),
    23: (2000,2020,2180,2200,25500,25699,7500,7699),
    24: (1626.5,1660.5,1525,155925700,26039,7700,8039),
    25: (1850,1915,1930,1995,26040,26689,8040,8689),
    26: (814,849,859,894,26690,27039,8690,9039),
    27: (807,824,852,869,27040,27209,9040,9209),
    28: (703,748,758,803,27210,27659,9210,9659),
    29: (None,None,717,728,None,None,9660,9769),
    30: (2305,2315,2350,2360,27660,27759,9770,9869),
    31: (452,5,457.5,462.5,467.5,27760,27809,9870,9919),
    32: (None,None,1452,1496,None,None,9920,10359),
    33: (1990,1920,1990,1920,36000,36199,36000,36199),
    34: (2010,2025,2010,2025,36200,36349,36200,36349),
    35: (1850,1910,1850,1910,36350,36949,36350,36949),
    36: (1930,1990,1930,1990,36950,37549,36950,37549),
    37: (1910,1930,1910,1930,37550,37749,37550,37749),
    38: (2570,2620,2570,2620,37750,38249,37750,38249),
    39: (1880,1920,1880,1920,38250,38649,38250,38649),
    40: (2300,2400,2300,2400,38650,41589,38650,41589),
    41: (2496,2690,2496,2690,39650,41589,39650,41589),
    42: (3400,3600,3400,3600,41590,43589,41590,43589),
    43: (3600,3800,3600,3800,43590,45589,43590,45589),
    44: (703,803,703,803,45590,46589,45590,46589),
    45: (1446,1467,1447,1467,46590,46789,46590,46789),
    46: (5150,5925,5150,5925,46790,54539,46790,54539),
}

class LTE_Calc():
    bw_1p4_chsep = 7
    bw_3_chsep = 15
    bw_5_chsep = 25
    bw_10_chsep = 50
    bw_15_chsep = 75
    bw_20_chsep = 100
    def __init__(self):
        pass

    @classmethod
    def get_freq_ch(cls,band_num):
        return LTE_UL_DL[band_num]

    # bw 这里可以是 字符串"1p4"，也可以是数字 1.4
    @classmethod
    def get_bw_lmh_freq_ch(cls,band_num, bw):
        band_info = LTE_UL_DL[band_num]
        bw= str(bw).replace(".","p")
        sep = eval("cls.bw_"+bw+"_chsep")
        return(band_info[4]+sep,round((band_info[4]+band_info[5]+1)/2), band_info[5]-sep+1)
        

if __name__ == "__main__":
    print(LTE_Calc.get_freq_ch(1))
    print(LTE_Calc.get_bw_lmh_freq_ch(2,20))
    pass