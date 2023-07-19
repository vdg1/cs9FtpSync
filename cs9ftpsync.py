import psutil
import time
import xml.etree.ElementTree as ET
import ftplib
import io
import threading
import glob
import fnmatch
import os
from io import BytesIO
from icmplib import ping
from ftpsync.targets import FsTarget
from ftpsync.ftp_target import FTPTarget
from ftpsync.synchronizers import BiDirSynchronizer



user ="maintenance"
passwd = "spec_cal"

# create a threading class to sync the controller folder with the target
class sync(threading.Thread):
    def __init__(self, localFolder, remoteFolder, host, include=["*"]):
        threading.Thread.__init__(self)
        self.localFolder = localFolder
        self.remoteFolder = remoteFolder
        self.host = host
        self.kill = False
        self.include = include

    def run(self):
        print ("Starting sync thread for "+self.localFolder)
        while not self.kill:
            try:
                # recurse into local folders starting at self.localFolder
                for root, dirs, files in os.walk(self.localFolder):
                    # check if level is 1 (only one level deep)
                    if root.count(os.sep) == self.localFolder.count(os.sep):
                        print("root: "+root)
                        # filter dirs to include only dirs matching pattern list 'include'
                        dirs[:] = [d for d in dirs if any(fnmatch.fnmatch(d, pat) for pat in self.include)]
                    for dir in dirs:
                        # remove localFolder from root
                        root=root.replace(self.localFolder,"")
                        local = FsTarget(self.localFolder+root+"/"+dir)
                        scanRemoteFolder=self.remoteFolder+root+"/"+dir
                        remote = FTPTarget(scanRemoteFolder, host=self.host, username=user, password=passwd)
                        opts = {"force": True, "verbose": 3, "resolve": "ask", "dry_run": False, "exclude": ".git,*.bak", "match": "*", "create_folder": True, "delete_unmatched": True, "delete_extra": True, "ignore_time": False, "ignore_case": False, "ignore_existing": False, "ignore_errors": False, "preserve_perm": False, "preserve_symlinks": False, "preserve_remote_times": False, "progress": False, "stats": False, "timeshift": 0, "timeout": 15, "maxfails": 0, "maxtimeouts": 0, "maxdepth": 0, "maxsize": 0, "maxage": 0, "minsize": 0, "minage": 0, "dry_run": False, "exclude": ".git,*.bak"}
                        s = BiDirSynchronizer(local, remote, opts)
                        s.run()
            except ftplib.all_errors as e:
                print('FTP error:',self.host,":", e)
            except Exception as e:
                print('Error:', e)
            # wait 5 seconds
            time.sleep(5)
                


# function which returns a dict containing PID, cmd line arguments of processes with name 'src.exe' 
def getSRCProcesses(name):
    pid = {}
    # iterate over the all the running process and return cmd line arguments of processes with name 'src.exe'
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
      if proc.name() == name:
            # extract cmd line arguments of the process
            c=proc.cmdline()
            # parse the command line arguments of the process and extract the next argument after the argument '/USR'
            for arg in c:
                if arg == '/USR':
                    # remove last folder item from the path in the argument 
                    path=c[c.index  (arg) + 1].rsplit('\\', 1)[0]
                    # add to dict
                    pid[path] = proc
    return pid

def startFTPSyncProcess(path,processes):
    # extract controller name from path (last item of path)
    controllerName=path.rsplit('\\', 1)[1]
    # read xml config file in controller folder
    xml=ET.parse(path+"/"+controllerName+".controller")
    ns = {"ns": "http://www.staubli.com/robotics/controller/1"}
    root = xml.getroot()
    # extract the target ip address from the XML content in element 'Target' attribute 'hostname'
    target=root.find('ns:Target',ns).attrib['hostname']
    # print info and exit if target is empty
    if target == "":
        print("Target is empty")
        # return false
        return False
    print("Target: "+target)
    # ping target to check if it is online
    try:
        response = ping(target, count=1, timeout=1)
        if response.is_alive:
            print(target+" is online")
        else:
            print(target+" is offline")
            # return false
            return False
    except:
        print("Error: "+target+" is offline")
        # return false
        return False
    #
    # open controller.cfx in ./usr/configs and extract the serical number tag from the XML content
    xml=ET.parse(path+"/usr/configs/controller.cfx")
    root = xml.getroot()
    # find element of tag 'String' with attribute 'name'='SerialNumber' and return attribute 'value'
    localSerialNumber=root.find(".//String[@name='serialNumber']").attrib['value']
    # print info and exit if localSerialNumber is empty
    if localSerialNumber == "":
        print("local SerialNumber is empty")
        return False
    remoteSerialNumber=""
    print("local SerialNumber: "+localSerialNumber)
    #
    try:
        # open ftp connection to target and download /usr/configs/controller.cfx
        ftp = ftplib.FTP(host=target, user=user, passwd=passwd)
        ftp.cwd("/usr/configs")
        # retrieve file controller.cfx from target using a callback and store in string remoteXML
        remoteXML = BytesIO()
        ftp.retrbinary("RETR controller.cfx", remoteXML.write)
         # close ftp connection
        ftp.quit()
        #
        # parse remoteXML and extract the serial number tag from the XML content
        xml=ET.parse(io.StringIO(remoteXML.getvalue().decode("utf-8-sig")))
        root = xml.getroot()
        # find element of tag 'String' with attribute 'name'='SerialNumber' and return attribute 'value'
        remoteSerialNumber=root.find(".//String[@name='serialNumber']").attrib['value']
       
    except ftplib.all_errors as e:
        print('FTP error:',target,":", e)
        return False
    
    print("Remote SerialNumber: "+remoteSerialNumber)
    #
    # check if localSerialNumber and remoteSerialNumber are equal
    if localSerialNumber == remoteSerialNumber:
        print("SerialNumbers are equal")
        # create syncThread
        syncThread=sync(path+"\\usr\\usrapp", "/usr/usrapp", target, include=['a*','io*'])
        # start syncThread
        syncThread.start()
        processes[path]=syncThread

        # return true
        return True
    else:
        print("SerialNumbers are not equal")
        return False



def stopFTPSyncProcess(path,processes):
    print("stop "+path)
    processes[path].kill = True
    processes[path].join()
    del processes[path]
    print("stopped "+path)


# create main function
def main():
    cs8Processes = {}
    syncProcesses = {}

    # run an infinite loop every 5 seconds
    while True:
        # call the function to get the list of processes and print the cmd line arguments of the process
        pid = getSRCProcesses('src.exe')
        if pid:
            # iterate over the list of processes and print the command line arguments and pid of each process
            for p in pid:
                # check if cs8Processes dict does not contain the path of the process
                if p not in cs8Processes:
                    if startFTPSyncProcess(p,syncProcesses):
                        # add process to list
                        cs8Processes[p] = pid[p]
                        print("Add new src process to watch list: "+p)
                        # start ftp sync process
                        print("Start ftp sync process: "+p)
                    

        # copy cs8Processes dict to a new dict
        cs8ProcessesCopy = cs8Processes.copy()
        # iterate over cs8Processes dict and check if the process is still running
        for p in cs8ProcessesCopy:
            if p not in pid:
                # remove process from list
                print("Remove src process from watch list: "+p)
                del cs8Processes[p]
                # stop ftp sync process
                print("Stop ftp sync process: "+p)
                stopFTPSyncProcess(p, syncProcesses)
               

        
        time.sleep(10)
        
if __name__ == "__main__":
    main()