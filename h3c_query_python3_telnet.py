#!/usr/local/python3/bin/python3
# coding=utf-8


from netmiko import ConnectHandler
import time
import datetime
import json
import sys
import re
import logging
import os
import subprocess

class H3C:

    data={
        'hostname':None,
        'crc_list':{},
        'os_version':None,
        'port_list':{},
        'logic_port_list':{},
        'composed_logic_port':{},
        'port_vlan_list':{},
        'device_list':{},
        'port_connect_mac_list':[],
        'arp_list':[],
        'lldp_neighbor_info_list':{},
    }
    init_log_done=False
    client=None
    transport=None
    username=''
    ip=''
    funcName=''
    password = ''
    port = ''
    prompt = ''
    def recordLog(self,txt):
      if self.init_log_done:
        logging.info(txt)           
        # cmd =  "echo \'{0}\' >>{1} ".format(txt,self.exeLog)
        # handle = os.popen(cmd)
        # retTxt = handle.read()
        # handle.close()

    def run_command(self,cmd,logCmdFlag =False ):
        if logCmdFlag:
            self.recordLog(cmd)
        p = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True)
        (stdout, stderr) = p.communicate()
        if stdout:
            self.recordLog(stdout)
        if stderr:
            self.recordLog(stderr)
        
        return (stdout,stderr)
  
    def buildReponse(self,success = True,info = ''):
        res = {
            "success":success,
            "info": info
        }
        return res
   
    def outJson(self,str):  
        totalLen = len(str)
        readLen = 0
        while readLen < totalLen:
            if readLen + 4096 < totalLen:
                sys.stdout.write(str[readLen:readLen + 4096])
                readLen += 4096
            else:
                sys.stdout.write(str[readLen:])
                readLen = totalLen

            sys.stdout.flush()
            time.sleep(0.1) 

    def initClient(self):
        
        device = {
            'device_type': 'hp_comware_telnet',
            'ip': self.ip,
            'username': self.username,
            'password': self.password,
            'port': self.port,   
         }
        self.client = ConnectHandler(**device)
        self.prompt = self.client.find_prompt() 


    def closeClient(self):
        if self.client:
            self.client.disconnect()

    def queryDeviceManuinfo(self):
        cmd='display device manuinfo'
        retText = self.client.send_command(cmd)
        ret={}

        if 'Chassis' in retText:
            pattern = r'Chassis (\d+):\s+Chassis self:\s+DEVICE_NAME\s+:\s+(\S+)\s+DEVICE_SERIAL_NUMBER\s+:\s+(\S+)\s+MAC_ADDRESS\s+:\s+(\S+)\s+MANUFACTURING_DATE\s+:\s+(\S+)\s+VENDOR_NAME\s+:\s+(\S+)'
            matches = re.findall(pattern, retText, re.MULTILINE)
            for match in matches:
                chassis_number = match[0]
                device_name = match[1]
                device_serial_number = match[2]
                vendor_name = match[5]
                ret[device_serial_number]={
                  "slot_num":-1,
                  "device_sn":device_serial_number,
                  "brand":vendor_name,
                  "model":device_name,
                  "chassis_num":chassis_number,
                }
        elif 'PRODUCT' in retText:
            regex = r'Slot\s+(\d+)\s+CPU\s+0:[\s\S]+?DEVICE_SERIAL_NUMBER\s+:\s+([\w\d]+)[\s\S]+?VENDOR_NAME\s+:\s+([\w\d-]+)[\s\S]+?PRODUCT ID\s+:\s+([\w\d-]+)'
            matches = re.findall(regex, retText)
            for match in matches:
                ret[match[1]]={
                    "slot_num":match[0],
                    "device_sn":match[1],
                    "brand":match[2],
                    "model":match[3],
                   "chassis_num":-1,
                }
        else:
            regex = r'Slot\s+(\d+)\s+CPU\s+0:[\s\S]+?DEVICE_NAME\s+:\s+([\w\d-]+)[\s\S]+?DEVICE_SERIAL_NUMBER\s+:\s+([\w\d]+)[\s\S]+?VENDOR_NAME\s+:\s+([\w\d-]+)[\s\S]+?'
            matches = re.findall(regex, retText)
            for match in matches:
                ret[match[2]]={
                    "slot_num":match[0],
                    "device_sn":match[2],
                    "brand":match[3],
                    "model":match[1],
                   "chassis_num":-1,
                }


        self.data['device_list']=ret
        return  ret
            

    def queryAllPortVlan(self):
      self.data['logic_port_list']=logicPortList=  self.queryLogicPortList()   
      self.data['port_list']=portList= self.queryPortList()   
      self.data['port_vlan_list']=self.queryPortVlan(portList)
      self.data['port_vlan_list'].update(self.queryPortVlan(logicPortList))
      return self.data['port_vlan_list']

    def queryPortVlan(self,portNameList):
        ret={}
        
        for port_name in portNameList:
                portVlan=[]
                time.sleep(0.1)
                portVlanTxt=self.client.send_command(f'display interface {port_name} | include VLAN',expect_string=self.prompt, read_timeout=10)
                portVlanLines=portVlanTxt.split("\n")
                for portVlanline in portVlanLines:
                    # portVlanline='VLAN permitted: 1(default vlan), 2-12,8888,9000'
                    if 'VLAN permitted:' in portVlanline  :
                            text = re.sub(r'\([^)]*\)', '', portVlanline)
                            match = re.search(r"(?<=permitted: ).*$", text)
                            vlan_list = match.group(0).split(",")
                            for vlanNumStr in vlan_list:
                                if '-' in vlanNumStr:
                                    portVlan.append(vlanNumStr.strip()) 
                                    # start, end = map(int, v.split('-'))
                                    # portVlan[vlanKey].extend(range(start, end+1))
                                else:
                                    vlanNum=re.search(r'\d+', vlanNumStr).group()
                                    portVlan.append(vlanNum)

                ret[port_name] = portVlan
        return ret                           
        
    def queryPortCRCCount(self,port):
        # disp interface Ten-GigabitEthernet1/3/0/27 | inc CRC,
        try:
            cmdPort='disp interface {0} | inc CRC'.format(port)
            time.sleep(0.05)
            resultTxt= self.client.send_command(cmdPort)
            regCrc= r"([0-9]{1}) CRC"
            pattern = re.compile(regCrc, re.M )
            serObj = re.search(pattern, resultTxt.decode())
            # print(serObj)
            # exit(0)
            if serObj:
                return int(serObj.group(1))
            else:
                return -1
        except Exception as e:
            pass
        return -2

    def queryAllPortCRCCount(self):
        ret = {
            'phyPortList':[],
            'logicPortList':[]
        }
        phyPortList=self.queryPortList()
        logicPortList=self.queryLogicPortList()
        for port in phyPortList:
            tmpCount = self.quertPortCRCCount(port)
            ret['phyPortList'].append(
                {
                    'port_name':port,
                    'crc_count':tmpCount,
                }
            )

            
        for port in logicPortList:
            tmpCount = self.quertPortCRCCount(port)
            ret['logicPortList'].append(
                {
                    'port_name':port,
                    'crc_count':tmpCount,
                }
            )
        self.data['crc_list']=ret
        return ret            

    def queryPortList(self):   
        ret={}
        cmdPort='display interface brief '
        resultTxt=self.client.send_command(cmdPort)
        lines = resultTxt.split("\n")
        regPort = r"(GE|XGE|FE|E0|E2|E1|E3|E4|40GE)([0-9\/]{2,})"
        patternPort = re.compile(regPort, re.M )
        for line in lines:
            if 'BAGG'  in line or 'Trunk'  in line  or 'MGE' in line:
                continue
            serObjPort= re.search(patternPort, line)
            if serObjPort and serObjPort.group(1) and serObjPort.group(2):
                parts = line.split()
                port_name = parts[0]
                port_link_status = parts[1]
                port_speed = parts[2]
                #Type: A - access; T - trunk; H - hybrid
                port_link_type = parts[4]
                pvid = parts[5]
                if  len(parts)>6:
                    port_desc=parts[6]
                else:
                    port_desc=''
                
                ret[port_name] = {
                    'port_link_status': port_link_status,
                    'speed': port_speed,
                    'link_type': port_link_type,
                    'pvid': pvid,
                    'port_desc': port_desc,
                    # 'mac_address': mac_address
                }
        self.data['port_list']=ret 
        return ret  

    def queryOsVersion(self):
        ret =''
        cmd='disp version | include Software'
        retText = self.client.send_command(cmd)
        retText = retText.replace('"', '') 
        reg = r"Comware Software, ([a-zA-Z0-9., ]*)"
        pattern = re.compile(reg, re.M | re.I)
        serObj = re.search(pattern, retText)
        if serObj:
             self.data['os_version']=ret= serObj.group(1)
        return ret        

            
    def queryHostName(self):
        cmd='display current-configuration | include sysname'
        hostName = self.client.send_command(cmd)
        hostName=hostName.strip().split(' ')[1]
        #lines = resultTxt.decode().split("\n")
        self.data['hostname']=hostName
        return hostName
    
    def queryLogicPortList(self):
        ret={}
        cmdPort='display interface brief '
        resultTxt=self.client.send_command(cmdPort)
        lines = resultTxt.split("\n")

        for line in lines:
            if 'BAGG' not in line and 'Trunk' not in line :
                continue
            parts = line.split()
            port_name = parts[0]
            port_link_status = parts[1]
            port_speed = parts[2]
            #Type: A - access; T - trunk; H - hybrid
            port_link_type = parts[4]
            pvid = parts[5]
            if  len(parts)>6:
                port_desc=parts[6]
            else:
                port_desc=''
           
            ret[port_name] = {
                'port_link_status': port_link_status,
                'speed': port_speed,
                'link_type': port_link_type,
                'pvid': pvid,
                'port_desc': port_desc,                
                # 'mac_address': mac_address
            }
        self.data['logic_port_list']=ret 
        return ret        


    def queryComposedLogicPort(self):
        ret = {}
        cmd='disp link-aggregation  verbose'
        resultTxt = self.client.send_command(cmd)
        lines = resultTxt.split("\n")
        regPort = r"(GE|XGE|FE|E0|E2|E1|E3|E4|40GE)([0-9\/]{2,})"
        patternPort = re.compile(regPort, re.M )
        currentAgg = ''
        find='Agg'
        for line in lines:
            if 'Remote' in line:
                find=''
                continue
            match_aggr = re.search(r"Aggregate Interface:\s+(\S+)", line)
            if match_aggr:
                find='port'
                aggr_name = match_aggr.group(1)
                ret[aggr_name]=[]
                currentAgg=aggr_name
                continue
            if find=='port':
                find='port'
                serObjPort= re.search(patternPort, line)
                if serObjPort and serObjPort.group(1) and serObjPort.group(2):
                    port=serObjPort.group(1)+serObjPort.group(2)
                    ret[currentAgg].append(port)
                    continue
        self.data['composed_logic_port']=ret
        return ret            

    def queryArpList(self):
        cmd='disp arp'
        resultTxt = self.client.send_command(cmd)
        lines = resultTxt.split("\n")
        for line in lines:
            if 'Type:' in line or 'IP address' in line:
                continue
            parts = line.split()
            if len(parts)>5:
                self.data['arp_list'].append({
                    'ip': parts[0],
                    'mac': parts[1],
                    'port_name': parts[3],
                })
        return self.data['arp_list']
    
    def queryMacAddressList(self):
        cmd='disp mac-address'
        resultTxt = self.client.send_command(cmd)
        lines = resultTxt.split("\n")
        for line in lines:
            if 'MAC Address' in line or 'BAGG' in line or 'Trunk'  in line  or 'MGE' in line:
                continue
            parts = line.split()
            if len(parts)>3:
                self.data['port_connect_mac_list'].append({
                    'con_mac_address': parts[0],
                    'local_port': parts[3],
                })
        return self.data['port_connect_mac_list']
    
    def queryLLdpNeighborInfoList(self):
        cmd='disp lldp neighbor list'
        resultTxt = self.client.send_command(cmd)
        lines = resultTxt.split("\n")
        valFlag=False
        pattern = r'(\S+)\s+(\S+)\s+(\S+)\s+(.*)'
        for line in lines:
            if 'Port ID' in line and 'Local Interface' in line :
                valFlag=True
                continue
            if valFlag==False:
                continue
            match = re.match(pattern, line)
            if match:
                self.data['lldp_neighbor_info_list'][match.group(1)]={
                    'chassis_id': match.group(2),
                    'port_id': match.group(3),
                    'system_name': match.group(4).strip(), 
                }
        return self.data['lldp_neighbor_info_list']

if __name__ == '__main__':
    try:
        obj = H3C()
        obj.run_command('mkdir -p /var/log/switchAuto/')
        t = time.time()
        timenow = (int(t))   
        obj.exeLog = '/var/log/ihm/swithc-query-{0}-{1}.log'.format(datetime.date.today(),timenow)
        logging.basicConfig(level=logging.DEBUG,
                    filename=obj.exeLog,
                    filemode='a',
                    format=
                    '%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s'
                    )
        obj.init_log_done=True
        # xxx.sh 192.168.1.1  test testpwd 23 queryLogicPort
        obj.ip = sys.argv[1]
        obj.username = sys.argv[2]
        obj.password = sys.argv[3]
        obj.port = int(sys.argv[4])
        obj.funcName = sys.argv[5]
        obj.initClient()
        ret = ''
        if obj.funcName == 'queryComposedLogicPort':
            obj.queryComposedLogicPort()
            ret = obj.buildReponse(True,obj.data)   
        elif obj.funcName =='queryAllPortCRCCount':
            obj.queryAllPortCRCCount()
            ret = obj.buildReponse(True,obj.data)   
        elif obj.funcName =='queryDeviceManuinfo':
            obj.queryDeviceManuinfo()
            ret = obj.buildReponse(True,obj.data)           
        elif obj.funcName =='queryPortList':
            obj.queryPortList()
            ret = obj.buildReponse(True,obj.data)   
        elif obj.funcName =='queryHostName':
            obj.queryHostName()
            ret = obj.buildReponse(True,obj.data)   
        elif obj.funcName =='queryOsVersion':
            obj.queryOsVersion()
            ret = obj.buildReponse(True,obj.data)          
        elif obj.funcName =='queryLogicPortList':
            obj.queryLogicPortList()
            ret = obj.buildReponse(True,obj.data) 
        elif obj.funcName =='queryAllPortVlan':
            obj.queryAllPortVlan()
            ret = obj.buildReponse(True,obj.data)
        elif obj.funcName =='queryArpList':
            obj.queryArpList()
            ret = obj.buildReponse(True,obj.data)
        elif obj.funcName =='queryMacAddressList':
            obj.queryMacAddressList()
            ret = obj.buildReponse(True,obj.data)
        elif obj.funcName =='queryLLdpNeighborInfoList':
            obj.queryLLdpNeighborInfoList()
            ret = obj.buildReponse(True,obj.data)
        elif obj.funcName =='queryBaseInfo':
            obj.queryHostName()
            obj.queryDeviceManuinfo()
            obj.queryOsVersion()
            obj.queryPortList()
            obj.queryLogicPortList()
            obj.queryComposedLogicPort()
            ret = obj.buildReponse(True,obj.data)                                             
        else:
            ret = obj.buildReponse(False,'unknown function '+sys.argv[5])
        tmpJson = json.dumps(ret)
        obj.outJson(tmpJson)

    except Exception as e:
        msg = str(e)
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        info = (exc_type, fname, exc_tb.tb_lineno)
        msg += str(info)
        ret = obj.buildReponse(False,msg)
        obj.outJson(json.dumps(ret))
    obj.closeClient()
    os._exit(0)```




