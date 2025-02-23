from understat import Understat
import aiohttp
import asyncio

async def predictxG(team, opponent):
    async with aiohttp.ClientSession() as session:
        understat = Understat(session)

        #Get Modified xG based on last 5 games.
        results = await understat.get_team_results(team, 2024)
        recent_results = sorted(results, key=lambda x: x["datetime"], reverse=True)[:5]
        totalxG = 0
        avgxG = 0
        performBonus = 0

        for result in recent_results:
            side = result["side"]
            xG = result["xG"][side] 
            totalxG += float(xG)

            goals = result["goals"][side]
            if int(goals) > float(xG) and int(goals) - float(xG) >= 0.5: 
                #If team has outperformed their xG for that match then add an extra value.
                performBonus += 0.2
        avgxG = totalxG / 5
        finalxG = performBonus + avgxG

        #Get up to last 3 of matches against opponent.
        #for result in results:
            #for side in ["h", "a"]:
                #if result[side]["title"] == opponent:
                    #for each win add a modifier to xG.
                
        return round(finalxG)

loop = asyncio.get_event_loop()
loop.run_until_complete(predictxG("Manchester United"))