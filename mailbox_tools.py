import mailbox
from email.utils import parsedate
import dateutil.parser
import datetime


def extract_date(email):
    date = email.get('Date')
    return parsedate(date)


def sort_mbox(mbox):
    sorted_emails = sorted(mbox, key=extract_date)
    mbox.update( enumerate(sorted_emails) )
    mbox.flush()


def find_thread_start_index(mbox, message_index ):

    start = mbox[message_index]
    start_index = None

    for i in range(message_index - 1, -1, -1):
        if mbox[i].get("In-Reply-To") == start.get('message-id'):
            start = mbox[i]
            start_index = i

    return start_index


def find_children(mbox, start_index, start_message):
    for i in range( start_index, len(mbox) ):
        current = mbox[i]
        if current.get('In-Reply-To') == start_message.mbox_message.get('message-id'):
            child = EMail(current)
            child.set_parent(start_message)
            start_message.append_child(child)
    for child in start_message.children():
        find_children(mbox, start_index+1, child)


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

    def get_date_as_datetime(self):
        return dateutil.parser.parse(self.mbox_message["Date"])

    def get_message_id(self):
        return self.mbox_message["message-id"]

    def get_in_reply_to(self):
        return self.mbox_message["In-Reply-To"]

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


class MailThread():
    def __init__(self, root):
        self.root = root
        self._members = []
        self._members.append(self.root.get_message_id)

    def is_member_of(self, message_id):
        if message_id in self._members:
            return True
        return False

    def add_child(self, email):
        added = self.root.add_member(email)
        if added:
            self._members.append(email.get_message_id())
        return added


class Mailbox():
    def __init__(self, mbox):
        self._mbox = mbox
        self.threads_per_day = {}

    def _build_start_indices(self):
        self._start_indices = []
        self._reply_indices = []

        for k, v in self._mbox.items():
            if v["In-Reply-To"] is None:
                self._start_indices.append(k)
            else:
                self._reply_indices.append(k)
        print("start indices: ", len(self._start_indices))
        print("reply indices: ", len(self._reply_indices))

    def _get_start_index(self, dt):
        key = datetime.datetime.strftime(dt, "%Y%m%d" )
        try:
            return self._reversed_thread_indices.index(key)
        except ValueError:
            print("no index for ", key)
            delta_24h = datetime.timedelta(hours=24)
            dt = dt - delta_24h
            return self._get_start_index(dt)

    def build_threads(self):
        self._build_start_indices()
        for s_i in self._start_indices:
            root = MailThread( EMail(self._mbox[s_i]) )
            key = datetime.datetime.strftime( root.root.get_date_as_datetime(), "%Y%m%d" )
            self.threads_per_day.setdefault(key, list()).append(root)

        self._reversed_thread_indices = list(reversed(sorted(self.threads_per_day.keys())))

        for r_i in self._reply_indices:
            print(r_i)
            reply = EMail(self._mbox[r_i])
            latest_start_index =  reply.get_date_as_datetime()
            start = self._get_start_index( reply.get_date_as_datetime() )
            for rev_key in self._reversed_thread_indices[ start: ]:
                t = self.threads_per_day[rev_key]
                found = False
                for t  in self.threads_per_day[rev_key]:
                    if t.is_member_of( reply.get_in_reply_to() ):
                        found = t.add_child(reply)
                        break;
                if found:
                    break


    def build_threads_old(self):
        self._build_start_indices()

        for s_i in self._start_indices:
            start_mail = EMail(self._mbox[s_i])
            self.threads_per_day.append(start_mail)

            self._find_children(start_mail)

    def _find_children(self, parent):
        i_to_be_removed = []
        for r_i in self._reply_indices:
            if self._mbox[r_i]["In-Reply-To"] == parent.get_message_id():
                child = EMail( self._mbox[r_i] )
                child.set_parent(parent)
                parent.append_child(child)
                i_to_be_removed.append(r_i)
        #l3 = [x for x in l1 if x not in l2]
        self._reply_indices = [ r_i for r_i in self._reply_indices if r_i not in i_to_be_removed ]
        print("r_indices: ", len(self._reply_indices))
        for child in parent.children:
            self._find_children(child)



