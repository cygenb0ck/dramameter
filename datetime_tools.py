import datetime
import dateutil.parser
import pytz


def get_utc_datetime_from_string(str):
    dt = dateutil.parser.parse(str)
    return dt.astimezone(pytz.utc)

def get_utc_datetime_from_isoformat(str):
    return dateutil.parser.parse(str)


def get_utc_datetime_from_unaware_str(str):
    dt = dateutil.parser.parse(str)
    return pytz.utc.localize(dt)

