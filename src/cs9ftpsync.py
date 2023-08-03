import psutil
import time
import xml.etree.ElementTree as ET
import ftplib
import io
import threading
import glob
import fnmatch
import os
import datetime
from io import BytesIO
from icmplib import ping
from windows_toasts import WindowsToaster, ToastText2
from ftpsync.targets import FsTarget
from ftpsync.ftp_target import FTPTarget
from ftpsync.synchronizers import BiDirSynchronizer
from configparser import ConfigParser
# import version.py from the same folder
from version import __version__

print(f"Running version: {__version__}")



#inherit from BiDirSynchronizer to override some methods
class MyBiDirSynchronizer(BiDirSynchronizer):
    # override init
    def __init__(self, local, remote, options):
        super().__init__(local, remote, options)
        # list of upload/download files
        self._upload_pairs = []
        self._download_pairs = []
        self._delete_pairs = []

    def _interactive_resolve(self, pair):
        return super()._interactive_resolve( pair)
    
    # override on_copy_lo,cal
    def on_copy_local(self, pair):
        self._upload_pairs.append(pair)
        return super().on_copy_local(pair)
    
    # override on_copy_remote
    def on_copy_remote(self, pair):
        self._download_pairs.append(pair)
        return super().on_copy_remote(pair)
    
    # override on_delete_local
    def on_delete_local(self, pair):
        self._delete_pairs.append(pair)
        # call the parent method on_delete_local
        return super().on_delete_local(pair)
    
    # override on_delete_remote
    def on_delete_remote(self, pair):
        self._delete_pairs.append(pair)
        # call the parent method on_delete_remote
        return super().on_delete_remote(pair)
    

    
        
    

# create a threading class to sync the controller folder with the target
class sync(threading.Thread):
    def __init__(self, localFolder, remoteFolder, host, username, password, include=["*"], checkInterval=5):
        threading.Thread.__init__(self)
        self.localFolder = localFolder
        self.remoteFolder = remoteFolder
        self.host = host
        self.kill = False
        self.include = include
        self.username = username
        self.password = password
        self.checkInterval = checkInterval


    def run(self):
        print ("Starting sync thread for "+self.localFolder)
        while not self.kill:
            downloadedPaths = []
            try:
                # recurse into local folders starting at self.localFolder                
                for root, dirs, files in os.walk(self.localFolder):
                    # check if level is 1 (only one level deep)
                    if root.count(os.sep) == self.localFolder.count(os.sep):
                        # filter dirs to remove entries that do not match any pattern in list self.include
                        dirs[:] = [d for d in dirs if any(fnmatch.fnmatch(d, pattern) for pattern in self.include)]
                        
                    for dir in dirs:
                        # remove localFolder from root
                        root=root.replace(self.localFolder,"")
                        local = FsTarget(self.localFolder+root+"/"+dir)
                        scanRemoteFolder=self.remoteFolder+root+"/"+dir
                        remote = FTPTarget(scanRemoteFolder, host=self.host, username=self.username, password=self.password)
                        opts = {"force": True, "verbose": 3, "resolve": "ask", "dry_run": False, "exclude": ".git,*.bak", "match": "*", "create_folder": True, "delete_unmatched": True, "delete_extra": True, "ignore_time": False, "ignore_case": False, "ignore_existing": False, "ignore_errors": False, "preserve_perm": False, "preserve_symlinks": False, "preserve_remote_times": False, "progress": False, "stats": False, "timeshift": 0, "timeout": 15, "maxfails": 0, "maxtimeouts": 0, "maxdepth": 0, "maxsize": 0, "maxage": 0, "minsize": 0, "minage": 0, "dry_run": False, "exclude": ".git,*.bak"}
                        s = MyBiDirSynchronizer(local, remote, opts)
                        s.run()
            
                        print("")
                        if len(s._upload_pairs) > 0 or len(s._download_pairs) > 0:
                            print("Uploaded files:",len(s._upload_pairs))
                            print("Downloaded files:",len(s._download_pairs))
                        if len(s._download_pairs) > 0:
                            # consolidate the pairs list by removing duplicates of the same relative path of the local file
                    
                            for downloadedPath in s._download_pairs:
                                if downloadedPath.local is not None and not any(x == downloadedPath.local.rel_path for x in downloadedPaths):
                                    downloadedPaths.append(downloadedPath.local.rel_path)
                            
                                    
            except ftplib.all_errors as e:
                print('FTP error:',self.host,":", e)
            except Exception as e:
                print('Error:', e)

            if len(downloadedPaths) > 0:
                reloadApps = self.checkTouchedFolders(downloadedPaths)
                # create a windows toast message
                toaster = WindowsToaster("CS9 FTP Syncronisation")
                newToast = ToastText2()
                t=datetime.datetime.now()
                # add 20 seconds to the current time
                t=t+datetime.timedelta(seconds=20)
                newToast.SetExpirationTime(t)
                newToast.SetBody("Applications were downloaded from controller. Consider to reload following applications in SRS")
                line=", ".join(reloadApps)
                newToast.SetFirstLine(line)
                toaster.show_toast(newToast)
            # wait 5 seconds
            time.sleep(self.checkInterval)

    def checkTouchedFolders(self, downloadedPaths):
        reloadApps = []
                # iterate over pairs and walk up the folder tree to find the first folder that contains a *.dtx file
        for downloadedPath in downloadedPaths:
                    # split the relative path of the local file into a list of folders
            folders = downloadedPath.split("\\")
                    # iterate over the list of folders starting at the last folder
            for i in range(len(folders),0,-1):
                        # join the folders to a path
                path = "/".join(folders[0:i])
                        # check if the path contains a *.dtx file
                if len(glob.glob(path+"/*.dtx")) > 0:
                            # remove from start up to and including 'usrapp/' from the path
                    path = path[path.find("usrapp")+len("usrapp")+1:]
                            # add the path to the list of folders to reload
                    reloadApps.append(path)
                            # break the loop
                    break
        return reloadApps
                


# function which returns a dict containing PID, cmd line arguments of processes with name 'src.exe' 
def getSRCProcesses():
    pid = {}
    # iterate over all running process and return cmd line arguments of processes with name 'src.exe'
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
      if proc.name() == "src.exe":
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
    include = ["*"]
    # open config file ftpsync.ini in path using config parser
    config = ConfigParser()
    config.read(path+"/ftpsync.ini")
    # check if config file could be read
    if not config.sections():
        print("Error reading ftpsync.ini in ",path)
        return False
    # check if config file contains section 'ftpsync' and option 'enable' and if it is set to 'false'
    if config.has_option('ftpsync', 'enabled') and not config.getboolean('ftpsync', 'enabled'):
        print("ftpsync is disabled for ",path)
        return False
    # check if config file has option 'checkInterval' and if it is set to a value > 0
    if config.has_option('ftpsync', 'checkInterval') and config.getint('ftpsync', 'checkInterval') > 0:
        checkInterval = config.getint('ftpsync', 'checkInterval')
    else:
        checkInterval = 10
    
    # retrieve username and password from config file
    if config.has_option('ftpsync', 'username'):
        user = config.get('ftpsync', 'username')
    if config.has_option('ftpsync', 'password'):
        passwd = config.get('ftpsync', 'password')
    if config.has_option('ftpsync', 'include'):
        include = config.get('ftpsync', 'include').split(',')
        # remove leading and trailing spaces from items in list
        include = [x.strip() for x in include]
    # check if username and password are empty
    if user == "" or passwd == "":
        print("username or password is empty")
        return False
    

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
        syncThread=sync(path+"\\usr\\usrapp", "/usr/usrapp", target, user, passwd, include=include, checkInterval=checkInterval)
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


def main():
    cs8Processes = {}
    syncProcesses = {}

    # run an infinite loop every 5 seconds
    while True:
        # call the function to get the list of processes and print the cmd line arguments of the process
        pids = getSRCProcesses()
        if pids:
            # iterate over the list of processes and print the command line arguments and pid of each process
            for p in pids:
                # check if cs8Processes dict does not contain the path of the process
                if p not in cs8Processes:
                    if startFTPSyncProcess(p,syncProcesses):
                        # add process to list
                        cs8Processes[p] = pids[p]
                        print("Added new src.exe process to watch list: "+p)
                    

        # copy cs8Processes dict to a new dict
        cs8ProcessesCopy = cs8Processes.copy()
        # iterate over cs8Processes dict and check if the process is still running
        for p in cs8ProcessesCopy:
            # check if process is not running anymore or process was terminated
            
            if p not in pids or not pids[p].is_running():
                # remove process from list
                print("Remove src process from watch list: "+p)
                del cs8Processes[p]
                # stop ftp sync process
                print("Stop ftp sync process: "+p)
                stopFTPSyncProcess(p, syncProcesses)
               

        
        time.sleep(10)
        
if __name__ == "__main__":
    main()