import mysql.connector
import random

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password":"metropolia12",
    "database":"Glitch in Transit"
}


def dice_roll():
    dice = random.randint(1, 12)
    if dice == 1:
        airport = "EFHK"
    elif dice == 2:
        airport = "LEBL"
    elif dice == 3:
        airport = "LFMN"
    elif dice == 4:
        airport = "EDDM"
    elif dice == 5:
        airport = "LGTS"
    elif dice == 6:
        airport = "LOWW"
    elif dice == 7:
        airport = "EGLL"
    elif dice == 8:
        airport = "LIRF"
    elif dice == 9:
        airport = "ESSA"
    elif dice == 10:
        airport = "UKBB"
    elif dice == 11:
        airport = "EPKK"
    elif dice == 12:
        airport = "LYBE"
    return airport


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


def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def get_saved_screen_name(cur):
    cur.execute("SELECT screen_name FROM game WHERE status='active' LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else None

def get_game_status(cur, screen_name: str):
    cur.execute("SELECT status FROM game WHERE screen_name=%s", (screen_name,))
    row = cur.fetchone()
    return row[0] if row else None


def reset_game(cur, conn, screen_name: str):
    cur.execute("SELECT start_icao FROM game WHERE screen_name=%s", (screen_name,))
    row = cur.fetchone()
    start_icao = row[0] if row and row[0] else dice_roll()

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

#check if the player has enough points to unlock new level
def check_level_unlocks(cur, conn, screen_name: str):
    cur.execute("SELECT base_points, unlocked_continents FROM game WHERE screen_name=%s", (screen_name,))
    row = cur.fetchone()
    if not row:
        return

    score, unlocked_str = row
    unlocked = parse_unlocked(unlocked_str)

    changed = False
    if score >= LEVEL2_SCORE and "NA" not in unlocked:
        unlocked.add("NA")
        changed = True
        print("Level 2 unlocked: North America (NA)")

    if score >= LEVEL3_SCORE and "AS" not in unlocked:
        unlocked.add("AS")
        changed = True
        print("Level 3 unlocked: Asia (AS)")

    if changed:
        cur.execute("""
            UPDATE game SET unlocked_continents=%s WHERE screen_name=%s
        """, (format_unlocked(unlocked), screen_name))
        conn.commit()


def show_state(cur, screen_name: str):
    cur.execute("""
        SELECT g.gold, g.fuel, g.base_points, g.status, g.fuel_purchases_in_country,
               a.icao_code, a.name,
               c.country_code, c.name, c.continent,
               c.base_points, c.fuel_price, c.gold_reward
        FROM game g
        JOIN airport a ON a.icao_code = g.location_icao
        JOIN country c ON c.country_code = a.country_code
        WHERE g.screen_name = %s
    """, (screen_name,))
    row = cur.fetchone()
    if row is None:
        print("No game found for this player.")
        return

    (gold, fuel, base_points, status, purchases,
     icao, aname,
     ccode, cname, cont,
     base_pts, fuel_price, gold_reward) = row

    print("\n=== CURRENT STATE ===")
    print(f"Player: {screen_name} | Status: {status}")
    print(f"Location: {icao} - {aname} ({cname}, {cont})")
    print(f"Gold: {gold} | Fuel: {fuel}/{MAX_FUEL} | Base_points: {base_points}")
    print(f"Fuel purchases in this country: {purchases}/{MAX_PURCHASES_PER_COUNTRY}")
    print(f"Country rules: \nbase_points={base_pts}, gold_reward={gold_reward}, fuel_price={fuel_price} per fuel unit")


def list_airports_for_player(cur, screen_name: str):
    progress = get_player_progress(cur, screen_name)
    if not progress:
        return []

    unlocked = sorted(progress["unlocked"])
    placeholders = ",".join(["%s"] * len(unlocked))

    cur.execute(f"""
        SELECT a.icao_code, a.name,
               c.country_code, c.name, c.continent,
               c.fuel_price, c.gold_reward, c.base_points
        FROM airport a
        JOIN country c ON c.country_code = a.country_code
        WHERE c.continent IN ({placeholders})
        ORDER BY c.continent, c.name, a.name
    """, tuple(unlocked))

    return cur.fetchall()

#calculate how much fuel cost a trip
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
        print("No game found for this player.")
        return

    gold, fuel, purchases, status, fuel_price, country_name = row

    if status != "active":
        print("You can't buy fuel. This game is over.")
        return

    if purchases >= MAX_PURCHASES_PER_COUNTRY:
        print(f"You already bought fuel {purchases} times in {country_name}. Max is {MAX_PURCHASES_PER_COUNTRY}.")
        return

    if fuel >= MAX_FUEL:
        print("Your tank is already full.")
        return

    amount_to_buy = min(FUEL_QUARTER, MAX_FUEL - fuel)

    cost = fuel_price

    if gold < cost:
        print(f"Not enough gold. Need {cost}, you have {gold}.")
        return

    cur.execute("""
        UPDATE game
        SET gold = gold - %s,
            fuel = fuel + %s,
            fuel_purchases_in_country = fuel_purchases_in_country + 1
        WHERE screen_name = %s
    """, (cost, amount_to_buy, screen_name))
    conn.commit()

    print(f"Bought {amount_to_buy} fuel (1/4 tank) in {country_name} for {cost} gold.")
    print(f"Purchases in this country: {purchases + 1}/{MAX_PURCHASES_PER_COUNTRY}")


def get_current_country_and_continent(cur, screen_name: str):
    cur.execute("""
        SELECT c.country_code, c.continent
        FROM game g
        JOIN airport a ON a.icao_code = g.location_icao
        JOIN country c ON c.country_code = a.country_code
        WHERE g.screen_name=%s
    """, (screen_name,))
    row = cur.fetchone()
    if not row:
        return None, None
    return row


def check_win(cur, screen_name: str) -> bool:
    cur.execute("""
        SELECT location_icao, start_icao, base_points, gold, fuel, unlocked_continents
        FROM game
        WHERE screen_name=%s
    """, (screen_name,))
    row = cur.fetchone()
    if not row:
        return False

    location_icao, start_icao, score, gold, fuel, unlocked_str = row
    unlocked = parse_unlocked(unlocked_str)

    all_levels = {"EU", "NA", "AS"}.issubset(unlocked)

    if all_levels and score >= WIN_SCORE and location_icao == start_icao:
        print("\nYOU WIN!")
        print(f"Score: {score} | Gold: {gold} | Fuel: {fuel}")
        return True

    return False

#process to travel from an airport to another
def travel(cur, conn, screen_name: str, to_icao: str) -> bool:
    cur.execute("""
        SELECT g.location_icao, g.fuel, g.status
        FROM game g
        WHERE g.screen_name = %s
    """, (screen_name,))
    row = cur.fetchone()
    if row is None:
        print("No game found for this player.")
        return True

    from_icao, fuel, status = row

    if status != "active":
        print("This game is over. You can't travel.")
        return False

    if from_icao == to_icao:
        print("You're already at that airport.")
        return True

    cur.execute("""
        SELECT c.country_code, c.continent
        FROM airport a
        JOIN country c ON c.country_code = a.country_code
        WHERE a.icao_code = %s
    """, (from_icao,))
    row = cur.fetchone()
    if row is None:
        print("Current location airport not found in DB.")
        return True

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
        print("Invalid destination ICAO.")
        return True

    _, dest_airport_name, to_country, to_country_name, to_continent, base_points, gold_reward = dest

    progress = get_player_progress(cur, screen_name)
    if progress and to_continent not in progress["unlocked"]:
        print(f" Continent not unlocked yet: {to_continent}")
        return True

    fuel_cost = calculate_fuel_cost(from_country, from_continent, to_country, to_continent)
    if fuel < fuel_cost:
        print(f" Not enough fuel to travel. Need {fuel_cost}, you have {fuel}.")
        return True

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

    print(f"\nTraveled to {to_icao} - {dest_airport_name} ({to_country_name}, {to_continent})")
    print(f"Fuel cost: {fuel_cost} | Points gained: {base_points} | Gold gained: {gold_gain}")

    cur.execute("""
                SELECT g.fuel, g.gold, c.fuel_price
                FROM game g
                         JOIN airport a ON a.icao_code = g.location_icao
                         JOIN country c ON c.country_code = a.country_code
                WHERE g.screen_name = %s
                """, (screen_name,))
    row = cur.fetchone()

    if row:
        fuel_left, gold_left, current_fuel_price = row

        if fuel_left <= 0 and gold_left < current_fuel_price:
            cur.execute("UPDATE game SET status = 'dead' WHERE screen_name = %s", (screen_name,))
            conn.commit()
            print("\nGAME OVER. You ran out of fuel and don't have enough gold to buy more.")
            return False
        elif fuel_left <= 0:
            print("\nYou ran out of fuel, but you still have enough gold to buy more.")

    if check_win(cur, screen_name):
        return False

    return True


def show_manual(start_icao: str):
    print("\n=== GAME MANUAL ===\n")
    print(f"The portal that will bring you back to your universe is located at {start_icao}.")
    print("The portal will only open after you have successfully unlocked all three levels and collected at least 220 points.\n")

    print("Travel across the world and return to the starting point once you are ready to win the game and go home!\n")

    print("LEVEL GUIDE\n")
    print("Level 1:")
    print("You can only travel in Europe\n")

    print("Level 2:")
    print("Unlock North America by collecting 80 points.")
    print("You can only travel in Europe and North America.\n")

    print("Level 3:")
    print("Unlock Asia by collecting 160 points.")
    print("You can now travel between Europe, North America and Asia.\n")

    print("SCORING SYSTEM")
    print("Every time you travel to a new airport, you earn points based on the continent you travel to.\n")

    print("For traveling within the continent:")
    print("Europe: 20 points")
    print("Asia: 30 points")
    print("North America: 40 points\n")

    print("GOLD")
    print("You are rewarded with gold only when you travel to a different country.\n")

    print("FUEL")
    print("Traveling will cost fuel and the game will end if you run out of fuel.")
    print("Fuel cost depends on whether you travel within a country, within a continent, or between continents.\n")

    print("Traveling within the same country:")
    print("Europe: 10 fuel")
    print("North America: 15 fuel")
    print("Asia: 15 fuel\n")

    print("Traveling between countries in the same continent costs more fuel.")
    print("For traveling between countries in:")
    print("Europe: 30 fuel")
    print("North America: 60 fuel")
    print("Asia: 60 fuel\n")

    print("Traveling between continents costs the most fuel.")
    print("Europe to North America: 90 fuel")
    print("Europe to Asia: 90 fuel")
    print("North America to Asia: 120 fuel\n")

    print("You can purchase more fuel using gold, but fuel prices vary depending on the country you are purchasing from.")
    print("You can purchase fuel a maximum of 4 times per country.\n")

def start_menu(cur, conn):
    print("\nWELCOME TO GLITCH IN TRANSIT ")
    print("================================")

    saved_name = get_saved_screen_name(cur)  # ideal: que solo mire status='active'
    has_saved = saved_name is not None

    print("\n=== START MENU ===")
    if has_saved:
        print("1) Continue")
        print("2) New Game")
        print("3) Exit")
    else:
        print("1) New Game")
        print("2) Exit")

    while True:
        choice = input("Choose an option: ").strip()

        if has_saved:
            if choice == "1":
                status = get_game_status(cur, saved_name)
                if status != "active":
                    print("\nGAME OVER: that save is dead and cannot be continued.")
                    cur.execute("DELETE FROM game")
                    conn.commit()
                    return ("exit", None)

                print(f"\n Continuing saved game for: {saved_name}")
                return ("continue", saved_name)
            elif choice == "2":
                screen_name = input("Enter a screen name for the new game: ").strip()
                if not screen_name:
                    print("Screen name cannot be empty.")
                    continue

                cur.execute("DELETE FROM game")
                conn.commit()

                start_icao = dice_roll()

                cur.execute("""
                    INSERT INTO game (screen_name, location_icao, start_icao, gold, fuel, base_points, status, unlocked_continents)
                    VALUES (%s, %s, %s, %s, %s, 0, 'active', 'EU')
                """, (screen_name, start_icao, start_icao, START_GOLD, START_FUEL))

                conn.commit()

                print(f"\nStarting airport: {start_icao}")
                print("New game started!")
                show_manual(start_icao)

                return ("new", screen_name)

            elif choice == "3":
                print("\n Goodbye!")
                return ("exit", None)

            else:
                print("Invalid option. Please choose again.")

        else:
            if choice == "1":
                screen_name = input("Enter a screen name for the new game: ").strip()
                if not screen_name:
                    print("Screen name cannot be empty.")
                    continue

                cur.execute("DELETE FROM game")
                conn.commit()

                start_icao = dice_roll()

                cur.execute("""
                    INSERT INTO game (screen_name, location_icao, start_icao, gold, fuel, base_points, status, unlocked_continents)
                    VALUES (%s, %s, %s, %s, %s, 0, 'active', 'EU')
                """, (screen_name, start_icao, start_icao, START_GOLD, START_FUEL))
                conn.commit()

                print(f"\n Starting airport: {start_icao}")
                print(" New game started!")
                show_manual(start_icao)

                return ("new", screen_name)

            elif choice == "2":
                print("\n Goodbye!")
                return ("exit", None)

            else:
                print("Invalid option. Please choose again.")


def main():
    conn = get_conn()
    cur = conn.cursor()

    try:
        action, screen_name = start_menu(cur, conn)
        if action == "exit" or not screen_name:
            return

        while True:
            show_state(cur, screen_name)

            status = get_game_status(cur, screen_name)
            if status != "active":
                print("\nThis game is not active anymore. Game over.")
                break

            if check_win(cur, screen_name):
                break

            print("\nActions:")
            print("1) Travel")
            print("2) Buy fuel")
            print("q) Quit")

            action = input("Choose: ").strip().lower()

            if action == "q":
                break

            elif action == "1":
                airports = list_airports_for_player(cur, screen_name)
                if not airports:
                    print("No airports available.")
                    continue

                from_country, from_continent = get_current_country_and_continent(cur, screen_name)
                if not from_country or not from_continent:
                    print("Could not read current country/continent.")
                    continue

                print("\n=== AIRPORTS ===")
                for idx, (
                    icao, name,
                    to_country_code, to_country_name, to_continent,
                    dest_fuel_price, dest_gold_reward, dest_base_points
                ) in enumerate(airports, start=1):

                    fuel_cost = calculate_fuel_cost(from_country, from_continent, to_country_code, to_continent)

                    gold_gain = dest_gold_reward if to_country_code != from_country else 0

                    print(
                        f"{idx}) {icao} - {name} ({to_country_name}, {to_continent}) | "
                        f"\n| Trip fuel: {fuel_cost} | +Gold: {gold_gain} | Fuel price there: {dest_fuel_price} | +Pts: {dest_base_points} |")

                choice = input("\nChoose airport number (or 'c' to cancel): ").strip().lower()
                if choice == "c":
                    continue
                if not choice.isdigit():
                    print("Invalid input.")
                    continue

                idx_choice = int(choice)
                if idx_choice < 1 or idx_choice > len(airports):
                    print("Out of range.")
                    continue

                to_icao = airports[idx_choice - 1][0]
                keep_playing = travel(cur, conn, screen_name, to_icao)

                if not keep_playing:
                    if check_win(cur, screen_name):
                        break

                    choice2 = input("\nPress 'r' to restart or 'q' to quit: ").strip().lower()
                    if choice2 == "r":
                        reset_game(cur, conn, screen_name)
                        print("\nGame restarted!")
                    else:
                        break

            elif action == "2":
                buy_fuel(cur, conn, screen_name)

                if check_win(cur, screen_name):
                    break

            else:
                print("Invalid action.")

    finally:
        cur.close()
        conn.close()
        print("\nGame closed.")

if __name__ == "__main__":
    main()