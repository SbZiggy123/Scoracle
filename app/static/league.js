console.log("league.js loaded");

function pollMatchResult() {
  fetch(`/league_update?league_id=${leagueId}&match_id=${matchId}`)
    .then(response => response.json())
    .then(data => {
      if (data.success && data.leaderboard) {
        const leaderboardTable = document.getElementById("leaderboard");
        if (leaderboardTable) {
          leaderboardTable.innerHTML = "";
          data.leaderboard.forEach((player, index) => {
            const row = document.createElement("tr");
            row.innerHTML = `<td>${index + 1}</td>
                             <td>${player.username}</td>
                             <td>${player.score}</td>`;
            leaderboardTable.appendChild(row);
          });
        }
      }
    })
    .catch(error => console.error("Error polling match result:", error));
}

const pollingInterval = setInterval(pollMatchResult, 30000);

window.addEventListener("beforeunload", function() {
  clearInterval(pollingInterval);
});

function placeBet(leagueId, matchId, prediction, button) {
  console.log("placeBet called with:", leagueId, matchId, prediction);
  let betAmount = prompt("Enter bet amount:");
  if (!betAmount || isNaN(betAmount) || betAmount <= 0) {
    alert("Invalid bet amount");
    return;
  }
  
  fetch('/place_bet', {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      league_id: leagueId,
      match_id: matchId,
      bet_amount: parseInt(betAmount),
      prediction: prediction
    })
  })
  .then(response => response.json())
  .then(data => {
    alert(data.message);
    if (data.success) {
      button.disabled = true;
      window.location.reload();
      pollMatchResult();
    }
  })
  .catch(error => console.error("Error placing bet:", error));
}
// timer countdown
if (typeof timeLeft !== 'undefined' && timeLeft > 0) {
  const countdownEl = document.getElementById('countdown');

  function updateCountdown() {
    if (timeLeft <= 0) {
      countdownEl.textContent = 'Round ended!';
      return;
    }
    const days = Math.floor(timeLeft / 86400);
    const hours = Math.floor((timeLeft % 86400) / 3600);
    const minutes = Math.floor((timeLeft % 3600) / 60);
    const seconds = timeLeft % 60;

    countdownEl.textContent = `${days}d ${hours}h ${minutes}m ${seconds}s`;
    timeLeft--;
    setTimeout(updateCountdown, 1000);
  }

  updateCountdown();
}