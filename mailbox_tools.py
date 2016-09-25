import mailbox
from email.utils import parsedate
import dateutil.parser
import datetime
import itertools

import datetime_tools


def extract_date(email):
    date = email.get('Date')
    return parsedate(date)


def sort_mbox(mbox):
    sorted_emails = sorted(mbox, key=extract_date)
    mbox.update(enumerate(sorted_emails))
    mbox.flush()


def find_thread_start_index(mbox, message_index):
    start = mbox[message_index]
    start_index = None

    for i in range(message_index - 1, -1, -1):
        if mbox[i].get("In-Reply-To") == start.get('message-id'):
            start = mbox[i]
            start_index = i

    return start_index


def find_children(mbox, start_index, start_message):
    for i in range(start_index, len(mbox)):
        current = mbox[i]
        if current.get('In-Reply-To') == start_message.mbox_message.get('message-id'):
            child = EMail(current)
            child.set_parent(start_message)
            start_message.append_child(child)
    for child in start_message.children():
        find_children(mbox, start_index + 1, child)


def fix_mbox(mbox):
    for k, v in mbox.items():
        d_str = v['Date']
        if d_str == None:
            print("found a mail without date - removing from mailbox ...")
            mbox.remove(k)
    mbox.flush()


class EMail():
    def __init__(self, mbox_message):
        self.mbox_message = mbox_message
        self.parent = None
        self.children = list()

    def set_parent(self, message):
        self.parent = message

    def append_child(self, message):
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
            self.append_child(email)
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
    def __init__(self, mbox):
        self._mbox = mbox
        self.threads_per_day = {}
        self._start_indices = []
        self._reply_indices = []
        self.start = None
        self.end = None

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

        for r_i in self._reply_indices:
            print(r_i)
            reply = EMail(self._mbox[r_i])

            if not self._check_bounds_reversed_indices(reply.get_utc_datetime()):
                print("message {} belongs to older thread".format(reply.get_message_id()))
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
                print("message {} belongs to older thread".format(reply.get_message_id()))

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



    def get_plot_values(self, interval_pattern):
        p_vals = []
        for day_key, threads in self.threads_per_day.items():
            for t in threads:
                p_vals.append(t.get_plot_values(interval_pattern))
        return p_vals
