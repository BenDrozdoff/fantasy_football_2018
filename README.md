
# Fantasy Football Draft Tool
### Ben Drozdoff

#### A tool to help you track your draft in an iPython notebook and select players based on injury-adjusted value over replacement

### Usage

Customize your league with your own scoring and roster settings.  Common presets are already defaulted, so just pass in the settings you'd like to override.  See below for a 12 team league with half-PPR.


```python
from models.league import League
league = League("demo_league", roster_settings = {'teams': 12}, scoring_settings = {'rec': 0.5})

```

### See best available players


```python
league.best_available_players(n=4)
```




    [Bell, Le'Veon, rb, PIT,
     Johnson, David, rb, ARZ,
     Gurley, Todd, rb, LAR,
     Elliott, Ezekiel, rb, DAL]



### Simulate a draft


```python
league.teams[0].name = "Team with first pick"
drafted_player = league.player_by_name("Bell, Le\'Veon")
drafted_player.add_to_team(team_name="Team with first pick")
league.best_available_players(n=5)
```




    [Johnson, David, rb, ARZ,
     Gurley, Todd, rb, LAR,
     Elliott, Ezekiel, rb, DAL,
     Gordon, Melvin, rb, LAC,
     Kamara, Alvin, rb, NOR]



### Save progress to disk
I certainly don't trust a kernel to not die in the 8th round, you shouldn't either!


```python
league.save_to_disk()
```

### Reload progress from disk


```python
resumed_league = League.load_from_disk("demo_league")
```

### Goals for season start
In addition to this helpful best_available_players method, I'd like to add a method that considers current team makeup to determine which player will add the most value to a team.  If I already have 3 RB, it might not be the best use of resources to take a RB in the 4th round, even if that RB has the highest value over replacement level

Additionally, I'd like to use the infrastructure in place to calculate auction values, not only for predraft, but on the fly.
