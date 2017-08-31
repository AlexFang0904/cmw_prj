#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, visa, threading, time, string
from datetime import datetime
from band_def import TEST_LIST
# from band_def import TEST_LIST_L
# from band_def import TEST_LIST_W
from MACRO_DEFINE import *
from config_default import config
from config_default import SENSE_PARAM
from adb import adb

#import msvcrt

#PM = visa.instrument("TCPIP0::192.168.0.1::inst0::INSTR")
#PM = visa.instrument("GPIB1::20::INSTR")

param_FDCorrection="1920000000, 1.0, 1980000000, 1.0, 2110000000, 1.0, 2170000000, 1.0, 1850000000, 1.0,1910000000, 1.0, 1930000000, 1.0, 1990000000, 1.0, 699000000, 0.6, 849000000, 0.6, 869000000, 0.6, 894000000, 0.6, 925000000, 0.6, 960000000, 0.6, 880000000, 0.6, 915000000, 0.6, 2300000000, 1.2, 2535000000, 1.2, 2700000000, 1.2"

md_map = {"WCDMA":"WT","TDSC":"WT","LTE":"LTE","GSM":"GSM"}

class ConnectionError(Exception):
    pass

class RM_CMW(visa.ResourceManager):
    pass

class handle_instr():
    def __init__(self, instr, phone_hd=None):
        self.instr=instr
        self.phone_hd=phone_hd

    def instr_write(self, *args, **kwargs):
        try:
            self.instr.write(*args, **kwargs)
        except:
            print("write error ",args)
            time.sleep(4)
            self.instr.write(*args, **kwargs)

    def instr_query(self, *args, **kwargs):
        try:
            m = self.instr.query(*args,**kwargs)
        # return self.instr.query(cmd)
        except:
            print("query error {0}",args)
            time.sleep(4)
            m = self.instr.query(*args,**kwargs)
        return m

    def instr_reset_cmw(self):
        self.instr_write("*RST;*OPC")
        self.instr_write("*CLS;*OPC?")
        time.sleep(2)
        # preset instr
        self.instr_write("SYSTem:PRESet:ALL;*OPC")
        # self.instr_write("SYSTem:PRESet:ALL")
        print("instr reset.......")
        time.sleep(4)

    def instr_close(self):
        self.instr.close()

    def get_instr_version(self):
        return self.instr_query("*IDN?",delay = 5).strip()

    def set_remote_display(self, state=True):
        if state:
            self.instr_write("SYSTem:DISPlay:UPDate ON")
        else:
            self.instr_write("SYSTem:DISPlay:UPDate OFF")

    def set_FDCorrection(self,loss_matrix):
        lossName = self.instr_query ("CONFigure:BASE:FDCorrection:CTABle:CATalog?")
        # if lossName.find ("CMW_loss") != -1:
            # self.instr_write ("CONFigure:BASE:FDCorrection:CTABle:DELete 'CMW_loss'")
        self.instr_write("CONFigure:BASE:FDCorrection:CTABle:DELete:ALL")
        self.instr_write("CONFigure:BASE:FDCorrection:CTABle:CREate 'CMW_loss', {loss_matrix}".format(loss_matrix=loss_matrix))
        self.instr_write ("CONFigure:FDCorrection:ACTivate RF1C, 'CMW_loss', RXTX, RF1")
        self.instr_write ("CONFigure:FDCorrection:ACTivate RF1O, 'CMW_loss', RXTX, RF1")

    def LTE_para_configure(self,md,test_list):
        if self.LWGT_check_connection(md):
            # self.instr_write("CONFigure:LTE:SIGN:DL:RSEPre:LEVel -80")
            self.LWGT_set_dl_pwr(md)
            self.LTE_ch_redirection(test_list[0])
            pass
        else:
            self.instr_write ("SOURce:LTE:SIGN:CELL:STATe OFF")
            self.instr_reset_cmw()
            self.set_FDCorrection(param_FDCorrection)
            test_DD = "FDD" if int(test_list[0].BAND[2:])<33 else "TDD"
            self.instr_write ("CONFigure:LTE:SIGN:DMODe {DD}".format(DD=test_DD))
            self.instr_write ("CONFigure:LTE:SIGN:PCC:BAND {band}".format(band=test_list[0].BAND))
            self.instr_write ("CONFigure:LTE:SIGN:RFSettings:CHANnel:UL {0}".format(test_list[0].CH_UL))
        self.instr_write ("ROUTe:LTE:MEAS:SCENario:CSPath 'LTE Sig1'")
        self.instr_write ("SOURce:LTE:SIGN:CELL:STATe ON")
        while self.instr_query("SOURce:LTE:SIGN:CELL:STATe:ALL?").strip() != "ON,ADJ":
            time.sleep(1)
        self.instr_write ("CONFigure:LTE:MEAS:MEValuation:REPetition SINGleshot")
        # �����
        self.LWGT_set_ul_pwr(md, pwr="MAX")

    def LWGT_set_dl_pwr(self, md, pwr=None):
        if md=="WCDMA":
            if pwr == None:
                pwr = -56.10
            self.instr_write("CONFigure:WCDMa:SIGN:RFSettings:COPower {0}".format(pwr))
        elif md == "TDSC":
            if pwr == None:
                pwr = -60
            self.instr_write("CONFigure:TDSCdma:SIGN:DL:LEVel:PCCPch {0}".format(pwr))
        elif md == "LTE":
            if pwr == None :
                pwr = -80
            self.instr_write("CONFigure:LTE:SIGN:DL:RSEPre:LEVel {pwr}".format(pwr=pwr))
        elif md == "GSM":
            if pwr == None :
                pwr = -80
            self.instr_write("CONFigure:GSM:SIGN:RFSettings:LEVel:TCH {pwr}".format(pwr=pwr))

    def LWGT_set_ul_pwr(self, md, pwr):
        def WT_set_ul_pwr(md, pwr="MAX"):
            confirm_res = { "MAX":  "MAXP", "MIN":  "MINP", }
            if pwr == "MAX":
                # PM.write ("CONFigure:TDSCdma:MEAS:TPC:SETup ALL1")
                self.instr_write("CONFigure:{md}:SIGN:UL:TPC:SET ALL1".format(md=md))
            elif pwr == "MIN":
                self.instr_write("CONFigure:{md}:SIGN:UL:TPC:SET ALL0".format(md=md))
            elif isinstance(pwr, (int,float)):
                self.instr_write("CONFigure:{md}:SIGN:UL:CARRier:TPC:TPOWer {pwr}".format(md=md,pwr=pwr))
                self.instr_write("CONFigure:{md}:SIGN:UL:TPC:SET CLOop".format(md=md))
            else:
                return
            for i in range(10):
                res_tpc = self.instr_query("CONFigure:{md}:SIGN:UL:TPC:STATe?".format(md=md)).strip()
                if res_tpc == "IDLE" or res_tpc == confirm_res.get(pwr,"TPL"):
                    # raise ConnectionError
                    break
                time.sleep(0.5)
        
        def GSM_set_ul_pwr(md, pwr="MAX"):
            if pwr == "MAX":
                present_state = self.LWGT_get_state(md)
                pcl = 5 if present_state.g_BAND in ("G085","G09") else 0
                self.instr_write("CONFigure:GSM:SIGN:RFSettings:PCL:TCH:CSWitched {pcl}".format(pcl = pcl))
            elif isinstance(pwr, int):
                self.instr_write("CONFigure:GSM:SIGN:RFSettings:PCL:TCH:CSWitched {pcl}".format(pcl = pwr))
            else:
                return 

        def LTE_set_ul_pwr(md, pwr="MAX"):
            if pwr == "MAX":
                self.instr_write("CONFigure:LTE:SIGN:UL:PUSCh:TPC:SET MAXPower")
            elif isinstance(pwr, (int,float)):
                self.instr_write("CONFigure:LTE:SIGN:UL:PUSCh:TPC:CLTPower {pwr}".format(pwr=pwr))
                self.instr_write("CONFigure:LTE:SIGN:UL:PUSCh:TPC:SET CLOop")
            else:
                return 

        func = eval(md_map[md]+"_set_ul_pwr")
        return func(md, pwr)

    def LWGT_ch_travel(self, md, test_list, mea_item):
        total_res = {}
        for item in mea_item:
            total_res[item]=[]
        try:
            for dest_state in test_list:
                if md in ['WCDMA', "TDSC"]:
                    self.WT_ch_redirection(md, dest_state)
                else:
                    getattr(self, md+"_ch_redirection")(dest_state)
                for i in range(3):
                    try:
                        temp = getattr(self, md_map[md]+"_acquire_meas")(md, mea_item)
                        break
                    except ConnectionError as e:
                        if not self.LWGT_check_connection(md):
                            self.LWGT_set_port_route(md,"main")
                            self.LWGT_set_dl_pwr(md)
                            self.LWGT_disconnect_off(md, state_on=True)
                            self.LWGT_connect(md)
                        else:
                            print("still connected, try again")
                for item in temp.keys():
                    total_res[item].append(dest_state+temp[item])
                print("")
        finally:
            self.LWGT_data_output(md, total_res, 
                                  os.path.splitext(config[md]['data_save'])[0]+datetime.today().strftime("_%Y_%m_%d_%H_%M")
                                  +os.path.splitext(config[md]['data_save'])[1])
            print(total_res)

    def LWGT_set_port_route(self,md,route_path = "main"):
        route_m = "RF1C,RX1,RF1C,TX1"
        route_d = "RF1C,RX1,RF1O,TX1"
        route = {
            "main"  :   route_m,
            "div"   :   route_d,
        }
        # TODO
        self.instr_write("ROUTe:{md}:SIGN:SCENario:SCELl {route}".format(
            md=md, route=route[route_path]))

    def LWG_get_RSRP(self, md="LTE"):
        # cmd_md = "WCDMa" if md=="WCDMA" else md
        if md != "GSM":
            self.instr_write("CONFigure:{md}:SIGN:UEReport:ENABle ON".format(md=md))
            # time.sleep(1)
        if md == "LTE":
            res = self.instr_query("SENSe:LTE:SIGN:UEReport:RSRP:RANGe?")
            while "NAV" in res:
                time.sleep(1)
                res = self.instr_query("SENSe:LTE:SIGN:UEReport:RSRP:RANGe?")
            RSRP = list(map(float, res.strip().split(",")[:2]))
        elif md == "WCDMA":
            res = self.instr_query("SENSe:WCDMa:SIGN:UEReport:CCELl?")
            while "NAV" in res:
                time.sleep(1)
                res = self.instr_query("SENSe:WCDMa:SIGN:UEReport:CCELl?")
            RSRP = list(map(float, res.strip().split(",")[:2]))
        elif md == "GSM":
            res = self.instr_query("SENSe:GSM:SIGN:RREPort:RXLevel:RANGe?")
            while "NAV" in res:
                time.sleep(1)
                res = self.instr_query("SENSe:GSM:SIGN:RREPort:RXLevel:RANGe?")
            RSRP = list(map(float, res.strip().split(",")[:2]))
        return RSRP

    def LWGT_get_state(self, md):
        def GSM_get_state():
            g_ch = self.instr_query("CONFigure:GSM:SIGN:RFSettings:CHANnel:TCH?").strip()
            g_band = self.instr_query("SENSe:GSM:SIGN:BAND:TCH?").strip()
            return ue_struct_g(g_band, int(g_ch))

        def LTE_get_state():
            band = self.instr_query("CONFigure:LTE:SIGN:PCC:BAND?").strip()
            ch_ul = self.instr_query("CONFigure:LTE:SIGN:RFSettings:PCC:CHANnel:UL?").strip()
            ch_dl = self.instr_query("CONFigure:LTE:SIGN:RFSettings:PCC:CHANnel:DL?").strip()
            bw = self.instr_query("CONFigure:LTE:SIGN:CELL:BANDwidth:DL?").strip()
            return ue_struct_l(band, int(ch_ul),int(ch_dl), bw)
        
        def WCDMA_get_state():
            band = self.instr_query("CONFigure:WCDMa:SIGN:CARRier:BAND?").strip()
            ch_ul = self.instr_query("CONFigure:WCDMa:SIGN:RFSettings:CARRier:CHANnel:UL?").strip()
            ch_dl = self.instr_query("CONFigure:WCDMa:SIGN:RFSettings:CARRier:CHANnel:DL?").strip()
            return ue_struct_w(band, int(ch_ul), int(ch_dl))

        def TDSC_get_state():
            t_band = self.instr_query("CONFigure:TDSCdma:SIGN:RFSettings:BAND?").strip()
            t_ch = self.instr_query("CONFigure:TDSCdma:SIGN:RFSettings:CHANnel?").strip()
            return ue_struct_t(t_band, int(t_ch))

        md_get_state = eval(md+"_get_state")
        return md_get_state()
    
    def LWGT_check_connection(self, md = "LTE"):
        if md == "LTE":
            res_ps = self.instr_query("FETCh:LTE:SIGN:PSWitched:STATe?").strip()
            res_rrc = self.instr_query("SENSe:LTE:SIGN:RRCState?").strip()
            if res_ps == "CEST" and res_rrc == "CONN":
                return True
            else:
                return False
        elif md in ["WCDMA","TDSC"]:
            res_cs = self.instr_query("FETCh:{0}:SIGN:CSWitched:STATe?".format(md)).strip()
            res_ps = self.instr_query("FETCh:{0}:SIGN:PSWitched:STATe?".format(md)).strip()
            if res_cs == "CEST" and res_ps == "ATT" :
                if md == "WCDMA":
                    ue_info_dinfo = self.instr_query("SENSe:{0}:SIGN:UESinfo:DINFo?".format(md)).strip().split(",")[1:3]
                    if ue_info_dinfo[0]=="OK" and ue_info_dinfo[1]=="OK":
                        pass
                    else: 
                        return False
                return True
            else:
                return False
        elif md == "GSM":
            res_cs = self.instr_query("FETCh:GSM:SIGN:CSWitched:STATe?").strip()
            if res_cs == "CEST":
                return True
            else:
                return False
        else :
            return True

    def LWGT_connect(self,md):
        print("{md} connect begin".format(md = md))
        for j in range(3):
            for i in range(30):
                if md == "LTE":
                    self.instr_write("CALL:LTE:SIGN:PSWitched:ACTion CONNect")
                    time.sleep(2)
                    res_ps = self.instr_query( "FETCh:LTE:SIGN:PSWitched:STATe?").strip()
                    res_rrc = self.instr_query("SENSe:LTE:SIGN:RRCState?").strip()
                    print("\r{0:<5} ".format(res_ps),end="")
                    print("Connecting phone, {0}".format(i),end="")
                    if res_ps == "CEST" and res_rrc == "CONN":
                        break
                elif md in ["WCDMA","TDSC"]:
                    res_ps = self.instr_query("FETCh:{0}:SIGN:CSWitched:STATe?".format(md),delay=1).strip()
                    print("\r{0:<5} ".format(res_ps),end="")
                    print("Connecting phone, {0}".format(i),end="")
                    if res_ps == "REG":
                        self.instr_write("CALL:{0}:SIGN:CSWitched:ACTion CONNect".format(md))
                    elif res_ps == "CEST":
                        break
                    time.sleep(2)
                elif md == "GSM":
                    if config['GSM']['WITHSIM']:
                        res_cs = self.instr_query("FETCh:GSM:SIGN:CSWitched:STATe?").strip()
                        print("\r{0:<5} ".format(res_cs),end="")
                        print("Connecting phone, {0}".format(i),end="")
                        if config['GSM']['call_type']:
                            if res_cs == "SYNC":
                                self.instr_write("CALL:GSM:SIGN:CSWitched:ACTion CONNect")
                            elif res_cs == "ALER":
                                print("  Please answer the call",end="")
                        else:
                            if res_cs == "SYNC":
                                print("  Please call from phone",end="")

                        if res_cs == "CEST":
                            break
                        time.sleep(2)
                else:
                    break
            print("")
            if not self.LWGT_check_connection(md) and j != 2:
                print("phone reboot")
                self.phone_hd.adb_reboot()
                save_state = self.LWGT_get_state(md)
                if md == "LTE":
                    self.LTE_para_configure(md, (save_state,))
                elif md == ["WCDMA","TDSC"]:
                    self.WT_para_configure(md, (save_state,))
                elif md == "GSM":
                    self.GSM_para_configure(md, (save_state,))
                    # TODO
                    pass
                time.sleep(PHONE_REBOOT_TIME)
            else:
                break
        if self.LWGT_check_connection(md):
            print("Connection Established!")
        else:
            print("Conecting failed")
        return 0

    def LWGT_disconnect_off(self, md="LTE", state_on = False):
        if md == "LTE":
            for i in range(15):
                if self.instr_query("SENSe:LTE:SIGN:RRCState?").strip() == "IDLE":
                    break
                else:
                    res = self.instr_query("FETCh:LTE:SIGN:PSWitched:STATe?").strip()
                    if res == "CEST":
                        self.instr_write("CALL:LTE:SIGN:PSWitched:ACTion DISConnect")
                    elif res == "ATT":
                        self.instr_write("CALL:LTE:SIGN:PSWitched:ACTion DETach")
                    time.sleep(1)
            if not state_on:
                self.instr_write("SOURce:LTE:SIGN:CELL:STATe OFF")
                while self.instr_query("SOURce:LTE:SIGN:CELL:STATe:ALL?").strip() != "OFF,ADJ":
                    time.sleep(1)
        elif md in ["WCDMA","TDSC"]:
            for i in range(15):
                res_cs = self.instr_query("FETCh:{md}:SIGN:CSWitched:STATe?".format(md=md)).strip()
                res_ps = self.instr_query("FETCh:{md}:SIGN:PSWitched:STATe?".format(md=md)).strip()
                if res_cs == "ON" and res_ps == "ON":
                    break
                else:
                    if res_cs == "REG" and res_ps == "ATT":
                        self.instr_write("CALL:{md}:SIGN:CSWitched:ACTion UNRegister".format(md=md))
                    elif res_cs == "CEST" and res_ps == "ATT":
                        self.instr_write("CALL:{md}:SIGN:CSWitched:ACTion DISCconnect".format(md=md))
                time.sleep(1)
            if not state_on:
                self.instr_write("SOURce:{md}:SIGN:CELL:STATe OFF".format(md=md))
                while self.instr_query("SOURce:{md}:SIGN:CELL:STATe:ALL?".format(md=md)).strip() != "OFF,ADJ":
                    time.sleep(1)
        elif md == "GSM":
            for i in range(15):
                res_cs = self.instr_query("FETCh:GSM:SIGN:CSWitched:STATe?").strip()
                if res_cs == "CEST":
                    self.instr_write("CALL:GSM:SIGN:CSWitched:ACTion DISC")
                if res_cs not in ["CEST","ALER", "CONN", "REL"]:
                    break
            if not state_on:
                self.instr_write("SOURce:GSM:SIGN:CELL:STATe OFF")
                while self.instr_query("SOURce:GSM:SIGN:CELL:STATe:ALL?").strip() != "OFF,ADJ":
                    time.sleep(1)

    def LTE_ch_redirection(self, dest_state):
        md = "LTE"
        last_state = self.LWGT_get_state(md)
        dest_DD = "FDD" if int(dest_state.BAND[2:])<33 else "TDD"
        last_DD = "FDD" if int(last_state.BAND[2:])<33 else "TDD"

        if dest_DD == last_DD:
            if dest_state.BAND == last_state.BAND:
                # switch_mode = "redirection"
                switch_mode = "Handover"
            else:
                switch_mode = "Handover"
        else:
            switch_mode = "ENHandover"
        print(last_state)
        print("Try {sw} to band {st.BAND}, channel {st.CH_UL}, bw {st.BW}".format(sw=switch_mode,st=dest_state))
        if switch_mode == "redirection":
            # self.instr_write("CONFigure:LTE:SIGN:DL:RSEPre:LEVel -80")
            self.LWGT_set_dl_pwr(md="LTE", pwr=-80)
            # band_str = "CONFigure:LTE:SIGN:PCC:BAND {0}".format(dest_state.BAND)
            ch_str = "CONFigure:LTE:SIGN:RFSettings:CHANnel:UL {0}".format(dest_state.CH_UL)
            bw_str = "CONFigure:LTE:SIGN:CELL:BANDwidth:DL {0}".format(dest_state.BW)
            str_list = []
            if dest_state.BW <= last_state.BW:
                str_list+=[bw_str, ch_str]
            else:
                str_list+=[ch_str, bw_str]
            for cmd in str_list:
                self.instr_write(cmd)
                time.sleep(2)
        elif switch_mode == "Handover":
            self.instr_write("PREPare:LTE:SIGN:HANDover:DESTination 'LTE Sig1'")
            self.instr_write("PREPare:LTE:SIGN:HANDover:MMODe HANDover")
            self.instr_write("PREPare:LTE:SIGN:HANDover:ENHanced {md}, {st.BAND}, {st.CH_DL}, {st.BW}, NS01".format(md=dest_DD, st=dest_state))
            # self.instr_write("PREPare:LTE:SIGN:HANDover: {st.BAND}, {st.CH_DL}, {st.BW}, NS01".format(st=dest_state))
            self.instr_write("CALL:LTE:SIGN:PSWitched:ACTion HANDover")
            time.sleep(2)

        elif switch_mode == "ENHandover":
            self.instr_write("PREPare:LTE:SIGN:HANDover:DESTination 'LTE Sig1'")
            self.instr_write("PREPare:LTE:SIGN:HANDover:MMODe HANDover")
            self.instr_write("PREPare:LTE:SIGN:HANDover:ENHanced {md}, {st.BAND}, {st.CH_DL}, {st.BW}, NS01".format(md=dest_DD, st=dest_state))
            self.instr_write("CALL:LTE:SIGN:PSWitched:ACTion HANDover")
            time.sleep(5)

        # check RRC_STATE 
        for i in range(10):
            if self.instr_query("SENSe:LTE:SIGN:RRCState?").strip() == "CONN":
                break
            time.sleep(1)
        if not self.LWGT_check_connection(md="LTE"):
            self.LWGT_connect(md="LTE")

        present_state = self.LWGT_get_state(md)
        if present_state == dest_state:
            print("{0} sucessful".format(switch_mode))
        else:
            print("{0} faild".format(switch_mode))
        pass

    def LTE_acquire_meas(self, md, mea_item = None):
        output_res = {}
        if not mea_item:
            mea_item = ("aclr",)
        if not self.LWGT_check_connection(md):
            print("{md} not connected".format(md=md))
            self.LWGT_connect(md)
        if "aclr" in mea_item:
            output_res["aclr"]=self.LTE_meas_aclr()
        if "sensm" in mea_item:
            output_res["sensm"]=self.LTE_meas_sense(route_path="main")
        if "sensd" in mea_item:
            output_res["sensd"]=self.LTE_meas_sense(route_path="div")
        return output_res

    def LTE_meas_aclr(self):
        md = "LTE"
        test_DD = self.instr_query("CONFigure:LTE:SIGN:DMODe?").strip()
        if test_DD == "FDD":
            self.instr_write("CONFigure:LTE:MEAS:MEValuation:MSUBframes 0,10,0")
        else:
            self.instr_write("CONFigure:LTE:MEAS:MEValuation:MSUBframes 2,10,0")

        self.LWGT_set_ul_pwr(md, pwr="MAX")
        time.sleep(1)
        self.instr_write("INITiate:LTE:MEAS:MEValuation")
        while self.instr_query("FETCh:LTE:MEAS:MEValuation:STATe:ALL?").strip() != "RDY,ADJ,INV":
            time.sleep(1)
        res = self.instr_query("FETCh:LTE:MEAS:MEValuation:ACLR:AVERage?").strip().split(",")
        res = tuple(round(float(res[i]),2) for i in [2,3,4,5,6] )
        print(res)
        return res

    def LTE_meas_sense(self,route_path="main"):
        md = "LTE"
        self.instr_write("CONFigure:LTE:SIGN:EBLer:REPetition SING")
        self.instr_write("CONFigure:LTE:SIGN:EBLer:SCONdition NONE")

        self.LWGT_set_dl_pwr(md)
        # self.LWGT_set_ul_pwr(md, pwr="MAX")
        self.LWGT_set_ul_pwr(md, pwr=-20)
        if route_path == "div":
            self.LWGT_set_port_route(md,"div")
            time.sleep(2)
        
        pwr, ber = self.LWGT_sense_alg(md)
        
        self.LWGT_set_dl_pwr(md)
        if route_path == "div":
            self.LWGT_set_port_route(md,"main")
            time.sleep(2)
        print("sense {rp} : {pwr}, {ber}".format(rp=route_path, pwr=pwr, ber= ber))
        time.sleep(1)
        return (pwr, ber)

    def LTE_meas_sense_cell(self, md, down_level, frame=1000, output_pwr_format="RS_EPRE"):
        # self.instr_write("CONFigure:LTE:SIGN:DL:RSEPre:LEVel {0}".format(down_level))
        self.LWGT_set_dl_pwr(md, pwr=down_level)
        self.instr_write("CONFigure:LTE:SIGN:EBLer:SFRames {frame}".format(frame=frame))
        self.instr_write("INITiate:LTE:SIGN:EBLer")
        while self.instr_query("FETCh:LTE:SIGN:EBL:STATe:ALL?").strip() != "RDY,ADJ,INV":
            time.sleep(1)
        res =self.instr_query("FETCh:LTE:SIGN:EBLer:RELative?").strip().split(",")
        if int(res[0])==0:
            ber = round(100-float(res[1]),2)
            if output_pwr_format=="RS_EPRE":
                return down_level, ber
            elif output_pwr_format=="cell_power":
                cell_pwr = round(float(self.instr_query("SENSe:LTE:SIGN:DL:FCPower?")),2)
                return cell_pwr, ber
        else: 
            raise ConnectionError

    def LWGT_sense_alg(self,md):
        pwr_init = SENSE_PARAM[md]['pwr_init']
        pwr_coarse = SENSE_PARAM[md]['pwr_coarse']
        pwr_fine = SENSE_PARAM[md]['pwr_fine']
        frame_coarse = SENSE_PARAM[md]['frame_coarse']
        frame_fine = SENSE_PARAM[md]['frame_fine']
        BER_THRESHOLD = SENSE_PARAM[md]['BER_THRESHOLD']

        meas_func = getattr (self, md_map[md]+"_meas_sense_cell")

        # init, coarse, pwr_back, fine, pwr_back_fine, end
        EBL_state = "init"
        while EBL_state != "end":
            if EBL_state == "init":
                pwr, ber = meas_func(md, pwr_init,frame=frame_coarse)
                if ber < BER_THRESHOLD:
                    EBL_state = "coarse"
                else:
                    EBL_state = "pwr_back"
            elif EBL_state == "coarse":
                pwr = pwr - pwr_coarse
                if ber != 0:
                    pwr = pwr+0.4*pwr_coarse
                pwr, ber = meas_func(md, pwr,frame=frame_coarse)
                if ber < BER_THRESHOLD:
                    EBL_state = "coarse"
                else:
                    EBL_state = "pwr_back"
            elif EBL_state == "pwr_back":
                pwr = pwr + pwr_coarse
                pwr, ber = meas_func(md, pwr,frame=frame_coarse)
                if ber < BER_THRESHOLD:
                    EBL_state = "fine"
                else:
                    EBL_state = "pwr_back"
            elif EBL_state == "fine" :
                pwr = pwr - pwr_fine
                pwr, ber = meas_func(md, pwr,frame=frame_fine)
                if ber < BER_THRESHOLD:
                    EBL_state = "fine"
                else:
                    EBL_state = "pwr_back_fine"
            elif EBL_state == "pwr_back_fine":
                pwr = pwr + pwr_fine
                pwr, ber = meas_func(md, pwr,frame=frame_fine)
                if ber < BER_THRESHOLD:
                    EBL_state = "end"
                else:
                    EBL_state = "pwr_back_fine"
            print("\r{0}, {1}, {2}".format(round(pwr,2), ber, EBL_state),end="")
            # except TypeError as e:
                # print("BER test error, NoneType receive")
        print("")
        if md == "LTE":
            pwr = float(self.instr_query("SENSe:LTE:SIGN:DL:FCPower?"))
        return (round(pwr,1), round(ber,2))

    def LWGT_data_output(self, md, output_result, fp):
        if not os.path.exists(config["Report_file"]):
            os.mkdir(config["Report_file"])
        with open(os.path.join(config["Report_file"], fp),'w') as f:
            ue_info = eval("str_ue_info_"+md)
            for i,t in test_item_map[md].items():
                if t[0] in output_result:
                    f.write("{0}\n".format("\t".join(t[1])))
                    for line in output_result[t[0]]:
                        f.write("{0!s}".format(ue_info(line[:ue_info.para_num])))
                        f.write("\t{0}\n".format("\t".join(map(str,line[ue_info.para_num:]))))
        pass
    
    def GSM_para_configure(self, md, test_list=None):
        def GSM_MEA_configure():
            self.instr_write("CONFigure:GSM:MEAS:MEValuation:REPetition SINGleshot")
            self.instr_write("CONF:GSM:MEAS:MEV:SCO:MOD 10")
            self.instr_write("CONF:GSM:MEAS:MEV:SCO:SSW 10")
            self.instr_write("CONF:GSM:MEAS:MEV:SCO:SMOD 10")

        if self.LWGT_check_connection(md):
            self.LWGT_set_dl_pwr(md, pwr=-80)
            self.GSM_ch_redirection(test_list[0])
        else:
            self.instr_reset_cmw()
            self.set_FDCorrection(param_FDCorrection)
            self.instr_write("CONFigure:GSM:SIGN:BAND:BCCH {band}".format(band=test_list[0].g_BAND))
            self.instr_write("CONFigure:GSM:SIGN:RFSettings:CHANnel:TCH {ch}".format(ch=test_list[0].g_CH))
        self.instr_write("ROUTe:GSM:MEAS:SCENario:CSPath 'GSM Sig1'")
        self.instr_write("SOURce:GSM:SIGN:CELL:STATe ON")
        while self.instr_query("SOURce:GSM:SIGN:CELL:STATe:ALL?").strip() != "ON,ADJ":
            time.sleep(1)
        GSM_MEA_configure()
        self.LWGT_set_ul_pwr(md, pwr = "MAX")

    def GSM_acquire_meas(self, md, mea_item=None):
        output_res = {}
        if not mea_item:
            mea_item = ("switch_spetrum",)
        if not self.LWGT_check_connection(md):
            print("{md} not connected".format(md=md))
            self.LWGT_connect(md)

        if "switch_spetrum" in mea_item:
            output_res["switch_spetrum"]=self.GSM_meas_ssw()
        if "sensm" in mea_item:
            output_res["sensm"]=self.GSM_meas_sense(route_path = "main")
        if "sensd" in mea_item:
            ue_info_g = self.LWGT_get_state(md)
            # TODO
            if ue_info_g.g_BAND in [gsm_band_map[i][0] for i in config['GSM']['div-support']]:
                output_res["sensd"]=self.GSM_meas_sense(route_path="div")
        return output_res

    def GSM_meas_sense(self, route_path = "main"):
        md = "GSM"
        self.instr_write("CONFigure:GSM:SIGN:BER:CSWitched:SCONdition NONE")
        self.instr_write("CONFigure:GSM:SIGN:BER:CSWitched:MMODe BBBurst")

        self.LWGT_set_dl_pwr(md)
        self.LWGT_set_ul_pwr(md, pwr="MAX")

        if route_path == "div":
            self.LWGT_set_port_route(md,"div")
            time.sleep(2)

        pwr, ber = self.LWGT_sense_alg(md)

        print("rscp is {0}".format(self.LWG_get_RSRP(md)))

        self.LWGT_set_dl_pwr(md)
        if route_path == "div":
            self.LWGT_set_port_route(md,"main")
            time.sleep(2)

        self.instr_write("ABORt:GSM:SIGN:BER:CSWitched")
        while self.instr_query("FETCh:GSM:SIGN:BER:CSWitched:STATe?").strip() != "OFF":
            time.sleep(1)

        print("sense {rp} : {pwr}, {ber}".format(rp=route_path, pwr=pwr, ber= ber))
        time.sleep(1)
        return (pwr, ber)

    def GSM_meas_sense_cell(self, md, down_level, frame=100):
        self.LWGT_set_dl_pwr(md, pwr = down_level)
        self.instr_write("CONFigure:GSM:SIGN:BER:CSWitched:SCOunt {frame}".format(frame = frame))
        self.instr_write("INITiate:GSM:SIGN:BER:CSWitched")
        while self.instr_query("FETCh:GSM:SIGN:BER:CSWitched:STATe:ALL?").strip() != "RDY,ADJ,INV":
            time.sleep(1)
        res = self.instr_query("FETCh:GSM:SIGN:BER:CSWitched?").strip().split(",")
        if int(res[0])==0:
            ber = round(float(res[2]),2)
            return down_level, ber
        else: 
            raise ConnectionError

    def GSM_meas_ssw(self):
        md = "GSM"
        self.LWGT_set_ul_pwr(md, pwr="MAX")
        time.sleep(1)
        self.instr_write("INITiate:GSM:MEAS:MEValuation")
        while self.instr_query("FETCh:GSM:MEAS:MEValuation:STATe:ALL?").strip() != "RDY,ADJ,INV":
            time.sleep(1)
        res = self.instr_query("FETCh:GSM:MEAS:MEValuation:SSWitching:FREQuency?").strip().split(",")
        res = tuple(round(float(res[i]),2) for i in [20,21,22] )
        print(res)
        return res

    def GSM_ch_redirection(self, dest_state):
        md = "GSM"
        last_state = self.LWGT_get_state(md)
        print("try redrection to {0}".format(dest_state))
        if last_state.g_BAND == dest_state.g_BAND:
            self.instr_write("CONFigure:GSM:SIGN:RFSettings:CHANnel:TCH {ch}".format(ch=dest_state.g_CH))
            time.sleep(2)
        else:
            if last_state.g_BAND != "G19" and dest_state.g_BAND != "G19" and config['GSM']['switch_type']:
                self.instr_write("PREPare:GSM:SIGN:HANDover:DESTination 'GSM Sig1'")
                self.instr_write("PREPare:GSM:SIGN:HANDover:TARGet {band}".format(band = dest_state.g_BAND))
                self.instr_write("PREPare:GSM:SIGN:HANDover:CHANnel:TCH {ch}".format(ch = dest_state.g_CH))
                self.instr_write("PREPare:GSM:SIGN:HANDover:LEVel:TCH -80".format(ch = dest_state.g_CH))
                self.instr_write("PREPare:GSM:SIGN:HANDover:PCL 5")
                self.instr_write("CALL:GSM:SIGN:HANDover:STARt")
                if self.instr_query("CONFigure:GSM:SIGN:BAND:BCCH?") != dest_state.g_BAND:
                    handover_state = "DUAL"
                else:
                    handover_state = "OFF"
                for i in range(10):
                    if self.instr_query("FETCh:GSM:SIGN:HANDover:STATe?").strip() == handover_state:
                        break
                    time.sleep(1)
            else:
                self.LWGT_disconnect_off(md, state_on=False)
                print("phone reboot")
                self.phone_hd.adb_reboot()
                self.GSM_para_configure(md, (dest_state,))

                time.sleep(PHONE_REBOOT_TIME)
                self.LWGT_connect(md)
                pass

        for i in range(10):
            if self.LWGT_check_connection():
                break
            time.sleep(1)
        present_state = self.LWGT_get_state(md)
        if present_state == dest_state:
            print("redirection successful")
        else :
            print("redirection failed")

    def WT_ch_redirection(self, md, dest_state):
        self.LWGT_set_dl_pwr(md)
        last_state = self.LWGT_get_state(md)
        print("try redrection to {0}".format(dest_state))
        if last_state.BAND != dest_state.BAND:
            if md == "WCDMA":
                self.instr_write("CONFigure:{md}:SIGN:BAND {band}".format(md=md, band=dest_state.BAND))
            else :
                self.instr_write("CONFigure:{md}:SIGN:RFSettings:BAND {band}".format(md=md, band=dest_state.BAND))
            time.sleep(8)
        if last_state.CH_UL != dest_state.CH_UL:
            # self.instr_write("CONFigure:{md}:SIGN:RFSettings:CHANnel:UL {ch_ul}".format(md=md, ch_ul=dest_state.CH_UL))
            self.instr_write("CONFigure:{md}:SIGN:RFSettings:CHANnel{ch_ul}".format(md=md, ch_ul=(":UL " if md == "WCDMA" else " ")+str(dest_state.CH_UL)))
            time.sleep(6)
        if self.LWGT_check_connection(md):
            if self.LWGT_get_state(md) == dest_state:
                print("redirection successful")
            else:
                print("redirection failed but connected")
                print(self.LWGT_get_state(md))
        else:
            print("------------redirection error---------------------------")

    def WT_para_configure(self, md, test_list = None):
        str_sig1 = {"WCDMA" : "WCDMA Sig1", "TDSC": "TD-SCDMA Sig1"}
        if self.LWGT_check_connection(md):
            # self.TDSC_ch_redirection(test_list[0])
            self.WT_ch_redirection(md, test_list[0])
        else:
            self.instr_write("SOURce:{0}:SIGN:CELL:STATe OFF".format(md))
            while self.instr_query("SOUR:{0}:SIGN:CELL:STAT:ALL?".format(md)).strip()!="OFF,ADJ":
                time.sleep(1)
            self.instr_reset_cmw()
            self.set_FDCorrection(param_FDCorrection)
            self.instr_write("CONFigure:{0}:SIGN:RFSettings:BAND {1}".format(md, test_list[0].BAND))
            self.instr_write("CONFigure:{0}:SIGN:RFSettings:CHANnel {1}".format(md, test_list[0].CH_UL))
            # TODO
            self.instr_write("CONFigure:{0}:SIGN:CONNection:TMODe:RMC:TMODe MODE2".format(md))
        self.instr_write("ROUTe:{0}:MEAS:SCENario:CSPath '{1}'".format(md, str_sig1[md]))
        self.instr_write("SOURce:{0}:SIGN:CELL:STATe ON".format(md))
        while self.instr_query("SOUR:{0}:SIGN:CELL:STAT:ALL?".format(md)).strip()!="ON,ADJ":
            time.sleep(1)
        print("Cell initialling done")
        self.instr_write("CONFigure:{0}:MEAS:MEValuation:REPetition SINGleshot".format(md))
        self.instr_write("CONF:{0}:MEAS:MEV:SCO:MOD 10".format(md))
        self.instr_write("CONF:{0}:MEAS:MEV:SCO:SPEC 10".format(md))
        self.LWGT_set_ul_pwr(md,pwr="MAX")

    def WT_acquire_meas(self,md, mea_item=None):
        output_res = {}
        if not mea_item:
            mea_item = ("aclr",)
        if not self.LWGT_check_connection(md):
            print("Not connected")
            self.LWGT_connect(md)

        if "aclr" in mea_item:
            output_res["aclr"] = self.WT_meas_aclr(md)
        if "sensm" in mea_item:
            output_res["sensm"] = self.WT_meas_sense(md, route_path="main")
        if "sensd" in mea_item:
            ue_info = self.LWGT_get_state(md)
            # TODO
            if ue_info.BAND in [wt_band_map[i][0] for i in config[md].get("div-support", ())]:
                output_res["sensd"] = self.WT_meas_sense(route_path="div")
        return output_res

    def WT_meas_aclr(self, md):
        # self.instr_write("CONFigure:WCDMa:SIGN:UL:TPC:SET ALL1")
        self.LWGT_set_ul_pwr(md, pwr="MAX")
        self.instr_write("INITiate:{0}:MEAS:MEValuation".format(md))
        while self.instr_query("FETCh:{0}:MEAS:MEValuation:STATe:ALL?".format(md)).strip() != "RDY,ADJ,INV":
            time.sleep(1)
        if md == "WCDMA":
            res = self.instr_query("FETCh:{0}:MEAS:MEValuation:SPECtrum:AVERage? RELative".format(md)).split(",")
            res = tuple(round(float(res[i]),2) for i in [2,3,15,4,5] )
        else :
            res = self.instr_query("FETCh:{0}:MEAS:MEValuation:SPECtrum:AVERage?".format(md)).split(",")
            for i in [2,3,4,5]:
                res[i] = float(res[i]) - float(res[1])
            res = tuple(round(float(res[i]),2) for i in [2,3,13,4,5] )
        # print("print before aclr")
        print(res)
        return res

    def WT_meas_sense(self, md, route_path="main"):
        self.instr_write("CONFigure:{0}:SIGN:BER:SCONdition None".format(md))
        self.instr_write("CONFigure:{0}:SIGN:BER:REPetition SINGleshot".format(md))

        self.LWGT_set_dl_pwr(md)
        self.LWGT_set_ul_pwr(md, pwr="MAX")
        if route_path == "div":
            self.LWGT_set_port_route(md, "div")
            time.sleep(2)

        pwr,ber = self.LWGT_sense_alg(md)

        self.LWGT_set_dl_pwr(md)
        if route_path == "div":
            self.LWGT_set_port_route(md, "main")
            time.sleep(2)
        print("sense {rp} : {pwr}, {ber}".format(rp=route_path, pwr=pwr, ber= ber))
        time.sleep(1)
        return (pwr, ber)

    def WT_meas_sense_cell(self, md, down_level, frame = 100):
        # self.instr_write("CONFigure:WCDMa:SIGN:RFSettings:COPower {0}".format(down_level))
        self.LWGT_set_dl_pwr(md, pwr=down_level)
        self.instr_write("CONFigure:{0}:SIGN:BER:TBLocks {1}".format(md, frame))
        time.sleep(1)
        self.instr_write("INITiate:{0}:SIGN:BER".format(md))
        while self.instr_query("FETCh:{0}:SIGN:BER:STATe:ALL?".format(md)).strip() != "RDY,ADJ,INV":
            time.sleep(1)
        res = self.instr_query("FETCh:{0}:SIGN:BER?".format(md)).split(",")
        # print(res)
        # if int(res[0]) == 0 and "INV" not in res:
        if int(res[0]) == 0 :
            return (down_level, round(float(res[1]),2))
        else:
            raise ConnectionError

    def test(self, md):
        self.set_FDCorrection(param_FDCorrection)
        getattr(self,md_map[md]+"_para_configure")(md, TEST_LIST[md])
        self.LWGT_connect(md)
        mea_item = [test_item_map[md][i][0] for i in config[md]['test_item']]
        self.LWGT_ch_travel(md , TEST_LIST[md], mea_item)


if __name__ == '__main__':
    # rm = visa.ResourceManager()
    # instr = rm.open_resource("TCPIP0::10.237.70.10::inst0::INSTR")
    try:
        time_start = time.time()
        phone = adb()
        # phone.adb_reboot()

        rm = RM_CMW()
        if "dev_ip" in config:
            m = handle_instr(rm.open_resource("TCPIP0::{0}::inst0::INSTR".format(config["dev_ip"])), phone)
        elif "gpib" in config:
            m = handle_instr(rm.open_resource("GPIB0::{0}::INSTR".format(config["gpib"])), phone)
        else:
            m = None
        if m:
            print(m.get_instr_version())
            m.set_remote_display(state=True)

            # m.tdsc_test()

            for i, v in enumerate(config.get('TEST_RF', ())):
                md = standard_map[v]
                m.test(md)
                if i+1 < len(config['TEST_RF']) :
                    if config['TEST_RF'][i] != config['TEST_RF'][i+1]:
                        m.LWGT_disconnect_off(md,state_on=False)
            m.instr_close()
        rm.close()
    finally:
        time_end = time.time()
        print("time elaped {0}:{1}".format(int(time_end-time_start)//60, int(time_end-time_start)%60))
