#!/usr/bin/env bash
import configparser
import mailbox
import datetime
import json

import matplotlib.pyplot as plt
import matplotlib


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

def save_pretty_json( json_data, filename ):
    outfile = open( filename, "w")
    outfile.write( json.dumps(json_data, indent = 4, sort_keys = True ) )
    outfile.close()

def load_json( filename ):
    raw_data  = open( filename ).read()
    json_data = json.loads( raw_data )
    return json_data


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


def test_plot(tags_by_interval, func_date_key_to_timestamp, filename=None):
    sorted_keys = tags_by_interval.keys()
    sorted_keys.sort()
    # print sorted_keys
    # plotvalues
    pvals = {}
    #    for date_key, tags_by_tag in tags_by_interval.iteritems():
    for date_key in sorted_keys:
        # print date_key
        tags_by_tag = tags_by_interval[date_key]
        for tag, count in tags_by_tag.iteritems():
            # print(tag)
            if tag not in pvals:
                pvals[tag] = {'xvals': list(), 'yvals': list()}

            date_val = func_date_key_to_timestamp(date_key) / (3600 * 24)

            pvals[tag]['xvals'].append(date_val)
            pvals[tag]['yvals'].append(count)

    # save_pretty_json( pvals, 'pvals.json' )

    plt.clf()
    for tag, vals in pvals.iteritems():
        # print tag
        # x_range = range( len(  vals['xvals'] ) )
        # plt.xticks( x_range, vals['xvals'] )
        # plt.plot( x_range, vals['yvals'] )
        plt.plot(vals['xvals'], vals['yvals'])
    # plt.show()
    if filename == None:
        plt.show()
    else:
        plt.savefig(filename)


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

# def plot_by_interval(data, interval_pattern)
    


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.cfg')

    # mbox = mailbox.mbox( config['MAILMAN']['merged_mbox'] )
    # #find_date_formats(mbox)
    # mpd = get_mails_per_interval(mbox, key_pattern)
    # save_pretty_json(mpd, "mpd.json")

    mpd = load_json("mpd.json")
    plot_by_all(mpd)
