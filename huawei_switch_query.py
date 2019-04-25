#!/usr/local/python27/bin/python2
# -*- coding: utf-8 -*
import json
import re
import telnetlib
import time
import sys
import os


class Huawei:

    __tnIp = None
    __username = None
    __password = None
    __tnConn = None
    __sysname = None
    __filterTag = None

    __manage_vlan_ints = {}
    __mem = {}
    __flash = {}
    __vlans = {}
    __os_version = ''
    __phy_ports = {}  #
    __bagg_ports = {}  #
    __vlan_tag_ports = {}  # Vlan Tagged Port
    __vlan_untag_ports = {}  # Vlan Untagged Port
    __bagg_phy_port_rels = {}  #

    __port_mac_port_list = {}  #
    __port_ip_mac_map = {}  # 端口互连对应的设备ip和mac映射
    __port_mac_ip_map = {}  # 端口互连对应的设备ip和mac映射

    def __init__(self, tnIp, username, password):

        self.__tnIp = tnIp
        self.__username = username
        self.__password = password





    def get_all_info(self):
        try:

            self.telnet_connect()
            self.get_sysname()
            self.get_manager_info()
            self.get_mem_info()
            self.get_flash_info()
            self.get_vlan_info()
            self.get_os_version()
            self.get_phy_port_info()
            self.get_bagg_port_info()
            self.get_neighbor_info()


            result = {}
            result['host_name'] = self.__sysname
            result['manage'] = self.__manage_vlan_ints
            result['memory'] = self.__mem
            result['flash'] = self.__flash
            result['os_version'] = self.__os_version
            result['phy_ports'] = self.__phy_ports
            result['bagg_ports'] = self.__bagg_ports
            result['bagg_phy_port_rels'] = self.__bagg_phy_port_rels
            result['vlans'] = self.__vlans
            result['port_mac'] = self.__port_mac_port_list
            result['slots'] = {}

            # print json.dumps(result)
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


        except Exception,e:
            msg = str(e).encode('utf-8')
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            msg += "huawei.get_all_info execute exception\r\n"
            info = (exc_type, fname, exc_tb.tb_lineno)
            msg += str(info)
            msg += str(info)
            print msg

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
        #0009-4553-ac1b 1/-                               GE0/0/24            dynamic
        reg = r'([0-9a-zA-Z]+\-[0-9a-zA-Z]+\-[0-9a-zA-Z]+)[ ]+[0-9a-zA-Z\-/]+[ ]+([GE|XGE|FE|E0|E1|40GE]+[0-9\/]+|Eth\-Trunk[0-9]+)[ ]+[\S\s]*'
        pattern = re.compile(reg, re.M | re.I)

        lines = resultTxt.split("\n")
        for line in lines:
            seObj = re.search(pattern, line)
            if seObj:
                portName = self._port_name_format(seObj.group(2))
                if not portName:
                    continue
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

    def _get_port_mac_arr_key(self, mac, ip):
        return 'm:' + mac + '|ip:' + ip

    def _get_neighbor_info_by_lldp(self):

        cmd = 'display lldp nei'
        oldResultTxt= self.moreV1(self.__tnConn, cmd)
        if oldResultTxt :
            regPortName = r"([Ten\-Gigabit|M\-Gigabit|Forty\-Gigabit|Gigabit|Fast]*Ethernet[0-9\/]+[ ]+has[ ]+0[ ]+neighbors)"
            resultTxt = re.sub(regPortName," ",oldResultTxt)
            #GigabitEthernet0/0/3 has 1 neighbors:
            resultTxt = re.split(r'([0-9a-zA-Z\/]+[ ]+has[ ]+[0-9]+[ ]+neighbors:)', resultTxt)

            """GigabitEthernet0/0/21 has 1 neighbors:
                Chassis ID     :172.16.75.93 
                Port ID        :0015-65b9-49d2
            """
            regIp = r"Chassis[ ]+ID[ ]+:([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)"
            regMac = r"Port[ ]+ID[ ]+:([0-9a-zA-Z]+\-[0-9a-zA-Z]+\-[0-9a-zA-Z]+)"
            regPortName = r"([Ten\-Gigabit|M\-Gigabit|Forty\-Gigabit|Gigabit|Fast]*Ethernet[0-9\/]+)[ ]+has[ ]+[0-9]+"
            patternIp = re.compile(regIp, re.M | re.I)
            patternPortName = re.compile(regPortName, re.M | re.I)
            patternMac = re.compile(regMac, re.M | re.I)
            currentName = None

            for item in resultTxt:
                # 当前设备的端口
                portName = re.search(patternPortName, item)
                if portName :
                   currentName = portName.group(1)
                   continue

                if currentName:

                    ipObj = re.search(patternIp, item)
                    ip = ''
                    macObj = re.search(patternMac, item)
                    mac = ''
                    if ipObj :
                      ip = ipObj.group(1)
                    if macObj:
                      mac = macObj.group(1)

                    if ip or mac :
                        if not self.__port_mac_port_list.has_key(currentName):
                            self.__port_mac_port_list[currentName] = {}
                        key = self._get_port_mac_arr_key(mac, ip)
                        self.__port_mac_port_list[currentName][key] = {'mac': mac, 'ip': ip}
                    currentName = None

    def _get_neighbor_info_by_arp(self):
        cmd = 'display  arp'
        resultTxt = self.moreV1(self.__tnConn, cmd)
        if not resultTxt:
            return


        #172.16.200.106  0050-56ac-2d6d  20        D-0  GE0/0/24
        reg = r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)[ ]+([0-9a-zA-Z\-]+)[ ]+[0-9]+[ ]+[0-9a-zA-Z\-]+[ ]+([GE|XGE|FE|E0|E1|40GE]+[0-9\/]+|Eth\-Trunk[0-9]+)'
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

                if portName:
                    if not self.__port_mac_port_list.has_key(portName):
                        self.__port_mac_port_list[portName] = {}
                    key = self._get_port_mac_arr_key(mac, ip)
                    self.__port_mac_port_list[portName][key] = {'mac': mac, 'ip': ip}

    def _port_name_format(self, tempPort):

        portFull = ''
        if 'Eth-Trunk' in tempPort:
            portFull = tempPort
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

        # 新的获取方式，适合一次读取多条数据

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

    def get_vlan_info(self):
        cmd = 'display vlan | include VLAN'
        resultTxt = self.more(self.__tnConn, cmd, 2)
        vlans = {}

        if resultTxt:
            lines = resultTxt.split("\n")
            for line in lines:
                if '----' in line:
                    continue

                reg = r"([0-9]+)[ ]+([a-zA-Z]+)[ ]+([a-zA-Z]+)[ ]+([a-zA-Z]+)[ ]+([a-zA-Z]+)[ ]+([a-zA-Z0-9 ]+)"
                re_pattern = re.compile(reg, re.M | re.I)
                serObj = re.search(re_pattern, line)
                if serObj:
                    vlanId = int(serObj.group(1))
                    if vlanId <= 1024:
                        oneVlan = {}
                        oneVlan['id'] = vlanId
                        oneVlan['name'] = serObj.group(6)
                        oneVlan['status'] = serObj.group(2)
                        oneVlan['ports'] = self.get_def_vlan_ports(vlanId)

                        vlans[vlanId] = oneVlan

        self.__vlans = vlans

        return vlans

    def get_bagg_port_info(self):
        #
        cmd = 'dis int Eth-Trunk | include Eth-Trunk'
        resultTxt = self.more(self.__tnConn, cmd, 2)

        bagg_ports = {}
        port_names = {}
        baggPhyRels = {}

        if resultTxt:
            lines = resultTxt.split("\n")
            for line in lines:

                if cmd in line:
                    continue

                reg = r"(Eth-Trunk[0-9]+)"
                pattern = re.compile(reg, re.M | re.I)
                serObj = re.search(pattern, line)

                if serObj:
                    portName = serObj.group(1)
                    port_names[portName] = portName

        # ----------------------------------------#
        #
        for name in port_names:

                #
             cmd = 'display interface ' + name
             resultTxt = self.more(self.__tnConn, cmd, 1.5)

             if resultTxt :
                oneBaggPort = {}
                oneBaggPort['full_port_name'] = name
                num = self.patten_find(r"Eth-Trunk([0-9]+)", name, '')
                if num:
                    oneBaggPort['port_name'] = 'BAGG' + num
                else:
                    oneBaggPort['port_name'] = num

                #

                reg = r"Description:([a-zA-Z0-9-_.\/ ]+)\r\n"
                oneBaggPort['description'] = self.patten_find(reg, resultTxt, '')

                reg = name+r"[ ]+current[ ]+state[ ]+: ([a-zA-Z]+)"
                oneBaggPort['port_status'] = self.patten_find(reg, resultTxt, '')

                reg = r"Hardware address is ([a-zA-Z0-9\-]+)"
                oneBaggPort['port_mac'] = self.patten_find(reg, resultTxt, '')

                #FULL HALF
                reg = r"Duplex: ([a-zA-Z ]+)"
                oneBaggPort['port_duplex'] = self.patten_find(reg, resultTxt, '')


                reg = r"Current BW: ([0-9a-zA-Z ]+)"
                oneBaggPort['port_rate_xs'] = self.patten_find(reg, resultTxt, '')

                #华为看不到，php端通过端口名称识别最大速率
                reg = r"Maximal BW: ([0-9]+[a-zA-Z]+),"
                oneBaggPort['port_rate'] = self.patten_find(reg, resultTxt, '')
                oneBaggPort['port_access_type'] = ''
                bagg_ports[name] = oneBaggPort

                relPorts = self.get_bagg_phy_rel(resultTxt)
                baggPhyRels[name] = relPorts

        cmd = 'dis port vlan | include Eth-Trunk'
        resultTxt = self.more(self.__tnConn, cmd, 1.5)
        if resultTxt:
            lines = resultTxt.split("\n")
            for line in lines:
                if cmd in line:
                    continue

                if self.__filterTag in line:
                    continue
                # GigabitEthernet0/0/1    access       1     -
                reg = r"(Eth-Trunk[0-9]+)[ ]+([a-zA-Z]+)[ ]+"
                pattern = re.compile(reg, re.M | re.I)
                serObj = re.search(pattern, line)

                if serObj:
                    portName = serObj.group(1)
                    bagg_ports[portName]['port_access_type'] = serObj.group(2)


        self.__bagg_ports = bagg_ports
        self.__bagg_phy_port_rels = baggPhyRels

        return bagg_ports

    def get_phy_port_info(self):
        #
        cmd = 'display current-configuration | include '
        cmd += 'interface (Ten-Gigabit|M-Gigabit|forty-Gigabit|Gigabit|Fast|)Ethernet'
        resultTxt = self.more(self.__tnConn, cmd, 2)
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
                    portName = serObj.group(1) + "Ethernet" + serObj.group(2)
                    port_names[portName] = portName
        #
        for name in port_names:

            #
            cmd = 'display interface ' + name
            resultTxt = self.more(self.__tnConn, cmd, 1.5)
            onePhyPort = {}
            onePhyPort['port_name'] = name

            #

            reg = r"Description:([a-zA-Z0-9-_.\/ ]+)\r\n"
            onePhyPort['description'] = self.patten_find(reg, resultTxt, '')

            reg = name+r"[ ]+current[ ]+state[ ]+: ([a-zA-Z]+)"
            onePhyPort['port_status'] = self.patten_find(reg, resultTxt, '')

            reg = r"Hardware address is ([a-zA-Z0-9\-]+)"
            onePhyPort['port_mac'] = self.patten_find(reg, resultTxt, '')

            #端口的工作模式：COMMON COPPER是电口模式，COMMON FIBER是光口模式
            reg = r"Port Mode: ([a-zA-Z ]+)"
            onePhyPort['port_type'] = self.patten_find(reg, resultTxt, '')

            #FULL HALF
            reg = r"Duplex: ([a-zA-Z ]+)"
            onePhyPort['port_duplex'] = self.patten_find(reg, resultTxt, '')


            reg = r"Speed :([0-9a-zA-Z ]+)"
            onePhyPort['port_rate_xs'] = self.patten_find(reg, resultTxt, '')

            #华为看不到，php端通过端口名称识别最大速率
            onePhyPort['port_rate'] = ''
            onePhyPort['port_access_type'] = ''


            # --------------------#
            #
            phy_ports[name] = onePhyPort

        cmd = 'dis port vlan | include Ethernet'
        resultTxt = self.more(self.__tnConn, cmd, 1.5)

        if resultTxt:
            lines = resultTxt.split("\n")
            for line in lines:
                if cmd in line:
                    continue

                if self.__filterTag in line:
                    continue
                # GigabitEthernet0/0/1    access       1     -
                reg = r"(Ten\-Gigabit|M\-Gigabit|forty\-Gigabit|Gigabit|Fast|)?Ethernet([0-9\/]+)[ ]+([a-zA-Z]+)[ ]+"
                pattern = re.compile(reg, re.M | re.I)
                serObj = re.search(pattern, line)

                if serObj:
                    portName = serObj.group(1)+"Ethernet"+serObj.group(2)
                    phy_ports[portName]['port_access_type'] = serObj.group(3)

        self.__phy_ports = phy_ports

        return phy_ports

        # return phy_ports

    def get_items(self, text, attrs):
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

        return result

    def get_bagg_phy_rel(self,text):
        ret = []
        reg = r'(Ten\-Gigabit|M\-Gigabit|forty\-Gigabit|Gigabit|Fast|)?Ethernet([0-9\/]+)'
        pattern = re.compile(reg, re.M)
        serObj = re.findall(pattern, text)

        if serObj:
            for item in serObj:
                temp = item[0]+"Ethernet"+item[1]
                ret.append(temp)
        return ret

    def get_def_vlan_ports(self,vlanId):

        def_vlan_port= []

        strVlanId=str(vlanId)
        #
        cmd = 'display  vlan '+ strVlanId
        resultTxt = self.more(self.__tnConn, cmd, 2)
        if resultTxt:
            reg = r'([GE|XGE|Eth\-Trunk|FE|E0|E1|40GE]{2,}[0-9/]+)'
            pattern = re.compile(reg, re.M)
            serObj = re.findall(pattern, resultTxt)
            if serObj :
                ports = self.parse_vlan_port_list(serObj)
                if ports:
                    def_vlan_port.extend(ports)

        return def_vlan_port

    def parse_vlan_port_list(self,portList):
        ports = []
        for tempPort in portList:
            port = self.convert_port_brief_to_full(tempPort)
            if port:
                ports.append(port)

        return ports

    #vlan 展示的端口是缩写。。
    def convert_port_brief_to_full(self,tempPort):

        portFull = False
        # TODO 应该 少M-GigabitEthernet 缩写 （不知道缩写叫什么，此为管理口）
        if  'GE' in tempPort and  'XGE' not in tempPort and '40GE' not in tempPort:
            portFull = tempPort.replace('GE','GigabitEthernet')
        elif 'XGE' in tempPort :
            portFull = tempPort.replace('XGE', 'Ten-GigabitEthernet')
        elif 'FE' in tempPort:
            portFull = tempPort.replace('FE', 'FastEthernet')
        elif 'Eth-Trunk' in tempPort:
            portFull = tempPort
        elif '40GE' in tempPort :
            portFull = tempPort.replace('40GE', 'Forty-GigabitEthernet')
        elif 'E0' in tempPort or 'E1' in tempPort :
            portFull = tempPort.replace('E', 'Ethernet')

        return portFull

    def get_os_version(self):
        cmd = 'dis version | include Software'
        resultText = self.more(self.__tnConn, cmd,2)
        if resultText:
            reg = r"Software, ([a-zA-Z0-9., ()]*)"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, resultText)
            if serObj:
                self.__os_version = serObj.group(1)

        return self.__os_version

    def get_flash_info(self):

        flashs = {
            'total_flash': 0,
            'free_flash': 0,
        }
        cmd = 'dir'
        resultText = self.more(self.__tnConn, cmd)
        if resultText:
            #
            reg = r"([0-9,]+) KB total"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, resultText)
            if serObj:
                #数字带有逗号 如65,535
                total_flash = serObj.group(1).replace(',', '')
                flashs['total_flash'] = int(total_flash) * 1024

            reg = r"([0-9,]+) KB free"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, resultText)
            if serObj:
                free_flash =  serObj.group(1).replace(',', '')
                flashs['free_flash'] = int(free_flash) * 1024
            else:
                flashs['free_flash'] = 0

        self.__flash = flashs

        return flashs

    #获取内存信息
    def get_mem_info(self):

        cmd = 'display memory-usage'
        mems = {
            'total_mem': 0,
            'used_mem': 0,
            'used_rate': 0
        }
        memText = self.more(self.__tnConn, cmd,2)
        if memText:
            #
            reg = r"System Total Memory Is: ([0-9]+)"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, memText)
            if serObj:
                mems['total_mem'] = serObj.group(1)

            #
            reg = r"Total Memory Used Is: ([0-9]+)"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, memText)
            if serObj:
                mems['used_mem'] = serObj.group(1)

            #
            reg = r"Memory Using Percentage Is: ([0-9]+)%"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, memText)
            if serObj:
                mems['used_rate'] = serObj.group(1)

        self.__mem = mems

        return mems

    # 获取管理接口信息
    def get_manager_info(self):
        cmd = 'display interface vlanif'
        resultTxt = self.more(self.__tnConn, cmd)
        manage_vlan_ints = {}
        manage_vlan_int_names = {}

        if resultTxt:
            lines = resultTxt.split("\n")
            for line in lines:

                if not "Vlan" in line:
                    continue

                if self.__filterTag in line:
                    continue

                reg = r"(Vlanif[0-9]+) current state"
                vlanIntName = self.patten_find(reg, line, '')
                if vlanIntName:
                    manage_vlan_int_names[vlanIntName] = vlanIntName

            #
        for name in manage_vlan_int_names:
            cmd = 'display interface ' + name
            resultTxt = self.more(self.__tnConn, cmd)
            oneVlanInt = self.parse_vlaninterface(resultTxt, name)
            manage_vlan_ints[name] = oneVlanInt

        self.__manage_vlan_ints = manage_vlan_ints

        return manage_vlan_ints

    #解析管理接口文本
    def parse_vlaninterface(self,vlanIntTxt, name):

        one_vlan_int = {}
        one_vlan_int['name'] = name

        # state current state :
        reg = r"current state : ([a-zA-Z]+)"
        one_vlan_int['state'] = self.patten_find(reg, vlanIntTxt, '')

        # mac
        reg = r"address is ([a-zA-Z0-9.]+)"
        one_vlan_int['mac'] = self.patten_find(reg, vlanIntTxt, '')

        # ip
        reg = r"Internet Address is ([0-9.]+)"
        one_vlan_int['ip'] = self.patten_find(reg, vlanIntTxt, '')

        return one_vlan_int

    def get_sysname(self):

        cmd = 'display current-configuration | include sysname'
        resultTxt = self.more(self.__tnConn,cmd,3)

        if resultTxt:
            reg = r"sysname ([a-zA-Z0-9\-_.]+)"
            hostname = self.patten_find(reg, resultTxt, '')
            if hostname:
                self.__sysname = hostname
                self.__filterTag = self.__sysname


    def more(self,tnConn,cmd,timeout=1.5,more=True):
        escTxt = '\x08\x08'
        moreTxt = "---- More ----"

        tnConn.write(cmd + '\n')
        time.sleep(timeout)
        result = tnConn.read_very_eager()
        if '---- More ----' in result:
            result = result.replace(escTxt, '')
            result = result.replace(moreTxt, '')
            if more:
                while more:

                    tnConn.write(' ')
                    time.sleep(1)
                    res = tnConn.read_very_eager()

                    if '---- More ----' in res:
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

    def patten_find(self, patten, str, defValue=''):

        #
        re_pattern = re.compile(patten, re.M | re.I)
        serObj = re.search(re_pattern, str)
        if serObj:
            return serObj.group(1)
        else:
            return defValue

    def telnet_connect(self):
        tnconn = telnetlib.Telnet()
        try:
            tnconn.open(self.__tnIp)
        except :
           raise Exception(" ip:"+self.__tnIp +" telnet connection is fail ")

        tnconn.read_until('Username:')
        tnconn.write(self.__username + '\n')
        time.sleep(1)
        tnconn.read_until('Password:')
        tnconn.write(self.__password + '\n')
        time.sleep(2)
        self.__tnConn = tnconn
        return tnconn

if __name__ == '__main__':
    ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    huawei = Huawei(ip, username, password)
    huawei.get_all_info()
    os._exit(0)
