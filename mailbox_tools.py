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
        return datetime_tools.get_utc_datetime_from_string(self.mbox_message["Date"])

    def get_message_id(self):
        return self.mbox_message["message-id"]

    def get_in_reply_to(self):
        return self.mbox_message["In-Reply-To"]

    def get_subject(self):
        return self.mbox_message["Subject"]

    def add_member(self, email):
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
        t_end = end_dt
        for c in self.children:
            t = c.get_end_datetime_r(t_end)
            if t > t_end:
                t_end = t
        return t_end




class MailThread():
    def __init__(self, root):
        # the starting message
        self.root = root
        # list holding the massage_ids of the participating mails
        self._members = []
        self._members.append(self.root.get_message_id())
        # start datetime of thread
        self.start = root.get_utc_datetime()
        # datetime of the last mail
        self.end = root.get_utc_datetime()

    def finalize(self):
        self.end = self.root.get_end_datetime_r(self.start)

    def contains_message_id(self, message_id):
        if message_id in self._members:
            return True
        return False

    def add_child(self, email):
        added = self.root.add_member(email)
        if added:
            self._members.append(email.get_message_id())
            end_dt = email.get_utc_datetime()
            if end_dt > self.end:
                self.end = end_dt

        return added

    def get_plot_values(self, interval_pattern):
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

        p_vals = {}
        for ik, count in sorted(accum_counts.items()):
            p_vals.setdefault('x_vals', []).append(datetime.datetime.strptime(ik, interval_pattern))
            p_vals.setdefault('y_vals', []).append(count)

        return p_vals


class Mailbox():
    def __init__(self, mbox_file, sort = False, fix = False):
        p = pathlib.Path(mbox_file)
        if not p.is_file():
            raise IOError("file not found: ", mbox_file)

        self._mbox = mailbox.mbox( mbox_file )

        if fix:
            self._fix_mbox()
        if sort:
            self._sort()

        self.threads_per_day = {}
        self._start_indices = []
        self._reply_indices = []
        self._reversed_thread_indices = []
        self.start = None
        self.end = None

    def _fix_mbox(self):
        for k, v in self._mbox.items():
            d_str = v['Date']
            if d_str == None:
                print("found a mail without date - removing from mailbox ...")
                self._mbox.remove(k)
        self._mbox.flush()

    def _sort_mbox(self):
        sorted_emails = sorted(self._mbox, key=_extract_date)
        self._mbox.update(enumerate(sorted_emails))
        self._mbox.flush()

    def _build_start_indices(self):
        for k, v in self._mbox.items():
            if v["In-Reply-To"] is None:
                self._start_indices.append(k)
            else:
                self._reply_indices.append(k)
        print("start indices: ", len(self._start_indices))
        print("reply indices: ", len(self._reply_indices))

    def _check_bounds_reversed_indices(self, dt):
        # start = datetime_tools.get_utc_datetime_from_unaware_str( self._reversed_thread_indices[0] )
        end = datetime_tools.get_utc_datetime_from_unaware_str(self._reversed_thread_indices[-1])

        # if start >= dt >= end:
        if dt >= end:
            return True
        return False

    def _get_start_index(self, dt):
        key = datetime.datetime.strftime(dt, "%Y%m%d")

        while True:
            try:
                return True, self._reversed_thread_indices.index(key)
            except ValueError:
                delta_24h = datetime.timedelta(hours=24)
                dt = dt - delta_24h
                if not self._check_bounds_reversed_indices(dt):
                    return False, None
                key = datetime.datetime.strftime(dt, "%Y%m%d")

    def build_threads(self):
        self._build_start_indices()
        for s_i in self._start_indices:
            root = MailThread(EMail(self._mbox[s_i]))
            key = datetime.datetime.strftime(root.root.get_utc_datetime(), "%Y%m%d")
            self.threads_per_day.setdefault(key, list()).append(root)

        # _reversed_thread_indices
        # first entry: newest threads
        # last entry : oldest threads
        self._reversed_thread_indices = list(reversed(sorted(self.threads_per_day.keys())))

        alternative_start = []

        for r_i in self._reply_indices:
            print(r_i)
            reply = EMail(self._mbox[r_i])

            if not self._check_bounds_reversed_indices(reply.get_utc_datetime()):
                print("message {} belongs to older thread".format(reply.get_message_id()))
                alternative_start.append(reply)
                continue

            in_bounds, start = self._get_start_index(reply.get_utc_datetime())
            if not in_bounds:
                # print("already out of bounds")
                continue

            found = False
            for rev_key in self._reversed_thread_indices[start:]:
                t = self.threads_per_day[rev_key]
                for t in self.threads_per_day[rev_key]:
                    if t.contains_message_id(reply.get_in_reply_to()):
                        found = t.add_child(reply)
                        break;
                if found:
                    break
            if not found:
                alternative_start.append(reply)
                print("message {} belongs to older thread".format(reply.get_message_id()))

        print("mbox size: ",len(self._mbox.keys()))
        print("alt_star:  ", len(alternative_start))

        start_threads = self.threads_per_day[ list(sorted(self.threads_per_day.keys()))[0] ]
        for thread in start_threads:
            if self.start == None or thread.start < self.start:
                self.start = thread.start
        for k,tpd in self.threads_per_day.items():
            for t in tpd:
                if self.end == None or t.end > self.end:
                    self.end = t.end

        print("threads started on ", self.start.isoformat())
        print("threads ended on   ", self.end.isoformat())

    def build_threads_alt(self):
        mails = {}
        print("creating {0} mails".format(len(self._mbox.keys())))
        for k, v in self._mbox.items():
            sys.stdout.write(".")
            mail = EMail(v)
            mails[mail.get_message_id()] = mail

        sys.stdout.flush()

        print("\nbuilding threads")
        i = 0
        for mail in mails.values():
            sys.stdout.write(".")
            i += 1
            if mail._tb_v == True:
                continue

            parent_id = mail.get_in_reply_to()
            if parent_id in mails.keys():
                parent = mails[parent_id]
                parent.add_child(mail)
                mail.set_parent(parent)
            else:
                thread = MailThread(mail)
                key = datetime.datetime.strftime(mail.get_utc_datetime(), "%Y%m%d")
                self.threads_per_day.setdefault(key, list()).append(thread)
            mail._tb_v = True

        sys.stdout.flush()

        # finalize all threads:
        for k, tpd in self.threads_per_day.items():
            for t in tpd:
                t.finalize()

        # TODO: if mailbox is sorted, then just access first and last mail
        # find start date for mailbox
        start_threads = self.threads_per_day[list(sorted(self.threads_per_day.keys()))[0]]
        for thread in start_threads:
            if self.start == None or thread.start < self.start:
                self.start = thread.start

        # find end date for mailbox
        end_threads = self.threads_per_day[ list(sorted(self.threads_per_day.keys()))[-1] ]
        for thread in end_threads:
            if self.end == None or thread.end > self.end:
                self.end = thread.end

        print("\nthreads started on ", self.start.isoformat())
        print("threads ended on   ", self.end.isoformat())

    def get_plot_values(self, interval_pattern):
        print("preparing plot values")
        p_vals = []
        for day_key, threads in self.threads_per_day.items():
            sys.stdout.write(".")
            for t in threads:
                p_vals.append(t.get_plot_values(interval_pattern))
        sys.stdout.flush()
        return p_vals
