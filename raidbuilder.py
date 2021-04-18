import itertools
import time

from database import get_player

TANKS = ["WAR", "PLD", "DRK", "GNB"]
HEALERS = ["WHM", "SCH", "AST"]
MELEES = ["MNK", "DRG", "NIN", "SAM"]
RANGED = ["BRD", "MCH", "DNC"]
CASTERS = ["BLM", "SMN", "RDM"]
LIMITED = ["BLU"]
DPS = [*MELEES, *RANGED, *CASTERS]
JOBS = [*TANKS, *HEALERS, *DPS]


def job_string_to_list(job_string: str):
    return job_string.split(",")


class Character:
    """A Class defining a character.
    Note: Job_list should be given in Order of priority."""
    def __init__(self, discord_id, name, job_list):
        self.discord_id = discord_id
        self.character_name = name
        self.jobs = []
        if isinstance(job_list, str):
            self.set_jobs(job_string_to_list(job_list))
        else:
            self.set_jobs(job_list)

    def set_jobs(self, job_list):
        for job in job_list:
            if job in JOBS and job not in self.jobs:
                self.jobs.append(job)
            elif job in self.jobs:
                print(f"{job} already registered")
            else:
                print(f"{job} is not a valid job")


def make_character_from_db(conn, discord_id, name):
    p = get_player(conn, discord_id, name)
    if p:
        return Character(p[1], p[2], p[3])
    else:
        print(f"No Character with id {discord_id} and name {name} found in db.")


def calc_composition_score(combination: tuple[Character], picked_jobs: tuple, n_tanks: int, n_healers: int, n_dps: int):
    # First checks - do we have the correct number of roles? if not, don't bother
    if sum(t in picked_jobs for t in TANKS) != n_tanks:
        score = 0
    elif sum(h in picked_jobs for h in HEALERS) != n_healers:
        score = 0
    elif sum(d in picked_jobs for d in DPS) != n_dps:
        score = 0
    else:
        job_prios = []
        for i, member in enumerate(combination):
            idx = member.jobs.index(picked_jobs[i])  # Combination and picked jobs must be in the correct order
            job_prios.append(len(JOBS) - idx)  # First job in list gets highest priority and so on

        score = sum(job_prios)

        # Extra score boosts/detractors

        # Do we have duplicates?
        if len(picked_jobs) != len(set(picked_jobs)):
            score -= 10  # Weight here might need to be adjusted

        # Group DPS comp
        if sum(d in picked_jobs for d in MELEES) > 0:
            if sum(d in picked_jobs for d in RANGED) > 0:
                if sum(d in picked_jobs for d in CASTERS) > 0:
                    # We have at least one of each type of DPS
                    score += 5
                else:
                    # We have at least two different types of DPS
                    score += 3

            elif sum(d in picked_jobs for d in CASTERS) > 0:
                # We have at least two different types of DPS
                score += 3
        elif sum(d in picked_jobs for d in CASTERS) > 0 and sum(d in picked_jobs for d in RANGED) > 0:
            # We have at least two different types of DPS
            score += 3

        # TODO: add number of participated raids into calculation

    return score


def make_raid(characters: list[Character], n_tanks: int, n_healers: int, n_dps: int):
    """Given a list of Characters, this will form the most desirable possible raid composition"""
    n_raiders = n_tanks + n_healers + n_dps

    # If not enough raiders are given, we might as well stop here
    if len(characters) < n_raiders:
        print("Not enough participants")
        return None

    groups_comps_and_scores = []
    # Iterate through all possible combinations of the given number of players
    for group in itertools.combinations(characters, n_raiders):
        # Get all jobs for each member of this combination in one list of lists
        job_lists = []
        for member in group:
            job_lists.append(member.jobs)

        # Get all possible job combinations
        comps = itertools.product(*job_lists)

        # Iterate over comps and get scores
        for comp in comps:
            score = calc_composition_score(group, comp, n_tanks, n_healers, n_dps)
            if score > 0:  # only append viable combinations
                groups_comps_and_scores.append([group, comp, score])

    # We find the best comp by looking for the max score
    best = max(groups_comps_and_scores, key=lambda x: x[2])

    # Get list of best raids if there are multiple
    best_score = best[2]
    all_bests = [raid for raid in groups_comps_and_scores if raid[2] == best_score]

    # Statistics, out of curiosity, comment out later:
    print(f"There are {len(groups_comps_and_scores)} viable combinations.")
    print(f"Best score of {best_score} appears {len(all_bests)} times.")

    return all_bests


if __name__ == '__main__':
    # Test raidbuilder functionality
    participants = [
        Character(1, "Nama Zu",     "GNB,PLD,MCH"),
        Character(2, "Na Mazu",     "DRK,GNB,MNK"),
        Character(3, "Zu Nama",     "WHM,AST,PLD,BRD"),
        Character(4, "Zuna Ma",     "BLM,SMN,RDM,SCH"),
        Character(5, "Mama Zu",     "BRD,WHM,RDM"),
        Character(6, "Uza Man",     "MNK,SAM,GNB"),
        Character(7, "Zuzu Nana",   "DNC"),
        Character(8, "Yes Yes",     "PLD,WAR,MCH,DNC"),
        Character(9, "Dummy Thicc", "BLM,SAM"),
        Character(10, "Blue Chicken", "WHM,SMN"),
        Character(11, "Ragu Bolognese", "DRG,NIN")
    ]

    # Checking how long this takes
    begin = time.time()

    # Get X best raids
    best_raids = make_raid(participants, 2, 2, 4)

    end = time.time()
    print(f"Calculations took {end-begin} seconds.")

    # Print Names in order
    print([p.character_name for p in participants])

    # Print Composition in order of Names (Bench is indicated by ---)
    for group, comp, score in best_raids:
        print_line = []
        for player in participants:
            if player in group:
                print_line.append(comp[group.index(player)])
            else:
                print_line.append('---')
        print(print_line)

