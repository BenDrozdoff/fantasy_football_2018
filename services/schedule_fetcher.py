import pandas as pd
import requests
import xmltodict

def pull_schedule():
    schedule_df = pd.DataFrame()
    for week in range(1, 17):
        response = requests.get(f"http://www.nfl.com/ajax/scorestrip?season=2019&seasonType=REG&week={week}")
        for game in xmltodict.parse(response.text)["ss"]["gms"]["g"]:
            schedule_df = schedule_df.append(
                pd.DataFrame(
                    {"Offense": [game["@h"]], 
                     "DefensiveTeam": [game["@v"]], 
                     "OffenseIsHome": [True], 
                     "week": [week]}
                ), 
                ignore_index=True)
            schedule_df = schedule_df.append(
                pd.DataFrame(
                    {"Offense": [game["@v"]], 
                     "DefensiveTeam": [game["@h"]], 
                     "OffenseIsHome": [False], 
                     "week": [week]}
                ), 
                ignore_index=True)
    return schedule_df