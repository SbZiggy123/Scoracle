
document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    const tabButtons = document.querySelectorAll('.tab-button');
    const playerContainers = document.querySelectorAll('.players-table-container');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            // Remove active class from all buttons
            tabButtons.forEach(btn => btn.classList.remove('active'));

            this.classList.add('active');

            playerContainers.forEach(container => container.classList.add('hidden'));
            
            // Show the selected container
            const teamToShow = this.dataset.team;
            document.getElementById(`${teamToShow}-players-container`).classList.remove('hidden');
        });
    });
    
    // Player prediction inputs
    const playerDataMap = {};
    
    // Fetch player data for calculations
    function fetchPlayerData() {
        const matchId = window.location.pathname.split('/').pop();
        
        fetch(`/api/player-predictions/${matchId}`)
            .then(response => response.json())
            .then(data => {
                // Combine both team players
                const allPlayers = [...data.home_players, ...data.away_players];
                
                // Create map of player ID to player data
                allPlayers.forEach(player => {
                    playerDataMap[player.id] = player;
                });
            })
            .catch(error => console.error('Error fetching player data:', error));
    }
    
    // Call fetch function on page load
    fetchPlayerData();
    
    // Calculate multiplier and potential points for a player prediction (without minutes)

    function calculatePlayerMultiplier(playerId, goals, shots) {
        const player = playerDataMap[playerId];
        
        if (!player) return { multiplier: 1.0, points: 100 };
        
        // Get expected stats
        const expectedStats = player.expected_stats;
        const expGoals = expectedStats.exp_goals;
        const expShots = expectedStats.exp_shots;
        
        // Special case for zero predictions - make it rewarding only when unexpected
        let zeroBonus = 0;
        
        // If player typically scores but you predict 0, that's a bold bet
        if (goals === 0 && expGoals > 0.5) {
            zeroBonus += Math.min(expGoals * 0.5, 1.0);  // Bonus up to 1.0 for predicting 0 when expected is high
        }
        
        if (shots === 0 && expShots > 2) {
            zeroBonus += Math.min(expShots * 0.2, 0.5);  // Bonus up to 0.5 for predicting 0 shots when expected is high
        }
        
        // Calculate deviation from expectations
        const goalsDiff = Math.abs(goals - expGoals);
        const shotsDiff = Math.abs(shots - expShots);
        
        // Exponential scaling for bold predictions
        // Using power functions makes the multiplier grow much faster as predictions get bolder
        const goalsMultiplier = Math.pow(goalsDiff / 0.8, 1.5);  // More aggressive curve
        const shotsMultiplier = Math.pow(shotsDiff / 1.5, 1.3);  // Slightly less aggressive
        
        // Higher weight for goals, lower for shots
        const goalsWeight = 0.7;
        const shotsWeight = 0.3;
        
        // Base multiplier
        let baseMultiplier = 1.0;
        
        // Calculate weighted average multiplier with exponential factors
        let multiplier = baseMultiplier + (
            goalsMultiplier * goalsWeight +
            shotsMultiplier * shotsWeight +
            zeroBonus
        );
        
        // Extra bonus for predicting far from expected
        // Rewards very bold predictions more.
        if (goalsDiff > 2 || shotsDiff > 5) {
            multiplier *= 1.2;  // 20% bonus for very bold predictions
        }
        
        // Ensure multiplier has reasonable bounds
        multiplier = Math.max(1.0, min = Math.min(multiplier, 10.0)); 
        
        // Round to 2 decimal places
        multiplier = Math.round(multiplier * 100) / 100;
        
        // Get bet amount
        const betAmount = document.querySelector('#player_bet_amount').value || 50;
        
        // Calculate potential points based on bet amount
        const points = Math.round(betAmount * multiplier);
        
        return { multiplier, points, betAmount };
    }
    
    // Update multiplier display when inputs change
    function attachInputListeners() {
        const goalInputs = document.querySelectorAll('.player-goals-input');
        const shotInputs = document.querySelectorAll('.player-shots-input');
        
        const allInputs = [...goalInputs, ...shotInputs];
        
        allInputs.forEach(input => {
            input.addEventListener('change', function() {
                const playerId = this.dataset.playerId;
                updatePlayerMultiplier(playerId);
            });
            
            input.addEventListener('input', function() {
                const playerId = this.dataset.playerId;
                updatePlayerMultiplier(playerId);
            });
        });
        
        const betAmountInput = document.querySelector('#player_bet_amount');
        if (betAmountInput) {
            betAmountInput.addEventListener('input', function() {
                // Make sure bet amount is within bounds
                let amount = parseInt(this.value) || 0;
                amount = Math.max(10, Math.min(500, amount));
                this.value = amount;
                
                // Update all visible player multipliers
                document.querySelectorAll('[data-player-id]').forEach(elem => {
                    if (elem.tagName === 'TR') {
                        updatePlayerMultiplier(elem.dataset.playerId);
                    }
                });
            });
        }
    }
    
    // Update multiplier display for a specific player
    function updatePlayerMultiplier(playerId) {
        const goalsInput = document.querySelector(`.player-goals-input[data-player-id="${playerId}"]`);
        const shotsInput = document.querySelector(`.player-shots-input[data-player-id="${playerId}"]`);
        const multiplierDisplay = document.querySelector(`.prediction-multiplier[data-player-id="${playerId}"]`);
        
        if (!goalsInput || !shotsInput || !multiplierDisplay) return;
        
        const goals = parseInt(goalsInput.value) || 0;
        const shots = parseInt(shotsInput.value) || 0;
        
        const { multiplier, points } = calculatePlayerMultiplier(playerId, goals, shots);
        
        multiplierDisplay.textContent = `${multiplier.toFixed(2)}x (${points} pts)`;
    }
    
    attachInputListeners();
    
    const saveButtons = document.querySelectorAll('.save-player-prediction');
    
    saveButtons.forEach(button => {
        button.addEventListener('click', function() {
            const playerId = this.dataset.playerId;
            savePlayerPrediction(playerId);
        });
    });
    
    // Save a single player prediction
    function savePlayerPrediction(playerId) {
        const goalsInput = document.querySelector(`.player-goals-input[data-player-id="${playerId}"]`);
        const shotsInput = document.querySelector(`.player-shots-input[data-player-id="${playerId}"]`);
        const leagueSelect = document.querySelector('#player_league_select');
        const betAmountInput = document.querySelector('#player_bet_amount');
        
        if (!goalsInput || !shotsInput || !leagueSelect || !betAmountInput) return;
        
        const goals = parseInt(goalsInput.value) || 0;
        const shots = parseInt(shotsInput.value) || 0;
        const leagueId = leagueSelect.value;
        const betAmount = parseInt(betAmountInput.value) || 50;
        
        // Create prediction array with just this player
        const predictions = [{
            player_id: playerId,
            goals: goals,
            shots: shots,
            league_id: leagueId,
            bet_amount: betAmount
        }];
        
        // Send to end
        savePredictions(predictions, () => {
            const button = document.querySelector(`.save-player-prediction[data-player-id="${playerId}"]`);
            const originalText = button.textContent;
            
            button.textContent = "Saved!";
            button.style.backgroundColor = "#28a745";
            
            setTimeout(() => {
                button.textContent = originalText;
                button.style.backgroundColor = "";
            }, 2000);
        });
    }
    
    // Save all button
    const saveAllButton = document.getElementById('save-all-player-predictions');
     
    if (saveAllButton) {
        saveAllButton.addEventListener('click', function() {
            saveAllPlayerPredictions();
        });
    }
    
    // Save all player predictions. Bottom button
    function saveAllPlayerPredictions() {
        const predictions = [];
        const leagueSelect = document.querySelector('#player_league_select');
        const betAmountInput = document.querySelector('#player_bet_amount');
        
        if (!leagueSelect || !betAmountInput) return;
        
        const leagueId = leagueSelect.value;
        const betAmount = parseInt(betAmountInput.value) || 50;
        
        // Collect all player predictions that have at least one field filled
        document.querySelectorAll('[data-player-id]').forEach(elem => {
            if (elem.tagName !== 'TR') return; 
            
            const playerId = elem.dataset.playerId;
            const goalsInput = document.querySelector(`.player-goals-input[data-player-id="${playerId}"]`);
            const shotsInput = document.querySelector(`.player-shots-input[data-player-id="${playerId}"]`);
            
            if (!goalsInput || !shotsInput) return;
            
            // Only include if at least one field has a value
            if (goalsInput.value || shotsInput.value) {
                predictions.push({
                    player_id: playerId,
                    goals: parseInt(goalsInput.value) || 0,
                    shots: parseInt(shotsInput.value) || 0,
                    league_id: leagueId,
                    bet_amount: betAmount
                });
            }
        });
  
        if (predictions.length === 0) {
            alert("No player predictions to save!");
            return;
        }
        
        // Send to end
        savePredictions(predictions, () => {
           // Some feedback
            const button = document.getElementById('save-all-player-predictions');
            const originalText = button.textContent;
            
            button.textContent = "All Predictions Saved!";
            button.style.backgroundColor = "#28a745"; // Green
            
            setTimeout(() => {
                button.textContent = originalText;
                button.style.backgroundColor = "";
            }, 2000);
        });
    }
    
    // Call to save predictions uses py operations
    function savePredictions(predictions, successCallback) {
        const matchId = window.location.pathname.split('/').pop();
        
        fetch(`/api/player-predictions/${matchId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(predictions)
        })
        .then(response => response.json())
        .then(data => {
            if (data.results) {
                // Call success callback
                if (successCallback) successCallback();
                
                // Update multipliers with server values
                data.results.forEach(result => {
                    if (result.success) {
                        const multiplierDisplay = document.querySelector(`.prediction-multiplier[data-player-id="${result.player_id}"]`);
                        if (multiplierDisplay) {
                            multiplierDisplay.textContent = `${result.multiplier}x (${result.potential_points} pts)`;
                        }
                    }
                });
            } else if (data.error) {
                alert(`Error: ${data.error}`);
            }
        })
        .catch(error => {
            console.error('Error saving predictions:', error);
            alert('Failed to save predictions. Please try again.');
        });
    }
});