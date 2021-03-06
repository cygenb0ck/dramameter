#!/usr/bin/env bash
import configparser
import mailbox
import datetime
import pytz
import dateutil.parser
import json
import os

import matplotlib.pyplot as plt
import matplotlib

import zamg
import mailbox_tools
import datetime_tools
import collections
import pandas

config = None

#key_pattern = "%Y-%m-%d-%H" # "2008-08-28-12"
key_pattern = "%Y-%m-%d" # "2008-08-28"



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


def ordereddict_from_dict_sorted_by_key( d ):
    keys = sorted(d.keys())
    od = collections.OrderedDict()
    for k in keys:
        od[k] = d[k]
    return od

def ordereddict_from_dict_sorted_by_key_inverse( d ):
    keys = list( reversed( sorted(d.keys()) ) )
    od = collections.OrderedDict()
    for k in keys:
        od[k] = d[k]
    return od


def get_mails_per_interval(mbox, interval_pattern):
    print("getting mails per hour")
    mails_per_interval = dict()
    for k, v in mbox.items():
        d_str = v['Date']

        if d_str is None:
            continue
        dt_obj = datetime_tools.get_utc_datetime_from_string_with_timezone(d_str)
        dt_key = datetime.datetime.strftime(dt_obj, interval_pattern)

        if dt_key not in mails_per_interval:
            mails_per_interval[dt_key] = 0

        mails_per_interval[dt_key] += 1

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


def plot_detailed_one_thread_per_chart(threads_by, zamg_df = None):
    total_threads = 0
    for threads in threads_by.values():
        for t in threads:
            total_threads += 1

    if total_threads == 0:
        print("no threds to plot!")
        return

    # workaround, because iterator does not work if we have only one row
    if total_threads == 1:
        fig, ax1 = plt.subplots(nrows = 1, sharex=False, sharey=False )
        t = next(iter(threads_by.values()))[0]
        title = "{0} / {1} - {2}".format(t.root.get_subject(),
                                         datetime.datetime.strftime(t.start, "%Y-%m-%d %H:%M"),
                                         datetime.datetime.strftime(t.end, "%Y-%m-%d %H:%M"))
        ax1.set_title(title)
        ax1.set_ylabel("mail count")
        t.plot_detailed(ax=ax1)
        if zamg is not None:
            delta_24h = datetime.timedelta(hours=24)
            df_for_thread = zamg_df.loc[(zamg_df.index > t.start - delta_24h) & (zamg_df.index < t.end + delta_24h)]
            if len(df_for_thread.values) > 0:
                ax2 = ax1.twinx()
                ax2.plot(df_for_thread.index, df_for_thread.values, linestyle="--")
                ax2.set_ylabel("temperature at 14:00 [°C]")

    else:

        fig, ax1 = plt.subplots( nrows = total_threads, sharex=False, sharey=False )
        ax_iter = iter(ax1)
        for threads in threads_by.values():
            for t in threads:
                ax = next(ax_iter)
                title = "{0} / {1} - {2}".format(t.root.get_subject(),
                                                 datetime.datetime.strftime(t.start, "%Y-%m-%d %H:%M"),
                                                 datetime.datetime.strftime(t.end, "%Y-%m-%d %H:%M"))
                ax.set_title(title)
                ax.set_ylabel("mail count")
                t.plot_detailed(ax=ax)
                # t.plot(ax=ax)
                if zamg_df is not None:
                    delta_24h = datetime.timedelta(hours=24)
                    df_for_thread = zamg_df.loc[(zamg_df.index > t.start-delta_24h) & (zamg_df.index < t.end+delta_24h)]
                    if len(df_for_thread.values) == 0:
                        continue
                    ax2 = ax.twinx()
                    # # pandas plot issue
                    # # x_compat=True is needed to avoid the pandas-plot issue
                    # # see https://github.com/pydata/pandas/issues/14322
                    # df_for_thread.plot(ax=ax2, x_compat=True)
                    ax2.plot(df_for_thread.index, df_for_thread.values, linestyle="--")
                    ax2.set_ylabel("temperature at 14:00 [°C]")
    plt.show()
    # plt.savefig("threads.png", bbox_inches="tight")


def plot_detailed_all_threads_above_temp_one_chart_per_year(mailbox, zamg_dfs, temp):
    column_descriptor = ('Wien Hohe Warte', '48,2486', '16,3564', '198.0', 'Anhöhe', 'Ebene', 'Lufttemperatur',
                         'Lufttemperatur um 14 MEZ (°C)')
    df_filtered = zamg.get_dfs_where_val_gt(zamg_dfs, column_descriptor, temp)

    threads = {}
    for k, df in df_filtered.items():
        date_list = [x.to_pydatetime() for x in df.index]
        t = mailbox.get_threads_active_on_dates(date_list)
        if len(t) > 0:
            threads[k] = t

    # workaround, because iterator does not work if we have only one row
    if len(threads.keys()) == 1:
        fig, axis = plt.subplots(nrows=1, sharex=False, sharey=False)
        key = next( iter( threads.keys() ) )
        for t in threads[key]:
            # t.plot_detailed(ax=axis, color="g")
            t.plot_detailed(ax=axis)
        axis2 = axis.twinx()
        df = df_filtered[key]
        axis2.set_ylabel("T [°C] at 14:00")
        # axis2.set_ylim(bottom=15, top=40)
        axis2.plot(df.index, df.values, linestyle="--", color="r")
    else:
        fig, axes = plt.subplots( nrows=len(threads.keys()), sharex=False, sharey=False )
        ax_iter = iter(axes)

        df_filtered = ordereddict_from_dict_sorted_by_key(df_filtered)
        for k, df in df_filtered.items():
            if k not in threads.keys():
                continue
            axis = next(ax_iter)
            for t in threads[k]:
                # t.plot_detailed(ax=axis, color="g")
                t.plot_detailed(ax=axis)
            axis.set_ylim(bottom=1)
            axis.set_ylabel("mailcount")
            axis2 = axis.twinx()
            axis2.set_ylabel("T [°C] at 14:00")
            axis2.plot( df.index, df.values, linestyle="--", color="r" )

    plt.show()


if __name__ == "__main__":
    if not os.path.isfile('config.cfg'):
        print("config.cfg not available. please create one based on config.cfg.example")
        quit()

    config = configparser.ConfigParser()
    config.read('config.cfg')

    # intern = mailbox_tools.Mailbox("./mailman_archives/2006-May.txt")
    # intern = mailbox_tools.Mailbox( "./mailman_archives/2015_merged.txt" )
    intern = mailbox_tools.Mailbox( config['MAILMAN']['merged_mbox'] )

    # find_date_formats(mbox)

    #mpd = get_mails_per_interval(mbox, key_pattern)
    # save_pretty_json(mpd, "mpd.json")
    # mpd = load_json("mpd.json")

    zamg_list = zamg.transpose_files(config['ZAMG']['local_storage'], config['ZAMG']['filename_pattern'])
    zamg_dfs = zamg.open_files(zamg_list)

    zamg_df = zamg.concat_dfs(zamg_dfs)


    # filtered_dfs = zamg.get_dfs_where_T_gt_val(zamg_dfs, 25.0)
    column_descriptor = ('Wien Hohe Warte','48,2486','16,3564','198.0','Anhöhe','Ebene','Lufttemperatur','Lufttemperatur um 14 MEZ (°C)')
    filtered_dfs = zamg.get_dfs_where_val_gt(zamg_dfs, column_descriptor, 25.0)

    #mask = (df['date'] > start_date) & (df['date'] <= end_date)
    # t_wien = zamg_df.loc[(zamg_df.index > intern.start) & (zamg_df.index < intern.end)]
    # t_wien = t_wien.loc[:,column_descriptor]
    t_wien = zamg_df.loc[:,column_descriptor]


    print("----- by count -----")
    by_count = intern.get_threads_by_count(min=65)
    by_count = ordereddict_from_dict_sorted_by_key_inverse(by_count)
    for k, threads in by_count.items():
        print(k)
        for t in threads:
            print("\t", t.root.get_subject())
    print("----- by duration -----")
    by_duration = intern.get_threads_by_duration(min=datetime.timedelta(days=50))
    by_duration = ordereddict_from_dict_sorted_by_key_inverse(by_duration)
    for k, threads in by_duration.items():
        print(k)
        for t in threads:
            print("\t", t.duration, t.root.get_subject())


    # plot_detailed_one_thread_per_chart(by_count, t_wien)
    plot_detailed_all_threads_above_temp_one_chart_per_year(intern, zamg_dfs, 20)
