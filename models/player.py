# coding: utf-8

import numpy as np


class Player:
    def __init__(self, league, projection, team_id=None):
        self.league = league
        self.team_id = team_id
        self.id = projection['id']
        self.name = projection['player']
        self.nfl_team = projection['tm']
        self.position = projection['position']
        self.projections_by_week = {}
        self.points_by_week = {}
        self.add_projection(projection)

    def __repr__(self):
        return ', '.join([self.name, self.position, self.nfl_team])

    def add_projection(self, projection):
        self.projections_by_week[projection['week']] = {
            key: value
            for key, value in projection.items() if key not in []
        }

    def add_to_team(self, team_id=None, team_name=None):
        if team_id:
            acquiring_team = self.league.teams[team_id]
        elif team_name:
            acquiring_team = self.league.team_by_name(team_name)
        acquiring_team.add_player(self)

    def weekly_points(self, week):
        points = 0.0
        projection = self.projections_by_week.get(week)
        if not projection:
            self.points_by_week[week] = points
            return
        for category, value in self.league.scoring_settings.items():
            points += value * float(projection.get(category, 0))
        self.points_by_week[week] = points

    def season_points(self):
        relevant_weeks = range(1, 17)
        for week in relevant_weeks:
            self.weekly_points(week)
        return sum(self.points_by_week.values())

    def value_over_replacement(self):
        position_injury = self.league.injury_simulations[self.position]
        weekly_rep_level = self.league.replacement_level[self.position] / 16
        player_weeks = np.array([
            self.points_by_week[week]
            for week in sorted(self.points_by_week.keys())
        ])
        player_weekly_values = (1 - position_injury) * (
            player_weeks - weekly_rep_level)
        player_weekly_values[player_weekly_values < 0] = 0
        return player_weekly_values.sum()
