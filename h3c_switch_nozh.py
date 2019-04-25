#!/usr/local/python27/bin/python2
# -*- coding: utf-8 -*-
import re
import telnetlib
import time
import json
import sys
import os


class H3C:
    __tnConn = None             #
    __filterTag = None  #
    __doubleQuot = ''
    __newVersion=False

    #--------------------#
    #
    __sysname = None            #
    __manage_vlan_ints = {}     #
    __mem={}                    #
    __flash = {}                #
    __os_version = ""           #
    __phy_ports = {}            #
    __bagg_ports = {}           #
    __vlans ={}                 #
    __vlan_tag_ports = {}       #
    __vlan_untag_ports = {}     #
    __bagg_phy_port_rels = {}   #
    __slot_list = {}

    __port_mac_port_list = {}  #
    __port_ip_mac_map = {}  # 端口互连对应的设备ip和mac映射
    __port_mac_ip_map = {}  # 端口互连对应的设备ip和mac映射

    attrs={
        "phy_port":[
            {'name': 'port_name', 'doc': '', 'get_mode': 'manual','reg': '', 'def_val':''},
            {'name': 'description', 'doc': '', 'get_mode': 'regular', 'reg': 'Description: ([a-zA-Z0-9-_.\/ ]+)\r\n', 'def_val':''},
            {'name': 'port_status', 'doc': '', 'get_mode': 'regular', 'reg': 'current state: (\w+)', 'def_val':''},
            {'name': 'port_mac', 'doc': '', 'get_mode': 'regular', 'reg': 'Hardware Address: ([a-zA-Z0-9\-]+)', 'def_val':''},
            {'name': 'port_access_type', 'doc': '', 'get_mode': 'regular', 'reg': 'Port link-type: ([a-zA-Z]+)', 'def_val':''},
            {'name': 'port_type', 'doc': '', 'get_mode': 'regular', 'reg': 'Media type is ([a-zA-Z0-9 ]+)', 'def_val':''},
            {'name': 'port_rate', 'doc': '', 'get_mode': 'regular', 'reg': 'Port hardware type is ([a-zA-Z0-9_ ]+)', 'def_val':''},
            {"name": "port_rate_xs", "doc": "", "get_mode": "regular", "reg": "([a-zA-Z0-9]+)-speed mode", 'def_val':''},
            {"name": "port_duplex", "doc": "", "get_mode": "regular", "reg": "([a-zA-Z0-9]+)-duplex mode", 'def_val':''}
        ],
        "bagg_port": [
            {'name': 'port_name', 'doc': '', 'get_mode': 'manual', 'reg': '', 'def_val':''},
            {'name': 'full_port_name', 'doc': '', 'get_mode': 'manual', 'reg': '', 'def_val':''},
            {'name': 'description', 'doc': '', 'get_mode': 'regular', 'reg': 'Description: ([a-zA-Z0-9-_.\/ ]+)\r\n', 'def_val':''},
            {'name': 'port_status', 'doc': '', 'get_mode': 'regular', 'reg': 'current state: (\w+)', 'def_val':''},
            {'name': 'port_mac', 'doc': '', 'get_mode': 'regular', 'reg': 'Hardware Address: ([a-zA-Z0-9\-]+)', 'def_val':''},
            {'name': 'port_access_type', 'doc': '', 'get_mode': 'regular', 'reg': 'Port link-type: ([a-zA-Z]+)', 'def_val':''},
            {'name': 'port_rate', 'doc': '', 'get_mode': 'regular', 'reg': 'Bandwidth: ([0-9]+[ ]*[mgkbpsit]*)', 'def_val':''},
            {"name": "port_rate_xs", "doc": "", "get_mode": "regular", "reg": "([a-zA-Z0-9]+)-speed mode", 'def_val':''},
            {"name": "port_duplex", "doc": "", "get_mode": "regular", "reg": "([a-zA-Z0-9]+)-duplex mode", 'def_val':''}
        ]

    }

    def __setitem__(self, k, v):
        self.k = v


    def __init__(self, tnIp, username, password):

        self.tnIp = tnIp  #
        self.username = username  #
        self.password = password  #


    def patten_find(self, patten, str, defValue=''):

        #
        re_pattern = re.compile(patten, re.M | re.I)
        serObj = re.search(re_pattern, str)
        if serObj:
            return serObj.group(1)
        else:
            return defValue


    def h3c_get_items(self, text, attrs):
        result = {}

        for attr in attrs:
            if attr['get_mode'] == r'regular':
                name=attr['name']

                #
                pattern = re.compile(attr['reg'], re.M | re.I)
                serObj = re.search(pattern, text)
                if serObj:
                    result[name] = serObj.group(1)
                else:
                    result[name] = ""

        return result;



    def more(self, tn, cmd, timeout=2.5):


        escTxt = '\x1B\x5B\x31\x36\x44\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x1B\x5B\x31\x36\x44'
        moreTxt="---- More ----"

        tn.write(cmd + '\n')
        time.sleep(timeout)
        result = tn.read_very_eager()
        if '---- More ----' in result:

            #result.replace('---- More ----', '')
            result = result.replace(escTxt, '')
            result = result.replace(moreTxt, '')
            while True:
                #tn.write('\n')
                tn.write(' ')
                time.sleep(1)
                res = tn.read_very_eager()

                if '---- More ----' in res:
                    res = res.replace(escTxt, '')
                    res = res.replace(moreTxt, '')
                    result += res
                else:
                    res = res.replace(escTxt, '')
                    res = res.replace(moreTxt, '')
                    result += res
                    break

        return result


    
    def telnet_connect(self):

        tnconn = telnetlib.Telnet()
        try:
            tnconn.open(self.tnIp)
        except:
            print "Cannot open host"
            return

        #res=tnconn.read_until('Username:',3)
        res = tnconn.read_until('login:', 5)
        if "login:" in res:
            self.__doubleQuot='"'
            self.__newVersion=True

        tnconn.write(self.username + '\n')
        tnconn.read_until('Password:')
        tnconn.write(self.password + '\n')
        time.sleep(3)

        self.__tnConn = tnconn

        return tnconn


    def h3c_sysname(self):
        cmd = 'display current-configuration | include sysname'
        resultTxt = self.more(self.__tnConn, cmd,3)
        if resultTxt:
            reg = r"sysname ([a-zA-Z0-9-_]+)"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, resultTxt)
            if serObj:
                self.__sysname = serObj.group(1)
                self.__filterTag = '<' + self.__sysname + '>'



    def h3c_parse_vlaninterface(self, vlanIntTxt, name):
        one_vlan_int = {
            'state':'',
            'mac':'',
            'ip':''
        }
        one_vlan_int['name'] = name

        #
        reg = r"current state: (\w+)"
        pattern = re.compile(reg, re.I)
        serObj = re.search(pattern, vlanIntTxt)
        if serObj:
            one_vlan_int['state'] = serObj.group(1)

        #
        reg = r"Hardware Address: ([a-zA-Z0-9-]+)"
        pattern = re.compile(reg, re.I)
        serObj = re.search(pattern, vlanIntTxt)
        if serObj:
            one_vlan_int['mac'] = serObj.group(1)

        #
        reg = r"Internet Address[ ]*(:|is)[ ]*([0-9.]+)"
        pattern = re.compile(reg, re.I)
        serObj = re.search(pattern, vlanIntTxt)
        if serObj:
            one_vlan_int['ip'] = serObj.group(2)

        return one_vlan_int


    #
    def h3c_manager_info(self):
        # jsonify(result)
        #
        cmd = 'display interface Vlan-interface | include ^Vlan-interface'
        resultTxt = self.more(self.__tnConn, cmd)
        manage_vlan_ints = {}
        manage_vlan_int_names = {}

        if resultTxt:
            vlanInts = resultTxt.split("\n")
            for vlanInt in vlanInts:
                if not vlanInt:
                    continue
                if not "Vlan-interface" in vlanInt:
                    continue
                if self.__filterTag in vlanInt:
                    continue
                reg = r"(Vlan-interface[0-9]+)"
                vlanIntName = self.patten_find(reg, vlanInt, '')
                if vlanIntName:
                    manage_vlan_int_names[vlanIntName] = vlanIntName

        #
        for name in manage_vlan_int_names:
            cmd = 'display interface ' + name
            resultTxt = self.more(self.__tnConn, cmd)

            oneVlanInt = self.h3c_parse_vlaninterface(resultTxt, name)
            manage_vlan_ints[name]=oneVlanInt

        self.__manage_vlan_ints=manage_vlan_ints

        return manage_vlan_ints

    #
    def h3c_mem_info(self):

        if self.__newVersion:
            return self.get_new_version_mem()
        else:
            return self.get_old_version_mem()


    def get_old_version_mem(self):

        mems = {
            'total_mem': 0,
            'used_mem': 0,
            'used_rate': 0
        }

        cmd = 'display memory'
        memText = self.more(self.__tnConn, cmd)
        if memText:

            #
            reg = r"System Total Memory\(bytes\): ([0-9]+)"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, memText)
            if serObj:
                mems['total_mem'] = serObj.group(1)

            #
            reg = r"Total Used Memory\(bytes\): ([0-9]+)"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, memText)
            if serObj:
                mems['used_mem'] = serObj.group(1)

            #
            reg = r"Used Rate: ([0-9]+)%"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, memText)
            if serObj:
                mems['used_rate'] = serObj.group(1)

        self.__mem = mems

        return mems


    def get_new_version_mem(self):

        mems = {
            'total_mem':0,
            'used_mem':0,
            'used_rate':0
        }

        cmd = 'display memory'
        memText = self.more(self.__tnConn, cmd)
        if memText:

            lines = memText.split("\n")
            for line in lines:

                #Mem:        506440    323124    183316         0      1296     88204       36.2%
                reg = r"Mem:[ ]+([0-9]+)[ ]+([0-9]+)[ ]+"
                pattern = re.compile(reg, re.M | re.I)
                serObj = re.search(pattern, line)
                # 新版单位是kb，统一转成byte
                if serObj:
                    mems['total_mem'] += int(serObj.group(1))*1024
                    mems['used_mem'] += int(serObj.group(2))*1024

            if mems['total_mem'] != 0:
                tmpRate = float(mems['used_mem']) * 100 / float(mems['total_mem'])
                mems['used_rate'] = int(round(tmpRate, 0))

        self.__mem = mems

        return mems

    #
    def h3c_flash_info(self):

        flashs = {}

        cmd = 'dir'
        resultText = self.more(self.__tnConn, cmd)
        if resultText:

            #
            reg = r"([0-9]+) KB total"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, resultText)
            if serObj:
                flashs['total_flash'] = int(serObj.group(1))*1024
            else:
                flashs['total_flash'] = 0

            #
            reg = r"([0-9]+) KB free"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, resultText)
            if serObj:
                flashs['free_flash'] = int(serObj.group(1))*1024
            else:
                flashs['free_flash'] = 0

        self.__flash = flashs

        return flashs

    #
    def h3c_os_version(self):

        cmd = 'dis version | include ' + self.__doubleQuot + 'Comware Software' + self.__doubleQuot
        resultText = self.more(self.__tnConn, cmd)
        if resultText:

            #
            reg = r"Comware Software, ([a-zA-Z0-9., ]*)"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, resultText)
            if serObj:
                self.__os_version = serObj.group(1)
            else:
                self.__os_version = ''

        return self.__os_version

    def h3c_get_version_info(self):
        mems = {}
        cmd = 'dis version '
        resultText = self.more(self.__tnConn, cmd)
        if resultText:
            #固件版本
            reg = r"Comware Software, ([a-zA-Z0-9., ]*)"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, resultText)
            if serObj:
                self.__os_version = serObj.group(1)
            else:
                self.__os_version = ''

            #memory
            if self.__newVersion:
                reg = r"DRAM\:[ ]+([0-9]+)M bytes"
            else:
                reg = r"([0-9]+)M[ ]+bytes DRAM"

            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, resultText)
            if serObj :
                #M 转成b
                memory = serObj.group(1)
                mems['total_mem'] = int(memory) * 1024 * 1024
                mems['used_mem'] = ""
                mems['used_rate'] = ""
                self.__mem = mems

    #
    def h3c_phy_port_info(self):

        #
        cmd = 'display current-configuration | include ' + self.__doubleQuot
        cmd +='interface (Ten-Gigabit|M-Gigabit|forty-Gigabit|Gigabit|Fast|)Ethernet'+ self.__doubleQuot
        resultTxt = self.more(self.__tnConn, cmd, 2.5)
        phy_ports = {}
        port_names = {}
        if resultTxt:
            lines = resultTxt.split("\n")
            for line in lines:
                if cmd in line:
                    continue

                if self.__filterTag in line:
                    continue

                reg = r"(Ten\-Gigabit|M\-Gigabit|forty\-Gigabit|Gigabit|Fast|)?Ethernet([0-9\/]+)"
                pattern = re.compile(reg, re.M | re.I)
                serObj = re.search(pattern, line)
                if serObj:
                    portName = serObj.group(1)+"Ethernet"+serObj.group(2)
                    port_names[portName] = portName
        #
        for name in port_names:

            cmd = 'display interface ' + name
            resultTxt = self.more(self.__tnConn, cmd, 2)

            onePhyPort=self.h3c_get_items(resultTxt, self.attrs['phy_port'])
            onePhyPort['port_name']=name
            phy_ports[name] = onePhyPort

        self.__phy_ports = phy_ports

        return phy_ports

    #
    def h3c_bagg_phy_rel(self, baggName):

        #
        cmd = 'dis link-aggregation verbose ' + baggName
        resultTxt = self.more(self.__tnConn, cmd, 2.5)

        relPorts = []
        start = False
        if resultTxt:
            lines = resultTxt.split("\n")
            for line in lines:
                if not start:
                    #other h3c net switch
                    reg = r"(Port[ ]+Status[ ]+Priority[ ]+Ope)"
                    startFlag = self.patten_find(reg, line, '')
                    if startFlag:
                        start = True

                    continue

                if '----------' in line:
                    continue

                #
                reg = r"([GE|XGE|FE|E0|E1|40GE]{2,}[0-9\/]+)"
                re_pattern = re.compile(reg, re.M)
                tempPortList = re.findall(re_pattern, line)

                if tempPortList:
                    tempPort = tempPortList[0]
                    portFull = False
                    # TODO 应该 少M-GigabitEthernet 缩写 （不知道缩写叫什么，此为管理口）
                    if 'GE' in tempPort and 'XGE' not in tempPort and '40GE' not in tempPort:
                        portFull = tempPort.replace('GE', 'GigabitEthernet')
                    elif 'XGE' in tempPort:
                        portFull = tempPort.replace('XGE', 'Ten-GigabitEthernet')
                    elif 'FE' in tempPort:
                        portFull = tempPort.replace('FE', 'FastEthernet')
                    elif '40GE' in tempPort:
                        portFull = tempPort.replace('40GE', 'Forty-GigabitEthernet')
                    elif 'E0' in tempPort or 'E1' in tempPort:
                        portFull = tempPort.replace('E', 'Ethernet')

                    if portFull:
                      relPorts.append(portFull)


                if '----------' in line:
                    #
                    break

        return relPorts


    #
    def h3c_bagg_port_info(self):

        #
        cmd = 'display interface Bridge-Aggregation | include Bridge-Aggregation'
        resultTxt = self.more(self.__tnConn, cmd, 2)

        bagg_ports = {}
        port_names = {}

        if resultTxt:
            lines = resultTxt.split("\n")

            for line in lines:

                if "Description:" in line:
                    continue

                if cmd in line:
                    continue

                if self.__filterTag in line:
                    continue

                reg = r"(Bridge-Aggregation[0-9]*)"
                pattern = re.compile(reg, re.M | re.I)
                serObj = re.search(pattern, line)
                if serObj:
                    portName = serObj.group(1)
                    port_names[portName] = portName

        # ----------------------------------------#
        #
        for name in port_names:
            cmd = 'display interface ' + name
            resultTxt = self.more(self.__tnConn, cmd, 2)
            oneBaggPort = self.h3c_get_items(resultTxt, self.attrs['bagg_port'])
            oneBaggPort['full_port_name'] = name
            num=self.patten_find(r"Bridge-Aggregation([0-9]*)", name, '')
            if num:
                oneBaggPort['port_name'] = 'BAGG' + num
            else:
                oneBaggPort['port_name'] = num
            bagg_ports[name] = oneBaggPort

        self.__bagg_ports = bagg_ports

        #----------------------------------------#
        #
        baggPhyRels={}
        for name in port_names:
            relPorts=self.h3c_bagg_phy_rel(name)
            baggPhyRels[name]=relPorts


        self.__bagg_phy_port_rels=baggPhyRels

        return bagg_ports

    def h3c_vlan_info(self):

        #
        cmd = 'dis vlan  all | include ' + self.__doubleQuot + 'VLAN ID' + self.__doubleQuot
        resultTxt = self.more(self.__tnConn, cmd, 1)

        vlans = {}
        vlan_ids = {}

        if resultTxt:
            lines = resultTxt.split("\n")
            for line in lines:

                if cmd in line:
                    continue

                if self.__filterTag in line:
                    continue

                reg = r"VLAN ID: ([0-9]*)"
                vlanId = self.patten_find(reg, line, '')
                if vlanId:
                    vlan_ids[vlanId] = vlanId

        #
        for vlanId in vlan_ids:
            oneVlan = {}
            iVlanId = int(vlanId)
            cmd = 'display vlan ' + vlanId
            resultTxt = self.more(self.__tnConn, cmd, 1.5)

            reg = r"Name: ([a-zA-Z0-9 ]+)\r\n"
            vlanName = self.patten_find(reg, resultTxt, '')

            oneVlan = {}
            oneVlan['id'] = iVlanId
            oneVlan['name'] = vlanName
            oneVlan['status'] = ''
            oneVlan['ports'] = self.h3c_get_vlan_port(resultTxt)

            vlans[iVlanId] = oneVlan

        self.__vlans = vlans

        return vlans

    def h3c_get_vlan_port(self,txt):
        portList = []
        reg = r"([Ten\-Gigabit|M\-Gigabit|Forty\-Gigabit|Gigabit|Fast]*Ethernet[0-9\/]+|Bridge-Aggregation[0-9]+)"
        pattern = re.compile(reg, re.M | re.I)
        serObj = re.findall(pattern, txt)
        if serObj:
            portList = serObj
        return  portList

    #得到序列号
    def h3c_get_slot_info(self):
        cmd = 'display device manuinfo'
        resultText = self.more(self.__tnConn, cmd)
        if resultText:
          
            lines  = resultText.split("Slot")
            reg = r'DEVICE_SERIAL_NUMBER[ ]+:[ ]+([0-9a-zA-Z]+)'
            pattern = re.compile(reg, re.M | re.I)
            i = 1
            for line in lines :
                serObj = re.search(pattern, line)
                if serObj:
                    key  = serObj.group(1)
                    if not self.__slot_list.has_key(key):
                        self.__slot_list[key] = {}
                    self.__slot_list[key]['slotNum'] = i
                    i+=1

    # 获取连接端信息
    # TODO 端口展现格式，和邻居展示格式没有100%确定
    def get_neighbor_info(self):

         self._get_neighbor_info_by_arp()
         # 和卞庆丰讨论，只需要连接端的mac和ip信息，所以注释掉学习到的mac
         # self._get_neighbor_info_by_learn()
         self._get_neighbor_info_by_lldp()

    def _get_neighbor_info_by_learn(self):
        cmd = 'dis  mac-address'
        resultTxt = self.moreV1(self.__tnConn, cmd)
        if not resultTxt:
            return
        #   000c-2914-b7ca   1          Learned          BAGG1                    Y
        # 0018-8223-fa4e  1        Learned         GigabitEthernet1/0/24     AGING
        isV1 = False
        isV2 = False
        lines = resultTxt.split("\n")
        for line in lines:
            if isV1:
                self._get_neighbor_info_by_learn_v1(line)
            elif isV2:
                self._get_neighbor_info_by_learn_v2(line)
            else:
                isV1 = self._get_neighbor_info_by_learn_v1(line)
                isV2 = self._get_neighbor_info_by_learn_v2(line)


    def _get_neighbor_info_by_learn_v1(self,line):
        regV1 = r'([0-9a-zA-Z]+\-[0-9a-zA-Z]+\-[0-9a-zA-Z]+)[ ]+[0-9]+[ ]+[0-9a-zA-Z]+[ ]+([GE|XGE|FE|E0|E1|40GE]+[0-9\/]+|BAGG[0-9]+)[ ]+[\S\s]*'
        patternV1 = re.compile(regV1, re.M | re.I)
        seObj = re.search(patternV1, line)
        isV1 = False
        if seObj:
            isV1 = True
            portName = self._port_name_format(seObj.group(2))
            if not portName:
                return False
            mac = seObj.group(1)
            if self.__port_mac_ip_map.has_key(mac):
                ip = self.__port_mac_ip_map[mac]
            else:
                ip = ''
            # ip后面根据lldp 协议和三层的arp 补全
            if not self.__port_mac_port_list.has_key(portName):
                self.__port_mac_port_list[portName] = {}

            key = self._get_port_mac_arr_key(mac, ip)
            self.__port_mac_port_list[portName][key] = {'mac': mac, 'ip': ip}
        return isV1

    def _get_neighbor_info_by_learn_v2(self,line):
        regV2 = r'([0-9a-zA-Z]+\-[0-9a-zA-Z]+\-[0-9a-zA-Z]+)[ ]+[0-9]+[ ]+[0-9a-zA-Z]+[ ]+([0-9a-zA-Z\-]+[0-9\/]+)[ ]+[\S\s]*'
        patternV2 = re.compile(regV2, re.M | re.I)
        seObj = re.search(patternV2, line)
        isV2 = False
        if seObj:
            isV2 = True
            portName = seObj.group(2)
            if not portName:
                return False
            mac = seObj.group(1)
            if self.__port_mac_ip_map.has_key(mac):
                ip = self.__port_mac_ip_map[mac]
            else:
                ip = ''
            # ip后面根据lldp 协议和三层的arp 补全
            if not self.__port_mac_port_list.has_key(portName):
                self.__port_mac_port_list[portName] = {}

            key = self._get_port_mac_arr_key(mac, ip)
            self.__port_mac_port_list[portName][key] = {'mac': mac, 'ip': ip}
        return isV2

    def _get_port_mac_arr_key(self,mac,ip):
        return 'm:'+mac+'|ip:'+ip

    def _get_neighbor_info_by_lldp(self):
        #兼容两个版本V3V5V7 https://jingyan.baidu.com/article/86fae3461bb6cc3c49121ad1.html
        cmdOld = 'dis lldp neighbor-information  '
        cmdNew = 'dis lldp neighbor-information verbose '

        resultTxtNew = self.moreV1(self.__tnConn, cmdNew)
        if resultTxtNew and r'Management address' in resultTxtNew:
            resultTxt = resultTxtNew
        else:
            resultTxtOld = self.moreV1(self.__tnConn, cmdOld)
            if resultTxtOld and r'Management address' in resultTxtOld:
                resultTxt = resultTxtOld
            else:
                return

        resultTxt = re.split(r'(LLDP neighbor-information)', resultTxt)
        regIp = r"Management address[ ]+\:[ ]+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)"
        regPortName = r"of port [0-9]+\[([\S\s]*)\]"
        patternIp = re.compile(regIp, re.M | re.I)
        patternPortName= re.compile(regPortName, re.M | re.I)

        for item in resultTxt:
            #对端的ip
            ip = re.search(patternIp, item)
            #当前设备的端口
            portName = re.search(patternPortName,  item)
            if ip and portName:
                if self.__port_ip_mac_map.has_key(ip.group(1)):
                    mac = self.__port_ip_mac_map[ip.group(1)]
                else:
                    mac = ''

                if not self.__port_mac_port_list.has_key(portName.group(1)):
                    self.__port_mac_port_list[portName.group(1)] = {}
                key = self._get_port_mac_arr_key(mac, ip.group(1))
                self.__port_mac_port_list[portName.group(1)][key] = {'mac': mac, 'ip': ip.group(1)}

    def _get_neighbor_info_by_arp(self):
        cmd = 'show arp'
        resultTxt = self.moreV1(self.__tnConn, cmd)
        if not resultTxt:
            return
        #   192.168.16.3    487a-da74-f8e4 16         BAGG1                    1200  D
        reg = r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)[ ]+([0-9a-zA-Z\-]+)[ ][0-9]+[ ]+([GE|XGE|FE|E0|E1|40GE]+[0-9\/]+|BAGG[0-9]+)[ ]+[\S\s]*'
        pattern = re.compile(reg, re.M | re.I)
        lines = resultTxt.split("\n")
        for line in lines:
            seObj = re.search(pattern, line)
            if seObj:
                ip = seObj.group(1)
                mac = seObj.group(2)
                self.__port_mac_ip_map[mac] = ip
                self.__port_ip_mac_map[ip] = mac
                portName = self._port_name_format(seObj.group(3))

                if portName :
                    if not self.__port_mac_port_list.has_key(portName):
                        self.__port_mac_port_list[portName] = {}
                    key = self._get_port_mac_arr_key(mac, ip)
                    self.__port_mac_port_list[portName][key] = {'mac': mac, 'ip': ip}

    def _port_name_format(self,tempPort):

        portFull = ''
        if 'BAGG' in tempPort :
            portFull = tempPort.replace('BAGG', 'Bridge-Aggregation')
            return portFull
        # TODO 应该 少M-GigabitEthernet 缩写 （不知道缩写叫什么，此为管理口）
        if 'GE' in tempPort and 'XGE' not in tempPort and '40GE' not in tempPort:
            portFull = tempPort.replace('GE', 'GigabitEthernet')
            return portFull
        elif 'FE' in tempPort:
            portFull = tempPort.replace('FE', 'FastEthernet')
        elif 'XGE' in tempPort:
             portFull = tempPort.replace('XGE', 'Ten-GigabitEthernet')
        elif '40GE' in tempPort:
            portFull = tempPort.replace('40GE', 'Forty-GigabitEthernet')
        elif 'E0' in tempPort or 'E1' in tempPort:
            portFull = tempPort.replace('E', 'Ethernet')

        return portFull

    #新的获取方式，适合一次读取多条数据
    def moreV1(self, tnConn, cmd, timeout=1.5, more=True):
        escTxt = '\x08\x08'
        moreTxt = "-- More --"
        tnConn.write(cmd + '\n')
        time.sleep(timeout)
        result = tnConn.read_very_eager()

        if moreTxt in result:
            result = result.replace(escTxt, '')
            result = result.replace(moreTxt, '')
            if more:
                while more:

                    for i in range(0, 54):
                        tnConn.write(' ')
                    time.sleep(2)
                    res = tnConn.read_very_eager()
                    if moreTxt in res:
                        res = res.replace(escTxt, '')
                        res = res.replace(moreTxt, '')
                        result += res
                    else:
                        res = res.replace(escTxt, '')
                        res = res.replace(moreTxt, '')
                        result += res
                        break
            else:
                #
                tnConn.write('q')
                time.sleep(1)

        return result


    def h3c_info(self):
        try:
            self.telnet_connect()
            self.h3c_sysname()
            self.h3c_manager_info()
            self.h3c_get_version_info()
            self.h3c_flash_info()
            self.h3c_vlan_info()
            self.h3c_phy_port_info()
            self.h3c_bagg_port_info()
            self.get_neighbor_info()
            self.h3c_get_slot_info()



            #--------------------#
            result={}
            result['host_name']=self.__sysname
            result['manage'] = self.__manage_vlan_ints
            result['memory'] = self.__mem
            result['flash'] = self.__flash
            result['os_version'] = self.__os_version
            result['phy_ports'] = self.__phy_ports
            result['bagg_ports'] = self.__bagg_ports
            result['bagg_phy_port_rels'] = self.__bagg_phy_port_rels
            result['bagg_phy_port_rels'] = self.__bagg_phy_port_rels
            result['port_mac'] = self.__port_mac_port_list
            result['vlans'] = self.__vlans
            result['slots'] = self.__slot_list

            #print json.dumps(result)
            tmpJson = json.dumps(result)
            totalLen = len(tmpJson)
            readLen = 0
            while readLen < totalLen:
                if readLen + 4096 < totalLen:
                    sys.stdout.write(tmpJson[readLen:readLen + 4096])
                    readLen += 4096
                else:
                    sys.stdout.write(tmpJson[readLen:])
                    readLen = totalLen

                sys.stdout.flush()
                time.sleep(0.1)

        except Exception, e:
            msg=str(e).encode('utf-8')
            exc_type, exc_obj, exc_tb = sys.exc_info();
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            msg += "\r\n"
            info = (exc_type, fname, exc_tb.tb_lineno)
            msg += str(info)
            print msg
        except:
            print "execute exception"

if __name__ == '__main__':
    #
    #ip = '192.168.23.253'  #
    #username = 'admin'  #
    #password = 'admin'  #

    ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    h3c = H3C(ip, username, password)

    h3c.h3c_info()
    os._exit(0)
