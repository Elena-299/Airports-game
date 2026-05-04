import random

def dice_roll():
    dice = random.randint(1, 12)
    if dice == 1:
        return "EFHK"
    elif dice == 2:
        return "LEBL"
    elif dice == 3:
        return "LFMN"
    elif dice == 4:
        return "EDDM"
    elif dice == 5:
        return "LGTS"
    elif dice == 6:
        return "LOWW"
    elif dice == 7:
        return "EGLL"
    elif dice == 8:
        return "LIRF"
    elif dice == 9:
        return "ESSA"
    elif dice == 10:
        return "UKBB"
    elif dice == 11:
        return "EPKK"
    else:
        return "LYBE"

MAX_FUEL = 120
START_GOLD = 0
START_FUEL = MAX_FUEL
FUEL_QUARTER = MAX_FUEL // 4  # 30
MAX_PURCHASES_PER_COUNTRY = 4

SAME_COUNTRY_FUEL_COST = {
    "NA": 15,
    "AS": 15,
    "EU": 10
}

FUEL_COST_MATRIX = {
    ("NA", "NA"): 60,
    ("NA", "AS"): 120,
    ("NA", "EU"): 90,

    ("AS", "NA"): 120,
    ("AS", "AS"): 60,
    ("AS", "EU"): 90,

    ("EU", "NA"): 90,
    ("EU", "AS"): 90,
    ("EU", "EU"): 30
}

LEVEL2_SCORE = 80
LEVEL3_SCORE = 160
WIN_SCORE = 220


def create_new_game(cursor, conn, screen_name):
    start_icao = dice_roll()

    cursor.execute("DELETE FROM game")
    conn.commit()

    cursor.execute("""
        INSERT INTO game (screen_name, location_icao, start_icao, gold, fuel, base_points, status, unlocked_continents)
        VALUES (%s, %s, %s, %s, %s, 0, 'active', 'EU')
    """, (screen_name, start_icao, start_icao, START_GOLD, START_FUEL))

    conn.commit()

    return {
        "success": True,
        "message": "New game created",
        "screen_name": screen_name,
        "start_icao": start_icao,
        "fuel": START_FUEL,
        "gold": START_GOLD,
        "base_points": 0,
        "status": "active",
        "unlocked_continents": "EU"
    }

def get_game_state(cursor, screen_name):
    cursor.execute("""
        SELECT g.screen_name, g.location_icao, g.gold, g.fuel,
               g.base_points, g.status, g.unlocked_continents,
               a.name, c.name
        FROM game g
        JOIN airport a ON a.icao_code = g.location_icao
        JOIN country c ON c.country_code = a.country_code
        WHERE g.screen_name = %s
    """, (screen_name,))
    row = cursor.fetchone()
    if not row:
        return {
            "success": False,
            "error": "Game not found"
        }
    return {
        "success": True,
        "screen_name": row[0],
        "location_icao": row[1],
        "gold": row[2],
        "fuel": row[3],
        "base_points": row[4],
        "status": row[5],
        "unlocked_continents": row[6],
        "location_airport_name": row[7],
        "location_country_name": row[8]
    }

def parse_unlocked(value: str):
    if not value:
        return {"EU"}
    return {x.strip() for x in value.split(",") if x.strip()}

def format_unlocked(s: set[str]):
    return ",".join(sorted(s))

def get_player_progress(cur, screen_name: str):
    cur.execute("""
        SELECT location_icao, fuel, gold, base_points, unlocked_continents
        FROM game
        WHERE screen_name = %s
    """, (screen_name,))
    row = cur.fetchone()
    if not row:
        return None
    location_icao, fuel, gold, base_points, unlocked_str = row
    return {
        "location_icao": location_icao,
        "fuel": fuel,
        "gold": gold,
        "base_points": base_points,
        "unlocked": parse_unlocked(unlocked_str)
    }

def check_level_unlocks(cur, conn, screen_name):
    cur.execute("""
        SELECT base_points, unlocked_continents
        FROM game
        WHERE screen_name = %s
    """, (screen_name,))
    row = cur.fetchone()

    if not row:
        return {
            "success": False,
            "error": "Game not found"
        }

    score, unlocked_str = row
    unlocked = parse_unlocked(unlocked_str)

    changed = False
    unlocked_messages = []

    if score >= LEVEL2_SCORE and "NA" not in unlocked:
        unlocked.add("NA")
        changed = True
        unlocked_messages.append("Level 2 unlocked: North America")

    if score >= LEVEL3_SCORE and "AS" not in unlocked:
        unlocked.add("AS")
        changed = True
        unlocked_messages.append("Level 3 unlocked: Asia")

    if changed:
        cur.execute("""
            UPDATE game
            SET unlocked_continents = %s
            WHERE screen_name = %s
        """, (format_unlocked(unlocked), screen_name))
        conn.commit()

    return {
        "success": True,
        "changed": changed,
        "messages": unlocked_messages,
        "unlocked_continents": format_unlocked(unlocked)
    }


def check_win(cur, screen_name):
    cur.execute("""
        SELECT location_icao, start_icao, base_points, gold, fuel, unlocked_continents
        FROM game
        WHERE screen_name = %s
    """, (screen_name,))
    row = cur.fetchone()

    if not row:
        return False

    location_icao, start_icao, score, gold, fuel, unlocked_str = row
    unlocked = parse_unlocked(unlocked_str)

    all_levels = {"EU", "NA", "AS"}.issubset(unlocked)

    if all_levels and score >= WIN_SCORE and location_icao == start_icao:
        return True

    return False

def reset_game(cur, conn, screen_name: str):
    cur.execute("""
        SELECT start_icao
        FROM game
        WHERE screen_name = %s
    """, (screen_name,))

    row = cur.fetchone()

    if not row:
        return {
            "success": False,
            "error": "Game not found."
        }

    start_icao = row[0] if row[0] else dice_roll()

    cur.execute("""
        UPDATE game
        SET location_icao = %s,
            gold = %s,
            fuel = %s,
            base_points = 0,
            status = 'active',
            fuel_purchases_in_country = 0,
            unlocked_continents = 'EU',
            started_at = CURRENT_TIMESTAMP
        WHERE screen_name = %s
    """, (start_icao, START_GOLD, MAX_FUEL, screen_name))

    conn.commit()

    state = get_game_state(cur, screen_name)

    return {
        "success": True,
        "message": "Game restarted.",
        "state": state
    }

def list_airports_for_player(cursor, screen_name):
    progress = get_player_progress(cursor, screen_name)

    if not progress:
        return {
            "success": False,
            "error": "Player not found"
        }

    unlocked = sorted(progress["unlocked"])

    placeholders = ",".join(["%s"] * len(unlocked))

    cursor.execute(f"""
        SELECT a.icao_code, a.name,
               c.country_code, c.name, c.continent,
               c.fuel_price, c.gold_reward, c.base_points
        FROM airport a
        JOIN country c ON c.country_code = a.country_code
        WHERE c.continent IN ({placeholders})
        ORDER BY c.continent, c.name, a.name
    """, tuple(unlocked))

    rows = cursor.fetchall()

    airports = []

    for row in rows:
        airports.append({
            "icao_code": row[0],
            "airport_name": row[1],
            "country_code": row[2],
            "country_name": row[3],
            "continent": row[4],
            "fuel_price": row[5],
            "gold_reward": row[6],
            "base_points": row[7]
        })

    return {
        "success": True,
        "current_location": progress["location_icao"],
        "airports": airports
    }

def calculate_fuel_cost(from_country, from_continent, to_country, to_continent):
    if from_country == to_country:
        return SAME_COUNTRY_FUEL_COST[from_continent]
    return FUEL_COST_MATRIX[(from_continent, to_continent)]

def buy_fuel(cur, conn, screen_name: str):
    cur.execute("""
        SELECT g.gold, g.fuel, g.fuel_purchases_in_country, g.status,
               c.fuel_price, c.name
        FROM game g
        JOIN airport a ON a.icao_code = g.location_icao
        JOIN country c ON c.country_code = a.country_code
        WHERE g.screen_name = %s
    """, (screen_name,))
    row = cur.fetchone()

    if not row:
        return {
            "success": False,
            "error": "No game found for this player."
        }

    gold, fuel, purchases, status, fuel_price, country_name = row

    if status != "active":
        return {
            "success": False,
            "error": "You can't buy fuel. This game is over."
        }

    if purchases >= MAX_PURCHASES_PER_COUNTRY:
        return {
            "success": False,
            "error": f"You already bought fuel {purchases} times in {country_name}. Max is {MAX_PURCHASES_PER_COUNTRY}."
        }

    if fuel >= MAX_FUEL:
        return {
            "success": False,
            "error": "Your tank is already full."
        }

    amount_to_buy = min(FUEL_QUARTER, MAX_FUEL - fuel)
    cost = fuel_price

    if gold < cost:
        return {
            "success": False,
            "error": f"Not enough gold. You need {cost}, but you have {gold}."
        }

    cur.execute("""
        UPDATE game
        SET gold = gold - %s,
            fuel = fuel + %s,
            fuel_purchases_in_country = fuel_purchases_in_country + 1
        WHERE screen_name = %s
    """, (cost, amount_to_buy, screen_name))
    conn.commit()

    state = get_game_state(cur, screen_name)

    return {
        "success": True,
        "message": f"Bought {amount_to_buy} fuel in {country_name} for {cost} gold.",
        "purchases_in_country": purchases + 1,
        "max_purchases_per_country": MAX_PURCHASES_PER_COUNTRY,
        "state": state
    }

def travel(cur, conn, screen_name: str, to_icao: str):
    cur.execute("""
        SELECT g.location_icao, g.fuel, g.status
        FROM game g
        WHERE g.screen_name = %s
    """, (screen_name,))
    row = cur.fetchone()

    if row is None:
        return {
            "success": False,
            "error": "No game found for this player."
        }

    from_icao, fuel, status = row

    if status != "active":
        return {
            "success": False,
            "error": "This game is over. You can't travel."
        }

    if from_icao == to_icao:
        return {
            "success": False,
            "error": "You're already at that airport."
        }

    cur.execute("""
        SELECT c.country_code, c.continent
        FROM airport a
        JOIN country c ON c.country_code = a.country_code
        WHERE a.icao_code = %s
    """, (from_icao,))
    row = cur.fetchone()

    if row is None:
        return {
            "success": False,
            "error": "Current location airport not found in DB."
        }

    from_country, from_continent = row

    cur.execute("""
        SELECT a.icao_code, a.name,
               c.country_code, c.name, c.continent,
               c.base_points, c.gold_reward
        FROM airport a
        JOIN country c ON c.country_code = a.country_code
        WHERE a.icao_code = %s
    """, (to_icao,))
    dest = cur.fetchone()

    if dest is None:
        return {
            "success": False,
            "error": "Invalid destination ICAO."
        }

    _, dest_airport_name, to_country, to_country_name, to_continent, base_points, gold_reward = dest

    progress = get_player_progress(cur, screen_name)
    if progress and to_continent not in progress["unlocked"]:
        return {
            "success": False,
            "error": f"Continent not unlocked yet: {to_continent}"
        }

    fuel_cost = calculate_fuel_cost(from_country, from_continent, to_country, to_continent)
    if fuel < fuel_cost:
        return {
            "success": False,
            "error": f"Not enough fuel to travel. Need {fuel_cost}, you have {fuel}."
        }

    gold_gain = gold_reward if to_country != from_country else 0
    reset_purchase_counter = (to_country != from_country)

    if reset_purchase_counter:
        cur.execute("""
            UPDATE game
            SET location_icao = %s,
                fuel = fuel - %s,
                gold = gold + %s,
                base_points = base_points + %s,
                fuel_purchases_in_country = 0
            WHERE screen_name = %s
        """, (to_icao, fuel_cost, gold_gain, base_points, screen_name))
    else:
        cur.execute("""
            UPDATE game
            SET location_icao = %s,
                fuel = fuel - %s,
                gold = gold + %s,
                base_points = base_points + %s
            WHERE screen_name = %s
        """, (to_icao, fuel_cost, gold_gain, base_points, screen_name))

    conn.commit()

    check_level_unlocks(cur, conn, screen_name)

    cur.execute("""
        SELECT g.fuel, g.gold, c.fuel_price
        FROM game g
        JOIN airport a ON a.icao_code = g.location_icao
        JOIN country c ON c.country_code = a.country_code
        WHERE g.screen_name = %s
    """, (screen_name,))
    row = cur.fetchone()

    game_over = False
    win = False
    extra_message = ""

    if row:
        fuel_left, gold_left, current_fuel_price = row

        if fuel_left <= 0 and gold_left < current_fuel_price:
            cur.execute("UPDATE game SET status = 'dead' WHERE screen_name = %s", (screen_name,))
            conn.commit()
            game_over = True
            extra_message = "GAME OVER. You ran out of fuel and don't have enough gold to buy more."
        elif fuel_left <= 0:
            extra_message = "You ran out of fuel, but you still have enough gold to buy more."

        if check_win(cur, screen_name):
            win = True

        state = get_game_state(cur, screen_name)
    else:
        state = None

    return {
        "success": True,
        "message": f"Traveled to {to_icao} - {dest_airport_name} ({to_country_name}, {to_continent})",
        "fuel_cost": fuel_cost,
        "points_gain": base_points,
        "gold_gain": gold_gain,
        "game_over": game_over,
        "win": win,
        "extra_message": extra_message,
        "state": state
    }