const BASE_URL = "http://127.0.0.1:5000";

function getScreenName() {
    return document.getElementById("screenName").value.trim();
}

function showMessage(message) {
    document.getElementById("messageBox").textContent = message;
}

function showGameScreen() {
    document.getElementById("welcomeScreen").classList.add("hidden");
    document.getElementById("gameScreen").classList.remove("hidden");
}

function goToWelcome() {
    document.getElementById("gameScreen").classList.add("hidden");
    document.getElementById("welcomeScreen").classList.remove("hidden");
}

function updateState(state) {
    if (!state) return;

    document.getElementById("playerName").textContent = state.screen_name || "-";
    document.getElementById("location").textContent = state.location_icao || "-";
    document.getElementById("fuel").textContent = state.fuel ?? "-";
    document.getElementById("gold").textContent = state.gold ?? "-";
    document.getElementById("points").textContent = state.base_points ?? "-";
    document.getElementById("status").textContent = state.status || "-";
    document.getElementById("unlocked").textContent = state.unlocked_continents || "-";
}

async function startNewGame() {
    const screenName = getScreenName();

    if (!screenName) {
        alert("Please enter a screen name.");
        return;
    }

    try {
        const response = await fetch(`${BASE_URL}/new-game`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ screen_name: screenName })
        });

        const data = await response.json();

        if (data.success) {
            showGameScreen();
            showMessage(data.message);
            await loadState();
            await loadAirports();
        } else {
            showMessage(data.error || "Could not start game.");
        }
    } catch (error) {
        showMessage("Error connecting to backend.");
        console.error(error);
    }
}

async function loadGameFromWelcome() {
    const screenName = getScreenName();

    if (!screenName) {
        alert("Please enter a screen name.");
        return;
    }

    showGameScreen();
    await loadState();
    await loadAirports();
}

async function loadState() {
    const screenName = getScreenName();

    try {
        const response = await fetch(`${BASE_URL}/state/${screenName}`);
        const data = await response.json();

        if (data.success) {
            updateState(data);
            showMessage("Game state loaded.");
        } else {
            showMessage(data.error || "Could not load state.");
        }
    } catch (error) {
        showMessage("Error loading state.");
        console.error(error);
    }
}

async function loadAirports() {
    const screenName = getScreenName();

    try {
        const response = await fetch(`${BASE_URL}/airports/${screenName}`);
        const data = await response.json();

        if (!data.success) {
            showMessage(data.error || "Could not load airports.");
            return;
        }

        const airportsList = document.getElementById("airportsList");
        airportsList.innerHTML = "";

        data.airports.forEach(airport => {
            const card = document.createElement("div");
            card.className = "airport-card";

            card.innerHTML = `
                <h3>${airport.icao_code}</h3>
                <p><strong>${airport.airport_name}</strong></p>
                <p>${airport.country_name} (${airport.continent})</p>
                <p>Fuel price: ${airport.fuel_price}</p>
                <p>Gold reward: ${airport.gold_reward}</p>
                <p>Points: ${airport.base_points}</p>
                <button class="travel-btn">Travel</button>
            `;

            card.querySelector(".travel-btn").onclick = () => travelToAirport(airport.icao_code);
            airportsList.appendChild(card);
        });

        showMessage("Airports loaded.");
    } catch (error) {
        showMessage("Error loading airports.");
        console.error(error);
    }
}

async function travelToAirport(toIcao) {
    const screenName = getScreenName();

    showFlightAnimation(`Departing to ${toIcao}...`);

    try {
        const response = await fetch(`${BASE_URL}/travel`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                screen_name: screenName,
                to_icao: toIcao
            })
        });

        const data = await response.json();

        if (data.success) {
            setTimeout(async () => {
                showFlightAnimation(`Arrived at ${toIcao}!`);

                showMessage(data.message + (data.extra_message ? " " + data.extra_message : ""));

                if (data.state && data.state.success) {
                    updateState(data.state);
                }

                await loadAirports();
            }, 1200);
        } else {
            showMessage(data.error || "Travel failed.");
        }
    } catch (error) {
        showMessage("Error during travel.");
        console.error(error);
    }
}

async function buyFuel() {
    const screenName = getScreenName();

    try {
        const response = await fetch(`${BASE_URL}/buy-fuel`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ screen_name: screenName })
        });

        const data = await response.json();

        if (data.success) {
            showMessage(data.message);
            if (data.state && data.state.success) {
                updateState(data.state);
            }
        } else {
            showMessage(data.error || "Could not buy fuel.");
        }
    } catch (error) {
        showMessage("Error buying fuel.");
        console.error(error);
    }
}

async function resetGame() {
    const screenName = getScreenName();

    try {
        const response = await fetch(`${BASE_URL}/reset-game`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ screen_name: screenName })
        });

        const data = await response.json();

        if (data.success) {
            showMessage(data.message);
            if (data.state && data.state.success) {
                updateState(data.state);
            }
            await loadAirports();
        } else {
            showMessage(data.error || "Could not reset game.");
        }
    } catch (error) {
        showMessage("Error resetting game.");
        console.error(error);
    }
}

function showFlightAnimation(text) {
    const animationBox = document.getElementById("flightAnimation");
    const flightText = document.getElementById("flightText");

    flightText.textContent = text;
    animationBox.classList.remove("hidden");

    setTimeout(() => {
        animationBox.classList.add("hidden");
    }, 2000);
}