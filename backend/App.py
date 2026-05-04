from flask import Flask, jsonify, request
from flask_cors import CORS
from Database import Database
from Game_logic import create_new_game, get_game_state, list_airports_for_player, travel, buy_fuel, reset_game

app = Flask(__name__)
CORS(app)

db = Database()


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "backend works"})

@app.route("/db-test", methods=["GET"])
def db_test():
    try:
        conn = db.connect()
        cursor = conn.cursor()

        cursor.execute("SELECT DATABASE();")
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "success": True,
            "database": result[0]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/new-game", methods=["POST"])
def new_game():
    try:
        data = request.get_json()
        screen_name = data.get("screen_name")

        if not screen_name:
            return jsonify({
                "success": False,
                "error": "screen_name is required"
            })

        conn = db.connect()
        cursor = conn.cursor()

        result = create_new_game(cursor, conn, screen_name)

        cursor.close()
        conn.close()

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/state/<screen_name>", methods=["GET"])
def state(screen_name):
    try:
        conn = db.connect()
        cursor = conn.cursor()
        result = get_game_state(cursor, screen_name)
        cursor.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/airports/<screen_name>", methods=["GET"])
def airports(screen_name):
    try:
        conn = db.connect()
        cursor = conn.cursor()

        result = list_airports_for_player(cursor, screen_name)

        cursor.close()
        conn.close()

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/travel", methods=["POST"])
def travel_route():
    try:
        data = request.get_json()
        screen_name = data.get("screen_name")
        to_icao = data.get("to_icao")

        if not screen_name or not to_icao:
            return jsonify({
                "success": False,
                "error": "screen_name and to_icao are required"
            })

        conn = db.connect()
        cur = conn.cursor()

        result = travel(cur, conn, screen_name, to_icao)

        cur.close()
        conn.close()

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })
@app.route("/buy-fuel", methods=["POST"])
def buy_fuel_route():
    try:
        data = request.get_json()
        screen_name = data.get("screen_name")

        if not screen_name:
            return jsonify({
                "success": False,
                "error": "screen_name is required"
            })

        conn = db.connect()
        cur = conn.cursor()

        result = buy_fuel(cur, conn, screen_name)

        cur.close()
        conn.close()

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/reset-game", methods=["POST"])
def reset_game_route():
    try:
        data = request.get_json()
        screen_name = data.get("screen_name")

        if not screen_name:
            return jsonify({
                "success": False,
                "error": "screen_name is required"
            })

        conn = db.connect()
        cur = conn.cursor()

        result = reset_game(cur, conn, screen_name)

        cur.close()
        conn.close()

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == "__main__":
    app.run(debug=True)