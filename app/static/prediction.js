document.addEventListener('DOMContentLoaded', function() {
    const homeScoreInput = document.getElementById('home-score');
    const awayScoreInput = document.getElementById('away-score');
    const oddsMultiplierSpan = document.getElementById('odds-multiplier');
    const exactPointsSpan = document.getElementById('exact-points');
    const resultPointsSpan = document.getElementById('result-points');
    
    // Get data from the template 
    const matchData = document.getElementById('match-data');
    const homeExpected = parseFloat(matchData.dataset.homeExpected);
    const awayExpected = parseFloat(matchData.dataset.awayExpected);
    const basePoints = parseInt(matchData.dataset.basePoints || "100");

    // Calculate points based on user prediction vs expected scores
    function calculatePoints(homeScore, awayScore) {
        // Calculate how "unlikely" the prediction is
        const homeDiff = Math.abs(homeScore - homeExpected);
        const awayDiff = Math.abs(awayScore - awayExpected);
        let totalDiff = homeDiff + awayDiff;
        
        // Apply dampening for extreme stupid predictions
        if (totalDiff > 4) {
            totalDiff = 4 + (totalDiff - 4) * 0.5;
        }
        
        // Calculate multiplier (capped at 8x)
        const oddsMultiplier = Math.min(1.0 + (totalDiff * 0.5), 8.0);
        
        return {
            multiplier: oddsMultiplier.toFixed(2),
            exactScore: Math.round(basePoints * oddsMultiplier),
            correctResult: basePoints
        };
    }

    function updatePredictionDisplay() {
        const homeScore = parseInt(homeScoreInput.value) || 0;
        const awayScore = parseInt(awayScoreInput.value) || 0;

        const points = calculatePoints(homeScore, awayScore);

        // Update display
        oddsMultiplierSpan.textContent = points.multiplier;
        exactPointsSpan.textContent = points.exactScore;
        resultPointsSpan.textContent = points.correctResult;
    }

    // Add event listeners for score inputs
    homeScoreInput.addEventListener('input', updatePredictionDisplay);
    awayScoreInput.addEventListener('input', updatePredictionDisplay);

    // Initialize display
    updatePredictionDisplay();
});

/* odds multiplier is over 1.00x even when user bets AI prediction 
cos its based on the expected score which can be a decimal... AI prediction rounds that*/