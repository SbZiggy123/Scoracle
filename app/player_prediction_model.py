import aiohttp
from understat import Understat

class PlayerPredictionSystem:
    def __init__(self):
        self.base_points = 100  # Works similar to PredictionSystem
    
    # No way to get definite players that will play so predict
    async def get_likely_match_players(self, match_id, season):
        """Get likely players for an upcoming match based on recent games"""
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            
            # Get match details
            fixtures = await understat.get_league_fixtures("epl", season)
            match = next((fixture for fixture in fixtures if fixture["id"] == match_id), None)
            
            if not match:
                return None
                
            home_team = match["h"]["title"]
            away_team = match["a"]["title"]
            
            # Get team players
            home_players = await understat.get_team_players(home_team, season)
            away_players = await understat.get_team_players(away_team, season)
            
            # Get recent matches to identify active players
            home_results = await understat.get_team_results(home_team, season)
            away_results = await understat.get_team_results(away_team, season)
            
            # Sort by recent match date
            home_recent_matches = sorted(home_results, key=lambda x: x["datetime"], reverse=True)[:3]
            away_recent_matches = sorted(away_results, key=lambda x: x["datetime"], reverse=True)[:3]
            
            # Get player data from recent matches
            home_recent_players = []
            away_recent_players = []
            
            # Await heavy
            for match in home_recent_matches:
                try:
                    match_players = await understat.get_match_players(match["id"])
                    # Filter to just this team's players
                    if "h" in match_players and match["h"]["title"] == home_team:
                        home_recent_players.extend(match_players["h"].values())
                    elif "a" in match_players and match["a"]["title"] == home_team:
                        home_recent_players.extend(match_players["a"].values())
                except Exception as e:
                    print(f"Error getting players for match {match['id']}: {e}")
            
            for match in away_recent_matches:
                try:
                    match_players = await understat.get_match_players(match["id"])
                    # Filter to just this team's players
                    if "h" in match_players and match["h"]["title"] == away_team:
                        away_recent_players.extend(match_players["h"].values())
                    elif "a" in match_players and match["a"]["title"] == away_team:
                        away_recent_players.extend(match_players["a"].values())
                except Exception as e:
                    print(f"Error getting players for match {match['id']}: {e}")
            
            # Process and rank players
            processed_home_players = self.process_and_rank_players(home_players, home_recent_players)
            processed_away_players = self.process_and_rank_players(away_players, away_recent_players)
            
            return {
                "match": match,
                "home_team": home_team,
                "away_team": away_team,
                "home_players": processed_home_players,
                "away_players": processed_away_players
            }
    
    def process_and_rank_players(self, team_players, recent_players):
        """Process and rank players by likelihood of playing"""
        # Create a map of player_id to their data from recent games. Works ok.
        recent_players_dict = {}
        for player in recent_players:
            player_id = player.get("player_id")
            if player_id and player_id not in recent_players_dict:
                recent_players_dict[player_id] = player
            elif player_id and int(player.get("time", 0)) > int(recent_players_dict[player_id].get("time", 0)):
                # Keep the record with more minutes if player appears multiple times
                recent_players_dict[player_id] = player
        
        # Enhance team players with recent match data
        processed_players = []
        for player in team_players:
            player_data = {
                "id": player.get("id"),
                "name": player.get("player_name"),
                "position": player.get("position", "").split()[0] if player.get("position") else "", # Main pos
                "games": int(player.get("games", 0)),
                "goals": int(player.get("goals", 0)),
                "shots": int(player.get("shots", 0)),
                "xG": float(player.get("xG", 0)),
                "assists": int(player.get("assists", 0)),
                "key_passes": int(player.get("key_passes", 0)),
                "xA": float(player.get("xA", 0)), # possibly later
                "time": int(player.get("time", 0)),
                "avg_mins_per_game": int(player.get("time", 0)) / int(player.get("games", 1)),
                "goals_per_90": (int(player.get("goals", 0)) / int(player.get("time", 90))) * 90,
                "shots_per_90": (int(player.get("shots", 0)) / int(player.get("time", 90))) * 90,
                "recently_played": False,
                "last_mins_played": 0,
                "likelihood": 0  # Playing likelihood score
            }
            
            # Add recent match data if available
            if player.get("id") in recent_players_dict:
                recent_data = recent_players_dict[player.get("id")]
                player_data["recently_played"] = True
                player_data["last_mins_played"] = int(recent_data.get("time", 0))
                player_data["recent_position"] = recent_data.get("position", "")
                
                # Calculate likelihood score 
                player_data["likelihood"] = int(recent_data.get("time", 0)) * 0.7 + int(player.get("time", 0)) * 0.3
            else:
                # Player didn't play in recent matches
                player_data["likelihood"] = int(player.get("time", 0)) * 0.3
            
            processed_players.append(player_data)
        
        # Sort by likelihood of playing 
        sorted_players = sorted(processed_players, key=lambda x: x["likelihood"], reverse=True)
        
        # Take only the top players who are likely to play
        return sorted_players[:18]  # More?
    
    def calculate_player_expected_stats(self, player):
        """Calculate expected stats for a player based on historical data"""
        exp_goals_per_90 = player["goals_per_90"]
        exp_shots_per_90 = player["shots_per_90"]
        
        # Expected minutes - use average or recent minutes if available see above
        exp_minutes = player["last_mins_played"] if player["recently_played"] else player["avg_mins_per_game"]
        
        # maybe remove this entirely?
        return {
            "exp_goals": round(exp_goals_per_90 * (exp_minutes / 90), 2),
            "exp_shots": round(exp_shots_per_90 * (exp_minutes / 90), 2),
            "exp_minutes": round(exp_minutes)
        }
    
    def calculate_prediction_multiplier(self, player, predicted_goals, predicted_shots, predicted_minutes):
        """Calculate multiplier based on how bold the prediction is"""
        # Get baseline expectations
        expected = self.calculate_player_expected_stats(player)
        
        # Calculate deviation of user from expectations. Like games. multiplier derived from how fat they deviate
        goals_diff = abs(predicted_goals - expected["exp_goals"])
        shots_diff = abs(predicted_shots - expected["exp_shots"])
        minutes_diff = abs(predicted_minutes - expected["exp_minutes"])
        
        # Normalize differences based on typical ranges
        normalized_goals_diff = min(goals_diff / 1.0, 3.0)  # Capped
        normalized_shots_diff = min(shots_diff / 2.0, 2.0)  
        normalized_minutes_diff = min(minutes_diff / 30.0, 1.5)  
        
        base_multiplier = 1.0
        
        # Different weights for different stats
        goals_weight = 0.5
        shots_weight = 0.3
        minutes_weight = 0.2
        
        # Calculate weighted average multiplier
        multiplier = base_multiplier + (
            normalized_goals_diff * goals_weight +
            normalized_shots_diff * shots_weight +
            normalized_minutes_diff * minutes_weight
        )
        
        multiplier = max(1.0, min(multiplier, 8.0))
        
        return round(multiplier, 2)
    
    def calculate_points(self, player, predicted_goals, predicted_shots, predicted_minutes):
        """Calculate potential points for a player prediction"""
        multiplier = self.calculate_prediction_multiplier(
            player, predicted_goals, predicted_shots, predicted_minutes
        )
        
        return {
            "multiplier": multiplier,
            "potential_points": int(self.base_points * multiplier)
        }