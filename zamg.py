import configparser
import pandas
import fnmatch
import os
import matplotlib.pyplot as plt

config = None


def transpose_zamg_files(path, pattern):
    '''
    looks for ZAMG Jahrbuch csv files in PATH matching PATTERN, loads them using panda with
     skiprows=4, encoding='iso-8859-1', delimiter=';'
     transposes them and saves them, adding "_transposed" before the end
    :param path: path where to look for files
    :param pattern: pattern to match against
    :return: a list holding the complete filenames including path of the transposed files
    '''
    transposed_files = list()
    for file in os.listdir(path):
        if fnmatch.fnmatch(file, pattern):
            in_file = path + file
            df = pandas.read_csv(in_file, skiprows=4, encoding='iso-8859-1', delimiter=';')
            df = df.transpose()
            out_file = in_file.replace(".csv", "_transposed.csv")
            df.to_csv(out_file)
            transposed_files.append(out_file)
    return transposed_files


def plot_zamg_temp(zamg_file ):
    print(zamg_file)
    df = pandas.read_csv(zamg_file, header=[1,2,3,4,5,6,7,8], index_col=0, decimal=',')
    df['Wien Hohe Warte']['48,2486']['16,3564']['198.0']['Anhöhe']['Ebene']\
        ['Lufttemperatur']['Lufttemperatur um 14 MEZ (°C)'].plot()
    plt.show()


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.cfg')

    t_files = transpose_zamg_files( config['ZAMG']['local_storage'], config['ZAMG']['filename_pattern'] )
    plot_zamg_temp( t_files[0] )
