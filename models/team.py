# coding: utf-8

from collections import defaultdict
from scipy.stats import binom
import numpy as np


class Team:
    def __init__(self, id, league, name=None):
        self.league = league
        self.id = id
        self.players_by_id = {}
        self.name = name

    def __repr__(self):
        return self.name if self.name else "Team {}".format(self.id)

    def add_player(self, player, auction_price=None):
        if player.id not in self.league.available_players.keys():
            raise KeyError(
                f"Player {player.name}, id {player.id} is not available")
        if len(self.players_by_id) < self.league.roster_settings['roster_size']:
            self.players_by_id[player.id] = player
            player.team_id = self.id
            self.league.available_players.pop(player.id)
            if auction_price:
                self.league.auction_budget_spent += auction_price
                self.league.calculate_auction_values()
        else:
            raise ValueError(f"Team {self.id} roster is already full")

    def remove_player(self, player_id):
        if player_id not in self.players_by_id.keys():
            raise KeyError(f"Player with id {player_id} not on team {self.id}")
        else:
            removed_player = self.players_by_id.pop(player_id)
            removed_player.team_id = None
            self.league.available_players[player_id] = removed_player

    def value_from_player(self, player):
        def flex_empty(team_makeup):
            if self.league.roster_settings['flex'] == 0:
                return False
            else:
                for position in self.league.roster_settings['flex_positions']:
                    if (team_makeup[position] - 1 >=
                            self.league.roster_settings[position]):
                        return False
                return True

        def projected_leaders(players, positions):
            return sorted(
                players,
                key=
                lambda player: player.weekly_points(week) if player.weekly_points(week) and player.position in positions else 0.0,
                reverse=True)

        total_value = 0
        team_makeup = defaultdict(lambda: 0)
        for rostered_player in self.players_by_id.values():
            team_makeup[rostered_player.position] += 1
        if team_makeup[player.position] < self.league.roster_settings[player.
                                                                      position]:
            return player.value_over_replacement()
        elif (player.position in self.league.roster_settings['flex_positions']
              and flex_empty(team_makeup)):
            return player.value_over_replacement()
        else:
            players_to_evaluate = list(self.players_by_id.values())
            players_to_evaluate.extend([player])
            for week in range(1, 17):
                week_injury_rate = self.league.injury_simulations[
                    player.position][week - 1]

                weekly_projected_leaders = projected_leaders(
                    players_to_evaluate, [player.position])

                player_rank = weekly_projected_leaders.index(player)

                total_starting_players = self.league.roster_settings[
                    player.position]
                non_flex_pct = 1 if player_rank < total_starting_players else (
                    1 - binom.cdf(
                        # Probability that few enough players ahead get hurt to
                        # prevent player from starting
                        player_rank - total_starting_players,
                        player_rank,
                        week_injury_rate))
                if (player.position not in
                        self.league.roster_settings['flex_positions']
                        or non_flex_pct == 1
                        or self.league.roster_settings['flex'] == 0):
                    total_value += np.min(
                        week_injury_rate * non_flex_pct *
                        (player.weekly_points(week) -
                         self.league.replacement_level[player.position] / 16),
                        0)
                    continue
                else:
                    weekly_projected_leaders = projected_leaders(
                        players_to_evaluate,
                        self.league.roster_settings['flex_positions'])

                    player_rank = weekly_projected_leaders.index(player)

                    total_flex_eligible_starters = sum([
                        self.league.roster_settings[pos] for pos in
                        self.league.roster_settings['flex_positions']
                    ])

                    injury_rates = []
                    injury_rate_weights = []
                    for pos in self.league.roster_settings['flex_positions']:
                        injury_rates.append(
                            self.league.injury_simulations[pos][week - 1])
                        injury_rate_weights.append(
                            self.league.roster_settings[pos])

                    flex_pct = 1 if player_rank < total_flex_eligible_starters else (
                        1 - binom.cdf(
                            # Probability that few enough players ahead get hurt to
                            # prevent player from starting
                            player_rank - total_flex_eligible_starters,
                            player_rank,
                            np.average(
                                injury_rates, weights=injury_rate_weights)))

                    start_pct = (1 - non_flex_pct) * flex_pct + non_flex_pct
                    total_value += np.min(
                        week_injury_rate * start_pct *
                        (player.weekly_points(week) -
                         self.league.replacement_level[player.position] / 16),
                        0)
            return total_value

    def best_pick(self, n=5):
        added_value = {}
        for player in self.league.available_players.values():
            added_value[player.id] = self.value_from_player(player)

        top_player_ids = list(
            sorted(
                added_value, key=lambda p_id: added_value[p_id],
                reverse=True))[:n]
        return [(self.league.player_universe[id], added_value[id])
                for id in top_player_ids]
