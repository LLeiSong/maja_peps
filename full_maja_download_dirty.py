#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""
Checks if a maja processing submitted to PEPS is completed.
If completed, the product is downloaded
"""
import re
import os.path
import optparse
import sys
import requests
import shutil

###########################################################################


class OptionParser (optparse.OptionParser):

    def check_required(self, opt):
        option = self.get_option(opt)

        # Assumes the option's 'default' is set to None!
        if getattr(self.values, option.dest) is None:
            self.error("%s option not supplied" % option)

# ##########################################################################


def downloadFile(url, fileName, email, password):
    r = requests.get(url, auth=(email, password), stream=True, verify=False)
    with open(fileName, 'wb') as f:
        shutil.copyfileobj(r.raw, f)
    return


def getURL(url, fileName, email, passwd):
    req = requests.get(url, auth=(email, passwd), verify=False)
    with open(fileName, "w") as f:
        if sys.version_info[0] < 3:
            f.write(req.text.encode('utf-8'))
        else:
            f.write(req.text)
        if req.status_code == 200:
            print("Request OK")
        else:
            print("Wrong request status {}".format(str(req.status_code)))
            sys.exit(-1)

    return


# ######################### MAIN
# ==================
# parse command line
# ==================
if len(sys.argv) == 1:
    prog = os.path.basename(sys.argv[0])
    print('      ' + sys.argv[0] + ' [options]')
    print("     Aide : ", prog, " --help")
    print("        ou : ", prog, " -h")
    print("example : python %s -a peps.txt -g Full_MAJA_31TCJ_51_2019.log -w ./Full_MAJA_31TCJ_51_2019 " %
          sys.argv[0])

    sys.exit(-1)
else:
    usage = "usage: %prog [options] "
    parser = OptionParser(usage=usage)

    parser.add_option("-w", "--write_dir", dest="write_dir", action="store", type="string",
                      help="Path where the products should be downloaded", default='.')
    parser.add_option("-a", "--auth", dest="auth", action="store", type="string",
                      help="Peps account and password file")
    parser.add_option("-l", "--log", dest="logName", action="store", type="string",
                      help="log file name ", default='Full_Maja.log')

    (options, args) = parser.parse_args()
    parser.check_required("-a")

    if not (os.path.exists(options.write_dir)):
        os.mkdir(options.write_dir)
print("---------------------------------------------------------------------------")


# ====================
# read authentication file
# ====================
try:
    f = open(options.auth)
    try:
        (email, passwd) = f.readline().split(' ')
        if passwd.endswith('\n'):
            passwd = passwd[:-1]
        f.close()
    except ValueError:
        print("error with password file content")
        sys.exit(-2)
except IOError:
    print("error with password file")
    sys.exit(-2)

# =======================================
# read log file from full_maja_process.py
# =======================================

try:
    with open(options.logName) as f:
        lignes = f.readlines()
        urlStatus = None
        for ligne in lignes:
            if ligne.startswith("<wps:ExecuteResponse"):
                wpsId = ligne.split("pywps-")[1].split(".xml")[0]
                urlStatus = "https://peps.cnes.fr/cgi-bin/mapcache_results/logs/joblog-{}.log".format(wpsId)
        if urlStatus is None:
            print("url for production status not found in logName %s" % options.logName)
            sys.exit(-4)
except IOError:
    print("error with logName file provided as input or as default parameter")
    sys.exit(-3)

statusFileName = options.logName.replace('log', 'stat')
getURL(urlStatus, statusFileName, email, passwd)

# get json file from urlStatus
# ====================

urls = []
try:
    with open(statusFileName) as f:
        lignes = f.readlines()
        for ligne in lignes:
            if ligne.find("https://peps.cnes.fr/cgi-bin/mapcache_results/maja/8cd3cfe2-f263-11ea-a8ad-0242ac110002") >= 0:
                url = re.search('https:(.+).zip', ligne).group(0)
                urls.append(url)
except IOError:
    print("error with status url found in logName")
    sys.exit(-3)

for url in urls:
    L2AName = url.split('/')[-1]
    if L2AName.find('NOVALD') >= 0:
        print("%s was too cloudy" % L2AName)
    elif os.path.isfile(os.path.join(options.write_dir, L2AName)):
        print("skipping {}: already on disk".format(L2AName))
    else:
        print("downloading %s" % L2AName)
        downloadFile(url, "%s/%s" % (options.write_dir, L2AName), email, passwd)
    downloadFile(url, "%s/%s" % (options.write_dir, L2AName), email, passwd)
print("---------------------------------------------------------------------------")
