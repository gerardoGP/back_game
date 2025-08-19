import random

# --- CONSTANTES DE CONFIGURACIÓN DEL JUEGO ---
INITIAL_BALANCE = 100000
SPIN_COST = 10
ALLOWED_BETS = [0.20, 0.50, 1.00, 2.00, 5.00, 10.00, 25.00, 50.00]
REELS = 7
ROWS = 5
WILD_SYMBOL = 'W'
SYMBOLS = ['7', '💎', '⭐', '🍉', '🔔', '🍊', '💰', '🤠', WILD_SYMBOL]

# Cintas para el juego base (Wilds muy raros)
REEL_STRIP = (
    ['🍊'] * 26 +
    ['💰'] * 22 +
    ['🔔'] * 18 +
    ['🍉'] * 14 +
    ['⭐'] * 8 +
    ['💎'] * 6 +
    ['7'] * 3 +
    ['🤠'] * 3 +
    [WILD_SYMBOL] * 2
)

# Cintas para el bonus (Scatters muy raros)
BONUS_REEL_STRIP = (
    ['🔔'] * 28 +
    ['🍉'] * 25 +
    ['⭐'] * 20 +
    ['💎'] * 15 +
    ['7'] * 7 +
    ['🤠'] * 2
)

FREE_SPINS_SCATTER_SYMBOL = '🤠'
BASE_FREE_SPINS = 10

# --- DEFINICIÓN DE LÍNEAS DE PAGO ---
PAYLINES = [
    [2, 2, 2, 2, 2, 2, 2],
    [1, 1, 1, 1, 1, 1, 1],
    [3, 3, 3, 3, 3, 3, 3],
    [0, 0, 0, 0, 0, 0, 0],
    [4, 4, 4, 4, 4, 4, 4],
    [0, 1, 2, 3, 2, 1, 0],
    [4, 3, 2, 1, 2, 3, 4]
]

# --- TABLA DE PAGOS (Multiplicadores de apuesta) ---
PAYTABLE = {
    '7': {3: 10, 4: 50, 5: 200, 6: 1000, 7: 5000},
    '💎': {3: 5, 4: 20, 5: 80, 6: 400, 7: 1500},
    '⭐': {3: 2.5, 4: 12, 5: 40, 6: 200, 7: 750},
    '🍉': {3: 1, 4: 5, 5: 15, 6: 50, 7: 200},
    '🔔': {3: 0.5, 4: 3, 5: 10, 6: 25, 7: 100},
    '🍊': {3: 0.2, 4: 1.5, 5: 5, 6: 12, 7: 50},
    '💰': {3: 0.1, 4: 0.2, 5: 0.5, 6: 1, 7: 5},
    WILD_SYMBOL: {3: 15, 4: 75, 5: 250, 6: 1500, 7: 7500}
}

# --- ESTADO DEL JUEGO (en memoria) ---
def get_initial_state():
    """Devuelve un diccionario con el estado inicial del juego."""
    return {
        "balance": INITIAL_BALANCE,
        "is_in_free_spins": False,
        "free_spins_remaining": 0,
        "active_bonuses": {
            "hunt": False,
            "legendary": False
        },
        "sticky_wilds_positions": [],
        "is_bonus_buy_spin": False,
        "bonus_winnings": 0,
        "bonus_spins_played": 0,
        "bonus_global_multiplier": 1
    }

# --- FUNCIÓN AUXILIAR PARA CALCULAR PREMIOS POR LÍNEA ---
def calculate_line_prize(symbol_line, bet, line_index, game_state):
    """
    Calcula el premio para una única línea de pago.
    La línea es una lista de strings.
    """
    from .game import WILD_SYMBOL, FREE_SPINS_SCATTER_SYMBOL, PAYTABLE, PAYLINES

    if not symbol_line:
        return 0, 0, None, 1

    # 1. Determinar el símbolo de pago
    paying_symbol = None
    for symbol in symbol_line:
        if symbol != WILD_SYMBOL:
            paying_symbol = symbol
            break
    if paying_symbol is None:
        paying_symbol = WILD_SYMBOL

    if paying_symbol == FREE_SPINS_SCATTER_SYMBOL:
        return 0, 0, None, 1

    # 2. Contar coincidencias
    match_count = 0
    for symbol in symbol_line:
        if symbol == paying_symbol or symbol == WILD_SYMBOL:
            match_count += 1
        else:
            break

    # 3. Calcular premio
    prize = 0
    total_multiplier = 1
    if paying_symbol in PAYTABLE and match_count in PAYTABLE[paying_symbol]:
        prize = PAYTABLE[paying_symbol][match_count] * bet

        if prize > 0 and game_state.get("is_in_free_spins", False):
            line_pattern = PAYLINES[line_index]
            for i in range(match_count):
                if symbol_line[i] == WILD_SYMBOL:
                    current_pos = [i, line_pattern[i]]
                    for sticky_wild in game_state.get("sticky_wilds_positions", []):
                        if sticky_wild.get('pos') == current_pos:
                            total_multiplier *= sticky_wild.get('multiplier', 1)
                            break
    
    final_prize = prize * total_multiplier
    return final_prize, match_count, paying_symbol, total_multiplier