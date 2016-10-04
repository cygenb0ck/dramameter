import datetime
import dateutil.parser
import pytz


def get_utc_datetime_from_string_with_timezone(str):
    dt = dateutil.parser.parse(str)
    return dt.astimezone(pytz.utc)

def get_utc_datetime_from_isoformat(str):
    return dateutil.parser.parse(str)


def get_utc_datetime_from_unaware_str(str):
    dt = dateutil.parser.parse(str)
    return pytz.utc.localize(dt)


def get_utc_datetime_average( dt1, dt2 ):
    avg = datetime.datetime.utcfromtimestamp( (dt1.timestamp() + dt2.timestamp() ) / 2 )
    avg = pytz.utc.localize(avg)
    # avg = tz
    # avg.astimezone(dt1.tzname())
    return avg