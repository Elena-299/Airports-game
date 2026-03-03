import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password":"metropolia12",
    "database":"Glitch in Transit"
}

# this is gonna be change when the dice code is ready
START_AIRPORT_ICAO = "EFHK"
START_GOLD = 0
START_FUEL = 100

def get_conn():
    return mysql.connector.connect(**DB_CONFIG)

def get_saved_screen_name(cur):
    cur.execute("SELECT screen_name FROM game LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else None

def delete_saved_game(cur, conn):
    cur.execute("DELETE FROM game")
    conn.commit()

def reset_game(cur, conn, screen_name: str):
    cur.execute("""
        UPDATE game
        SET location_icao = %s,
            gold = %s,
            fuel = %s,
            score = 0,
            status = 'active',
            started_at = CURRENT_TIMESTAMP
        WHERE screen_name = %s
    """, (START_AIRPORT_ICAO, START_GOLD, START_FUEL, screen_name))
    conn.commit()


def has_saved_game(cur, screen_name: str) -> bool:
    cur.execute("""
        SELECT location_icao, gold, fuel, score, status
        FROM game
        WHERE screen_name = %s
    """, (screen_name,))
    row = cur.fetchone()
    if row is None:
        return False

    location_icao, gold, fuel, score, status = row
    if (location_icao == START_AIRPORT_ICAO and gold == START_GOLD and fuel == START_FUEL and score == 0 and status == "active"):
        return False
    return True


def start_menu(cur, conn):
    print("\nWELCOME TO GLITCH IN TRANSIT 🚀")
    print("================================")

    saved_name = get_saved_screen_name(cur)
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
                print(f"\n✅ Continuing saved game for: {saved_name}")
                return ("continue", saved_name)

            elif choice == "2":
                screen_name = input("Enter a screen name for the new game: ").strip()
                if not screen_name:
                    print("Screen name cannot be empty.")
                    continue

                # If you want ONLY ONE save slot, overwrite old save:
                cur.execute("DELETE FROM game")
                conn.commit()

                # Create the new row
                cur.execute("""
                    INSERT INTO game (screen_name, location_icao, gold, fuel, score, status)
                    VALUES (%s, %s, %s, %s, 0, 'active')
                """, (screen_name, START_AIRPORT_ICAO, START_GOLD, START_FUEL))
                conn.commit()

                print("\n🔄 New game started!")
                return ("new", screen_name)

            elif choice == "3":
                print("\n👋 Goodbye!")
                return ("exit", None)

            else:
                print("Invalid option. Please choose again.")

        else:
            if choice == "1":
                screen_name = input("Enter a screen name for the new game: ").strip()
                if not screen_name:
                    print("Screen name cannot be empty.")
                    continue

                cur.execute("""
                    INSERT INTO game (screen_name, location_icao, gold, fuel, score, status)
                    VALUES (%s, %s, %s, %s, 0, 'active')
                """, (screen_name, START_AIRPORT_ICAO, START_GOLD, START_FUEL))
                conn.commit()

                print("\n🔄 New game started!")
                return ("new", screen_name)

            elif choice == "2":
                print("\n👋 Goodbye!")
                return ("exit", None)

            else:
                print("Invalid option. Please choose again.")


def show_state(cur, screen_name: str):
    cur.execute("""
        SELECT g.gold, g.fuel, g.score, g.status,
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

    gold, fuel, score, status, icao, aname, ccode, cname, cont, base_pts, fuel_price, gold_reward = row

    print("\n=== CURRENT STATE ===")
    print(f"Player: {screen_name} | Status: {status}")
    print(f"Location: {icao} - {aname} ({cname}, {cont})")
    print(f"Gold: {gold} | Fuel: {fuel} | Score: {score}")
    print(f"Country rules: base_points={base_pts}, gold_reward={gold_reward}, fuel_price={fuel_price} per fuel unit")


def list_airports(cur):
    # here im listing all airports since we don't have routes or distance yet
    cur.execute("""
        SELECT a.icao_code, a.name, c.name, c.continent, c.base_points
        FROM airport a
        JOIN country c ON c.country_code = a.country_code
        ORDER BY c.continent, c.name, a.name
    """)
    return cur.fetchall()


def buy_fuel(cur, conn, screen_name: str):
    # buying fuel in current country: formula cost = units * fuel_price
    cur.execute("""
        SELECT g.gold, c.fuel_price
        FROM game g
        JOIN airport a ON a.icao_code = g.location_icao
        JOIN country c ON c.country_code = a.country_code
        WHERE g.screen_name = %s
    """, (screen_name,))
    gold, fuel_price = cur.fetchone()

    if fuel_price <= 0:
        print("Fuel price not set for this country.")
        return

    print(f"\nFuel price here: {fuel_price} gold per 1 fuel unit.")
    units_str = input("How many fuel units do you want to buy? (number or 'c' to cancel): ").strip().lower()
    if units_str == "c":
        return
    if not units_str.isdigit():
        print("Please enter a valid number.")
        return

    units = int(units_str)
    cost = units * fuel_price

    if gold < cost:
        print(f"❌ Not enough gold. You need {cost}, but you have {gold}.")
        return

    cur.execute("""
        UPDATE game
        SET gold = gold - %s,
            fuel = fuel + %s
        WHERE screen_name = %s
    """, (cost, units, screen_name))
    conn.commit()
    print(f"✅ Bought {units} fuel for {cost} gold.")


def travel(cur, conn, screen_name: str, to_icao: str) -> bool:
    """
    Travel to another airport.
    Since distance is not implemented yet:
      - fuel_cost is fixed (example: 10)
      - points_awarded = destination_country.base_points
      - gold_reward from destination country is added to gold
    Return True to continue, False if game over.
    """
    # Get current state and destination info
    cur.execute("SELECT location_icao, gold, fuel FROM game WHERE screen_name = %s", (screen_name,))
    from_icao, gold, fuel = cur.fetchone()

    if from_icao == to_icao:
        print("You're already at that airport.")
        return True

    cur.execute("""
        SELECT a.icao_code, a.name, c.country_code, c.continent, c.base_points, c.gold_reward
        FROM airport a
        JOIN country c ON c.country_code = a.country_code
        WHERE a.icao_code = %s
    """, (to_icao,))
    dest = cur.fetchone()
    if dest is None:
        print("Invalid destination ICAO.")
        return True

    _, dest_airport_name, dest_country_code, dest_continent, base_points, gold_reward = dest

    # TEMP rules until we implement distance:
    FUEL_COST = 10

    if fuel < FUEL_COST:
        print("❌ Not enough fuel to travel.")
        return True

    # Apply updates:
    cur.execute("""
        UPDATE game
        SET location_icao = %s,
            fuel = fuel - %s,
            gold = gold + %s,
            score = score + %s
        WHERE screen_name = %s
    """, (to_icao, FUEL_COST, gold_reward, base_points, screen_name))
    conn.commit()

    print(f"\n✅ Traveled to {to_icao} - {dest_airport_name} ({dest_country_code}, {dest_continent})")
    print(f"Fuel cost: {FUEL_COST} | Points gained: {base_points} | Gold gained: {gold_reward}")

    # Game over check
    cur.execute("SELECT fuel FROM game WHERE screen_name = %s", (screen_name,))
    fuel_left = cur.fetchone()[0]
    if fuel_left <= 0:
        cur.execute("UPDATE game SET status = 'dead' WHERE screen_name = %s", (screen_name,))
        conn.commit()
        print("\n💀 GAME OVER 💀 You ran out of fuel.")
        return False

    return True


def main():
    conn = get_conn()
    cur = conn.cursor()

    try:
        action, screen_name = start_menu(cur, conn)

        if action == "exit":
            return

        # screen_name is guaranteed to be set if we are playing
        while True:
            show_state(cur, screen_name)

            print("\nActions:")
            print("1) Travel")
            print("2) Buy fuel")
            print("q) Quit")

            action = input("Choose: ").strip().lower()

            if action == "q":
                quit_choice = input(
                    "\nQuit options:\n"
                    "1) Quit and SAVE (continue later)\n"
                    "2) Quit and RESET (start new game next time)\n"
                    "Choose 1 or 2: "
                ).strip()

                if quit_choice == "2":
                    # Reset means: clear saved game so next start menu won't show Continue
                    cur.execute("DELETE FROM game")
                    conn.commit()
                    print("\n✅ Save deleted. Next time you'll start a new game. Goodbye!")
                else:
                    print("\n✅ Game saved. Goodbye!")

                break

            elif action == "2":
                buy_fuel(cur, conn, screen_name)

            elif action == "1":
                # your travel flow here (same as before)
                airports = list_airports(cur)
                print("\n=== AIRPORTS ===")
                for idx, (icao, name, cname, cont, base_pts) in enumerate(airports, start=1):
                    print(f"{idx}) {icao} - {name} ({cname}, {cont}) | base_points={base_pts}")

                choice = input("\nChoose airport number (or 'c' to cancel): ").strip().lower()
                if choice == "c":
                    continue
                if not choice.isdigit():
                    print("Invalid input.")
                    continue

                idx = int(choice)
                if idx < 1 or idx > len(airports):
                    print("Out of range.")
                    continue

                to_icao = airports[idx - 1][0]
                keep_playing = travel(cur, conn, screen_name, to_icao)

                if not keep_playing:
                    choice2 = input("\nPress 'r' to restart or 'q' to quit: ").strip().lower()
                    if choice2 == "r":
                        # Restart = reset values for same player
                        reset_game(cur, conn, screen_name)
                        print("\n🔄 Game restarted!")
                    else:
                        break
            else:
                print("Invalid action.")

    finally:
        cur.close()
        conn.close()
        print("\nGame closed.")


if __name__ == "__main__":
    main()