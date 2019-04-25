#!/usr/local/python27/bin/python2
# -*- coding: utf-8 -*
import json
import re
import telnetlib
import time
import sys
import os


class Brocade:
    __tnIp = None
    __username = None
    __passwordOne = None
    __passwordTwo = None
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
    __portName_portNum_rel = {}  #端口编号和端口名称映射的字典

    __port_mac_port_list = {}  #
    __port_ip_mac_map = {}  # 端口互连对应的设备ip和mac映射
    __port_mac_ip_map = {}  # 端口互连对应的设备ip和mac映射

    def __init__(self, tnIp, username, passwordOne, passwordTwo):

        self.__tnIp = tnIp
        self.__username = username
        self.__passwordOne = passwordOne
        self.__passwordTwo = passwordTwo

    def get_all_info(self):
        try:

            self.telnet_connect()
            self.get_sysname()
            self.get_sys_os_info()
            self.get_phy_port_info()
            self.get_bagg_port_info()
            self.format_bagg_phy_port_rels()
            self.format_bagg_phy_port()
            self.get_vlan_info()
            self.format_vlan_info_ports()
            self.get_manager_info()
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
            msg += "Brocade.get_all_info execute exception\r\n"
            info = (exc_type, fname, exc_tb.tb_lineno)
            msg += str(info)
            msg += str(info)
            print msg

    # TODO 端口展现格式，和邻居展示格式没有100%确定
    def get_neighbor_info(self):
        #和卞庆丰讨论，只需要连接端的mac和ip信息，所以注释掉学习到的mac
        # self._get_neighbor_info_by_arp()
        # self._get_neighbor_info_by_learn()
        #下面方法注释掉主要是因为格式不确定，机器少，没有用例TODO
        # self._get_neighbor_info_by_lldp()
        pass

    def _get_neighbor_info_by_learn(self):
        cmd = 'show mac-address'
        resultTxt = self.more(self.__tnConn, cmd)
        if not resultTxt:
            return
        # 0050.56b0.4953  1/1/45-1/1/48  Dynamic       7812   24
        reg = r'([0-9a-zA-Z]+\.[0-9a-zA-Z]+\.[0-9a-zA-Z]+)[ ]+([0-9\-/]+)[ ]+[a-zA-Z]+[ ]+[\S\s]*'
        pattern = re.compile(reg, re.M | re.I)

        lines = resultTxt.split("\n")
        if not lines :
            return
        for line in lines:
            seObj = re.search(pattern, line)
            if seObj:
                portList = self._parse_port_to_list(seObj.group(2))
                if portList:
                    for portIndex in portList:
                        if self.__portName_portNum_rel.has_key(portIndex):
                            portName = self.__portName_portNum_rel[portIndex]
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
                            portName = self.__portName_portNum_rel[portIndex]
                            if not self.__port_mac_port_list.has_key(portName):
                                self.__port_mac_port_list[portName] = {}
                            key = self._get_port_mac_arr_key(mac, ip)
                            self.__port_mac_port_list[portName][key] = {'mac': mac, 'ip': ip}

    def _get_port_mac_arr_key(self, mac, ip):
        return 'm:' + mac + '|ip:' + ip

    #TODO
    def _get_neighbor_info_by_lldp(self):
        cmd = 'show lldp '

    def _get_neighbor_info_by_arp(self):
        cmd = 'show  arp'
        resultTxt = self.more(self.__tnConn, cmd)
        if not resultTxt:
            return

        """ 
        167   192.168.69.56   0242.c0a8.4538 Host     3   1/1/45-1/1/48  Valid  69   
        168   192.168.17.69   000b.ab56.419a Host     1   1/1/12         Valid  17   
        No.   IP              MAC            Type     Age Port           Status VLAN """
        reg = r'[0-9]+[ ]+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)[ ]+([0-9a-zA-Z\.]+)[ ]+[a-zA-Z]+[ ]+[0-9]+[ ]+([0-9\/-]+)[ ]+[a-zA-Z]+'
        pattern = re.compile(reg, re.M | re.I)
        lines = resultTxt.split("\n")
        for line in lines:
            seObj = re.search(pattern, line)
            if seObj:
                ip = seObj.group(1)
                mac = seObj.group(2)
                self.__port_mac_ip_map[mac] = ip
                self.__port_ip_mac_map[ip] = mac
                portList = self._parse_port_to_list(seObj.group(3))

                if portList :
                    for portIndex in portList:
                        if self.__portName_portNum_rel.has_key(portIndex):
                            portName = self.__portName_portNum_rel[portIndex]
                            if not self.__port_mac_port_list.has_key(portName):
                                self.__port_mac_port_list[portName] = {}
                            key = self._get_port_mac_arr_key(mac, ip)
                            self.__port_mac_port_list[portName][key] = {'mac': mac, 'ip': ip}

    #解析端口缩写，变成list
    def _parse_port_to_list(self,portStr):
        portList = []
        # 如：1/0/1-1/0/4
        if '-' in portStr :
            tmp =portStr.split('-')
            start = tmp[0]
            startList = start.split('/')

            startNum = int(startList[-1])
            startList.pop()
            pre = '/'.join(startList)
            end = tmp[-1]
            endList = end.split('/')
            endNum = int(endList[-1])

            for i in range(startNum,endNum):
                tmpStr = pre+'/'+str(i)
                portList.append(tmpStr)
        else:
            portList.append(portStr)

        return portList






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

    def get_vlan_info(self):
        cmd = 'show vlan'
        resultTxt = self.more(self.__tnConn, cmd)
        vlans = {}

        if resultTxt:
            lines = resultTxt.split("\n")
            currentVlan = None
            for line in lines:

                reg = r"PORT-VLAN ([0-9]+), Name ([0-9a-zA-Z\.\-\[\]]+), Priority level[0-9]+, [a-zA-Z ]+"
                patternVlanBase = re.compile(reg, re.M | re.I)
                reg = r"Tagged Ports: \(U([0-9]+)\/M([0-9]+)\)"
                patternTrunk= re.compile(reg, re.M | re.I)
                reg = r"Untagged Ports: \(U([0-9]+)\/M([0-9]+)\)"
                patternAccess = re.compile(reg, re.M | re.I)

                reg = r" ([0-9]+) "
                patternPortNum = re.compile(reg, re.M | re.I)

                serObj = re.search(patternVlanBase, line)
                if serObj:
                    vlanId = int(serObj.group(1))
                    oneVlan = {}
                    oneVlan['id'] = vlanId
                    currentVlan = serObj.group(1)
                    if serObj.group(2) != '[None]' :
                        oneVlan['name'] = serObj.group(2)
                    else :
                        oneVlan['name'] = ''
                    oneVlan['status'] = ''
                    oneVlan['ports'] = []
                    vlans[currentVlan] = oneVlan
                    continue

                if currentVlan :
                    serObj = re.search(patternTrunk, line)
                    if serObj :
                        portNumList = re.findall(patternPortNum, line)
                        if portNumList :
                            for v in portNumList :
                                portNum = serObj.group(1)+"/"+ serObj.group(2)+ "/"+ v
                                vlans[currentVlan]['ports'].append(portNum)
                        continue

                    serObj = re.search(patternAccess, line)
                    if serObj:
                        portNumList = re.findall(patternPortNum, line)

                        if portNumList:
                            for v in portNumList:
                                portNum = serObj.group(1) + "/" + serObj.group(2) + "/" + v
                                vlans[currentVlan]['ports'].append(portNum)
                        continue

        self.__vlans = vlans

        return vlans

    def format_bagg_phy_port_rels(self):

        if  self.__bagg_phy_port_rels and  self.__portName_portNum_rel :
            for k,v in self.__bagg_phy_port_rels.items():
                for index in range(len(v)):
                    if self.__portName_portNum_rel.has_key(v[index]):
                        self.__bagg_phy_port_rels[k][index] = self.__portName_portNum_rel[v[index]]

    def format_bagg_phy_port(self):

        if  self.__portName_portNum_rel and  self.__bagg_ports :
            #卞总说所有逻辑口用的mac地址都是端口1/1/1的
            if self.__portName_portNum_rel.has_key('1/1/1') :
                phyPort = self.__phy_ports[self.__portName_portNum_rel['1/1/1']]
                for k,v in self.__bagg_ports.items():
                    self.__bagg_ports[k]['port_mac'] = phyPort['port_mac']

    def format_vlan_info_ports(self):

        if self.__vlans and self.__portName_portNum_rel:
            for k, v in self.__vlans.items():
                for index in range(len(v['ports'])):
                    if self.__portName_portNum_rel.has_key(v['ports'][index]):
                        self.__vlans[k]['ports'][index] = self.__portName_portNum_rel[v['ports'][index]]

    def get_bagg_port_info(self):
        #
        cmd = 'show trunk'

        bagg_ports = {}
        baggPhyRels = {}

        resultTxt = self.more(self.__tnConn, cmd, 1)
        if resultTxt:#Trunk ID: 45
            portInfoList = resultTxt.split('Operational trunks:')
            if len(portInfoList) >=2 :
                portInfoList = portInfoList[1].replace("Hw Trunk ID: ",'')
                portInfoList =portInfoList.replace("\x08",' ')
            else:
                return

            portInfoList = re.split(r'(Trunk ID: [0-9]+)', portInfoList)

            relPort = r"([0-9]+/[0-9]+/[0-9]+|[0-9]+/[0-9]+)"
            relPortName = r'Trunk ID: ([0-9]+)'
            regStatus = r"Active Ports: ([0-9]+)"
            regAccessType = r"Tag: ([a-zA-Z]+)"
            regDuplex = r"Duplex: ([a-zA-Z]+)"
            regRateXs = r"Speed: ([a-zA-Z0-9]+)"

            patternRelPort = re.compile(relPort, re.M | re.I)
            patternPortName = re.compile(relPortName, re.M | re.I)
            patternAccessType = re.compile(regAccessType, re.M | re.I)
            patternDuplex = re.compile(regDuplex, re.M | re.I)
            patternRateXs = re.compile(regRateXs, re.M | re.I)
            patternStatus = re.compile(regStatus, re.M | re.I)

            # 按照名称分隔了字符串，名称被单独分到了一个元素里，内容在下一个元素
            lastPort = None
            for onePort in portInfoList:

                serObj = re.search(patternPortName, onePort)
                if serObj:

                    # 1/1/X 槽位认为是物理口，1/2/X 槽位为光口，目前博科公司此种型号这么分的，，目前没有别的字段读
                    portName = "TrunkId" + serObj.group(1)
                    bagg_ports[portName] = {}
                    bagg_ports[portName]['port_access_type'] = ''
                    bagg_ports[portName]['description'] = ''
                    bagg_ports[portName]['full_port_name'] = portName
                    bagg_ports[portName]['port_name'] = portName
                    bagg_ports[portName]['port_duplex'] = ''
                    bagg_ports[portName]['port_status'] = ''
                    bagg_ports[portName]['port_mac'] = ''
                    bagg_ports[portName]['port_rate_xs'] = ''
                    bagg_ports[portName]['port_rate'] = ''
                    lastPort = portName
                    baggPhyRels[lastPort] = {}
                    continue

                if lastPort :
                    serObj = re.findall(patternRelPort, onePort)
                    if serObj:
                            baggPhyRels[lastPort] = serObj
                    else:
                            baggPhyRels[lastPort] = {}

                    serObj = re.search(patternAccessType, onePort)
                    if serObj:
                        if serObj.group(1) == 'Yes' :
                            bagg_ports[lastPort]['port_access_type'] = 'trunk'
                        else:
                            bagg_ports[lastPort]['port_access_type'] = 'access'

                    serObj = re.search(patternDuplex, onePort)
                    if serObj:
                        bagg_ports[lastPort]['port_duplex'] = serObj.group(1)

                    serObj = re.search(patternRateXs, onePort)
                    if serObj:
                        bagg_ports[lastPort]['port_rate_xs'] = serObj.group(1)

                    serObj = re.search(patternStatus, onePort)
                    if serObj:
                        if serObj.group(1) == "0":
                            bagg_ports[lastPort]['port_status'] = 'down'
                        else:
                            bagg_ports[lastPort]['port_status'] = 'up'

                    lastPort = None

        self.__bagg_ports = bagg_ports
        self.__bagg_phy_port_rels = baggPhyRels

        return bagg_ports

    def get_phy_port_info(self):
        #
        cmd = 'show interfaces'
        resultTxt = self.more(self.__tnConn, cmd, 1)
        phy_ports = {}
        if resultTxt:
            portInfoList = re.split(r'([a-zA-Z]+[0-9\/]+ is [a-zA-Z]+, line protocol is [a-zA-Z]+)', resultTxt)

            regNameAndStatus = r"(Ten\-Gigabit|M\-Gigabit|forty\-Gigabit|Gigabit|Fast|)?Ethernet([0-9\/]+) is ([a-zA-Z]+)"
            regAccessType = r"port is tagged"
            regDuplex = r"configured duplex ([a-zA-Z]+),"
            regMac = r"address is ([a-zA-Z0-9\.-]+) "
            regRateXs = r"Configured speed ([a-zA-Z0-9\/]+), actual ([a-zA-Z0-9\/]+),"

            patternNameAndStatus = re.compile(regNameAndStatus, re.M | re.I)
            patternAccessType = re.compile(regAccessType, re.M | re.I)
            patternDuplex = re.compile(regDuplex, re.M | re.I)
            patternMac = re.compile(regMac, re.M | re.I)
            patternRateXs = re.compile(regRateXs, re.M | re.I)

            #按照名称分隔了字符串，名称被单独分到了一个元素里，内容在下一个元素
            lastPort = None
            for onePort in portInfoList:
                if cmd in onePort:
                    continue
                if self.__filterTag in onePort:
                    continue

                serObj = re.search(patternNameAndStatus, onePort)
                if serObj:

                    #1/1/X 槽位认为是物理口，1/2/X 槽位为光口，目前博科公司此种型号这么分的，，目前没有别的字段读

                    portName = serObj.group(1) + "Ethernet" + serObj.group(2)
                    phy_ports[portName] = {}
                    phy_ports[portName]['port_name'] = portName
                    phy_ports[portName]['port_status'] = serObj.group(3)
                    self.__portName_portNum_rel[serObj.group(2)] = portName
                    #暂时不处理
                    phy_ports[portName]['description'] = ''
                    phy_ports[portName]['port_rate'] = ''
                    tmpNum = serObj.group(2)
                    if tmpNum[2] == '2':
                        phy_ports[portName]['port_type'] = 'FX'
                    else:
                        phy_ports[portName]['port_type'] = 'TX'

                    lastPort = portName
                   # if(serObj.group(2) == '1/1/1') 物理口mac
                    continue

                if lastPort :
                    # 目前博科机子少也没有所谓的hybrid
                    serObj = re.search(patternAccessType, onePort)
                    if serObj:
                        phy_ports[lastPort]['port_access_type'] = 'trunk'
                    else :
                        phy_ports[lastPort]['port_access_type'] = 'access'

                    serObj = re.search(patternDuplex, onePort)
                    if serObj:
                        phy_ports[lastPort]['port_duplex'] = serObj.group(1)
                    else:
                        phy_ports[lastPort]['port_duplex'] = ''

                    serObj = re.search(patternMac, onePort)
                    if serObj:
                        phy_ports[lastPort]['port_mac'] = serObj.group(1)
                    else:
                        phy_ports[lastPort]['port_mac'] = ''

                    serObj = re.search(patternRateXs, onePort)
                    if serObj:
                        phy_ports[lastPort]['port_rate_xs'] = serObj.group(2)
                    else:
                        phy_ports[lastPort]['port_rate_xs'] = ''

                lastPort = None

        self.__phy_ports = phy_ports
        return phy_ports

    def get_items(self, text, attrs):
        result = {}

        for attr in attrs:
            if attr['get_mode'] == r'regular':
                name = attr['name']

                #
                pattern = re.compile(attr['reg'], re.M | re.I)
                serObj = re.search(pattern, text)
                if serObj:
                    result[name] = serObj.group(1)
                else:
                    result[name] = ""

        return result

    def get_bagg_phy_rel(self, text):
        ret = []
        reg = r'(Ten\-Gigabit|M\-Gigabit|forty\-Gigabit|Gigabit|Fast|)?Ethernet([0-9\/]+)'
        pattern = re.compile(reg, re.M)
        serObj = re.findall(pattern, text)

        if serObj:
            for item in serObj:
                temp = item[0] + "Ethernet" + item[1]
                ret.append(temp)
        return ret

    def get_def_vlan_ports(self, vlanId):

        def_vlan_port = []

        strVlanId = str(vlanId)
        #
        cmd = 'display  vlan ' + strVlanId
        resultTxt = self.more(self.__tnConn, cmd, 2)
        if resultTxt:
            reg = r'([GE|XGE|Eth\-Trunk|FE|E0|E1|40GE]{2,}[0-9/]+)'
            pattern = re.compile(reg, re.M)
            serObj = re.findall(pattern, resultTxt)
            if serObj:
                ports = self.parse_vlan_port_list(serObj)
                if ports:
                    def_vlan_port.extend(ports)

        return def_vlan_port

    def parse_vlan_port_list(self, portList):
        ports = []
        for tempPort in portList:
            port = self.convert_port_brief_to_full(tempPort)
            if port:
                ports.append(port)

        return ports

    # vlan 展示的端口是缩写。。
    def convert_port_brief_to_full(self, tempPort):

        portFull = False
        # TODO 应该 少M-GigabitEthernet 缩写 （不知道缩写叫什么，此为管理口）
        if 'GE' in tempPort and 'XGE' not in tempPort and '40GE' not in tempPort:
            portFull = tempPort.replace('GE', 'GigabitEthernet')
        elif 'XGE' in tempPort:
            portFull = tempPort.replace('XGE', 'Ten-GigabitEthernet')
        elif 'FE' in tempPort:
            portFull = tempPort.replace('FE', 'FastEthernet')
        elif 'Eth-Trunk' in tempPort:
            portFull = tempPort
        elif '40GE' in tempPort:
            portFull = tempPort.replace('40GE', 'Forty-GigabitEthernet')
        elif 'E0' in tempPort or 'E1' in tempPort:
            portFull = tempPort.replace('E', 'Ethernet')

        return portFull

    def get_sys_os_info(self):

        cmd = 'show Version'

        # 获取内存信息
        mems = {
            'total_mem': '',
            'used_mem': '',  # 看不到
            'used_rate': ''
        }
        flash = {
            'total_flash': '',
            'free_flash': '',  # 看不到
        }
        text = self.more(self.__tnConn, cmd, 1, False)
        if text:
            #
            reg = r"([0-9]+) ([a-zA-Z]+) DRAM"
            pattern = re.compile(reg, re.M)
            serObj = re.search(pattern, text)
            if serObj:
                unit = serObj.group(2).upper()
                mems['total_mem'] = serObj.group(1)
                if 'KB' in unit:
                    mems['total_mem'] = int(mems['total_mem']) * 1024
                elif 'MB' in unit:
                    mems['total_mem'] = int(mems['total_mem']) * 1024 * 1024

            reg = r"([0-9]+) ([a-zA-Z]+) flash memory"
            pattern = re.compile(reg, re.M)
            serObj = re.search(pattern, text)
            if serObj:
                unit = serObj.group(2).upper()
                flash['total_flash'] = serObj.group(1)
                if 'KB' in unit:
                    flash['total_flash'] = int(flash['total_flash']) * 1024
                elif 'MB' in unit:
                    flash['total_flash'] = int(flash['total_flash']) * 1024 * 1024

            reg = r"SW: (Version [0-9a-zA-Z\.\- ]+)"
            pattern = re.compile(reg, re.M | re.I)
            serObj = re.search(pattern, text)
            if serObj:
                self.__os_version = serObj.group(1)
        self.__mem = mems
        self.__flash = flash

    # 获取管理接口信息
    def get_manager_info(self):
        manager_info = {}
        if self.__portName_portNum_rel.has_key('1/1/1'):
            phyPort = self.__phy_ports[self.__portName_portNum_rel['1/1/1']]
            manager_info['mac'] = phyPort['port_mac']
        else :
            manager_info['mac'] = ''

        manager_info['ip'] = self.__tnIp
        manager_info['state'] = 'UP'
        manager_info['name'] = ''

        self.__manage_vlan_ints['default'] = manager_info

        return manager_info

    # 解析管理接口文本
    def parse_vlaninterface(self, vlanIntTxt, name):

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
        cmd = 'show running-config  | include hostname'
        resultTxt = self.more(self.__tnConn, cmd, 1)
        if resultTxt:
            reg = r"hostname ([a-zA-Z0-9\-_.]+)"
            hostname = self.patten_find(reg, resultTxt, '')
            if hostname:
                self.__sysname = hostname
                self.__filterTag = self.__sysname

    def more(self, tnConn, cmd, timeout=1.5, more=True):
        escTxt = '\x08\x08'
        moreTxt = "--More--"
        tnConn.write(cmd + '\r\n')
        time.sleep(timeout)
        result = tnConn.read_very_eager()

        if '--More--' in result:
            result = result.replace(escTxt, '')
            result = result.replace(moreTxt, '')
            if more:
                while more:

                    for i in range(0,54):
                     tnConn.write(' ')
                    time.sleep(2)
                    res = tnConn.read_very_eager()
                    if '--More--' in res:
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
        except:
            raise Exception(" ip:" + self.__tnIp + " telnet connection is fail ")

        tnconn.read_until('Please Enter Login Name:')
        tnconn.write(self.__username + '\r\n')
        tnconn.read_until('Please Enter Password:')
        tnconn.write(self.__passwordOne + '\r\n')
        time.sleep(1)
        tnconn.write('enable\r\n')
        tnconn.read_until('Password:')
        tnconn.write(self.__passwordTwo + '\r\n')
        time.sleep(1)
        self.__tnConn = tnconn
        return tnconn


if __name__ == '__main__':

    ip = sys.argv[1]
    username = sys.argv[2]
    passwordOne = sys.argv[3]
    passwordTwo = sys.argv[4]
    Brocade = Brocade(ip, username, passwordOne, passwordTwo)
    Brocade.get_all_info()
    os._exit(0)
