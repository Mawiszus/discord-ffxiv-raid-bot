from datetime import datetime
from pytz import timezone
from pytz.exceptions import UnknownTimeZoneError

from raidbuilder import job_string_to_list


class Event:
    def __init__(self, ev_id, name, timestamp, participant_names, participant_ids, jobs, state):
        self.id = ev_id
        self.name = name
        self.timestamp = timestamp

        if isinstance(participant_names, str):
            self.participant_names = job_string_to_list(participant_names)
        else:
            self.participant_names = participant_names

        if isinstance(participant_ids, str):
            self.participant_ids = job_string_to_list(participant_ids)
        else:
            self.participant_ids = participant_ids

        if isinstance(jobs, str):
            self.jobs = job_string_to_list(jobs)
        else:
            self.jobs = jobs

        self.state = state

    def get_time(self, user_timezone="GMT"):
        """Get timestamp in user_timezone, user_timezone uses formats known to pytz"""
        try:
            tz = timezone(user_timezone)
        except UnknownTimeZoneError:
            print(f"Unknown timezone {user_timezone}, use format like 'Europe/Amsterdam', displaying in GMT")
            tz = timezone("GMT")

        dt_object = datetime.fromtimestamp(self.timestamp, timezone(tz))
        return dt_object.strftime("%Y-%m-%d %H:%M:%S %Z%z")
