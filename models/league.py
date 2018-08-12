# coding: utf8

from definitions import ROOT_DIR
from models.player import Player
from models.team import Team
from scrape_projections import scrape_projections

import dill
import numpy as np
import os


class League:
    def __init__(self,
                 name,
                 scoring_settings=None,
                 roster_settings=None,
                 projection_source="web"):
        self.name = name
        self.projection_source = projection_source
        if not scoring_settings:
            scoring_settings = {}
        self.scoring_settings = {
            # I hate spaces in keys, but this allows projection parsing
            # to be much more elegant
            'pass yds': 0.04,
            'pass tds': 4.0,
            'int': -2.0,
            'rush yds': 0.1,
            'rush tds': 6.0,
            'rec': 0.0,
            'rec yds': 0.1,
            'rec tds': 6.0,
            'fum': -2.0,
        }
        for key, value in scoring_settings.items():
            self.scoring_settings[key] = value

        if not roster_settings:
            roster_settings = {}
        self.roster_settings = {
            'teams': 10,
            'roster_size': 16,
            'defense': 1,
            'kicker': 1,
            'qb': 1,
            'rb': 2,
            'wr': 2,
            'te': 1,
            'flex': 1,
            'flex_positions': ['rb', 'wr', 'te'],
            'auction_budget': None
        }
        for key, value in roster_settings.items():
            self.roster_settings[key] = value
        self.teams = {
            id: Team(id=id, league=self)
            for id in range(self.roster_settings['teams'])
        }

        self.player_universe = {}
        self.fill_player_universe()
        self.available_players = self.player_universe.copy()
        self.injury_likelihood()
        self.calculate_replacement_level()
        if self.roster_settings['auction_budget']:
            self.auction_budget_spent = 0
            self.calculate_auction_values()

    def save_to_disk(self, filename=None):
        file_path = os.path.join(ROOT_DIR, 'leagues',
                                 f"{filename if filename else self.name}.pkl")
        with open(file_path, 'wb') as output:
            dill.dump(self, output)

    @classmethod
    def load_from_disk(cls, filename):
        file_path = os.path.join(ROOT_DIR, 'leagues',
                                 "{}.pkl".format(filename))
        with open(file_path, 'rb') as saved_object:
            output = dill.load(saved_object)
        return output

    def __repr__(self):
        return f"League {self.name}, {self.roster_settings['teams']} teams"

    def fill_player_universe(self, source=None):
        source = source or self.projection_source
        if source == "web":
            all_projections = list(scrape_projections())
            file_path = os.path.join(ROOT_DIR, 'projections', 'v0.pkl')
            with open(file_path, 'wb') as output:
                dill.dump(all_projections, output)
        elif source == "disk":
            file_path = os.path.join(ROOT_DIR, 'projections', 'v0.pkl')
            with open(file_path, 'rb') as saved_projections:
                all_projections = dill.load(saved_projections)
        else:
            raise KeyError(
                f"Invalid source {source} must be \'web\' or \'disk\'")
        for projection in all_projections:
            if projection['id'] not in self.player_universe:
                self.player_universe[projection['id']] = Player(
                    league=self, projection=projection)
            else:
                self.player_universe[projection['id']].add_projection(
                    projection)

    def team_by_name(self, team_name):
        team_id, = [
            id for id, team in self.teams.items()
            if str(team.name) == team_name
        ]
        if team_id is None:
            raise KeyError(f"Team with name {team_name} not found")
        return self.teams[team_id]

    def player_by_name(self, player_name):
        player_id, = [
            id for id, player in self.player_universe.items()
            if player.name == player_name
        ]
        if not player_id:
            raise KeyError(f"Player with name {player_name} not found")
        return self.player_universe[player_id]

    def player_fuzzy_match(self, player_name_substring):
        players = [
            player for id, player in self.player_universe.items()
            if player_name_substring.lower() in player.name.lower()
        ]
        if not players:
            raise KeyError(
                f"Player name containing {player_name_substring} not found")
        return players[0] if len(players) == 1 else players

    def injury_likelihood(self):
        self.injury_simulations = {}
        # Obtained from
        # http://www.profootballlogic.com/articles/nfl-injury-rate-analysis/
        # Poisson probably isn't perfect here, distribution is likely bimodal
        # Where season ending injuries are the second mode
        # This feels close enough
        injury_stats = {
            'rb': {
                'likelihood': 0.051,
                'duration_mean': 3.9,
            },
            'wr': {
                'likelihood': .045,
                'duration_mean': 3.2
            },
            'qb': {
                'likelihood': .025,
                'duration_mean': 3.1
            },
            'te': {
                'likelihood': .049,
                'duration_mean': 2.6
            }
        }
        for position, injury_stat in injury_stats.items():
            injury_weeks = np.zeros([10000, 16])
            for simulation in range(10000):
                injured = [0] * 16
                for week in range(16):
                    if injured[week] == 0:
                        got_injured = np.random.random_sample(
                        ) <= injury_stat['likelihood']
                        if got_injured:
                            injury_length, = np.random.poisson(
                                injury_stat['duration_mean'], 1)
                            if injury_length > 0:
                                last_injured_week = np.min(
                                    [week + injury_length, 16])
                                injured[week:last_injured_week] = [1] * (
                                    last_injured_week - week)
                injury_weeks[simulation] = injured

            self.injury_simulations[position] = injury_weeks.mean(axis=0)

    def calculate_replacement_level(self):
        self.replacement_level = {}
        positions_to_check = ['qb', 'wr', 'rb', 'te']

        # Start with all players sorted by season points
        remaining_players = sorted(
            self.player_universe.values(),
            key=lambda player: player.season_points(),
            reverse=True)
        removed_ids = []

        total_bench_spots = (self.roster_settings['teams'] * (
            self.roster_settings['roster_size'] -
            (self.roster_settings['defense'] + self.roster_settings['kicker'] +
             self.roster_settings['qb'] + self.roster_settings['rb'] +
             self.roster_settings['wr'] + self.roster_settings['te'] +
             self.roster_settings['flex'])))
        starter_counts = {}
        for position in positions_to_check:
            starter_counts[position] = (
                self.roster_settings[position] * self.roster_settings['teams'])

        # I hate hardcoding this but can't think of a better way
        # QBs not being flexed makes it hard to assess their replacement level
        # So I chose to replicate general roster distribution

        starter_counts['qb'] += np.round(0.1 * total_bench_spots)
        total_bench_spots = np.round(0.9 * total_bench_spots)

        # Take out non-flex starters (and bench QBs)
        for position in positions_to_check:
            position_filtered = list(
                filter(lambda player: player.position == position,
                       remaining_players.copy()))
            ids_to_remove = [
                player.id
                for player in position_filtered[:int(starter_counts[position])]
            ]
            remaining_players = list(
                filter(lambda x: x.id not in ids_to_remove, remaining_players))
            removed_ids.extend(ids_to_remove)

        # Take out flex starters and other bench spots
        flex_starters = (
            self.roster_settings['flex'] * self.roster_settings['teams'])
        position_filtered = list(
            filter(
                lambda player: player.position in self.roster_settings['flex_positions'],
                remaining_players.copy()))
        ids_to_remove = [
            player.id for player in
            position_filtered[:int(flex_starters + total_bench_spots)]
        ]
        remaining_players = list(
            filter(lambda x: x.id not in ids_to_remove, remaining_players))
        removed_ids.extend(ids_to_remove)
        assert (len(removed_ids) == (
            self.roster_settings['roster_size'] -
            self.roster_settings['kicker'] - self.roster_settings['defense']) *
                self.roster_settings['teams'])

        # Now take the first player at each position for replacement level
        for position in positions_to_check:
            position_filtered = list(
                filter(lambda player: player.position == position,
                       remaining_players.copy()))
            self.replacement_level[position] = position_filtered[
                0].season_points()

    def best_available_players(self, position=None, n=20, auction=False):
        desired_output = ("auction_value"
                          if auction else "value_over_replacement")
        if position:
            eligible_players = [
                player for player in self.available_players.values()
                if player.position == position
            ]
        else:
            eligible_players = self.available_players.values()
        sorted_players = sorted(
            eligible_players,
            key=lambda player: getattr(player, desired_output)(),
            reverse=True)[:n]
        return [(player, np.round(getattr(player, desired_output)()))
                for player in sorted_players]

    def calculate_auction_values(self):
        if not self.roster_settings['auction_budget']:
            return
        self.auction_values = {}
        total_available_budget = (
            (self.roster_settings['auction_budget'] -
             self.roster_settings['defense'] - self.roster_settings['kicker'])
            * self.roster_settings['teams'] - self.auction_budget_spent)
        total_value_available = sum([
            player.value_over_replacement(auction=True)
            for player in self.available_players.values()
        ])
        for player_id, player in self.available_players.items():
            self.auction_values[player_id] = (
                player.value_over_replacement(auction=True) *
                total_available_budget / total_value_available)

    # TODO:
    # How many points would player X add to team Y (using injuries)
