#!/usr/local/python27/bin/python2
# -*- coding: utf-8 -*
import sys
import os
import paramiko
import json
import time
import getopt
import base64
import re
#光纤交换机
class Switch :
    
    __server_ip = ''
    __server_user = ''
    __server_passwd = ''
    __server_port = 22
    __sshClient = None

    __result = {
                "switchRole":"",
                "zoning":"",
                "switchId":"",
                "switchDomain":"",
                "switchType":"",
                "switchName":"",
                "switchWwn":"",
                "switchState":"",
                "switchBeacon":"",
                "switchMode":"",
                "portList":[],
                }
                    
   

    def __init__(self, ip, username, password):
        reload(sys)  
        sys.setdefaultencoding('utf8')   
        self.__server_user = username
        self.__server_passwd = password
        self.__server_ip = ip

    def ssh_connect(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.__server_ip, self.__server_port, self.__server_user, self.__server_passwd,None,None,None,False,False)
        self.__sshClient = ssh

    def ssh_disconnect(self):
        self.__sshClient.close()

    def exec_cmd(self, command, need_print=True,nedd_filter_char = False, bufsize=-1, timeout=None, get_pty=False, environment=None):
        '''
        客户端远程执行linux服务器上命令
        '''
        stdin, stdout, stderr = self.__sshClient.exec_command(command, bufsize, timeout, get_pty, environment)
        err = stderr.readline()

        if "" != err:
            print "command: " + command + " exec failed! ERROR :" + err
            return True, err
        elif need_print:
            print "command: " + command + " exec success."
            out = "".join(stdout.readlines())
            if nedd_filter_char:
                out = self.formatASCll(out)
            # out = json.dumps(stdout.readlines())
            totalLen = len(out)
            readLen = 0
            while readLen < totalLen:
                if readLen + 4096 < totalLen:
                    sys.stdout.write(out[readLen:readLen + 4096])
                    readLen += 4096
                else:
                    sys.stdout.write(out[readLen:])
                    readLen = totalLen

                sys.stdout.flush()
                time.sleep(0.1)
        else:
            return stdout, stdin
    
    def formatASCll(self, str):
        try:
            out = ""
            for ch in str:
                if 0x08 == ord(ch):
                    out = out[:-1]
                elif 0x0D == ord(ch):
                    out += r"\n"
                else:
                    out += ch     
        except Exception as e:
            out = ""

        return out
   
    def printDiyInfo(self):
        try:
            result = self.__result
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
        except Exception, e:
            msg = str(e).encode('utf-8')
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            msg += "printDiyInfo execute exception\r\n"
            info = (exc_type, fname, exc_tb.tb_lineno)
            msg += str(info)
            msg += str(info)
            print msg        

    def switchshow(self):
        command = r'switchshow'
        out, stdin = self.exec_cmd(command, False,True)
        portList = []
        switchNameReg = r'switchName:[\t]+(.*)\n'
        switchTypeReg= r'switchType:[\t]+(.*)\n'
        switchStateReg= r'switchState:[\t]+(.*)\n'
        switchModeReg= r'switchMode:[\t]+(.*)\n'
        switchRoleReg= r'switchRole:[\t]+(.*)\n'
        switchDomainReg= r'switchDomain:[\t]+(.*)\n'
        switchIdReg= r'switchId:[\t]+(.*)\n'
        switchWwnReg= r'switchWwn:[\t]+(.*)\n'
        zoningReg= r'zoning:[\t]+(.*)\n'
        switchBeaconReg=  r'switchBeacon:[\t]+(.*)\n'
        portReg = r'[ ]+[0-9]+[ ]+([0-9]+)[ ]+([0-9a-zA-Z]+)[ ]+([a-zA-Z]+)[ ]+([0-9a-zA-Z]+)[ ]+([a-zA-Z_]+)[ ]+([a-zA-Z]+)'
        portReg = re.compile(portReg, re.M | re.I)
        portconWwn1 = r'([0-9a-zA-Z\:]{23})'
        portconWwn2 = r"([0-9a-zA-Z]{16})"    
        if out:
            lines = out.readlines()
            for line in lines:
                serObj = re.search(portReg, line)
                if serObj:
                    tmp = {}
                    # print serObj.group(0),serObj.group(1),serObj.group(2),serObj.group(3),serObj.group(4),serObj.group(5),serObj.group(6),
                    # os._exit(0)
                    tmp["originText"] = line
                    tmp["portNum"] = serObj.group(1)
                    tmp["address"] = serObj.group(2)
                    tmp["media"] = serObj.group(3)
                    tmp["speed"] = serObj.group(4)
                    tmp["state"] = serObj.group(5)
                    tmp["proto"] = serObj.group(6)
                    serObj = re.search(portconWwn1, line)
                    if serObj:
                        tmp['conDevWwn'] = serObj.group(1) 
                    else :   
                        serObj = re.search(portconWwn2, line)
                        if serObj:
                            tmp['conDevWwn'] = serObj.group(1)   
                        else:
                            tmp['conDevWwn'] = ''
                    self.__result['portList'].append(tmp)
                    continue       
                   
                if "switchName" in line:
                    serObj = re.search(switchNameReg, line)
                    if serObj:
                        self.__result['switchName'] = serObj.group(1)
                    continue
                if "switchType" in line:
                    serObj = re.search(switchTypeReg, line)
                    if serObj:
                        self.__result['switchType'] = serObj.group(1) 
                    continue
                if "switchState" in line:
                    serObj = re.search(switchStateReg, line)
                    if serObj:
                        self.__result['switchState'] = serObj.group(1)
                    continue
                if "switchMode" in line:
                    serObj = re.search(switchModeReg, line)
                    if serObj:
                        self.__result['switchMode'] = serObj.group(1)
                    continue                       
                if "switchRole" in line:
                    serObj = re.search(switchRoleReg, line)
                    if serObj:
                        self.__result['switchRole'] = serObj.group(1)  
                    continue     
                if "switchDomain" in line:
                    serObj = re.search(switchDomainReg, line)
                    if serObj:
                        self.__result['switchDomain'] = serObj.group(1)  
                    continue     
                if "switchId" in line:
                    serObj = re.search(switchIdReg, line)
                    if serObj:
                        self.__result['switchId'] = serObj.group(1)  
                    continue     
                if "switchWwn" in line:
                    serObj = re.search(switchWwnReg, line)
                    if serObj:
                        self.__result['switchWwn'] = serObj.group(1)  
                    continue     
                if "zoning" in line:
                    serObj = re.search(zoningReg, line)
                    if serObj:
                        self.__result['zoning'] = serObj.group(1)  
                    continue     
                if "switchBeacon" in line:
                    serObj = re.search(switchBeaconReg, line)
                    if serObj:
                        self.__result['switchBeacon'] = serObj.group(1)  
                    continue 


                            


"""
命令实例   ./brocade_fs_query.py  ip=192.168.1.1  username=xx  pwd=xxx  opList=switchshow
这里opList 的值是逗号分隔的字符串，值是对应的函数名，便于以后扩展，实现非全量查询，因为可能只是获取部分信息
"""
if __name__ == '__main__':
    # 
    opts, args = getopt.getopt(sys.argv[1:], '',
                               ['opList=', 'ip=', 'username=', 'pwd='])
    opList = ip = username = password = op = None
    

    for opt_name, opt_value in opts:
        if opt_name == '--opList':
            opList = opt_value.split(',')
        elif opt_name == '--ip':
            ip = opt_value
        elif opt_name == '--username':
            username = opt_value
        elif opt_name == '--pwd':
            password = opt_value
        else:
            pass

    if opList:
        obj = Switch(ip, username, password)
        obj.ssh_connect()
        for index in range(len(opList)):
                method = getattr(obj, opList[index])
                method()   
        
        obj.printDiyInfo()  
        obj.ssh_disconnect()
    os._exit(0)
