from time import sleep, mktime
from collections import defaultdict, Counter
from copy import deepcopy
from datetime import timedelta, datetime
import os
import berserk

TOKEN_FILE = 'token'

PLAYERS_DIR = 'players'
PLAYERS = 'players.txt'

START_DATE = '2023.08.01'
END_DATE = '2024.07.31'

def is_valid_tournament(tournament):
    if tournament['createdBy'] != 'lichess':
        return False
    if tournament['rated'] != True:
        return False
    if tournament['variant']['name'] != 'Atomic':
        return False
    if tournament['clock']['limit'] < 60:
        return False
    return True

def calculate_bonus_score(tournament):
    bonus_score = 0
    tc = tournament["tournament"]["clock"]["limit"]
    tci = tournament["tournament"]["clock"]["increment"]
    if tc == 60 and tci == 0:
        bonus_score -= 60
    if tc == 60 and tci == 1:
        bonus_score -= 30
    if tc == 120 and tci == 0:
        bonus_score -= 30
    games_played = tournament["player"]["games"]
    games_played_over_50 = 0 if games_played <= 50 else games_played - 50
    games_played_over_18 = 0 if games_played <= 18 else games_played - 18 - games_played_over_50
    if games_played >= 100:
        return bonus_score + 150
    if games_played_over_50 > 0:
        bonus_score += games_played_over_50 // 2 * 2 if games_played_over_50 <= 100 else 150
    if games_played_over_18 > 0:
        bonus_score += games_played_over_18 // 2 * 5
    if games_played >= 18:
        bonus_score += 20
    if games_played <= 14:
        bonus_score -= 20
    if games_played <= 12:
        bonus_score -= 20
    if games_played <= 10:
        bonus_score -= 20
    return bonus_score

if __name__ == '__main__':
    # Init database
    if not os.path.isdir(PLAYERS_DIR):
        os.mkdir(PLAYERS_DIR)
    # Authorizing with berserk lichess API
    session, token = None, None
    with open(TOKEN_FILE) as t:
        token = t.readline().strip()
    session = berserk.TokenSession(token)
    print("Token provided, authorized on lichess.")
    if session is None:
        client = berserk.Client()
    else:
        client = berserk.Client(session)
    # Obtaining list of players
    if not os.path.isfile(PLAYERS):
        print("Error: the file '%s' must contain the player list (each nickname on separate line)" % PLAYERS)
        exit(1)
    all_player_ids = []
    with open(PLAYERS) as p:
        for line in p:
            if len(line.strip()) == 0:
                continue
            all_player_ids.append(line.strip().lower())
    start = berserk.utils.to_millis(datetime.strptime(START_DATE, '%Y.%m.%d'))
    end = berserk.utils.to_millis(datetime.strptime(END_DATE, '%Y.%m.%d'))

    for player_id in set(all_player_ids):
        print("Fetching tournaments of player '{}' (nickname lowercased)".format(player_id))
        path = f"/api/user/{player_id}/tournament/played"
        params = {
          "nb": 2000, # to change if not done ok for some player
          "performance": True
        }
        player_tournaments = []
        for i, tournament in enumerate(client._r.get(
          path, params=params, fmt=berserk.formats.NDJSON_LIST, converter=berserk.models.Game.convert
        )):
            if is_valid_tournament(tournament["tournament"]) == False:
              continue
            if tournament["tournament"]["startsAt"] > end:
              continue
            if tournament["tournament"]["startsAt"] < start:
              print("done for {}".format(player_id))
              break
            quota = tournament["player"]["games"] >= 10
            bonus_score = calculate_bonus_score(tournament)
            perf = tournament["player"]["performance"]
            player_tournaments.append((quota,
                perf + bonus_score,
                'https://lichess.org/tournament/'
                + tournament["tournament"]["id"] + ' ' + str(tournament["player"]["games"]) + ' ' + player_id + ' ' + str(perf) + ' ' + str(bonus_score) + ' ' + str(perf + bonus_score) + ' ' + tournament["tournament"]["fullName"] + '\n'))
        player_tournaments.sort(reverse=True)
        with open(os.path.join(PLAYERS_DIR, player_id), 'w') as plf:
            plf.write(''.join(item[2] for item in player_tournaments))
    print("Finished fetching tournaments")
