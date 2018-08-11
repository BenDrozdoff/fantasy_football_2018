# coding: utf-8

from scipy.stats import binom
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
        return self.points_by_week.get(week) or self._weekly_points(week)

    def _weekly_points(self, week):
        points = 0.0
        projection = self.projections_by_week.get(week)
        if not projection:
            self.points_by_week[week] = points
            return
        for category, value in self.league.scoring_settings.items():
            points += value * float(projection.get(category, 0))
        self.points_by_week[week] = points
        return points

    def season_points(self):
        relevant_weeks = range(1, 17)
        for week in relevant_weeks:
            self.weekly_points(week)
        return sum(self.points_by_week.values())

    def value_over_replacement(self, auction=False):
        position_injury = self.league.injury_simulations[self.position]
        weekly_rep_level = self.league.replacement_level[self.position] / 16
        player_weeks = np.array([
            self.points_by_week[week]
            for week in sorted(self.points_by_week.keys())
        ])
        player_weekly_values = (1 - position_injury) * (
            player_weeks - weekly_rep_level)
        if auction:
            player_weekly_values *= np.array([
                self.team_independent_start_pct(week) for week in range(1, 17)
            ])
        player_weekly_values[player_weekly_values < 0] = 0
        return player_weekly_values.sum()

    def auction_value(self):
        return self.league.auction_values[self.id]

    def team_independent_start_pct(self, week):
        week_injury_rate = self.league.injury_simulations[self.position][week -
                                                                         1]
        weekly_projected_leaders = sorted(
            self.league.player_universe.values(),
            key=
            lambda player: player.weekly_points(week) if player.weekly_points(week) and player.position == self.position else 0.0,
            reverse=True)

        player_rank = weekly_projected_leaders.index(self)

        total_starting_players = (self.league.roster_settings[self.position] *
                                  self.league.roster_settings['teams'])
        without_flex_pct = 1 if player_rank < total_starting_players else (
            1 - binom.cdf(
                # Probability that few enough players ahead get hurt to prevent
                # player from starting
                player_rank - total_starting_players,
                player_rank,
                week_injury_rate))
        if (self.position not in self.league.roster_settings['flex_positions']
                or without_flex_pct == 1):
            return without_flex_pct
        else:
            weekly_projected_leaders = sorted(
                self.league.player_universe.values(),
                key=
                lambda player: player.weekly_points(week) if player.weekly_points(week) and player.position in self.league.roster_settings['flex_positions'] else 0.0,
                reverse=True)

            player_rank = weekly_projected_leaders.index(self)

            total_flex_eligible_starters = (sum([
                self.league.roster_settings[pos]
                for pos in self.league.roster_settings['flex_positions']
            ]) * self.league.roster_settings['teams'])

            without_flex_pct = 1 if player_rank < total_flex_eligible_starters else (
                1 - binom.cdf(
                    # Probability that few enough players ahead get hurt to prevent
                    # player from starting
                    player_rank - total_flex_eligible_starters,
                    player_rank,
                    week_injury_rate))

            return (1 - without_flex_pct) * without_flex_pct
