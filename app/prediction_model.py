import aiohttp
from understat import Understat

'''PREDICTION MODEL'''
# Gonna try basic class of functions
class PredictionSystem:
    def __init__(self):
        self.home_weight = 1.2  # Home advantage multiplier.. Change it? Maybe for teams that perform esp well at home?
        self.base_points = 100  # Base points for correct predictions... More for risky... To be used in the leagues
        
    # Creating a summed xg here of last 5 games which will be used to predict score
    def calculate_expected_score(self, recent_xg):
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
        return round(weighted_xg, 2)

    async def get_team_recent_data(self, team_name, season):
        """Get recent match data for a team directly from Understat"""
        async with aiohttp.ClientSession() as session:
            understat = Understat(session)
            results = await understat.get_team_results(team_name, season)
            
            # Sort by most recent
            recent_results = sorted(results, key=lambda x: x["datetime"], reverse=True)[:5]
            
            # Extract xG values based on home/away
            recent_xg = []
            for match in recent_results:
                if match["h"]["title"] == team_name:
                    recent_xg.append(float(match["xG"]["h"]))
                else:
                    recent_xg.append(float(match["xG"]["a"]))
                    
            return recent_xg
    
    def predict_score(self, home_xg, away_xg):
        """Generate AI prediction for the match"""
        home_expected = self.calculate_expected_score(home_xg) * self.home_weight
        away_expected = self.calculate_expected_score(away_xg)
        
        # Round to nearest likely football score
        home_score = round(home_expected)
        away_score = round(away_expected)
        
        return home_score, away_score

    """User will alter his bet live IN the webapp. It NEEDS to update odds then and there... This will be moved to js"""

    def calculate_odds(self, home_xg, away_xg, user_prediction):
        """Calculate betting odds and potential points"""
        # Calculate expected scores
        home_expected = self.calculate_expected_score(home_xg) * self.home_weight
        away_expected = self.calculate_expected_score(away_xg)
        
        # AI prediction... Just rounding expected
        ai_home, ai_away = self.predict_score(home_xg, away_xg)
        
        # Calculate how "unlikely" the user's prediction is compared to expected values
        # We are ccomparing this to expected score NOT AI score
        home_diff = abs(user_prediction[0] - home_expected)
        away_diff = abs(user_prediction[1] - away_expected)
        total_diff = home_diff + away_diff
        
        # multiplier for unlikely predictions.. Idk what exactly to put but crazy bets gotta be more.
        odds_multiplier = 1.5 ** total_diff
        
        # Calculate potential points
        """For correct_result... Should be some formula not based on their score but instead their team they chose to win"""
        potential_points = {
            "exact_score": int(self.base_points * odds_multiplier),  # Exact score
            "correct_result": int(self.base_points),  # They get base points for correct score for now 
            "wrong_result": 0  # Wrong result
        }
        
        # Calculate result probabilities
        probabilities = self.calculate_probabilities(home_expected, away_expected)
        
        return {
            "ai_prediction": {"home": ai_home, "away": ai_away},
            "expected_scores": {"home": home_expected, "away": away_expected},
            "odds_multiplier": round(odds_multiplier, 2),
            "potential_points": potential_points,
            "probabilities": probabilities
        }
    
    def calculate_probabilities(self, home_expected, away_expected):
        """Calculate win/draw/loss probabilities"""
        diff = home_expected - away_expected
        home_win = min(0.45 + (0.1 * diff), 0.9)
        draw = max(0.2 - (0.05 * abs(diff)), 0.05)
        away_win = 1 - (home_win + draw)
        
        return {
            "home_win": round(home_win * 100, 1),
            "draw": round(draw * 100, 1),
            "away_win": round(away_win * 100, 1)
        }
        
        
# Player prediction here