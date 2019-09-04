import os
import pandas as pd


class PlayByPlayAggregator:
    @staticmethod
    def read_file(filename=None):
        if not filename:
            filename = "pbpdata.csv"
        return pd.read_csv(os.path.join(os.path.dirname(os.path.realpath(__file__)), filename))

    @classmethod
    def prepare_columns(cls):
        df = cls.read_file()
        df["CompletePass"] = df["PassOutcome"] == "Complete"
        df["OffensiveTouchdown"] = (df["Touchdown"]) & (df["EPA"] > 0)
        df["PassAttempt"] = df["PassAttempt"] & df["Passer"].notnull() & (df["PlayType"] != "No Play")
        df["RushAttempt"] = df["RushAttempt"] & df["Rusher"].notnull() & (df["PlayType"] != "No Play")
        df["OffenseIsHome"] = df["posteam"] == df["HomeTeam"]
        df["PassTD"] = df["OffensiveTouchdown"] & df["PassAttempt"]
        df["RushTD"] = df["OffensiveTouchdown"] & df["RushAttempt"]
        df["RushYards"] = df["Yards.Gained"] * df["RushAttempt"]
        df["PassYards"] = df["Yards.Gained"] * df["PassAttempt"]
        return df

    @classmethod
    def aggregate(cls):
        df = cls.prepare_columns()
        model_df = df.groupby(["GameID", "posteam", "DefensiveTeam", "OffenseIsHome"]).sum().reset_index()[
            ["GameID", "posteam", "DefensiveTeam", "OffenseIsHome", "PassAttempt", "RushAttempt", "CompletePass", 
            "PassTD", "RushTD", "RushYards", "PassYards", "InterceptionThrown"]].rename(
                columns={"posteam": "Offense"})
        model_df["CompletePct"] = model_df["CompletePass"] / model_df["PassAttempt"]
        return model_df