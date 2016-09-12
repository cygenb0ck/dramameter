import requests
from bs4 import BeautifulSoup
import re

import configparser

session = None
config = None

def get_archive( archive_name ):
    print("trying to download {0} ...".format(archive_name))

    url = config['MAILMAN']['url'] + archive_name
    archive = session.get( url )

    if not archive.ok:
        print("failed ...")
        return

    path = config['MAILMAN']['local_storage'] + "/" + archive_name.replace("txt.gz","txt")
    f = open(path, "w")
    f.write(archive.text)
    f.close()

    print("... done")


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.cfg')

    login_data = {
        'username' : config['MAILMAN']['username'],
        'password' : config['MAILMAN']['password'] }

    session = requests.Session()
    overview = session.post(config['MAILMAN']['url'], login_data)

    if not overview.ok:
        print("login failed!")
        quit()

    soup = BeautifulSoup(overview.text)

    pattern = re.compile("\d{4}-\w+\.txt.gz")

    for a in soup.find_all( 'a', { 'href' : pattern } ):
        get_archive( a.get('href') )

