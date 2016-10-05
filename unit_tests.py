import unittest

import dateutil.parser
import datetime
import datetime_tools
import mailbox_tools

class TestDateTimeTools(unittest.TestCase):
    def setUp(self):
        pass

    def test_get_utc_datetime_from_string(self):
        s1 = "2006-05-22 10:00 CET"
        d1 = datetime_tools.get_utc_datetime_from_string_with_timezone(s1)
        self.assertEqual(d1.tzname(), "UTC")
        d1_str = datetime.datetime.strftime( d1, "%Y-%m-%d %H:%M %Z" )
        self.assertEqual(d1_str, "2006-05-22 08:00 UTC")

        s2 = "2006-05-22 10:00 UTC"
        d2 = datetime_tools.get_utc_datetime_from_string_with_timezone(s2)
        self.assertEqual(d2.tzname(), "UTC")
        d2_str = datetime.datetime.strftime( d2, "%Y-%m-%d %H:%M %Z" )
        self.assertEqual(d2_str, "2006-05-22 10:00 UTC")


    def test_average(self):
        s1 = "2006-05-22 10:00 CET"
        s2 = "2006-05-22 12:00 CET"

        avg = datetime_tools.get_utc_datetime_average(dateutil.parser.parse(s1), dateutil.parser.parse(s2))
        avg_str = datetime.datetime.strftime(avg, "%Y-%m-%d %H:%M %Z")
        self.assertEqual( avg_str, "2006-05-22 09:00 UTC" )


class TestMailBoxTools(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.mailbox = mailbox_tools.Mailbox("./mailman_archives/2006-May.txt", True, True)

    def test_mail_dates_utc(self):
        for m in self.mailbox.mails.values():
            tz = datetime.datetime.strftime( m.get_utc_datetime(), "%Z" )
            self.assertEqual( tz, "UTC" )

    def _are_children_in_members_r(self, members, mail):
        self.assertIn( mail.get_message_id(), members )
        for c in mail.children:
            self._are_children_in_members_r(members, c)

    def test_members(self):
        for threads in self.mailbox.threads_per_day.values():
            for t in threads:
                self._are_children_in_members_r(t.members, t.root)
                self.assertGreater(t.mailcount, 0)

    def test_get_threads_by_count(self):
        tbc1 = self.mailbox.get_threads_by_count()
        for count, threads in tbc1.items():
            for t in threads:
                self.assertEqual(t.mailcount, count)

        tbc2 = self.mailbox.get_threads_by_count(10)
        for count, threads in tbc2.items():
            for t in threads:
                self.assertGreaterEqual(t.mailcount, 10)

        tbc3 = self.mailbox.get_threads_by_count(max=10)
        for count, threads in tbc3.items():
            for t in threads:
                self.assertLessEqual(t.mailcount, 10)

        tbc4 = self.mailbox.get_threads_by_count(min = 5, max=10)
        for count, threads in tbc4.items():
            for t in threads:
                self.assertLessEqual(t.mailcount, 10)
                self.assertGreaterEqual(t.mailcount, 5)

    def test_get_threads_by_duration(self):
        tbd1 = self.mailbox.get_threads_by_duration()
        for duration, threads in tbd1.items():
            for t in threads:
                self.assertEqual(t.duration, duration)

        d1 = datetime.timedelta(days = 2)
        tb2 = self.mailbox.get_threads_by_duration(d1)
        for duration, threads in tb2.items():
            self.assertGreaterEqual(duration, d1)
            for t in threads:
                self.assertGreaterEqual(t.duration, d1)

        d2 = datetime.timedelta(days=3)
        tb3 = self.mailbox.get_threads_by_duration(max = d2)
        for duration, threads in tb3.items():
            self.assertLessEqual(duration, d2)
            for t in threads:
                self.assertLessEqual(t.duration, d2)

        tb4 = self.mailbox.get_threads_by_duration(min=d1, max=d2)
        for duration, threads in tb4.items():
            self.assertGreaterEqual(duration, d1)
            self.assertLessEqual(duration, d2)
            for t in threads:
                self.assertGreaterEqual(t.duration, d1)
                self.assertLessEqual(t.duration, d2)


class TestSlope(unittest.TestCase):
    def setUp(self):
        self.raw_data = {
            "x_vals" : [
                "2006-05-22 10:00 CET", # 08:00
                "2006-05-22 11:00 CET", # 09:00
                "2006-05-22 12:00 CET", # 10:00
                "2006-05-22 13:00 CET", # 11:00
                "2006-05-22 14:00 CET", # 12:00
            ],
            "y_vals" : [1,2,3,4,5]
        }
        self.data = {}
        self.data["x_vals"] = [dateutil.parser.parse(x) for x in self.raw_data["x_vals"]]
        self.data["y_vals"] = self.raw_data["y_vals"]

    def test_slope(self):
        s_data = mailbox_tools.slope( self.data )
        l = len(s_data["x_vals"])
        self.assertEqual( l, len(self.data["x_vals"])-1 )

        str = datetime.datetime.strftime( s_data['x_vals'][0], "%Y-%m-%d %H:%M %Z" )
        self.assertEqual(str, "2006-05-22 08:30 UTC" )

        for i in range(0, l-1):
            rx0 = self.data["x_vals"][i]
            # rx1 = self.data["x_vals"][i+1]

            x0 = s_data["x_vals"][i]
            x1 = s_data["x_vals"][i+1]

            self.assertEqual( x1.timestamp() - x0.timestamp(), 3600 )
            self.assertGreater( x0, rx0)
        for y in s_data["y_vals"]:
            self.assertEqual( y, 1 )



if __name__ == "__main__":
    unittest.main()