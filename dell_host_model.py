#!/usr/local/python27/bin/python2
# -*- coding: utf-8 -*


import time
import sys
import os
import commands
import json


class DellHostModel:
    __ip = ''
    __username = ''
    __password = ''

    __brand = ''
    __model = ''  # 型号
    __sn = ''  # 设备序列号
    __cpu = {
        "model": [],
        "num": 0
    }
    __memory = {
        "num": 0,
        "MemoryStickItems": []

    }
    __disk = {
        "num": 0,
        "diskList": []
    }
    __raid = {
        "model": ''  # 阵列卡型号
    }
    # 暂无 命令
    __hba = {

    }
    # 暂无
    __power = {

    }
    # 远程管理卡
    __remoteManageCard = {
        "name": ''
    }

    __networkCard = {
        "num": 0,
        "model": []
    }

    def __init__(self, ip, username, password):
        self.__username = username
        self.__password = password
        self.__ip = ip

    def execComand(self,command, bJson=True):
        data = commands.getoutput(command)
        if bJson == False:
            return data

        data = data.replace('"', '')
        arr = data.split("\n")
        return json.dumps(arr)

    def getBrand(self):
        command = 'snmpwalk -v 2c -c public %s 1.3.6.1.4.1.674.10892.5.1.1.4.0 | cut -d : -f4 |cut -b 3-' % (self.__ip)
        self.__brand = self.execComand(command, False)
        self.__brand = self.__brand.replace("\"",'')

    def getModel(self):
        command = 'snmpwalk -v 2c -c public %s 1.3.6.1.4.1.674.10892.5.4.300.10.1.9.1 |cut -d : -f4 |cut -b 3-' % (self.__ip)
        self.__model = self.execComand(command, False)
        self.__model = self.__model.replace("\"", '')

    def getSn(self):
        command = 'snmpwalk -v 2c -c public %s 1.3.6.1.4.1.674.10892.2.1.1.11.0 |cut -d : -f4 |cut -b 3-' % (self.__ip)
        self.__sn = self.execComand(command, False)
        self.__sn = self.__sn.replace("\"", '')

    def getCpu(self):
        modelCommand = 'snmpwalk  -c public -v 2c %s 1.3.6.1.4.1.674.10892.5.4.1100.30.1.23.1 |cut -d : -f4 |cut -b 3-' % (
            self.__ip)
        ret = self.execComand(modelCommand, False)
        lines = ret.split("\n")
        if not lines:
            return
        for line in lines:
            self.__cpu['num'] += 1
            self.__cpu['model'].append(line.replace("\"", ''))

    def getMemory(self):
        command = 'snmpwalk -v 2c -c public %s 1.3.6.1.4.1.674.10892.5.4.1100.50.1.14 |cut -d : -f4 |cut -b 2-' % (self.__ip)
        ret = self.execComand(command, False)
        lines = ret.split("\n")
        if not lines:
            return
        for line in lines:
            self.__memory['num'] += 1
            self.__memory['MemoryStickItems'].append(line)

    def getDisk(self):
        command = 'snmpwalk -v 2c -c public %s 1.3.6.1.4.1.674.10892.5.5.1.20.130.4.1.11 |cut -d : -f4 |cut -b 2-' % (self.__ip)
        ret = self.execComand(command, False)
        lines = ret.split("\n")
        if not lines:
            return
        for line in lines:
            self.__disk['num'] += 1
            self.__disk['diskList'].append(line)

    def getRemoteManageCard(self):
        command = 'snmpwalk -v 2c -c public %s 1.3.6.1.4.1.674.10892.5.4.300.60.1.8.1.1  | cut -d : -f4|cut -b 3-' % (self.__ip)
        self.__remoteManageCard['name'] = self.execComand(command, False)
        self.__remoteManageCard['name'] = self.__remoteManageCard['name'].replace("\"", '')

    def getRaid(self):
        command = 'snmpwalk -v 2c -c public %s 1.3.6.1.4.1.674.10892.5.5.1.20.130.1.1.2 |cut -d : -f4|cut -b 3-' % (self.__ip)
        self.__raid['model'] = self.execComand(command, False)
        self.__raid['model'] = self.__raid['model'].replace("\"", '')

    def getNetworkCard(self):
        command = 'snmpwalk -v 2c -c public %s 1.3.6.1.4.1.674.10892.5.4.1100.90.1.6 |cut -d : -f4 |cut -d - -f1 |cut -b 3-' % (self.__ip)

        ret = self.execComand(command, False)
        lines = ret.split("\n")
        if not lines:
            return
        for line in lines:
            self.__networkCard['num'] += 1
            self.__networkCard['model'].append(line)

    def getAllInfo(self):
        try:
            self.getBrand()
            self.getModel()
            self.getCpu()
            self.getSn()
            self.getMemory()
            self.getDisk()
            self.getRaid()
            self.getNetworkCard()
            self.getRemoteManageCard()
            result = {}
            result['brand'] = self.__brand
            result['model'] = self.__model
            result['sn'] = self.__sn
            result['cpu'] = self.__cpu
            result['memory'] = self.__memory
            result['disk'] = self.__disk
            result['raid'] = self.__raid
            result['hba'] = self.__hba
            result['networkCard'] = self.__networkCard
            result['power'] = self.__power
            result['remoteManageCard'] = self.__remoteManageCard
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
            msg += "DellHostModel.get_all_info execute exception\r\n"
            info = (exc_type, fname, exc_tb.tb_lineno)
            msg += str(info)
            msg += str(info)
            print msg



if __name__ == '__main__':
    ip = sys.argv[1]
    if len(sys.argv) == 3:
        username = sys.argv[2]
        password = sys.argv[3]
    else:
        username = ''
        password = ''
    DellHostModel = DellHostModel(ip, username, password)
    DellHostModel.getAllInfo()
    os._exit(0)
