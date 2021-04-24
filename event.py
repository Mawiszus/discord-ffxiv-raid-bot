from datetime import datetime
from pytz import timezone
from pytz.exceptions import UnknownTimeZoneError

from raidbuilder import job_string_to_list, string_from_list
from database import get_event, create_connection


class Event:
    def __init__(self, ev_id, name, timestamp, participant_names, participant_ids, is_bench,
                 jobs, role_numbers, creator_id, state):
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

        if isinstance(is_bench, str):
            self.is_bench = job_string_to_list(is_bench)
        else:
            self.is_bench = is_bench

        if isinstance(jobs, str):
            self.jobs = job_string_to_list(jobs)
        else:
            self.jobs = jobs

        if isinstance(role_numbers, str):
            self.role_numbers = job_string_to_list(role_numbers)
        else:
            self.role_numbers = role_numbers
        self.role_numbers = [int(n) for n in self.role_numbers]

        self.creator_id = creator_id
        self.state = state

    def get_time(self, user_timezone='GMT'):
        """Get timestamp in user_timezone, user_timezone uses formats known to pytz"""
        try:
            tz = timezone(user_timezone)
        except UnknownTimeZoneError:
            print(f"Unknown timezone {user_timezone}, use format like 'Europe/Amsterdam', displaying in GMT")
            tz = timezone('GMT')

        dt_object = datetime.fromtimestamp(self.timestamp, tz)
        return dt_object.strftime("%d %B %Y %H:%M:%S %Z%z")

    def participants_as_str(self):
        return string_from_list(self.participant_names)

    def jobs_as_str(self):
        return string_from_list(self.jobs)

    def get_overview_string(self):
        name_string = string_from_list(self.participant_names)
        jobs_string = string_from_list(self.jobs)

        out = f"```\n" \
              f"Event Nr.:      {self.id}\n" \
              f"Name:           {self.name}\n" \
              f"Participants:   {name_string}\n" \
              f"Jobs:           {jobs_string}\n" \
              f"Time:           {self.get_time()}\n" \
              f"This event is {self.state}.```"
        return out


def make_event_from_db(conn, event_id):
    db_event = get_event(conn, event_id)
    event = Event(*db_event[0])
    return event


if __name__ == '__main__':
    # Testing functionality
    conn = create_connection(r"database/test.db")
    with conn:
        ev = make_event_from_db(conn, 1)
        print(ev.get_overview_string())
