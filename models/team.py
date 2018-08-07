# coding: utf-8


class Team:
    def __init__(self, id, league, name=None):
        self.league = league
        self.id = id
        self.players_by_id = {}
        self.name = name

    def __repr__(self):
        return self.name if self.name else "Team {}".format(self.id)

    def add_player(self, player):
        if player.id not in self.league.available_players.keys():
            raise KeyError(
                f"Player {player.name}, id {player.id} is not available")
        if len(self.players_by_id) < self.league.roster_settings['roster_size']:
            self.players_by_id[player.id] = player
            player.team_id = self.id
            self.league.available_players.pop(player.id)
        else:
            raise ValueError(f"Team {self.id} roster is already full")

    def remove_player(self, player_id):
        if player_id not in self.players_by_id:
            raise KeyError(f"Player with id {player_id} not on team {self.id}")
        else:
            removed_player = self.players_by_id.pop(player_id)
            removed_player.team_id = None
            self.league.available_players[player_id] = removed_player
