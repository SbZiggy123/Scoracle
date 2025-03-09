import aiohttp
from understat import Understat
import math

'''PREDICTION MODEL'''
# Gonna try basic class of functions
class PredictionSystem:
    def __init__(self):
        self.home_weight = 1.05  # Home advantage multiplier.. Change it? Maybe for teams that perform esp well at home?
        #self.base_points = 100  # Base points for correct predictions... More for risky... To be used in the leagues
        
    # Creating a summed xg here of last 5 games which will be used to predict score
    def calculate_expected_score(self, recent_xg, xg_performance=1.0):
        """Calculate expected score based on recent xG data"""
        if not recent_xg:
            return 1.0  # Default if no data available
            
        weights = [0.3, 0.25, 0.2, 0.15, 0.1]  # Most recent game has highest weight
    
        weights = weights[:len(recent_xg)] # Only take first x weight numbers if we can only get x when x < 5
        # Normalise weights if we have fewer than 5 games
        if len(weights) < 5:
            # Example if only 3 games then 0.3+0.25+0.2 = .75... 
            total = sum(weights)
            weights = [w/total for w in weights] # make em add up to 1.0
        # zip pairs then multiply each pair, sum them and round 2 deci places
        weighted_xg = sum(xg * weight for xg, weight in zip(recent_xg, weights))
        adjusted_xg = weighted_xg * xg_performance
        return round(adjusted_xg, 2)

    async def get_team_recent_data(self, team_name, league_code, season):
        """Get recent match data for a team with opposition information"""
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            results = await understat.get_team_results(team_name, season) # gets whole season
            
            
            total_goals = 0
            total_xg = 0
            
            for match in results:
                if match["h"]["title"] == team_name:
                    if match["goals"]["h"] is not None and match["xG"]["h"] is not None:
                        total_goals += int(match["goals"]["h"])
                        total_xg += float(match["xG"]["h"])
                else:
                    if match["goals"]["a"] is not None and match["xG"]["a"] is not None:
                        total_goals += int(match["goals"]["a"])
                        total_xg += float(match["xG"]["a"])
            
            # ratio
            xg_performance = 1.0
            if total_xg >= 1.0:
                xg_performance = total_goals / total_xg
                # Cap between 0.7 and 1.3
                xg_performance = max(0.7, min(1.3, xg_performance))
            
            # Sort by most recent
            recent_results = sorted(results, key=lambda x: x["datetime"], reverse=True)[:5]
            
            # Extract xG values and opposition teams based on home/away
            # Playing against a top team will affect the xg... Don't want that to affect the model TOO much
            recent_xg = []
            recent_goals = []
            opposition_teams = []
            match_dates = []
            match_results = []  # W, D, L
            
            for match in recent_results:
                if match["h"]["title"] == team_name:
                    # Team played at home
                    recent_xg.append(float(match["xG"]["h"]))
                    recent_goals.append(int(match["goals"]["h"]))
                    opposition_teams.append(match["a"]["title"])
                    result = "W" if match["goals"]["h"] > match["goals"]["a"] else "D" if match["goals"]["h"] == match["goals"]["a"] else "L"
                    match_results.append(result)
                else:
                    # Team played away
                    recent_xg.append(float(match["xG"]["a"]))
                    recent_goals.append(int(match["goals"]["a"]))
                    opposition_teams.append(match["h"]["title"])
                    result = "W" if match["goals"]["a"] > match["goals"]["h"] else "D" if match["goals"]["a"] == match["goals"]["h"] else "L"
                    match_results.append(result)
                
                
                match_date = match["datetime"].split(" ")[0]
                match_dates.append(match_date)
                
            return {
                "xg": recent_xg, 
                "goals": recent_goals,
                "opponents": opposition_teams,
                "dates": match_dates,
                "results": match_results,
                "xg_performance": round(xg_performance, 2)  # Include the performance ratio
            }
    
    async def get_league_positions(self, league_code, season):
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            table = await understat.get_league_table(league_code, season, with_headers=False)
            
            positions = {}
            for position, team_data in enumerate(table):
                team_name = team_data[0]
                positions[team_name] = position + 1
                
            return positions
        
    def adjust_for_opposition(self, expected_score, opposition_positions, league_size=20):
        if not opposition_positions:
            return expected_score
            
        # Calculate average position of recent opponents
        avg_position = sum(opposition_positions) / len(opposition_positions)
        
        # Position factor: 
        position_factor = 1.0 + (0.4 * ((league_size/2) - avg_position) / league_size)
        
        return round(expected_score * position_factor, 2)
    
    """
    async def get_team_xg_performance(self, team_name, season):
        # Function to see whether they outperform or underperform their xg
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            results = await understat.get_team_results(team_name, season)
            
            total_goals = 0
            total_xg = 0
            
            for match in results:
                if match["h"]["title"] == team_name:
                    if match["goals"]["h"] is not None and match["xG"]["h"] is not None:
                        total_goals += int(match["goals"]["h"])
                        total_xg += float(match["xG"]["h"])
                else:
                    if match["goals"]["a"] is not None and match["xG"]["a"] is not None:
                        total_goals += int(match["goals"]["a"])
                        total_xg += float(match["xG"]["a"])
            
            # if not enough data
            if total_xg < 1.0:
                return 1.0
                
            # Calculate ratio and cap between 0.7 and 1.3 
            ratio = total_goals / total_xg
            return max(0.7, min(1.3, ratio))
    """
    # Moving route stuff to here
    async def predict_match(self, match_id, league_code, season):
        """Generate match prediction with all factors"""
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            
            # Get match details
            fixtures = await understat.get_league_fixtures(league_code, season)
            match = next((fixture for fixture in fixtures if fixture["id"] == match_id), None)
            
            if not match:
                return None
                
            home_team = match["h"]["title"]
            away_team = match["a"]["title"]
            
            league_positions = await self.get_league_positions(league_code, season)
            
            # New dict with everything reduce calls
            home_data = await self.get_team_recent_data(home_team, league_code, season)
            away_data = await self.get_team_recent_data(away_team, league_code, season)
            
            # Extract xG performance ratios
            home_xg_performance = home_data["xg_performance"]
            away_xg_performance = away_data["xg_performance"]
            
            # Calculate base expected scores with xG performance adjustment
            home_expected = self.calculate_expected_score(home_data["xg"], home_xg_performance)
            away_expected = self.calculate_expected_score(away_data["xg"], away_xg_performance)
            
            # Adjust for opposition strength
            # Accessed through home_data y ... etc now. 
            home_opposition_positions = [league_positions.get(team, 10) for team in home_data["opponents"]]
            away_opposition_positions = [league_positions.get(team, 10) for team in away_data["opponents"]]
            
            home_expected = self.adjust_for_opposition(home_expected, home_opposition_positions)
            away_expected = self.adjust_for_opposition(away_expected, away_opposition_positions)
            
            # Round score for AI prediction
            home_score = round(home_expected)
            away_score = round(away_expected)
            
            # Calculate win probabilities
            probabilities = self.calculate_probabilities(home_expected, away_expected)
            
            return {
                "match": match,
                "home_xg": home_data["xg"],
                "away_xg": away_data["xg"],
                "home_goals": home_data["goals"],
                "away_goals": away_data["goals"],
                "home_opponents": home_data["opponents"],
                "away_opponents": away_data["opponents"],
                "home_dates": home_data["dates"],
                "away_dates": away_data["dates"],
                "home_results": home_data["results"],
                "away_results": away_data["results"],
                "home_xg_performance": home_xg_performance,
                "away_xg_performance": away_xg_performance,
                "home_expected": home_expected,
                "away_expected": away_expected,
                "prediction": {"home": home_score, "away": away_score},
                "probabilities": probabilities
            }   
    """User will alter his bet live IN the webapp. It NEEDS to update odds then and there... This will be moved to js"""
        
        # Server will use this when adding to DB... JS mirrors it
    def calculate_points(self, home_expected, away_expected, user_prediction, bet_amount=100):
        """Calculate points and multiplier for user prediction"""
        # Calculate how "unlikely" the user's prediction is for exact score
        home_diff = abs(user_prediction[0] - home_expected)
        away_diff = abs(user_prediction[1] - away_expected)
        total_diff = home_diff + away_diff
        
        # Apply dampening for extreme predictions
        if total_diff > 4:
            total_diff = 4 + (total_diff - 4) * 0.5
        
        # Calculate exact score multiplier 
        exact_score_multiplier = round(min(1.0 + (total_diff * 0.5), 8.0), 2)
        
        # Determine the result of the user's prediction
        predicted_result = "draw"
        if user_prediction[0] > user_prediction[1]:
            predicted_result = "home_win"
        elif user_prediction[0] < user_prediction[1]:
            predicted_result = "away_win"
        
        # Get probabilities for each outcome
        probabilities = self.calculate_probabilities(home_expected, away_expected)
        
        # Get the probability of the predicted result
        result_probability = 0
        if predicted_result == "home_win":
            result_probability = probabilities["home_win"] / 100
        elif predicted_result == "draw":
            result_probability = probabilities["draw"] / 100
        else:
            result_probability = probabilities["away_win"] / 100
        
        # Calculate result multiplier based on how unlikely the predicted result is
        result_multiplier = round(min(1.0 + (1.5 * (1 - result_probability)), 5.0), 2)
        
        return {
            "multiplier": exact_score_multiplier,
            "exact_score": int(bet_amount * exact_score_multiplier),
            "correct_result": int(bet_amount * result_multiplier),
            "predicted_result": predicted_result,
            "result_multiplier": result_multiplier
        }
    
    def calculate_probabilities(self, home_expected, away_expected):
        """Calculate win/draw/loss probabilities"""
        home_probs = {}
        away_probs = {}
        
        # Calculate goal probabilities for each team fix so
        for i in range(7):
            home_probs[i] = poisson_probability(i, home_expected)
            away_probs[i] = poisson_probability(i, away_expected)
        
        # Calculate match outcome probabilities
        home_win_prob = 0
        draw_prob = 0
        away_win_prob = 0
        
        # Sum probabilities for each outcome
        for home_goals in range(7):
            for away_goals in range(7):
                prob = home_probs[home_goals] * away_probs[away_goals]
                
                if home_goals > away_goals:
                    home_win_prob += prob
                elif home_goals == away_goals:
                    draw_prob += prob
                else:
                    away_win_prob += prob
        
        # Apply home advantage adjustment for home win
        home_edge = 0.05  # 5% home advantage
        home_win_prob = min(home_win_prob + home_edge, 0.9)
        
        #  sum to 1
        total = home_win_prob + draw_prob + away_win_prob
        home_win_prob /= total
        draw_prob /= total
        away_win_prob /= total
        
        return {
            "home_win": round(home_win_prob * 100, 1),
            "draw": round(draw_prob * 100, 1),
            "away_win": round(away_win_prob * 100, 1)
        }
    
    
def poisson_probability(k, lambd):
    return (math.exp(-lambd) * (lambd ** k)) / math.factorial(k)
    
    