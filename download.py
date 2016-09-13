import requests
from bs4 import BeautifulSoup
import re
import configparser
import subprocess
import os

session = None
config = None

# if True get_archive will not download, assumes data is already on disk
LOCAL = True

def get_archive( archive_name ):
    print("trying to download {0} ...".format(archive_name))

    dest_name = archive_name.replace("txt.gz","txt")

    if LOCAL:
        return dest_name

    url = config['MAILMAN']['url'] + archive_name
    archive = session.get( url )

    if not archive.ok:
        print("failed ...")
        return

    path = config['MAILMAN']['local_storage'] + "/" + dest_name
    f = open(path, "w")
    f.write(archive.text)
    f.close()

    print("... done")
    return dest_name


def merge_archives(archive_list, dest):
    try:
        os.remove(dest)
    except OSError:
        pass

    archive_list = [ config['MAILMAN']['local_storage']+ "/" + a for a in archive_list]

    cmd = "cat {0} >> {1}".format( " ".join(archive_list ), dest)
    print(cmd)
    subprocess.call(cmd, shell = True)


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

    archive_list =  [ a.get('href') for a in soup.find_all( 'a', {'href':pattern} )]
    downloaded_archives = [ get_archive(a) for a in archive_list ]

    merge_archives(downloaded_archives,config['MAILMAN']['merged_mbox'])