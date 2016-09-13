#!/usr/bin/env bash
import configparser
import mailbox
import datetime

config = None

datetime_patterns = [
    "%a, %d %b %Y %H:%M:%S %z",       # "Sun, 30 Apr 2006 19:19:01 +0200"
    "%a, %d %b %Y %H:%M:%S %z (%Z)",  # "Mon, 8 Aug 2016 19:27:36 +0000 (UTC)"
    "%a, %d %b %Y %H:%M:%S %Z",       # "Fri, 25 Jul 2014 16:48:04 GMT"
    "%a, %d %b %Y %H:%M:%S %z (PDT)", # "Thu, 6 Jun 2013 08:43:06 -0700 (PDT)"
    "%a, %d %b %Y %H:%M %z"           # "Tue, 11 Jun 2013 09:00 +0200"
]


def find_date_formats(mbox):
    print("blubb")
    for k, v in mbox.items():
        d_str = v['Date']

        # mail archive contains one message with has no date
        if d_str is None:
            continue

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



if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read('config.cfg')

    mbox = mailbox.mbox( config['MAILMAN']['merged_mbox'] )

    find_date_formats(mbox)

