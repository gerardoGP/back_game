# from flask import Flask
# from flask_cors import CORS
# from .routes import bp
import random
from flask import Flask, jsonify, request, session
from .game import (
    get_initial_state, ALLOWED_BETS, PAYLINES, BASE_FREE_SPINS,
    REELS, ROWS, REEL_STRIP, BONUS_REEL_STRIP, WILD_SYMBOL,
    FREE_SPINS_SCATTER_SYMBOL, PAYTABLE,
    calculate_line_prize
)
app = Flask(__name__)
# Añadimos una clave secreta para habilitar las sesiones de Flask
# app.secret_key = 'super-secret-key-for-demo' # En producción, esto debería ser un valor seguro y aleatorio
# CORS(app, supports_credentials=True) # supports_credentials=True es necesario para las sesiones
# app.register_blueprint(bp)

@app.route('/', methods=['GET'])
def test():
    return "<h1>Test</h1>"

@app.route('/initialize', methods=['POST'])
def initialize_game():
    """Crea un nuevo estado de juego y lo guarda en la sesión."""
    session['game_state'] = get_initial_state()
    return jsonify({"success": True, "message": "Game state initialized."})

@app.route('/gameState', methods=['GET'])
def get_game_state():
    """Obtiene el estado actual del juego desde la sesión."""
    # Si no hay estado en la sesión, crea uno nuevo.
    if 'game_state' not in session:
        session['game_state'] = get_initial_state()
    
    game_state = session['game_state']
    return jsonify({
        "balance": game_state["balance"],
        "allowed_bets": ALLOWED_BETS,
        "paylines": PAYLINES
    })

@app.route('/spin', methods=['POST'])
def handle_spin():
    if 'game_state' not in session:
        return jsonify({"error": "El juego no ha sido inicializado"}), 400
    
    game_state = session['game_state']
    data = request.get_json()
    try:
        bet = float(data.get("bet"))
    except (ValueError, TypeError):
        return jsonify({"error": "Formato de apuesta inválido"}), 400

    if bet not in ALLOWED_BETS:
        return jsonify({"error": "Apuesta no válida"}), 400

    if not game_state["is_in_free_spins"]:
        if game_state["balance"] < bet:
            return jsonify({"error": "Balance insuficiente"}), 400
        game_state["balance"] -= bet
    else:
        game_state["free_spins_remaining"] -= 1
        game_state["bonus_spins_played"] += 1

    result_matrix = [[None for _ in range(ROWS)] for _ in range(REELS)]
    if game_state["is_bonus_buy_spin"]:
        scatter_positions = random.sample(range(REELS * ROWS), 4)
        for pos in scatter_positions:
            reel_idx, row_idx = divmod(pos, ROWS)
            result_matrix[reel_idx][row_idx] = FREE_SPINS_SCATTER_SYMBOL
        game_state["is_bonus_buy_spin"] = False
    
    if game_state["is_in_free_spins"]:
        for wild_info in game_state["sticky_wilds_positions"]:
            r, c = wild_info["pos"]
            result_matrix[r][c] = WILD_SYMBOL

    active_reel_strip = BONUS_REEL_STRIP if game_state["is_in_free_spins"] else REEL_STRIP
    for r in range(REELS):
        for c in range(ROWS):
            if result_matrix[r][c] is None:
                symbol_str = random.choice(active_reel_strip)
                result_matrix[r][c] = symbol_str

    total_line_prize = 0
    winning_lines_info = []
    for i, line_pattern in enumerate(PAYLINES):
        symbol_line = [result_matrix[reel_idx][row_idx] for reel_idx, row_idx in enumerate(line_pattern)]
        prize, match_count, symbol, multiplier = calculate_line_prize(symbol_line, bet, i, game_state)
        if prize > 0:
            total_line_prize += prize
            winning_lines_info.append({
                "line_index": i, "symbol": symbol, "match_count": match_count,
                "prize": prize, "multiplier": multiplier
            })

    final_prize = total_line_prize
    game_state["balance"] += final_prize
    if game_state["is_in_free_spins"]:
        game_state["bonus_winnings"] += final_prize

    scatter_count = sum(col.count(FREE_SPINS_SCATTER_SYMBOL) for col in result_matrix)
    free_spins_won = 0
    retrigger_message = None
    if scatter_count >= 4:
        if game_state["is_in_free_spins"]:
            game_state["free_spins_remaining"] += 5
            retrigger_message = "¡+5 Giros Gratis!"
        else:
            free_spins_won = BASE_FREE_SPINS + (scatter_count - 4) * 2
            game_state["is_in_free_spins"] = True
            game_state["free_spins_remaining"] += free_spins_won
    
    if game_state["is_in_free_spins"]:
        for r in range(REELS):
            for c in range(ROWS):
                if result_matrix[r][c] == WILD_SYMBOL:
                    is_already_sticky = any(sw["pos"] == [r, c] for sw in game_state["sticky_wilds_positions"])
                    if not is_already_sticky:
                        game_state["sticky_wilds_positions"].append({
                            "pos": [r, c], "multiplier": random.choice([2, 3])
                        })

    response_data = {
        "resultMatrix": result_matrix, "totalPrize": final_prize,
        "newBalance": round(game_state["balance"], 2), "winningLines": winning_lines_info,
        "freeSpinsWon": free_spins_won, "retriggerMessage": retrigger_message,
        "freeSpinsRemaining": game_state["free_spins_remaining"]
    }

    if game_state["is_in_free_spins"] and game_state["free_spins_remaining"] == 0:
        response_data["bonus_summary"] = {
            "total_win": game_state["bonus_winnings"],
            "spins_played": game_state["bonus_spins_played"]
        }
        session['game_state'] = get_initial_state() # Reset state after bonus
    else:
        session['game_state'] = game_state # Save updated state

    return jsonify(response_data)

@app.route('/paytable', methods=['GET'])
def get_paytable():
    return jsonify(PAYTABLE)

@app.route('/buyBonus', methods=['POST'])
def buy_bonus():
    if 'game_state' not in session:
        return jsonify({"error": "El juego no ha sido inicializado"}), 400

    game_state = session['game_state']
    data = request.get_json()
    try:
        bet = float(data.get("bet"))
        bonus_type = data.get("bonusType")
    except (ValueError, TypeError):
        return jsonify({"error": "Datos de compra inválidos"}), 400

    if bet not in ALLOWED_BETS:
        return jsonify({"error": "Apuesta no válida"}), 400

    bonus_prices = {"standard": bet * 100, "legendary": bet * 300}
    price = bonus_prices.get(bonus_type)

    if price is None:
        return jsonify({"error": "Tipo de bono no válido"}), 400
    if game_state["balance"] < price:
        return jsonify({"error": "Balance insuficiente"}), 400

    game_state["balance"] -= price
    game_state["is_bonus_buy_spin"] = True
    
    spins_to_add = 0
    if bonus_type == 'standard':
        spins_to_add = BASE_FREE_SPINS
    elif bonus_type == 'legendary':
        spins_to_add = BASE_FREE_SPINS + 2
        game_state["active_bonuses"]["legendary"] = True

    game_state["is_in_free_spins"] = True
    game_state["free_spins_remaining"] = spins_to_add
    
    session['game_state'] = game_state # Save updated state

    return jsonify({
        "newBalance": game_state["balance"],
        "message": f"¡Bono comprado! {spins_to_add} Giros Gratis.",
        "freeSpinsRemaining": game_state["free_spins_remaining"]
    })


if __name__ == '__main__':
    app.run()