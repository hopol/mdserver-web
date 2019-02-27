# coding:utf-8

import sys
import io
import os
import time
import shutil

sys.path.append(os.getcwd() + "/class/core")
import public

app_debug = False
if public.isAppleSystem():
    app_debug = True


def getPluginName():
    return 'pm2'


def getPluginDir():
    return public.getPluginDir() + '/' + getPluginName()


def getServerDir():
    return public.getServerDir() + '/' + getPluginName()


def getInitDFile():
    if app_debug:
        return '/tmp/' + getPluginName()
    return '/etc/init.d/' + getPluginName()


def getArgs():
    args = sys.argv[2:]
    tmp = {}
    args_len = len(args)

    if args_len == 1:
        t = args[0].strip('{').strip('}')
        t = t.split(':')
        tmp[t[0]] = t[1]
    elif args_len > 1:
        for i in range(len(args)):
            t = args[i].split(':')
            tmp[t[0]] = t[1]

    return tmp


def checkArgs(data, ck=[]):
    for i in range(len(ck)):
        if not ck[i] in data:
            return (False, public.returnJson(False, '参数:(' + ck[i] + ')没有!'))
    return (True, public.returnJson(True, 'ok'))


def status():
    cmd = "ps -ef|grep pm2 |grep -v grep | grep -v python | awk '{print $2}'"
    data = public.execShell(cmd)
    if data[0] == '':
        return 'stop'
    return 'start'


def pm2NVMDir():
    path = '/root/.nvm'
    if public.isAppleSystem():
        user = public.execShell(
            "who | sed -n '2, 1p' |awk '{print $1}'")[0].strip()
        path = '/Users/' + user + '/.nvm'
    return path

__SR = '''#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
export HOME=/root
source %s/nvm.sh && ''' % pm2NVMDir()
__path = getServerDir() + '/list'


def pm2LogDir():
    path = '/root/.pm2'
    if public.isAppleSystem():
        user = public.execShell(
            "who | sed -n '2, 1p' |awk '{print $1}'")[0].strip()
        path = '/Users/' + user + '/.pm2'
    return path


def pm2Log():
    path = pm2LogDir() + '/pm2.log'
    return path


def pm2GetList():
    try:
        tmp = public.execShell("pm2 list|grep -v 'pm2 show'")
        t2 = tmp[0].replace("│", "").replace("└", "").replace(
            "─", "").replace("┴", "").replace("┘", "").strip().split("┤")
        if len(t2) == 1:
            return []
        tmpArr = t2[1].strip()
        if t2[1].find('App name') != -1:
            tmpArr = t2[2].strip()
        appList = tmpArr.split('\n')
        result = []
        tmp = public.execShell('lsof -c node -P|grep LISTEN')
        plist = tmp[0].split('\n')
        for app in appList:
            if not app:
                continue

            tmp2 = app.strip().split()
            appInfo = {}
            appInfo['name'] = tmp2[0]
            appInfo['id'] = tmp2[1]
            appInfo['mode'] = tmp2[3]
            appInfo['pid'] = tmp2[4]
            appInfo['status'] = tmp2[5]
            appInfo['restart'] = tmp2[6]
            appInfo['uptime'] = tmp2[7]
            appInfo['cpu'] = tmp2[8]
            appInfo['mem'] = tmp2[9] + ' ' + tmp2[10]
            appInfo['user'] = tmp2[11]
            appInfo['watching'] = tmp2[12]
            appInfo['port'] = 'OFF'
            appInfo['path'] = 'OFF'
            for p in plist:
                ptmp = p.split()
                if len(ptmp) < 8:
                    continue
                if ptmp[1] == appInfo['pid']:
                    appInfo['port'] = ptmp[8].split(':')[1].split('->')[0]
            if os.path.exists(__path + '/' + appInfo['name']):
                appInfo['path'] = public.readFile(
                    __path + '/' + appInfo['name'])
            result.append(appInfo)
        return result
    except Exception as e:
        return []


def pm2List():
    result = pm2GetList()
    return public.returnJson(True, 'ok', result)


def pm2Add():
    args = getArgs()
    data = checkArgs(args, ['path', 'run', 'pname'])
    if not data[0]:
        return data[1]

    path = args['path']
    run = args['run']
    pname = args['pname']

    runFile = (path + '/' + run).replace('//', '/')
    if not os.path.exists(runFile):
        return public.returnJson(False, '指定文件不存在!')

    nlist = pm2GetList()
    for node in nlist:
        if pname == node['name']:
            return public.returnJson(False, '指定项目名称已经存在!')
    if os.path.exists(path + '/package.json') and not os.path.exists(path + '/package-lock.json'):
        public.execShell("cd " + path + ' && npm install -s')
    public.execShell('cd ' + path + ' && pm2 start ' +
                     runFile + ' --name "' + pname + '"|grep ' + pname)
    public.execShell('pm2 save && pm2 startup')
    if not os.path.exists(__path):
        public.execShell('mkdir -p ' + __path)
    public.writeFile(__path + '/' + pname, path)
    return public.returnJson(True, '添加成功!')


def pm2Delete():
    args = getArgs()
    data = checkArgs(args, ['pname'])
    if not data[0]:
        return data[1]

    pname = args['pname']
    cmd = 'pm2 stop "' + pname + '" && pm2 delete "' + \
        pname + '" | grep "' + pname + '"'
    result = public.execShell(cmd)[0]
    if result.find('✓') != -1:
        public.execShell('pm2 save && pm2 startup')
        if os.path.exists(__path + '/' + pname):
            os.remove(__path + '/' + pname)
        return public.returnJson(True, '删除成功!')
    return public.returnJson(False, '删除失败!')


def pm2Stop():
    args = getArgs()
    data = checkArgs(args, ['pname'])
    if not data[0]:
        return data[1]

    pname = args['pname']
    result = public.execShell('pm2 stop "' + pname + '"|grep ' + pname)[0]
    if result.find('stoped') != -1:
        return public.returnJson(True, '项目[' + pname + ']已停止!')
    return public.returnJson(True, '项目[' + pname + ']停止失败!')


def pm2Start():
    args = getArgs()
    data = checkArgs(args, ['pname'])
    if not data[0]:
        return data[1]

    pname = args['pname']
    result = public.execShell('pm2 start "' + pname + '"|grep ' + pname)[0]
    if result.find('online') != -1:
        return public.returnJson(True, '项目[' + pname + ']已启动!')
    return public.returnJson(False, '项目[' + pname + ']启动失败!')


def pm2VerList():
    # 获取Node版本列表
    import re
    result = {}
    rep = 'v\d+\.\d+\.\d+'

    cmd = __SR + ' nvm ls-remote|grep -v v0|grep -v iojs'
    # print cmd
    tmp = public.execShell(cmd)
    result['list'] = re.findall(rep, tmp[0])
    tmp = public.execShell("nvm version")
    result['version'] = tmp[0].strip()
    return public.returnJson(True, 'ok', result)


if __name__ == "__main__":
    func = sys.argv[1]
    if func == 'status':
        print status()
    elif func == 'restart':
        print restart()
    elif func == 'reload':
        print reload()
    elif func == 'list':
        print pm2List()
    elif func == 'add':
        print pm2Add()
    elif func == 'delete':
        print pm2Delete()
    elif func == 'stop':
        print pm2Stop()
    elif func == 'start':
        print pm2Start()
    elif func == 'get_logs':
        print pm2Log()
    elif func == 'versions':
        print pm2VerList()
    else:
        print 'error'