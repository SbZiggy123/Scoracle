// Player prediction functionality gonna try do without page reload if fail do with
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
    
    // Calculate multiplier and potential points for a player prediction
    function calculatePlayerMultiplier(playerId, goals, shots, minutes) {
        const player = playerDataMap[playerId];
        
        if (!player) return { multiplier: 1.0, points: 100 };
        
        // Get expected stats
        const expectedStats = player.expected_stats;
        
        // Calculate deviation from expectations
        const goalsDiff = Math.abs(goals - expectedStats.exp_goals);
        const shotsDiff = Math.abs(shots - expectedStats.exp_shots);
        const minutesDiff = Math.abs(minutes - expectedStats.exp_minutes);
        
        // Normalize differences based on typical ranges
        const normalizedGoalsDiff = Math.min(goalsDiff / 1.0, 3.0);
        const normalizedShotsDiff = Math.min(shotsDiff / 2.0, 2.0);
        const normalizedMinutesDiff = Math.min(minutesDiff / 30.0, 1.5);
        
        // Calculate base multiplier
        let baseMultiplier = 1.0;
        
        // Maybe change
        const goalsWeight = 0.5;
        const shotsWeight = 0.3;
        const minutesWeight = 0.2;
        
        // Calculate weighted average multiplier
        let multiplier = baseMultiplier + (
            normalizedGoalsDiff * goalsWeight +
            normalizedShotsDiff * shotsWeight +
            normalizedMinutesDiff * minutesWeight
        );
        
        // Ensure multiplier has reasonable bounds
        multiplier = Math.max(1.0, Math.min(multiplier, 8.0));
        
        // Round to 2 decimal places
        multiplier = Math.round(multiplier * 100) / 100;
        
        // Calculate potential points
        const points = Math.round(100 * multiplier);
        
        return { multiplier, points };
    }
    
    // Update multiplier display when inputs change
    function attachInputListeners() {
        const goalInputs = document.querySelectorAll('.player-goals-input');
        const shotInputs = document.querySelectorAll('.player-shots-input');
        const minuteInputs = document.querySelectorAll('.player-minutes-input');
        
        const allInputs = [...goalInputs, ...shotInputs, ...minuteInputs];
        
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
    }
    
    // Update multiplier display for a specific player
    function updatePlayerMultiplier(playerId) {
        const goalsInput = document.querySelector(`.player-goals-input[data-player-id="${playerId}"]`);
        const shotsInput = document.querySelector(`.player-shots-input[data-player-id="${playerId}"]`);
        const minutesInput = document.querySelector(`.player-minutes-input[data-player-id="${playerId}"]`);
        const multiplierDisplay = document.querySelector(`.prediction-multiplier[data-player-id="${playerId}"]`);
        
        if (!goalsInput || !shotsInput || !minutesInput || !multiplierDisplay) return;
        
        const goals = parseInt(goalsInput.value) || 0;
        const shots = parseInt(shotsInput.value) || 0;
        const minutes = parseInt(minutesInput.value) || 0;
        
        const { multiplier, points } = calculatePlayerMultiplier(playerId, goals, shots, minutes);
        
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
        const minutesInput = document.querySelector(`.player-minutes-input[data-player-id="${playerId}"]`);
        
        if (!goalsInput || !shotsInput || !minutesInput) return;
        
        const goals = parseInt(goalsInput.value) || 0;
        const shots = parseInt(shotsInput.value) || 0;
        const minutes = parseInt(minutesInput.value) || 0;
        
        
        // Create prediction array with just this player
        const predictions = [{
            player_id: playerId,
            goals: goals,
            shots: shots,
            minutes: minutes
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
        
        // Collect all player predictions that have at least one field filled
        document.querySelectorAll('[data-player-id]').forEach(elem => {
            if (elem.tagName !== 'TR') return; 
            
            const playerId = elem.dataset.playerId;
            const goalsInput = document.querySelector(`.player-goals-input[data-player-id="${playerId}"]`);
            const shotsInput = document.querySelector(`.player-shots-input[data-player-id="${playerId}"]`);
            const minutesInput = document.querySelector(`.player-minutes-input[data-player-id="${playerId}"]`);
            
            if (!goalsInput || !shotsInput || !minutesInput) return;
            
            // Only include if at least one field has a value
            if (goalsInput.value || shotsInput.value || minutesInput.value) {
                predictions.push({
                    player_id: playerId,
                    goals: parseInt(goalsInput.value) || 0,
                    shots: parseInt(shotsInput.value) || 0,
                    minutes: parseInt(minutesInput.value) || 0
                });
            }
        });
        // not possible yet... Needs fixing for correct working
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