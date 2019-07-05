#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
import json
import time
import os
import os.path
import optparse
import sys
import requests
import re
from datetime import date, datetime

###########################################################################


class OptionParser (optparse.OptionParser):

    def check_required(self, opt):
        option = self.get_option(opt)

        # Assumes the option's 'default' is set to None!
        if getattr(self.values, option.dest) is None:
            self.error("%s option not supplied" % option)

###########################################################################


def parse_catalog(search_json_file):
    # Filter catalog result
    with open(search_json_file) as data_file:
        data = json.load(data_file)

    if 'ErrorCode' in data:
        print(data['ErrorMessage'])
        sys.exit(-2)

    # Sort data
    download_dict = {}
    storage_dict = {}
    size_dict = {}
    if len(data["features"]) > 0:
        for i in range(len(data["features"])):
            prod = data["features"][i]["properties"]["productIdentifier"]
            print(prod, data["features"][i]["properties"]["storage"]["mode"])
            feature_id = data["features"][i]["id"]
            try:
                storage = data["features"][i]["properties"]["storage"]["mode"]
                platform = data["features"][i]["properties"]["platform"]
                resourceSize = data["features"][i]["properties"]["resourceSize"]
                # recup du numero d'orbite
                orbitN = data["features"][i]["properties"]["orbitNumber"]
                if platform == 'S1A':
                    # calcul de l'orbite relative pour Sentinel 1A
                    relativeOrbit = ((orbitN - 73) % 175) + 1
                elif platform == 'S1B':
                    # calcul de l'orbite relative pour Sentinel 1B
                    relativeOrbit = ((orbitN - 27) % 175) + 1

                if options.orbit is not None:
                    if prod.find("_R%03d" % options.orbit) > 0:
                        download_dict[prod] = feature_id
                        storage_dict[prod] = storage
                        size_dict[prod] = resourceSize

                else:
                    download_dict[prod] = feature_id
                    storage_dict[prod] = storage
                    size_dict[prod] = resourceSize
            except:
                pass
    else:
        print(">>> no product corresponds to selection criteria")
        sys.exit(-1)

    return(prod, download_dict, storage_dict, size_dict)

###########################################################################
def check_params(start_date, stop_date, tileid, orbit=None):
    """
    Check the parameters
    :param start_date: Starting Date, format : str(XXXX-XX-XX)
    :type start_date: str
    :param stop_date: End date, format : str(XXXX-XX-XX)
    :type stop_date: str
    :param tileid: MGRS tile ID
    :type tileid: str
    :param orbit: relative orbit number
    :type orbit: int
    """
    # Check dates
    start_date = start_date.split("-")
    stop_date = stop_date.split("-")
    start_date = datetime(int(start_date[0]), int(start_date[1]), int(start_date[2]))
    stop_date = datetime(int(stop_date[0]), int(stop_date[1]), int(stop_date[2]))
    
    days = (stop_date - start_date).days
    
    if days < 55 or days > 366:
        raise ValueError("The time interval must be between 2 months and 1 year")
    
    # Check orbit number
    if orbit :
        if orbit > 143 or orbit < 1:
            raise ValueError("The relative orbit number must be between 1 and 143")
    
    # Check tile regex
    re_tile = re.compile("^[0-6][0-9][A-Za-z]([A-Za-z]){0,2}%?$")
    if not re_tile.match(tileid):
        raise ValueError("The tile ID is in the wrong format")
    

# ===================== MAIN
# ==================
# parse command line
# ==================
if len(sys.argv) == 1:
    prog = os.path.basename(sys.argv[0])
    print('      ' + sys.argv[0] + ' [options]')
    print("     Aide : ", prog, " --help")
    print("        ou : ", prog, " -h")
    print("example  : python %s -a peps.txt -t 31TCJ -d 2018-01-01 -f 2018-03-01 -w TEST_MAJA" %
          sys.argv[0])
    print("example  : python %s -a peps.txt -t 31TCJ -o 51 -g Full_MAJA_31TCJ_51_2019.log -d 2018-01-01 -f 2018-03-01" %
          sys.argv[0])
    sys.exit(-1)
else:
    usage = "usage: %prog [options] "
    parser = OptionParser(usage=usage)

    parser.add_option("-a", "--auth", dest="auth", action="store", type="string",
                      help="Peps account and password file")
    parser.add_option("-n", "--no_download", dest="no_download", action="store_true",
                      help="Do not download products, just print curl command", default=False)
    parser.add_option("-d", "--start_date", dest="start_date", action="store", type="string",
                      help="start date, fmt('2015-12-22')", default=None)
    parser.add_option("-t", "--tile", dest="tile", action="store", type="string",
                      help="tile name like 31TCK')", default=None)
    parser.add_option("-o", "--orbit", dest="orbit", action="store", type="int",
                      help="Orbit Path number", default=None)
    parser.add_option("-f", "--end_date", dest="end_date", action="store", type="string",
                      help="end date, fmt('2015-12-23')", default='9999-01-01')
    parser.add_option("-g", "--log", dest="logName", action="store", type="string",
                      help="log file name ", default='Full_Maja.log')
    parser.add_option("--json", dest="search_json_file", action="store", type="string",
                      help="Output search JSON filename", default=None)

    (options, args) = parser.parse_args()
    parser.check_required("-a")


if options.search_json_file is None or options.search_json_file == "":
    options.search_json_file = 'search.json'


# date parameters of catalog request
if options.start_date is not None:
    start_date = options.start_date
    if options.end_date is not None:
        end_date = options.end_date
    else:
        end_date = date.today().isoformat()


if options.tile.startswith('T'):
    options.tile = options.tile[1:]

# Check params
check_params(start_date, end_date, options.tile, options.orbit)

# ====================
# read authentification file
# ====================
try:
    f = open(options.auth)
    (email, passwd) = f.readline().split(' ')
    if passwd.endswith('\n'):
        passwd = passwd[:-1]
    f.close()
except:
    print("error with password file")
    sys.exit(-2)


if os.path.exists(options.search_json_file):
    os.remove(options.search_json_file)


# =====================
# Start Maja processing
# =====================
peps = "http://peps.cnes.fr/resto/wps"


if options.orbit is not None:
    url = "%s?request=execute&service=WPS&version=1.0.0&identifier=FULL_MAJA&datainputs=startDate=%s;completionDate=%s;tileid=%s;relativeOrbitNumber=%s&status=true&storeExecuteResponse=true" % (
        peps, start_date, end_date, options.tile, options.orbit)
else:
    url = "%s?request=execute&service=WPS&version=1.0.0&identifier=FULL_MAJA&datainputs=startDate=%s;completionDate=%s;tileid=%s&status=true&storeExecuteResponse=true" % (
        peps, start_date, end_date, options.tile)


print(url)
if not options.no_download:
    req = requests.get(url, auth=(email, passwd))
    with open(options.logName, "w") as f:
        f.write(req.text.encode('utf-8'))
    print("---------------------------------------------------------------------------")
    if req.status_code == 200:
        if "Process FULL_MAJA accepted" in req.text.encode('utf-8'):
            print("Request OK !")
            print("To check completion and download results:")
            print("     python full_maja_download.py -a peps.txt -g {}".format(options.logName))
        else:
            print("Something is wrong : please check {} file".format(options.logName))
    else:
        print("Wrong request status {}".format(str(req.status_code)))
    print("---------------------------------------------------------------------------")
