from services.schedule_fetcher import pull_schedule
from services.projection.fantasy_regressor import FantasyRegressor
from services.projection.data_cleaning.play_by_play_aggregator import PlayByPlayAggregator

TARGETS = [
    "PassAttempt", 
    "RushAttempt", 
    "PassTD", 
    "RushTD", 
    "RushYards", 
    "PassYards", 
    "InterceptionThrown",
    "CompletePct"
]

def project():
    schedule = pull_schedule()
    model_df = PlayByPlayAggregator.aggregate()
    for target in TARGETS:
        regressor = FantasyRegressor(target).fit(model_df)
        schedule[target] = regressor.predict(schedule)

    schedule["CompletePass"] = schedule["PassAttempt"] * schedule["CompletePct"]
    return schedule