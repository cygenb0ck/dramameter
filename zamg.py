import configparser
import pandas
import fnmatch
import os
import matplotlib.pyplot as plt

config = None


def transpose_files(path, pattern, force = False):
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
            out_file = in_file.replace(".csv", "_transposed.csv")

            if os.path.isfile( out_file ) and force is not True:
                print("skipping {0}, transposed {1} already exists.".format(in_file, out_file))
                transposed_files.append(out_file)
                continue

            print("transposing {0}".format(in_file))
            df = pandas.read_csv(in_file, skiprows=4, encoding='iso-8859-1', delimiter=';')
            df = df.transpose()
            df.to_csv(out_file)
            transposed_files.append(out_file)

    return transposed_files


def open_files( file_list ):
    dfs = {}
    for full_file_name in file_list:
        year = full_file_name.split("/")[-1].split("_")[0]
        df = pandas.read_csv(full_file_name, header=[1,2,3,4,5,6,7,8], index_col=0, decimal=',')
        # convert index to datetime
        df.index = pandas.to_datetime( df.index, format="%d.%m.%Y" ).tz_localize("CET")
        dfs[year] = df
    return dfs


def concat_dfs( dfs ):
    df = pandas.concat( list(dfs.values()) )
    return df


def plot_df(df, column_descriptor):
    plt.clf()
    df.loc[:, column_descriptor].plot()
    plt.show()


def plot_dfs(dfs):
    plt.clf()

    fig, axes = plt.subplots( nrows = len(dfs), sharey=True )
    i = 0

    for year_str, df in dfs.items():
        df['Wien Hohe Warte']['48,2486']['16,3564']['198.0']['Anhöhe']['Ebene'] \
            ['Lufttemperatur']['Lufttemperatur um 14 MEZ (°C)'].plot(ax = axes[i])
        axes[i].set_title(year_str)
        i += 1

    plt.show()


def get_dfs_where_val_gt(dfs_in, column_descriptor, val):
    dfs_out = {}
    for k, df in dfs_in.items():
        d = df.loc[:,column_descriptor]
        dfs_out[k] = d.loc[d >= val ]
    return dfs_out

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.cfg')

    t_files = transpose_files(config['ZAMG']['local_storage'], config['ZAMG']['filename_pattern'])
    # plot_temp(t_files[0])
    dfs = open_files(t_files)
    #plot_files(dfs)
    column_descriptor = ('Wien Hohe Warte','48,2486','16,3564','198.0','Anhöhe','Ebene','Lufttemperatur','Lufttemperatur um 14 MEZ (°C)')
    d = get_dfs_where_val_gt(dfs, column_descriptor, 30.0)
