#!/usr/bin/env bash
import configparser
import mailbox
import datetime
import pytz
import dateutil.parser
import json

import matplotlib.pyplot as plt
import matplotlib

import zamg
import mailbox_tools
import datetime_tools


config = None


datetime_patterns = [
    "%a, %d %b %Y %H:%M:%S %z",       # "Sun, 30 Apr 2006 19:19:01 +0200"
    "%a, %d %b %Y %H:%M:%S %Z",       # "Fri, 25 Jul 2014 16:48:04 GMT"
    "%a, %d %b %Y %H:%M %z",          # "Tue, 11 Jun 2013 09:00 +0200"
    "%d %b %Y %H:%M:%S %z"            # "28 Aug 2008 12:58:53 +0000"
    #"%a, %d %b %Y %H:%M:%S %z (%Z)",  # "Mon, 8 Aug 2016 19:27:36 +0000 (UTC)"
    #"%a, %d %b %Y %H:%M:%S %z (PDT)", # "Thu, 6 Jun 2013 08:43:06 -0700 (PDT)"
    #"%a, %d %b %Y %H:%M:%S %z (EST)"  # "Sat, 9 Feb 2013 21:56:22 -0500 (EST)"
]

#key_pattern = "%Y-%m-%d-%H" # "2008-08-28-12"
key_pattern = "%Y-%m-%d" # "2008-08-28"

class DateFormatException(Exception):
    pass

class DatetimeEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            # return int(mktime(obj.timetuple()))
            return obj.isoformat()

        return json.JSONEncoder.default(self, obj)

def save_pretty_json( json_data, filename ):
    outfile = open( filename, "w")
    outfile.write( json.dumps(json_data, indent = 4, sort_keys = True, cls=DatetimeEncoder ) )
    outfile.close()

def load_json( filename ):
    raw_data  = open( filename ).read()
    json_data = json.loads( raw_data )
    return json_data



def convert_and_check_time( mbox ):
    for k, v in mbox.items():
        d_str = v["Date"]
        if d_str == None:
            continue

        dt = dateutil.parser.parse(d_str)


def find_date_formats(mbox):
    print("checking date formats")
    for k, v in mbox.items():
        d_str = v['Date']

        # mail archive contains one message with has no date
        if d_str is None:
            continue

        # remove timezone string identifier so we dont have to have use
        # a separate pettern for each unsupported timezone
        d_str = d_str.split(' (')[0]

        parseable = False
        for d_pattern in datetime_patterns:
            try:
                d_obj = datetime.datetime.strptime(d_str, d_pattern)
                parseable = True
                break
            except ValueError:
                pass
            except TypeError:
                print("caught TypeError!")
                print("k:         ", k)
                print("d_str:     ", d_str)
                print("d_pattern: ", d_pattern)

        if not parseable:
            print("could not convert \"{0}\" with current patterns".format(d_str))
            return


def get_datetime_from_string( d_str ):
    d_str = d_str.split(' (')[0]
    for d_pattern in datetime_patterns:
        try:
            d_obj = datetime.datetime.strptime(d_str, d_pattern)
            return d_obj
        except ValueError:
            pass
        except TypeError:
            print("caught TypeError!")
            print("d_str:     ", d_str)
    raise DateFormatException("Cannot parse ", d_str)




def get_mails_per_interval(mbox, interval_pattern):
    print("getting mails per hour")
    mails_per_interval = dict()
    for k, v in mbox.items():
        d_str = v['Date']

        if d_str == None:
            continue

        dt_obj = get_datetime_from_string(d_str)
        dt_key = datetime.datetime.strftime(dt_obj, interval_pattern)

        if dt_key not in mails_per_interval:
            mails_per_interval[dt_key] = 0

        #mails_per_day.setdefault( dt_key, 0 ).__add__(1)
        mails_per_interval[dt_key] = mails_per_interval[dt_key] + 1

    return mails_per_interval


'''
You must first convert your timestamps to Python datetime objects (use datetime.strptime).
Then use date2num to convert the dates to matplotlib format.

Plot the dates and values using plot_date:

dates = matplotlib.dates.date2num(list_of_datetimes)
plot_date(dates, values)
'''


#http://stackoverflow.com/questions/1574088/plotting-time-in-python-with-matplotlib
def plot_by_all( data ):
    x_vals = list()
    y_vals = list()
    for k in sorted(data):
        x_vals.append( datetime.datetime.strptime(k, key_pattern) )
        y_vals.append(data[k])

    x_vals2 = matplotlib.dates.date2num(x_vals)

    plt.clf()
    #plt.plot_date(x_vals2, y_vals)
    plt.plot(x_vals2, y_vals)
    plt.show()

def plot_by_interval(data, zamg_dfs = None):
    p_vals = {}
    # sort by year
    for k in sorted(data):
        v = data[k]
        d_obj = datetime.datetime.strptime(k, key_pattern)

        series_key = datetime.datetime.strftime(d_obj, "%Y")
        #data_key = datetime.datetime.strftime(d_obj, "%m-%d")

        p_vals.setdefault(series_key, dict()).setdefault("x_vals", list()).append(d_obj)
        p_vals.setdefault(series_key, dict()).setdefault("y_vals", list()).append(v)

    plt.clf()

    fig, axis = plt.subplots(nrows=len(p_vals)*2, sharex=False, sharey=False)

    a_iter = iter(axis)

    for k in sorted(p_vals):
        v = p_vals[k]
        ax = next(a_iter)

        y_vals = v["y_vals"]
        x_vals = matplotlib.dates.date2num(v["x_vals"])
        ax.plot_date(x_vals, y_vals)
        # ax.plot(x_vals, y_vals)

        ax = next(a_iter)
        if zamg_dfs is not None and k in zamg_dfs:
            df = zamg_dfs[k]
            df['Wien Hohe Warte']['48,2486']['16,3564']['198.0']['Anhöhe']['Ebene']\
                ['Lufttemperatur']['Lufttemperatur um 14 MEZ (°C)'].plot(ax=ax)

    plt.show()


def reformat_dateteime( in_date, in_pattern, out_pattern ):
    d = datetime.datetime.strptime(in_date, in_pattern)
    return datetime.datetime.strftime(d, out_pattern)


def get_pvals_for_mpds_by_dfs(mpd, filtered_dfs):
    p_vals = {}

    for period_id, df in filtered_dfs.items():
        for i in df.index:
            mpd_key = datetime.datetime.strftime(i, "%Y-%m-%d")
            p_vals.setdefault(period_id, dict()).setdefault("x_vals", list()).append(i)
            p_vals.setdefault(period_id, dict()).setdefault("y_vals", list()).append( mpd.get(mpd_key, 0) )
    return p_vals


def plot_pvals_filtered_dfs(p_vals, filtered_dfs, years = None):
    year_count = len(p_vals)

    if years is not None:
        i = 0
        for k in p_vals:
            if not k in years:
                continue
            i += 1

        year_count = i

    plt.clf()
    fig, axis = plt.subplots(nrows=year_count * 2, sharex=False, sharey=False)

    a_iter = iter(axis)

    for k in sorted(p_vals):
        if years is not None and not k in years:
            continue

        v = p_vals[k]
        ax = next(a_iter)

        y_vals = v["y_vals"]
        x_vals = matplotlib.dates.date2num(v["x_vals"])
        ax.plot_date(x_vals, y_vals, marker='x')
        # ax.plot(x_vals, y_vals)

        ax = next(a_iter)
        if filtered_dfs is not None and k in filtered_dfs:
            df = filtered_dfs[k]
            df.plot(ax=ax, marker='+', linestyle='' )

    plt.show()

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.cfg')

    intern_alt = mailbox_tools.Mailbox( "./mailman_archives/2006-May.txt" )
    # intern_alt = mailbox_tools.Mailbox( "./mailman_archives/2015_merged.txt" )
    # intern_alt = mailbox_tools.Mailbox( config['MAILMAN']['merged_mbox'] )

    # find_date_formats(mbox)

    #mpd = get_mails_per_interval(mbox, key_pattern)
    # save_pretty_json(mpd, "mpd.json")
    mpd = load_json("mpd.json")

    zamg_list = zamg.transpose_files(config['ZAMG']['local_storage'], config['ZAMG']['filename_pattern'])
    zamg_dfs = zamg.open_files(zamg_list)

    zamg_df = zamg.concat_dfs(zamg_dfs)


    # filtered_dfs = zamg.get_dfs_where_T_gt_val(zamg_dfs, 25.0)
    column_descriptor = ('Wien Hohe Warte','48,2486','16,3564','198.0','Anhöhe','Ebene','Lufttemperatur','Lufttemperatur um 14 MEZ (°C)')
    filtered_dfs = zamg.get_dfs_where_val_gt(zamg_dfs, column_descriptor, 25.0)

#    plot_by_all(mpd)
#     plot_by_interval(mpd, zamg_dfs)

#     p_vals = get_pvals_for_mpds_by_dfs(mpd, filtered_dfs)
#     plot_pvals_filtered_dfs(p_vals, filtered_dfs, ["2014","2015"])



    # # visualize mailing list

    intern_alt.build_threads_alt()
    # intern_alt.build_threads()

    #mask = (df['date'] > start_date) & (df['date'] <= end_date)
    t_wien = zamg_df.loc[ ( zamg_df.index > intern_alt.start) & ( zamg_df.index < intern_alt.end )  ]
    t_wien = t_wien.loc[:,column_descriptor]


    i_p_vals_alt = intern_alt.get_plot_values("%Y-%m-%d-%H")
    save_pretty_json(i_p_vals_alt, 'i_p_vals_alt_BRANCH_FIX.json')


    i_p_vals_from_other_working_branch = load_json("i_p_vals_BRANCH_ZAMG_INVESTIGATION.json")
    for pv_entry in i_p_vals_from_other_working_branch:
        pv_entry["x_vals"] = [ datetime_tools.get_utc_datetime_from_isoformat(x) for x in pv_entry["x_vals"] ]


    plt.clf()
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    # for p_vals in i_p_vals_alt:
    #     # ax1.plot( p_vals['x_vals'], p_vals['y_vals'])
    #     ax1.plot(p_vals['x_vals'], p_vals['y_vals'], color="b")
    #
    # for p_vals in i_p_vals_from_other_working_branch:
    #     ax1.plot(p_vals['x_vals'], p_vals['y_vals'], color="r")
    #
    # # ax1.set_yscale("log")

    # t_wien.plot( ax=ax1, color="g" )
    t_wien.plot( ax=ax2, color="r" )

    plt.show()

