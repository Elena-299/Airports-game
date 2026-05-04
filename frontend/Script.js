'use strict'

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

        if (data.success !== false) {
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


const AIRPORT_COORDS = {
  // Canada
  CYYZ: [43.6772, -79.6306], //Lester B. Pearson Int ap
  CYVR: [49.1947, -123.1792], //Vancouver Int ap
  CYWG: [49.9100, -97.2398], //Winnipeg Int ap
  // USA
  KDCA: [38.8521, -77.0377], //Ronald Reagan Washington National ap
  KJFK: [40.6413, -73.7781], //John F Kennedy ap
  KMCI: [39.2976, -94.7139], //Kansas city int ap
  KLAX: [33.9425, -118.4081], //Los Angeles int ap
  KMIA: [25.7959, -80.2870], //Miami int ap
  KSEA: [47.4502, -122.3088], //Seattle Tacoma int ap
  // Mexico
  MMMX: [19.4363, -99.0721], //Licenciado Benito Juarez int ap
  MMUN: [21.0365, -86.8771], //Cancun int ap
  MMTJ: [32.5411, -116.9701], //General Abelardo L. Rodriguez int ap
  // Cuba
  MUHA: [22.9892, -82.4091], //Jose Marti int ap
  // Jamaica
  MKJP: [17.9357, -76.7875], //Norman Manley int ap
  // Costa Rica
  MRLB: [10.5933, -85.5444], //Guanacaste ap
  // Bahamas
  MYNN: [25.0390, -77.4662], //Lynden Pindling int ap
  // Dominican Republic
  MDSD: [18.4297, -69.6689], //Las America int ap
  // El Salvador
  MSLP: [13.4409, -89.0557], //Monsenor Oscar Arnulfo Romero int ap

  // Finland
  EFHK: [60.3172, 24.9633], //Helsinki Vantaa ap
  // Spain
  LEBL: [41.2971, 2.0785], //Josep Tarradellas Barcelona-El Prat ap
  LEMD: [40.4936, -3.5668], //Adolfo Suarez Madrid-Barajas ap
  // France
  LFMN: [43.6584, 7.2159], //Nice-Cote d’Azur ap
  LFPO: [48.7233, 2.3794], //Paris-Orly ap
  // Germany
  EDDF: [50.0379, 8.5622], //Frankfurt am Main ap
  EDDB: [52.3667, 13.5033], //Berlin Brandenburg ap
  EDDM: [48.3537, 11.7750], //Munich ap
  // Greece
  LGAV: [37.9364, 23.9445], //Athens Eleftherios Venizelos int ap
  LGTS: [40.5197, 22.9709], //Thessaloniki Macedonia int ap
  // Austria
  LOWW: [48.1103, 16.5697], //Vienna int ap
  // UK
  EGLL: [51.4775, -0.4614], //London Heathrow ap
  EGPH: [55.9500, -3.3725], //Edinburgh ap
  // Italy
  LIRF: [41.8003, 12.2389], //Rome-Flumicino Leonardo da Vinci int ap
  LICJ: [38.1759, 13.0910], //Falcone-Borsellino ap
  LIMC: [45.6306, 8.7281], //Malpensa int ap
  // Sweden
  ESSA: [59.6519, 17.9186], //Stockholm arlanda ap
  ESGG: [57.6628, 12.2798], //Gothenburg-Landvetter ap
  // Ukraine
  UKBB: [50.3450, 30.8947], //Boryspil int ap
  UKLL: [49.8125, 23.9561], //Lviv int ap
  // Poland
  EPWA: [52.1657, 20.9671], //Warsaw chopin ap
  EPKK: [50.0777, 19.7848], //Krakow john paul II int ap
  EPGD: [54.3776, 18.4662], //Gdansk lech walesa ap
  // Serbia
  LYBE: [44.8184, 20.3091], //Belgrade Nikola Tesla international ap

  // Vietnam
  VVTS: [10.8188, 106.6520], //Tan San Nhat int ap
  VVNB: [21.2212, 105.8072], //Noi Bai int ap
  // Japan
  RJTT: [35.5494, 139.7798], //Tokyo Haneda int ap
  RJCC: [42.7752, 141.6922], //New Chitose ap
  RJFF: [33.5858, 130.4511], //Fukuoka ap
  // China
  ZBAA: [40.0799, 116.6031], //Beijing Capital int ap
  ZUCK: [29.7192, 106.6419], //Chongqing Jiangbei int ap
  ZLXY: [34.4471, 108.7516], //Xi’an Xianyang int ap
  ZWWW: [43.9071, 87.4742], //Urumqi Diwopu int ap
  // Russia
  ULLI: [59.8003, 30.2625], //Pulkovo ap
  UUEE: [55.9726, 37.4146], //Sheremetyevo Int ap
  UNKL: [56.1731, 92.4933], //Krasnoyarsk int ap
  UHWW: [43.3990, 132.1480], //Vladivostok int ap
  UNNT: [54.9663, 82.6507], //Novosibirsk Tolmachevo ap
  // India
  VIDP: [28.5562, 77.1000], //Indira Gandhi int ap
  VABB: [19.0896, 72.8656], //Chhatrapati Shivaji int ap
  VOMM: [12.9900, 80.1693], //Chennai int ap
  // Saudi Arabia
  OERK: [24.9576, 46.6988], //King Khalid int ap
  OEMA: [26.4282, 43.7235], //Prince Mohammad Bin Abdulaziz ap
  // Turkey
  LTAC: [40.1281, 32.9951], //Esenboga int ap
  LTAI: [36.8987, 30.8005], //Antalya int ap
  LTBJ: [38.2924, 27.1570], //Adnan Menderes int ap
  // Iran
  OIII: [35.6892, 51.3134], //Mehrabad int ap
  OISS: [29.5392, 52.5898], //Shiraz Shahid Dastghaib int ap
  // Kazakhstan
  UAAA: [43.3521, 77.0405], //Almaty int ap
  UACC: [51.0223, 71.4669], //Nursultan Nazarbayev int ap
  // Indonesia
  WIII: [6.1256, 106.6559], //Soekarno-Hatta int ap
  WADD: [-8.7482, 115.1672], //Ngurah Rai (Bali) int ap
};

let markers = [];
async function loadAirports() {
    const screenName = getScreenName();
    let map;

    try {
        const response = await fetch(`${BASE_URL}/airports/${screenName}`);
        const data = await response.json();

        if (!data.success) {
            showMessage(data.error || "Could not load airports.");
            return;
        }

        if (!map) {
            map = L.map("airportsMap").setView([20, 0], 2);
            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                attribution: "© OpenStreetMap contributors"
            }).addTo(map);
        }

        markers.forEach(m => m.remove());
        markers = [];

        data.airports.forEach(airport => {
            const coords = AIRPORT_COORDS[airport.icao_code];
            if (!coords) return;

            const marker = L.marker(coords).addTo(map);
            markers.push(marker)

            marker.bindPopup(`
                <strong>${airport.airport_name}</strong> — ${airport.icao_code}<br>
                ${airport.country_name} (${airport.continent})<br>
                Fuel: ${airport.fuel_price} &nbsp;|&nbsp;
                Gold: ${airport.gold_reward}<br>
                Points: ${airport.base_points}<br>
                <button onclick="travelToAirport('${airport.icao_code}')">Travel</button>
            `);
        });

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