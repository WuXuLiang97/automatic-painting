import datetime


def get_date():
    now = datetime.datetime.now()
    if now.hour < 6:
        previous_day = now - datetime.timedelta(days=1)
        return previous_day.strftime("%Y-%m-%d")
    else:
        return now.strftime("%Y-%m-%d")
