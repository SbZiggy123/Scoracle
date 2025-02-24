document.addEventListener('DOMContentLoaded', function() {
    
    const homeScoreInput = document.getElementById('home-score');
    const awayScoreInput = document.getElementById('away-score');
    const oddsMultiplierSpan = document.getElementById('odds-multiplier');
    const exactPointsSpan = document.getElementById('exact-points');
    const resultPointsSpan = document.getElementById('result-points'); // I'm having this as variable cos could be changed depending on game 
    
    // data from the template
    const matchData = document.getElementById('match-data');
    const homeXG = JSON.parse(matchData.dataset.homeXg);
    const awayXG = JSON.parse(matchData.dataset.awayXg);
    const homeWeight = parseFloat(matchData.dataset.homeWeight);
    const basePoints = parseInt(matchData.dataset.basePoints);

    // Converted this to js for live change stuff instead of having to do page reloads
    function calculateExpectedScore(recentXG) {
        if (!recentXG || recentXG.length === 0) return 1.0;

        const weights = [0.3, 0.25, 0.2, 0.15, 0.1].slice(0, recentXG.length);
        const totalWeight = weights.reduce((a, b) => a + b, 0);
        const normalisedWeights = weights.map(w => w / totalWeight);

        const weightedXG = recentXG.reduce((sum, xg, i) => {
            return sum + (parseFloat(xg) * normalisedWeights[i]);
        }, 0);

        return Number(weightedXG.toFixed(2));
    }

    function calculateOdds(homeScore, awayScore) {
        // Calculate expected scores
        const homeExpected = calculateExpectedScore(homeXG) * homeWeight;
        const awayExpected = calculateExpectedScore(awayXG);

        // Calculate how "unlikely" the prediction is
        const homeDiff = Math.abs(homeScore - homeExpected);
        const awayDiff = Math.abs(awayScore - awayExpected);
        const totalDiff = homeDiff + awayDiff;

        // Calculate multiplier for unlikely predictions
        const oddsMultiplier = Math.pow(1.5, totalDiff);

        // Calculate potential points and give base points which is grabbed from html data 
        const potentialPoints = {
            exactScore: Math.round(basePoints * oddsMultiplier),
            correctResult: basePoints
        };

        return {
            multiplier: Number(oddsMultiplier.toFixed(2)),
            points: potentialPoints
        };
    }

    function updatePredictionDisplay() {
        const homeScore = parseInt(homeScoreInput.value) || 0;
        const awayScore = parseInt(awayScoreInput.value) || 0;

        const odds = calculateOdds(homeScore, awayScore);

        // Update display
        oddsMultiplierSpan.textContent = odds.multiplier.toFixed(2);
        exactPointsSpan.textContent = odds.points.exactScore;
        resultPointsSpan.textContent = odds.points.correctResult;
    }

    // Add event listeners for score inputs
    homeScoreInput.addEventListener('input', updatePredictionDisplay);
    awayScoreInput.addEventListener('input', updatePredictionDisplay);

    // Initialize display
    updatePredictionDisplay();
});

/* odds multiplier is over 1.00x even when user bets AI prediction 
cos its based on the expected score which can be a decimal... AI prediction rounds that*/