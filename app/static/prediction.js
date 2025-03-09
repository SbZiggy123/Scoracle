document.addEventListener('DOMContentLoaded', function() {
    const homeScoreInput = document.getElementById('home-score');
    const awayScoreInput = document.getElementById('away-score');
    const oddsMultiplierSpan = document.getElementById('odds-multiplier');
    const exactPointsSpan = document.getElementById('exact-points');
    const resultPointsSpan = document.getElementById('result-points');
    const betAmountInput = document.getElementById('bet_amount');
    
    // Get data from the template 
    const matchData = document.getElementById('match-data');
    const homeExpected = parseFloat(matchData.dataset.homeExpected);
    const awayExpected = parseFloat(matchData.dataset.awayExpected);
    const basePoints = parseInt(matchData.dataset.basePoints || "100");
    
    const homeWinProb = parseFloat(matchData.dataset.homeWinProb || "50") / 100;
    const drawProb = parseFloat(matchData.dataset.drawProb || "25") / 100;
    const awayWinProb = parseFloat(matchData.dataset.awayWinProb || "25") / 100;

    // Calculate points based on user prediction vs expected scores
    function updatePrediction() {
        const homeScore = parseInt(homeScoreInput.value) || 0;
        const awayScore = parseInt(awayScoreInput.value) || 0;
        const betAmount = parseInt(betAmountInput.value) || 50;

        // For exact score multiplier
        const homeDiff = Math.abs(homeScore - homeExpected);
        const awayDiff = Math.abs(awayScore - awayExpected);
        let totalDiff = homeDiff + awayDiff;
        
        // Apply dampening for extreme stupid predictions
        if (totalDiff > 4) {
            totalDiff = 4 + (totalDiff - 4) * 0.5;
        }
        
        // Calculate exact score multiplier (capped at 8x)
        const exactScoreMultiplier = Math.min(1.0 + (totalDiff * 0.5), 8.0).toFixed(2);
        const exactScorePoints = Math.round(betAmount * exactScoreMultiplier);
        
        // Calculate correct result multiplier based on predicted outcome
        let predictedResult = "draw";
        let resultText = "Draw";
        let resultProbability = drawProb;
        
        if (homeScore > awayScore) {
            predictedResult = "home_win";
            resultText = "Home Win";
            resultProbability = homeWinProb;
        } else if (homeScore < awayScore) {
            predictedResult = "away_win";
            resultText = "Away Win";
            resultProbability = awayWinProb;
        }
        
        // Calculate multiplier - higher for unlikely outcomes
        const resultMultiplier = Math.min(1.0 + (1.5 * (1 - resultProbability)), 5.0).toFixed(2);
        const resultPoints = Math.round(betAmount * resultMultiplier);
        
        // Update display
        oddsMultiplierSpan.textContent = exactScoreMultiplier;
        exactPointsSpan.textContent = exactScorePoints;
        resultPointsSpan.innerHTML = `${resultPoints} <span class="multiplier">(${resultMultiplier}x)</span>`;
        
        // Update result indicator
        let resultIndicator = document.getElementById('result-indicator');
        if (!resultIndicator) {
            resultIndicator = document.createElement('div');
            resultIndicator.id = 'result-indicator';
            resultIndicator.className = 'result-indicator';
            document.querySelector('.prediction-odds').appendChild(resultIndicator);
        }
        
        // Set result indicator text and style
        resultIndicator.textContent = `Predicting: ${resultText}`;
        resultIndicator.dataset.result = predictedResult;
        
        // Apply styling based on probability
        if (resultProbability < 0.25) {
            resultIndicator.className = 'result-indicator unlikely';
        } else if (resultProbability < 0.45) {
            resultIndicator.className = 'result-indicator moderate';
        } else {
            resultIndicator.className = 'result-indicator likely';
        }
    }

    // Add styles for result indicator
    const style = document.createElement('style');
    style.textContent = `
    .result-indicator {
        margin-top: 10px;
        padding: 5px 10px;
        border-radius: 4px;
        display: inline-block;
        font-weight: bold;
    }
    .result-indicator.likely {
        background-color: #e0f7fa;
        color: #0288d1;
    }
    .result-indicator.moderate {
        background-color: #fff9c4;
        color: #ffa000;
    }
    .result-indicator.unlikely {
        background-color: #ffebee;
        color: #d32f2f;
    }
    .multiplier {
        font-size: 0.9em;
        color: #666;
    }
    `;
    document.head.appendChild(style);

    // Add event listeners
    homeScoreInput.addEventListener('input', updatePrediction);
    awayScoreInput.addEventListener('input', updatePrediction);
    
    if (betAmountInput) {
        betAmountInput.addEventListener('input', function() {
            // Make sure bet amount is within bounds
            let amount = parseInt(this.value) || 0;
            amount = Math.max(10, Math.min(500, amount));
            this.value = amount;
            
            updatePrediction();
        });
    }

    // Initialise all in 1
    updatePrediction();

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