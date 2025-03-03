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


    // CHARTS 
    
    const chartData = document.getElementById('chart-data');
    if (!chartData) return;
    
    const homeTeam = chartData.dataset.homeTeam;
    const awayTeam = chartData.dataset.awayTeam;
    const homeXg = JSON.parse(chartData.dataset.homeXg);
    const awayXg = JSON.parse(chartData.dataset.awayXg);
    const homeGoals = JSON.parse(chartData.dataset.homeGoals);
    const awayGoals = JSON.parse(chartData.dataset.awayGoals);
    const homeOpponents = JSON.parse(chartData.dataset.homeOpponents);
    const awayOpponents = JSON.parse(chartData.dataset.awayOpponents);
    const homeDates = JSON.parse(chartData.dataset.homeDates);
    const awayDates = JSON.parse(chartData.dataset.awayDates);
    const homeResults = JSON.parse(chartData.dataset.homeResults);
    const awayResults = JSON.parse(chartData.dataset.awayResults);
    
    // Create labels for each data point 
    const homeLabels = homeDates.map((date, i) => 
        `vs ${homeOpponents[i]} (${homeResults[i]})`);
    
    const awayLabels = awayDates.map((date, i) => 
        `vs ${awayOpponents[i]} (${awayResults[i]})`);
    
    // Create Home Team Chart
    const homeCtx = document.getElementById('homeTeamChart').getContext('2d');
    new Chart(homeCtx, {
        type: 'bar',
        data: {
            labels: homeLabels,
            datasets: [
                {
                    type: 'bar',
                    label: 'Goals',
                    data: homeGoals,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                },
                {
                    type: 'line',
                    label: 'xG',
                    data: homeXg,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(252, 134, 159, 0.2)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: `${homeTeam} - Goals vs xG in recent matches`
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function(tooltipItems) {
                            return homeLabels[tooltipItems[0].dataIndex];
                        },
                        label: function(context) {
                            if (context.datasetIndex === 0) {
                                return `Goals: ${context.raw}`;
                            } else {
                                return `xG: ${context.raw.toFixed(2)}`;
                            }
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Goals / xG'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Opponent'
                    }
                }
            }
        }
    });
    
    // away team chart
    const awayCtx = document.getElementById('awayTeamChart').getContext('2d');
    new Chart(awayCtx, {
        type: 'bar',
        data: {
            labels: awayLabels,
            datasets: [
                {
                    type: 'bar',
                    label: 'Goals',
                    data: awayGoals,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                },
                {
                    type: 'line',
                    label: 'xG',
                    data: awayXg,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    backgroundColor: 'rgba(252, 134, 159, 0.2)',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: `${awayTeam} - Goals vs xG in recent matches`
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function(tooltipItems) {
                            return awayLabels[tooltipItems[0].dataIndex];
                        },
                        label: function(context) {
                            if (context.datasetIndex === 0) {
                                return `Goals: ${context.raw}`;
                            } else {
                                return `xG: ${context.raw.toFixed(2)}`;
                            }
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Goals / xG'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Opponent'
                    }
                }
            }
        }
    });

});

/* odds multiplier is over 1.00x even when user bets AI prediction 
cos its based on the expected score which can be a decimal... AI prediction rounds that*/