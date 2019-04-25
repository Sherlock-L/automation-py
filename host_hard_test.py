#!/usr/local/python27/bin/python2
# -*- coding: utf-8 -*

import sys
import os
import paramiko
import json
import time
import getopt
import base64


# 主机硬件测试
class HostHardTest:
    __server_ip = ''
    __server_user = ''
    __server_passwd = ''
    __server_port = 22
    __sshClient = None
    __diskTmpFile = '/tmp/host_disk_fio_test.txt'

    def __init__(self, ip, username, password):
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
            print "command: " + command + " exec failed!\nERROR :" + err
            return True, err
        elif need_print:
            print "command: " + command + " exec success."
            out = "".join(stdout.readlines())
            if nedd_filter_char:
                out = self.backspace(out)
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

    def cpuTest(self, threads):
        command = 'sysbench cpu --cpu-max-prime=500000 --threads={0} run  > {1} &'\
            .format(params['threads'],params['reportPath'])
        self.exec_cmd(command)

    def readCpuTestReport(self, filePath):

        command = 'ps -e | grep sysbench'
        out, stdin = self.exec_cmd(command, False)
        # if process end
        if "" == out.readline():
            self.exec_cmd("cat " + filePath)

    def memTest(self, size):
        command = " memtester {0}G 1 > {1} &".format(params['memsize'], params['reportPath'])
        self.exec_cmd(command)

    def readMemTestReport(self, filePath):
        command = 'ps -e | grep memtester'
        out, stdin = self.exec_cmd(command, False)
        # if process end
        if "" == out.readline():
            self.exec_cmd("cat " + filePath,True,True)

    def diskTest(self, params):

        self.exec_cmd('echo "" > '+self.__diskTmpFile)
        if params['rw'] == 'randread':
            command = "fio --filename={0} --direct=1 --iodepth 1 --thread --rw={1} " \
                      "--ioengine=psync --bs={2} --size=2G --numjobs={3} --runtime=100 " \
                      "--group_reporting --name=mytest  > {4} & " \
                .format(self.__diskTmpFile,params['rw'], params['bs'], params['numjobs'], params['reportPath'])
        elif params['rw'] == 'randwrite':
            command = "fio --filename={0} --direct=1 --iodepth 1 --thread --rw={1} " \
                      "--ioengine=psync --bs={2} --size=2G --numjobs={3} --runtime=100 " \
                      "--group_reporting --name=mytest   > {4} & "\
                .format(self.__diskTmpFile,params['rw'], params['bs'], params['numjobs'],params['reportPath'])
        elif params['rw'] == 'randrw':
            command = "fio --filename={0} --direct=1 --iodepth 1 --thread --rw={1} " \
                      "--rwmixread=70 --ioengine=psync --bs={2} --size=2G --numjobs={3} --runtime=100 " \
                      "--group_reporting --name=mytest --ioscheduler=noop > {4} & " \
                .format(self.__diskTmpFile,params['rw'], params['bs'], params['numjobs'], params['reportPath'])
        else:
            return
        self.exec_cmd(command)

    def readDiskTestReport(self, filePath):
        command = 'ps -e | grep fio'
        out, stdin = self.exec_cmd(command, False)
        # if process end
        if "" == out.readline():
            self.exec_cmd("cat " + filePath)
            self.exec_cmd('echo "" > ' + self.__diskTmpFile,False)

    def backspace(self, str):
        try:
            out = ""
            for ch in str:
                if 0x08 == ord(ch):
                    out = out[:-1]
                else:
                    out += ch
        except Exception as e:
            print("Caught exception : " + str(e))
            out = ""

        return out


if __name__ == '__main__':
    # http://wiki.vemic.com/confluence/pages/viewpage.action?pageId=71013389  服务器性能测试工具使用说明
    opts, args = getopt.getopt(sys.argv[1:], '',
                               ['op=', 'ip=', 'username=', 'pwd=', 'base64param='])
    ip = username = password = op = None

    for opt_name, opt_value in opts:
        if opt_name == '--op':
            op = opt_value
        elif opt_name == '--ip':
            ip = opt_value
        elif opt_name == '--username':
            username = opt_value
        elif opt_name == '--pwd':
            password = opt_value
        elif opt_name == '--base64param':
            params = json.loads(base64.b64decode(opt_value))
        else:
            pass

    HostHardTest = HostHardTest(ip, username, password)
    HostHardTest.ssh_connect()
    # TODO check params
    if op == 'cpuTest':
        HostHardTest.cpuTest(params)
    elif op == 'memTest':
        HostHardTest.memTest(params)
    elif op == 'diskTest':
        HostHardTest.diskTest(params)
    elif op == 'diskReport':
        HostHardTest.readDiskTestReport(params['reportPath'])
    elif op == 'cpuReport':
        HostHardTest.readCpuTestReport(params['reportPath'])
    elif op == 'memReport':
        HostHardTest.readMemTestReport(params['reportPath'])
    else:
        print "op not define"
    HostHardTest.ssh_disconnect()
    os._exit(0)
