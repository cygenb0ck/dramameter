import mailbox
from email.utils import parsedate
import dateutil.parser
import datetime
import itertools
import pathlib
import sys

import datetime_tools


def _extract_date(email):
    date = email.get('Date')
    return parsedate(date)


def slope( graph ):
    if len(graph['x_vals']) != len(graph['y_vals']):
        raise  RuntimeError("graph: len(x_vals) != len(y_vals)!")

    l = len(graph["x_vals"])

    slope_graph = {}

    for i in range( 0, l - 1 ):
        x0 = graph["x_vals"][i]
        x1 = graph["x_vals"][i+1]
        x = datetime_tools.get_utc_datetime_average(x0, x1)
        slope_graph.setdefault("x_vals", list()).append(x)

        y0 = graph["y_vals"][i]
        y1 = graph["y_vals"][i+1]

        dx = ( x1.timestamp() - x0.timestamp() ) / 3600.0
        y = ( y1 - y0 ) / dx
        slope_graph.setdefault("y_vals", list()).append(y)

    return slope_graph




class EMail():
    def __init__(self, mbox_message):
        self.mbox_message = mbox_message
        self.parent = None
        self.children = list()
        #threadbuilding visited flag
        self._tb_v = False

    def set_parent(self, message):
        self.parent = message

    def add_child(self, message):
        self.children.append(message)

    def get_utc_datetime(self):
        return datetime_tools.get_utc_datetime_from_string_with_timezone(self.mbox_message["Date"])

    def get_message_id(self):
        return self.mbox_message["message-id"]

    def get_in_reply_to(self):
        return self.mbox_message["In-Reply-To"]

    def get_subject(self):
        return self.mbox_message["Subject"]

    def add_member(self, email):
        raise RuntimeError("im still used ...")
        if self.get_message_id() == email.get_in_reply_to():
            self.add_child(email)
            email.set_parent(self)
            return True
        else:
            added = False
            for c in self.children:
                added = c.add_member(email)
                if added == True:
                    return added
            return added

    def get_interval_keys_r(self, interval_pattern, interval_key_list):
        key = datetime.datetime.strftime(self.get_utc_datetime(), interval_pattern)
        interval_key_list.append(key)
        for c in self.children:
            interval_key_list = c.get_interval_keys_r(interval_pattern, interval_key_list)
        return interval_key_list

    def get_end_datetime_r(self, end_dt):
        if self.get_utc_datetime() > end_dt:
            end_dt = self.get_utc_datetime()
        for c in self.children:
            end_dt = c.get_end_datetime_r(end_dt)
        return end_dt

    def register_members(self, members, count = 0):
        members.add(self.get_message_id())
        self.count = count + 1
        for c in self.children:
            c.register_members(members, self.count)

    def plot_detailed(self, ax, *args, **kwargs):
        if len(self.children) == 0:
            xs = [self.get_utc_datetime()]
            ys = [self.count]
            ax.plot(xs, ys, *args, **kwargs)
        else:
            for c in self.children:
                xs = [self.get_utc_datetime(), c.get_utc_datetime()]
                ys = [self.count, c.count]
                ax.plot(xs, ys, *args, **kwargs)
                c.plot_detailed(ax, *args, **kwargs)


class MailThread():
    def __init__(self, root):
        # the starting message
        self.root = root
        # list holding the massage_ids of the participating mails
        self.members = set()
        self.members.add(self.root.get_message_id())
        # start datetime of thread
        self.start = root.get_utc_datetime()
        # datetime of the last mail
        self.end = root.get_utc_datetime()
        self.p_vals = None

    def finalize(self):
        self.end = self.root.get_end_datetime_r(self.start)
        self.duration = self.end - self.start
        self.root.register_members(self.members)
        self.mailcount = len(self.members)


    def contains_message_id(self, message_id):
        if message_id in self.members:
            return True
        return False

    def add_child(self, email):
        added = self.root.add_member(email)
        if added:
            self.members.append(email.get_message_id())
            end_dt = email.get_utc_datetime()
            if end_dt > self.end:
                self.end = end_dt

        return added

    def get_plot_values(self, interval_pattern = "%Y-%m-%d-%H %Z"):
        interval_key_list = self.root.get_interval_keys_r(interval_pattern, [])

        # count the frequency of the keys in interval_key_list
        count_per_interval = {key: len(list(group)) for key, group in itertools.groupby(interval_key_list)}

        accum_counts = {}
        prev_key = None
        for k, v in sorted(count_per_interval.items()):
            if prev_key is None:
                accum_counts[k] = v
            else:
                accum_counts[k] = accum_counts[prev_key] + v
            prev_key = k

        self.p_vals = {}
        for ik, count in sorted(accum_counts.items()):
            # strptime swallows timezone!!
            # self.p_vals.setdefault('x_vals', []).append(datetime.datetime.strptime(ik, interval_pattern))
            self.p_vals.setdefault('x_vals', []).append(dateutil.parser.parse(ik))
            self.p_vals.setdefault('y_vals', []).append(count)

        return self.p_vals

    def plot(self, ax, *args, **kwargs):
        if self.p_vals == None:
            self.get_plot_values()
        ax.plot(self.p_vals['x_vals'], self.p_vals['y_vals'], *args, **kwargs)

    def plot_detailed(self, ax, *args, **kwargs):
        self.root.plot_detailed(ax, *args, **kwargs)



class Mailbox():
    def __init__(self, mbox_file ):
        p = pathlib.Path(mbox_file)
        if not p.is_file():
            raise IOError("file not found: ", mbox_file)

        self._mbox = mailbox.mbox( mbox_file )
        self._built_threads = False
        self.threads_per_day = {}
        self.start = None
        self.end = None
        # assume unsorted mailbox
        self.sorted = False
        self.fixed = False
        self.p_vals = []

        self._fix_mbox()
        self._sort_mbox()

        self.mails = {}
        print("creating {0} mails".format(len(self._mbox.keys())))
        for k, v in self._mbox.items():
            sys.stdout.write(".")
            mail = EMail(v)
            self.mails[mail.get_message_id()] = mail

        sys.stdout.flush()

        self.build_threads()

    def __del__(self):
        self._mbox.close()

    def _fix_mbox(self):
        for k, v in self._mbox.items():
            d_str = v['Date']
            if d_str == None:
                print("found a mail without date - removing from mailbox ...")
                self._mbox.remove(k)
        self._mbox.flush()
        self.fixed = True

    def _sort_mbox(self):
        sorted_emails = sorted(self._mbox, key=_extract_date)
        self._mbox.update(enumerate(sorted_emails))
        self._mbox.flush()
        self.sorted = True

    def build_threads(self):
        if self._built_threads is True:
            print("threads were already built!")
            return

        print("\nbuilding threads")
        i = 0
        for mail in self.mails.values():
            sys.stdout.write(".")
            i += 1
            if mail._tb_v == True:
                continue

            parent_id = mail.get_in_reply_to()
            if parent_id in self.mails.keys():
                parent = self.mails[parent_id]
                parent.add_child(mail)
                mail.set_parent(parent)
            else:
                thread = MailThread(mail)
                key = datetime.datetime.strftime(mail.get_utc_datetime(), "%Y%m%d")
                self.threads_per_day.setdefault(key, list()).append(thread)
            mail._tb_v = True

        sys.stdout.flush()
        print("\n")

        # finalize all threads:
        for k, tpd in self.threads_per_day.items():
            for t in tpd:
                t.finalize()

        self.start = datetime_tools.get_utc_datetime_from_string_with_timezone( self._mbox[ 0]["Date"] )
        self.end   = datetime_tools.get_utc_datetime_from_string_with_timezone( self._mbox[len(self._mbox)-1]["Date"] )

        print("\nthreads started on ", self.start.isoformat())
        print("threads ended on   ", self.end.isoformat())
        self._built_threads = True

    def get_plot_values(self, interval_pattern):
        print("preparing plot values")
        self.p_vals = []
        for day_key, threads in self.threads_per_day.items():
            sys.stdout.write(".")
            for t in threads:
                self.p_vals.append(t.get_plot_values(interval_pattern))
        sys.stdout.flush()
        return self.p_vals

    def thread_slopes(self):
        self.s_vals = []
        for pv in self.p_vals:
            if len(pv['x_vals'])<2:
                continue
            s = slope(pv)
            self.s_vals.append( s )

        return self.s_vals

    def get_threads_by_count(self, min = None, max = None):
        tbc = {}
        for threads in self.threads_per_day.values():
            for t in threads:
                if (min is None or t.mailcount >= min) and (max is None or t.mailcount <= max):
                    tbc.setdefault(t.mailcount, list()).append(t)
        return tbc

    def get_threads_by_duration(self, min = None, max = None):
        tbd = {}
        for threads in self.threads_per_day.values():
            for t in threads:
                if( min is None or t.duration >= min ) and ( max is None or t.duration <= max ):
                    tbd.setdefault(t.duration, list()).append(t)
        return tbd

    def get_threads_active_within_range(self, start, end):
        if type(start) is str:
            s = dateutil.parser.parse(start)
        else:
            s = start
        if type(end) is str:
            e = dateutil.parser.parse(end)
        else:
            e = end

        twr = []

        for threads in self.threads_per_day.values():
            for t in threads:
                if t.end > s and t.start < e:
                    twr.append(t)
        return twr

    def get_threads_active_on_dates(self, date_list):
        tad = []

        for d in date_list:
            for threads in self.threads_per_day.values():
                for t in threads:
                    if t.start <= d <= t.end:
                        tad.append(t)

        return tad

