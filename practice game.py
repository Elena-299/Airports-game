import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "metropolia12",
    "database": "airport_adventure",
}


FUEL_COST_PER_COUNTRY = 10
GOLD_COST_PER_COUNTRY = 15


def get_conn():
    return mysql.connector.connect(**DB_CONFIG)


def show_state(cur):
    cur.execute("""
        SELECT gs.gold, gs.fuel, gs.score, gs.level, a.iata_code, a.name
        FROM game_state gs
        JOIN airports a ON a.id = gs.current_airport_id
        WHERE gs.id = 1
    """)
    gold, fuel, score, level, iata, name = cur.fetchone()
    print("\n=== CURRENT STATE ===")
    print(f"Location: {iata} - {name}")
    print(f"Gold: {gold} | Fuel: {fuel} | Score: {score} | Level: {level}")


def list_destinations(cur):
    cur.execute("""
        SELECT a2.id, a2.iata_code, a2.name, a2.continent, r.countries_moved, a2.base_points
        FROM game_state gs
        JOIN routes r ON r.from_airport_id = gs.current_airport_id
        JOIN airports a2 ON a2.id = r.to_airport_id
        WHERE gs.id = 1
        ORDER BY r.countries_moved ASC
    """)
    rows = cur.fetchall()

    print("\nWhere do you want to travel?")
    for idx, (aid, iata, name, cont, moved, base_points) in enumerate(rows, start=1):
        fuel_cost = moved * FUEL_COST_PER_COUNTRY
        gold_cost = moved * GOLD_COST_PER_COUNTRY
        print(f"{idx}) {iata} - {name} ({cont}) \n| moved through {moved} countries | cost: {fuel_cost} fuel, {gold_cost} gold | +{base_points} points |\n")

    return rows


def travel(cur, conn, chosen_airport_id):
    # get current airport and route info
    cur.execute("""
        SELECT gs.current_airport_id, r.countries_moved
        FROM game_state gs
        JOIN routes r ON r.from_airport_id = gs.current_airport_id
        WHERE gs.id = 1 AND r.to_airport_id = %s
    """, (chosen_airport_id,))
    result = cur.fetchone()

    if not result:
        print("Invalid destination.")
        return

    from_id, moved = result
    fuel_cost = moved * FUEL_COST_PER_COUNTRY
    gold_cost = moved * GOLD_COST_PER_COUNTRY

    # check resources
    cur.execute("SELECT gold, fuel FROM game_state WHERE id = 1")
    gold, fuel = cur.fetchone()

    if gold < gold_cost or fuel < fuel_cost:
        print("\n❌ Not enough gold or fuel to travel.")
        return

    # points for arriving
    cur.execute("SELECT base_points, iata_code, name FROM airports WHERE id = %s", (chosen_airport_id,))
    base_points, iata, name = cur.fetchone()

    # update state
    cur.execute("""
        UPDATE game_state
        SET current_airport_id = %s,
            gold = gold - %s,
            fuel = fuel - %s,
            score = score + %s
        WHERE id = 1
    """, (chosen_airport_id, gold_cost, fuel_cost, base_points))

    # insert travel log (simple, no FK yet)
    cur.execute("""
        INSERT INTO travel_log (game_id, from_airport_id, to_airport_id, countries_moved, gold_cost, fuel_cost)
        VALUES (1, %s, %s, %s, %s, %s)
    """, (from_id, chosen_airport_id, moved, gold_cost, fuel_cost))

    conn.commit()

    print(f"\n✅ You have moved through {moved} countries to get to {iata} - {name}.")


def main():
    conn = get_conn()
    cur = conn.cursor()

    try:
        while True:
            show_state(cur)
            destinations = list_destinations(cur)

            choice = input("\nChoose a number (or 'q' to quit): ").strip().lower()
            if choice == "q":
                break

            if not choice.isdigit():
                print("Please type a valid number.")
                continue

            idx = int(choice)
            if idx < 1 or idx > len(destinations):
                print("Choice out of range.")
                continue

            chosen_airport_id = destinations[idx - 1][0]
            travel(cur, conn, chosen_airport_id)

    finally:
        cur.close()
        conn.close()
        print("\nBye!")


if __name__ == "__main__":
    main()

#hello