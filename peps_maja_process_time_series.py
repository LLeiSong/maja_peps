#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-
import json
import time
import os
import os.path
import optparse
import sys
from datetime import date

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


# ===================== MAIN
# ==================
# parse command line
# ==================
if len(sys.argv) == 1:
    prog = os.path.basename(sys.argv[0])
    print('      ' + sys.argv[0] + ' [options]')
    print("     Aide : ", prog, " --help")
    print("        ou : ", prog, " -h")
    print("example 1 : python %s -l 'Toulouse' -a peps.txt -d 2016-12-06 -f 2017-02-01 -c S2ST" %
          sys.argv[0])
    print("example 2 : python %s --lon 1 --lat 44 -a peps.txt -d 2015-11-01 -f 2015-12-01 -c S2" %
          sys.argv[0])
    print("example 3 : python %s --lonmin 1 --lonmax 2 --latmin 43 --latmax 44 -a peps.txt -d 2015-11-01 -f 2015-12-01 -c S2" %
          sys.argv[0])
    print("example 4 : python %s -l 'Toulouse' -a peps.txt -c SpotWorldHeritage -p SPOT4 -d 2005-11-01 -f 2006-12-01" %
          sys.argv[0])
    print("example 5 : python %s -c S1 -p GRD -l 'Toulouse' -a peps.txt -d 2015-11-01 -f 2015-12-01" %
          sys.argv[0])
    sys.exit(-1)
else:
    usage = "usage: %prog [options] "
    parser = OptionParser(usage=usage)

    parser.add_option("-l", "--location", dest="location", action="store", type="string",
                      help="town name (pick one which is not too frequent to avoid confusions)", default=None)
    parser.add_option("-a", "--auth", dest="auth", action="store", type="string",
                      help="Peps account and password file")
    parser.add_option("-w", "--write_dir", dest="write_dir", action="store", type="string",
                      help="Path where the products should be downloaded", default='.')
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

    parser.add_option("--json", dest="search_json_file", action="store", type="string",
                      help="Output search JSON filename", default=None)
    parser.add_option("--windows", dest="windows", action="store_true",
                      help="For windows usage", default=False)

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

logname = "%s_%s_%s.log" % (options.tile, start_date, end_date)

# =====================
# Start Maja processing
# =====================


if options.write_dir is None:
    options.write_dir = os.getcwd()


if options.orbit is not None:
    url = "http://peps.cnes.fr/resto/wps?request=execute&service=WPS&version=1.0.0&identifier=FULL_MAJA&datainputs=startDate=%s;completionDate=%s;tileid=%s;relativeOrbitNumber=%s&status=true&storeExecuteResponse=true" % (
        start_date, end_date, options.tile, options.orbit)
else:
    url = "http://peps.cnes.fr/resto/wps?request=execute&service=WPS&version=1.0.0&identifier=FULL_MAJA&datainputs=startDate=%s;completionDate=%s;tileid=%s&status=true&storeExecuteResponse=true" % (
        start_date, end_date, options.tile)

start_maja = 'curl -o %s -k -u "%s:%s" "%s"' % (logname, email, passwd, url)
print(start_maja)
if not options.no_download:
    os.system(start_maja)
