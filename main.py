# --- START OF FILE main.py ---

# Required: pip install ttkbootstrap are you an actual fucking idiot me

import tkinter as tk
import tkinter.scrolledtext as scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading as th
import datetime as dt
import math as ma
import sys
import os
import logging
import random
import ast # Safer alternative to eval for simple literals
import json # For serializing save data
import base64 # For encoding save data
import time # Use standard time module

# --- Configuration ---
SAVE_FILE = "save_encoded.dat"
LOG_FILE = "gamelog.txt"
SAVE_VERSION = 20 # Incremented for Relics system and Ascension changes
UPDATE_INTERVAL_MS = 100
TICK_INTERVAL_S = 0.1
AUTOSAVE_INTERVAL_S = 30
DEVELOPER_MODE = False
POINT_THRESHOLD_SP = 1e24

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Utility Functions ---
ENDINGS = ["K","M","B","T","Qa","Qi","Sx","Sp","Oc","No","Dc","Ud","Dd","Td","Qad","Qid","Sxd","Spd","Ocd","Nod","Vg"]
def format_number(num):
    """Formats a number into a human-readable string with K, M, B, etc. suffixes."""
    if not isinstance(num, (int, float)) or ma.isnan(num) or ma.isinf(num): return str(num)
    if abs(num) < 1000: return "{:.2f}".format(round(num, 2))
    if num == 0: return "0.00"
    sign = "-" if num < 0 else ""
    num_abs = abs(num)
    count = 0
    power = 1000.0
    num_div = num_abs
    while num_div >= power and count < len(ENDINGS):
        num_div /= power
        count += 1
    if count == 0: return "{}{:.2f}".format(sign, round(num_abs, 2))
    else:
        idx = min(count - 1, len(ENDINGS) - 1)
        return "{}{:.2f}{}".format(sign, num_div, ENDINGS[idx])

# --- Game State Object ---
class GameState:
    def __init__(self):
        # --- Point Upgrades ---
        self.upgrade1_cost = 10.0
        self.upgrade1_level = 0
        self.upgrade1_max = 25
        self.upgrade2_cost = 100.0
        self.upgrade2_level = 0
        self.upgrade2_max = 10
        self.upgrade3_cost = 10000.0
        self.upgrade3_level = 0
        self.upgrade3_max = 10
        self.upgrade4_cost = 10000000.0
        self.upgrade4_level = 0
        self.upgrade4_max = 5
        # --- Click Upgrades ---
        self.upgrade5_complete = False
        self.upgrade6_complete = False
        self.upgrade7_cost = 1e6
        self.upgrade7_level = 0
        self.upgrade7_max = 50
        self.upgrade8_cost = 1e9
        self.upgrade8_level = 0
        self.upgrade8_max = 100
        # --- Calculated Modifiers ---
        self.multiplier = 1.0
        self.multiplier_strength = 1.0
        self.pps_exponent = 1.0
        self.click_power = 1.0
        self.click_crit_chance = 0.0
        self.click_crit_multiplier = 2.0
        self.auto_clicks_per_sec = 0.0
        self.click_point_scaling_bonus = 1.0
        # --- Purification State ---
        self.purify_times = 0
        self.max_purify = 10
        self.purify_cost = 1000.0
        self.rank1_booster = 1.0
        self.rank2_unlocked = False
        self.rank3_unlocked = False
        self.rank3_cost_multiplier = 1.0
        self.rank4_upg2_booster = 1.0
        self.rank5_upg3_booster = 0.0
        self.rank6_unlocked = False
        self.rank6_booster = 1.0
        # --- Crystalline State ---
        self.crystalline_unlocked = False
        self.crystalline_times = 0
        self.max_crystalline = 4
        self.crystalline_cost = 2.5e8
        self.cry1_booster = 1.0
        self.cry1_upg4_unlocked = False
        self.cry2_booster = 1.0
        self.cry3_unlocked = False
        self.cry4_unlocked = False
        self.crystalline_5_complete = False
        # --- Ascension State ---
        self.ascension_unlocked = False
        self.ascension_count = 0
        self.stardust = 0.0
        self.ascension_cost = 1e48 # Adjusted initial cost
        # --- Relics ---
        self.relic_levels = {} # Stores {relic_id: level}
        # --- Astral Upgrades ---
        self.astral_points_boost = 1.0
        self.astral_clicks_boost = 1.0
        self.astral_purify_boost = 1.0
        self.astral_upg1_start_level = 0
        self.astral_costs = {'points': 1, 'clicks': 1, 'purify': 5, 'upg1_start': 10}
        self.astral_levels = {'points': 0, 'clicks': 0, 'purify': 0, 'upg1_start': 0}
        # --- Synergy/Later Effects ---
        self.crystalline_completion_bonus = 1.0
        self.p11_pps_boost_per_clickpower = 0.0
        self.p12_autobuy_upg4_unlocked = False
        self.p14_upg2_boost = 1.0
        self.p16_cost_reduction_factor = 1.0
        self.p17_upg1_boost_to_rank4 = 1.0
        self.p18_passive_click_rate = 0.0
        self.p19_boost_multiplier = 1.0
        self.p20_limit_break_active = False
        self.p24_purify_cost_divisor = 1.0
        # --- Challenges ---
        self.challenge_completions = {}
        self.challenge_stardust_boost = 1.0
        # --- General State ---
        self.total_playtime = 0.0
        self.admin_panel_active = False
        self.last_save_time = time.time()
        # --- Scaling ---
        self.pps_point_scaling_exponent = 1.0

game_state = GameState()

# --- Global Variables ---
points = 0.0
clicks = 0.0
point_per_second = 0.0
is_running = True
autobuy_thread = None

# --- Relic Definitions ---
RELICS_DATA = {
    'relic_pt_mult': { 'name': "Star Prism", 'desc': "+5% Points per level (mult)", 'cost_base': 5, 'cost_scale': 1.8, 'max_level': None, 'effect': lambda lvl: 1.05 ** lvl },
    'relic_clk_mult': { 'name': "Kinetic Shard", 'desc': "+8% Effective Clicks per level (mult)", 'cost_base': 5, 'cost_scale': 1.8, 'max_level': None, 'effect': lambda lvl: 1.08 ** lvl },
    'relic_u1_str': { 'name': "Amplifying Lens", 'desc': "Upg1 base multiplier gain +0.02 per level", 'cost_base': 10, 'cost_scale': 2.0, 'max_level': 50, 'effect': lambda lvl: 0.02 * lvl },
    'relic_p6_exp': { 'name': "Echoing Chamber", 'desc': "P6 Purify Boost ^(1 + 0.01*Lvl)", 'cost_base': 25, 'cost_scale': 2.5, 'max_level': 20, 'effect': lambda lvl: 1.0 + 0.01 * lvl },
    'relic_sd_gain': { 'name': "Cosmic Magnet", 'desc': "+2% Stardust gain per level (mult)", 'cost_base': 50, 'cost_scale': 3.0, 'max_level': None, 'effect': lambda lvl: 1.02 ** lvl },
}

# --- Prestige Descriptions / Challenges / Astral ---
PURIFY_DESCRIPTIONS = [
    "x3 point gain. Afterwards, x2 point gain.", # P1 (Index 0)
    "+1 max level to Upgs 1 & 2.", # P2 (Index 1)
    "Upg 1-3 cost x0.95 (mult).", # P3 (Index 2)
    "Upg 2 Strength base multiplier x3.", # P4 (Index 3)
    "Upg 3 base exponent gain +0.01/lvl.", # P5 (Index 4)
    "Gain (1+Purify Times)^2 PPS multiplier.", # P6 (Index 5)
    "No boost.", "No boost. Try again?", "No boost. Next unlocks something!", # P7-9 (Index 6-8)
    "Unlock Crystalline layer.", # P10 (Index 9)
    "Click Power adds +0.1% base PPS per point.", # P11 (Index 10)
    "Autobuy Upgrade 4.", # P12 (Index 11)
    "Each Crystalline +5% points (mult).", # P13 (Index 12)
    "Upg 2 base factor +50% (1.1x -> 1.15x).", # P14 (Index 13)
    "Unlock buying Crystalline V.", # P15 (Index 14)
    "Reduce upgrade cost scaling per Crystalline.", # P16 (Index 15)
    "Upg 1 levels slightly boost Rank 4 effect.", # P17 (Index 16)
    "Passive Clicks (1% of Click Power/sec).", # P18 (Index 17)
    "Boost previous Purifications power x1.25.", # P19 (Index 18)
    "LIMIT BREAK: +10 Max Levels Upgs 1 & 2.", # P20 (Index 19) <<< MODIFIED
    "P21", "P22", "P23", # Index 20-22
    "Purify cost / sqrt(Purify Times).", # P24 (Index 23)
]
CRYSTALLINE_DESCRIPTIONS = [
    "x3 point gain. Unlock Upgrade 4.", # C1 (Index 0)
    "Point gain ^1.5.", # C2 (Index 1)
    "Autobuy Upgrades 1-3.", # C3 (Index 2)
    "Unlock Clicking & Click Upgs.", # C4 (Index 3)
    "Unlock P16-20+. Activate Playtime boost (needs Upg6). Unlock Ascension.", # C5 (Index 4)
]
ASTRAL_UPGRADE_DESCRIPTIONS = {
    'points': "Permanently increase all Point gain by 10% (mult).",
    'clicks': "Permanently increase Click Power by 15% (mult).",
    'purify': "Permanently increase Purification effect scaling by 5%.",
    'upg1_start': "Start each Crystalline/Ascension with +1 free Upgrade 1 level.",
}
CHALLENGES = {
    'c1': {
        'desc_base': "Reach Points without buying Upg2", 'max_completions': 10,
        'requirement_func': lambda gs, comp: 1e9 * (100**comp), 'requirement_desc_func': lambda req: f"Req: {format_number(req)} Points",
        'check_func': lambda gs, req: ( not ma.isinf(points) and points >= req and gs.upgrade2_level == 0 ),
        'reward_desc_func': lambda gs, comp: f"Reward: +{comp * 2}% Stardust Gain", 'apply_reward_func': lambda gs: setattr(gs, 'challenge_stardust_boost', gs.challenge_stardust_boost * 1.02)
    },
    'c2': {
        'desc_base': "Reach Clicks within 5 mins of Purify", 'max_completions': 5,
        'requirement_func': lambda gs, comp: 1e6 * (10**comp), 'requirement_desc_func': lambda req: f"Req: {format_number(req)} Clicks",
        'check_func': lambda gs, req: clicks >= req and gs.total_playtime <= 300,
        'reward_desc_func': lambda gs, comp: f"Reward: +{comp * 1}% Perm. Click Boost", 'apply_reward_func': lambda gs: setattr(gs, 'astral_clicks_boost', gs.astral_clicks_boost * 1.01)
    },
    'c3': {
        'desc_base': "Reach Crystalline without Upg3", 'max_completions': 3,
        'requirement_func': lambda gs, comp: comp + 1, 'requirement_desc_func': lambda req: f"Req: Reach Crystalline {req}",
        'check_func': lambda gs, req: gs.crystalline_times >= req and gs.upgrade3_level == 0,
        'reward_desc_func': lambda gs, comp: f"Reward: Upg3 Cost x{0.95**comp:.2f}", 'apply_reward_func': lambda gs: setattr(gs, 'rank3_cost_multiplier', gs.rank3_cost_multiplier * 0.95)
    },
}

# --- Core Calculation Logic ---
def calculate_click_point_bonus():
    """Calculates click bonus based on points > 1 Sp, with diminishing returns."""
    global points
    current_points = points if isinstance(points, (int, float)) and not ma.isnan(points) and not ma.isinf(points) else 0.0
    if current_points <= POINT_THRESHOLD_SP: return 1.0
    try:
        orders = ma.log10(current_points / POINT_THRESHOLD_SP)
        dampened_exponent = ma.log10(orders + 1.0) * 2.0 # Soft cap exponent
        return max(1.0, 2.0 ** dampened_exponent)
    except (ValueError, OverflowError): return 1.0

def get_upgrade2_factor(gs):
    base = 1.10
    boost = 0.05 if gs.p14_upg2_boost > 1.0 else 0
    return base + boost

def recalculate_multiplier_strength():
    global game_state
    gs = game_state
    factor = get_upgrade2_factor(gs)
    p17_boost = (1.0 + (gs.upgrade1_level * 0.002 * gs.astral_purify_boost)) if gs.purify_times >= 17 else 1.0
    gs.multiplier_strength = (factor ** gs.upgrade2_level) * gs.rank4_upg2_booster * p17_boost

def calculate_point_per_second():
    global point_per_second, game_state
    gs = game_state
    pps = 0.0
    try:
        # --- Calculate Relic Bonuses First ---
        relic_point_mult = RELICS_DATA['relic_pt_mult']['effect'](gs.relic_levels.get('relic_pt_mult', 0))
        relic_p6_exp_mult = RELICS_DATA['relic_p6_exp']['effect'](gs.relic_levels.get('relic_p6_exp', 0))
        # --- Calculate Base PPS ---
        base_pps_from_clicks = (gs.click_power * gs.astral_clicks_boost * gs.click_point_scaling_bonus * RELICS_DATA['relic_clk_mult']['effect'](gs.relic_levels.get('relic_clk_mult', 0))) * gs.p11_pps_boost_per_clickpower if gs.purify_times >= 11 else 0.0
        base_pps = 1.0 + base_pps_from_clicks
        # --- Apply Multipliers ---
        effective_multiplier = gs.multiplier * gs.multiplier_strength
        pps = base_pps * effective_multiplier * gs.rank1_booster
        if gs.rank6_unlocked: pps *= (gs.rank6_booster ** relic_p6_exp_mult) # Apply relic exponent to P6 boost
        pps *= gs.cry1_booster
        pps *= gs.crystalline_completion_bonus
        if gs.crystalline_5_complete and gs.upgrade6_complete: pps *= calculate_playtime_multiplier()
        pps *= gs.p19_boost_multiplier
        pps *= gs.astral_points_boost
        pps *= relic_point_mult # Apply point relic multiplier
        # --- Apply Exponents ---
        if gs.cry2_booster != 1.0: pps = pps ** gs.cry2_booster if pps > 0 else 0
        if gs.pps_exponent != 1.0: pps = pps ** gs.pps_exponent if pps > 0 else 0
        if gs.pps_point_scaling_exponent < 1.0: pps = pps ** gs.pps_point_scaling_exponent if pps > 0 else 0
    except (ValueError, OverflowError) as e:
        logging.warning(f"PPS calculation error: {e}")
        pps = 0.0 # Fallback to 0 on math errors

    point_per_second = round(pps, 3) if isinstance(pps, (int, float)) and not ma.isnan(pps) and not ma.isinf(pps) else 0.0

def calculate_playtime_multiplier():
    global game_state
    gs = game_state
    playtime_sec = gs.total_playtime if isinstance(gs.total_playtime, (int, float)) else 0
    if playtime_sec <= 0: return 1.0
    minutes_played = playtime_sec / 60.0
    bonus = ma.log(minutes_played + 1) + 1.0 # Use log(minutes+1)
    return max(1.0, round(bonus, 3))

def recalculate_derived_values():
    """Recalculates all game values that depend on multiple base stats or upgrades."""
    global game_state, points
    gs = game_state

    # --- Calculate Relic Bonuses ---
    relic_p6_exp_mult = RELICS_DATA['relic_p6_exp']['effect'](gs.relic_levels.get('relic_p6_exp', 0))
    relic_clk_mult = RELICS_DATA['relic_clk_mult']['effect'](gs.relic_levels.get('relic_clk_mult', 0))

    # --- Purify Based Effects ---
    purify_power_mult = gs.astral_purify_boost * (1.25 if gs.purify_times >= 19 else 1.0) # Include P19
    gs.rank6_booster = ((1.0 + gs.purify_times)**2.0) * purify_power_mult if gs.rank6_unlocked else 1.0
    gs.p11_pps_boost_per_clickpower = 0.001 * purify_power_mult if gs.purify_times >= 11 else 0.0
    gs.crystalline_completion_bonus = 1.0 + (gs.crystalline_times * 0.05 * purify_power_mult) if gs.purify_times >= 13 else 1.0
    gs.p14_upg2_boost = 1.5 if gs.purify_times >= 14 else 1.0
    gs.p16_cost_reduction_factor = max(0.5, 1.0 - (gs.crystalline_times * 0.005 * purify_power_mult)) if gs.purify_times >= 16 else 1.0
    gs.p17_upg1_boost_to_rank4 = purify_power_mult if gs.purify_times >= 17 else 1.0
    gs.p18_passive_click_rate = 0.01 * purify_power_mult if gs.purify_times >= 18 else 0.0
    gs.p24_purify_cost_divisor = max(1.0, ma.sqrt(gs.purify_times) * purify_power_mult) if gs.purify_times >= 24 else 1.0

    # --- Point Scaling ---
    gs.click_point_scaling_bonus = calculate_click_point_bonus()
    current_points_safe = points if isinstance(points, (int, float)) and not ma.isnan(points) and not ma.isinf(points) else 0.0
    gs.pps_point_scaling_exponent = 1.0
    if current_points_safe > POINT_THRESHOLD_SP:
        try:
            orders = ma.log10(current_points_safe / POINT_THRESHOLD_SP)
            red_str = 0.05 if gs.p20_limit_break_active else 0.02 # Stronger reduction post P20
            min_exp = 0.3 if gs.p20_limit_break_active else 0.5   # Lower floor post P20
            target_exp = 1.0 - (ma.log10(orders + 1.0) * red_str)
            gs.pps_point_scaling_exponent = max(min_exp, target_exp)
        except (ValueError, OverflowError): pass # Keep 1.0 on error

    # --- Click Effects ---
    gs.click_crit_chance = min(1.0, 0.05 * gs.upgrade7_level)
    gs.click_crit_multiplier = 2.0 + (0.2 * gs.upgrade7_level)
    effective_base_click = gs.click_power * gs.astral_clicks_boost * gs.click_point_scaling_bonus * relic_clk_mult
    base_auto_click = effective_base_click * (0.01 * gs.upgrade8_level)
    passive_click_from_p18 = effective_base_click * gs.p18_passive_click_rate if gs.p18_passive_click_rate > 0 else 0.0
    gs.auto_clicks_per_sec = base_auto_click + passive_click_from_p18

    # --- Recalc Dependent Values ---
    recalculate_multiplier_strength()
    calculate_point_per_second() # Applies relic point mult, relic P6 exp, PPS point scaling exp

    # --- Update Max Purify ---
    gs.max_purify = 20 if gs.crystalline_5_complete else (15 if gs.upgrade5_complete else 10)

    logging.debug(f"Derived values recalculated (PPS Scale Exp: {gs.pps_point_scaling_exponent:.3f}, Click Scale Bonus: x{gs.click_point_scaling_bonus:.2f})")


# --- Game Loop Logic ---
def game_tick():
    global points, clicks, point_per_second, game_state
    gs = game_state
    try:
        pps = point_per_second if isinstance(point_per_second, (int, float)) else 0.0
        current_points = points if isinstance(points, (int, float)) else 0.0
        current_clicks = clicks if isinstance(clicks, (int, float)) else 0.0
        cps = gs.auto_clicks_per_sec if isinstance(gs.auto_clicks_per_sec, (int, float)) else 0.0
        points = current_points + pps * TICK_INTERVAL_S
        clicks = current_clicks + cps * TICK_INTERVAL_S
        gs.total_playtime += TICK_INTERVAL_S
        if int(gs.total_playtime * 10) % 50 == 0: check_challenges()
    except Exception as e: logging.error(f"Error in game_tick: {e}", exc_info=True)

def game_loop_thread_func():
    logging.info("Game loop thread started.")
    while is_running:
        start = time.monotonic()
        game_tick()
        elapsed = time.monotonic() - start
        time.sleep(max(0, TICK_INTERVAL_S - elapsed))
    logging.info("Game loop thread finished.")


# --- Upgrade Functions ---
def upgrade1(): # Apply Relic Bonus
    global points, game_state
    gs = game_state
    cost = gs.upgrade1_cost
    if gs.upgrade1_level < gs.upgrade1_max and points >= cost:
        points -= cost
        gs.upgrade1_level += 1
        relic_u1_bonus = RELICS_DATA['relic_u1_str']['effect'](gs.relic_levels.get('relic_u1_str', 0))
        gs.multiplier += (1.0 + relic_u1_bonus) # Apply additive bonus from relic
        level_factor = 1.15
        reduction = gs.rank3_cost_multiplier * gs.p16_cost_reduction_factor
        gs.upgrade1_cost = round(10.0 * (level_factor ** gs.upgrade1_level) * reduction, 2)
        recalculate_derived_values()

def upgrade2():
    global points, game_state
    gs = game_state
    cost = gs.upgrade2_cost
    if gs.upgrade2_level < gs.upgrade2_max and points >= cost:
        points -= cost
        gs.upgrade2_level += 1
        level_factor = 1.25
        reduction = gs.rank3_cost_multiplier * gs.p16_cost_reduction_factor
        gs.upgrade2_cost = round(100.0 * (level_factor ** gs.upgrade2_level) * reduction, 2)
        recalculate_derived_values()

def upgrade3(): # Apply Soft Cap
    global points, game_state
    gs = game_state
    cost = gs.upgrade3_cost
    if gs.upgrade3_level >= gs.upgrade3_max or points < cost: return
    points -= cost
    gs.upgrade3_level += 1
    base_gain = 0.05 + gs.rank5_upg3_booster
    threshold = 2.0
    reduction_factor = 0.1
    effective_gain = base_gain
    if gs.pps_exponent > threshold: effective_gain *= reduction_factor
    if gs.p20_limit_break_active: effective_gain *= reduction_factor # Double reduction
    gs.pps_exponent += max(0.001, effective_gain) # Apply soft-capped gain
    level_factor = 1.35
    reduction = gs.rank3_cost_multiplier * gs.p16_cost_reduction_factor
    gs.upgrade3_cost = round(10000.0 * (level_factor ** gs.upgrade3_level) * reduction, 2)
    recalculate_derived_values()

def upgrade4():
    global points, game_state
    gs = game_state
    cost = gs.upgrade4_cost
    if not gs.cry1_upg4_unlocked: return
    if gs.upgrade4_level < gs.upgrade4_max and points >= cost:
        points -= cost
        gs.upgrade4_level += 1
        gs.upgrade3_max += 1
        level_factor = 1.5
        reduction = gs.p16_cost_reduction_factor
        gs.upgrade4_cost = round(10000000.0 * (level_factor ** gs.upgrade4_level) * reduction, 2)

def upgrade5():
    global clicks, game_state
    gs = game_state
    req = 1000.0
    if not gs.cry4_unlocked or gs.upgrade5_complete: return
    if clicks >= req:
        clicks -= req
        gs.upgrade5_complete = True
        gs.max_purify = 15
        logging.info("Upg5 Done!")
        recalculate_derived_values()
    else: logging.info(f"Need {format_number(req - clicks)} clicks for Upg5")

def upgrade6():
    global clicks, game_state
    gs = game_state
    req = 100000.0
    if not gs.cry4_unlocked or gs.upgrade6_complete: return
    if clicks >= req:
        clicks -= req
        gs.upgrade6_complete = True
        logging.info("Upg6 Done!")
        recalculate_derived_values()
    else: logging.info(f"Need {format_number(req - clicks)} clicks for Upg6")

def upgrade7():
    global clicks, game_state
    gs = game_state
    cost = gs.upgrade7_cost
    if not gs.cry4_unlocked: return
    if gs.upgrade7_level < gs.upgrade7_max and clicks >= cost:
        clicks -= cost
        gs.upgrade7_level += 1
        gs.upgrade7_cost *= 1.5
        recalculate_derived_values()

def upgrade8():
    global clicks, game_state
    gs = game_state
    cost = gs.upgrade8_cost
    if not gs.cry4_unlocked: return
    if gs.upgrade8_level < gs.upgrade8_max and clicks >= cost:
        clicks -= cost
        gs.upgrade8_level += 1
        gs.upgrade8_cost *= 2.0
        recalculate_derived_values()

# --- Prestige Functions ---
def apply_purification_effects(p_level_index): # P20 Only Upg1/2
    global game_state, autobuy_thread
    gs = game_state
    p_num = p_level_index + 1
    # --- Corrected Logic ---
    if p_num == 1:
        gs.rank1_booster = 3.0
    elif p_num > 1:
        gs.rank1_booster *= 2.0

    if p_num == 2:
        gs.rank2_unlocked = True
        gs.upgrade1_max += 1
        gs.upgrade2_max += 1
    if p_num == 3:
        gs.rank3_unlocked = True
        gs.rank3_cost_multiplier *= 0.95
    if p_num == 4:
        gs.rank4_upg2_booster = 3.0
    if p_num == 5:
        gs.rank5_upg3_booster = 0.01
    if p_num == 6:
        gs.rank6_unlocked = True
    if p_num == 10:
        gs.crystalline_unlocked = True
    if p_num == 12:
        gs.p12_autobuy_upg4_unlocked = True
        start_autobuy_thread_if_needed()
    if p_num == 19:
        gs.p19_boost_multiplier = 1.25
    if p_num == 20 and gs.crystalline_5_complete and not gs.p20_limit_break_active:
        gs.p20_limit_break_active = True
        levels_to_add = 10
        gs.upgrade1_max += levels_to_add
        gs.upgrade2_max += levels_to_add # ONLY Upg 1 & 2
        logging.info(f"P20 Limit Break Activated! (+{levels_to_add} Max Lvl Upg1 & Upg2)")

def apply_crystalline_effects(cry_level_achieved):
    global game_state, autobuy_thread
    gs = game_state
    if cry_level_achieved == 1:
        gs.cry1_booster = 3.0
        gs.cry1_upg4_unlocked = True
    elif cry_level_achieved == 2: gs.cry2_booster = 1.5
    elif cry_level_achieved == 3:
        gs.cry3_unlocked = True
        start_autobuy_thread_if_needed()
    elif cry_level_achieved == 4: gs.cry4_unlocked = True
    elif cry_level_achieved == 5:
        gs.crystalline_5_complete = True
        gs.ascension_unlocked = True

def reset_for_purify():
    global points, game_state
    gs = game_state
    points = 0.0
    gs.upgrade1_level = 0
    gs.upgrade1_cost = 10.0
    gs.upgrade2_level = 0
    gs.upgrade2_cost = 100.0
    gs.upgrade3_level = 0
    gs.upgrade3_cost = 10000.0
    gs.upgrade4_level = 0
    gs.upgrade4_cost = 10000000.0
    gs.multiplier = 1.0
    gs.pps_exponent = 1.0
    start_lvl1 = gs.astral_levels.get('upg1_start', 0)
    if start_lvl1 > 0:
        temp_cost = 10.0
        reduction = gs.rank3_cost_multiplier * gs.p16_cost_reduction_factor
        factor = 1.15
        relic_u1_bonus = RELICS_DATA['relic_u1_str']['effect'](gs.relic_levels.get('relic_u1_str', 0))
        for i in range(start_lvl1):
            gs.upgrade1_level += 1
            gs.multiplier += (1.0 + relic_u1_bonus)
            temp_cost = round(10.0 * (factor ** gs.upgrade1_level) * reduction, 2)
        gs.upgrade1_cost = temp_cost

def reset_for_crystalline():
    global points, game_state
    gs = game_state
    points = 0.0
    gs.purify_times = 0
    gs.purify_cost = 1000.0
    gs.rank1_booster = 1.0
    gs.rank2_unlocked = False
    gs.rank3_unlocked = False
    gs.rank3_cost_multiplier = 1.0
    gs.rank4_upg2_booster = 1.0
    gs.rank5_upg3_booster = 0.0
    gs.rank6_unlocked = False
    gs.rank6_booster = 1.0
    gs.p11_pps_boost_per_clickpower = 0.0
    gs.p12_autobuy_upg4_unlocked = False
    gs.crystalline_completion_bonus = 1.0
    gs.p14_upg2_boost = 1.0
    gs.p16_cost_reduction_factor = 1.0
    gs.p17_upg1_boost_to_rank4 = 1.0
    gs.p18_passive_click_rate = 0.0
    gs.p19_boost_multiplier = 1.0
    gs.p20_limit_break_active = False
    gs.p24_purify_cost_divisor = 1.0
    gs.upgrade1_max = 25
    gs.upgrade2_max = 10
    gs.upgrade3_max = 10
    gs.upgrade4_max = 5
    reset_for_purify()
    gs.crystalline_unlocked = True

def reset_for_ascension():
    global points, clicks, game_state
    gs = game_state
    logging.info("Resetting for Ascension...")
    points = 0.0
    clicks = 0.0
    gs.crystalline_times = 0
    gs.crystalline_cost = 2.5e8
    gs.cry1_booster = 1.0
    gs.cry1_upg4_unlocked = False
    gs.cry2_booster = 1.0
    gs.cry3_unlocked = False
    gs.cry4_unlocked = False
    gs.crystalline_5_complete = False
    gs.upgrade5_complete = False
    gs.upgrade6_complete = False
    gs.upgrade7_level = 0
    gs.upgrade7_cost = 1e6
    gs.upgrade7_max = 50
    gs.upgrade8_level = 0
    gs.upgrade8_cost = 1e9
    gs.upgrade8_max = 100
    gs.click_power = 1.0
    reset_for_crystalline()
    gs.ascension_unlocked = True

def purify():
    global points, game_state
    gs = game_state
    current_max = gs.max_purify
    can_purify, reason = False, "Max Reached"
    if gs.purify_times < current_max:
        if gs.purify_times < 10: can_purify=True
        elif gs.purify_times < 15:
            can_purify=gs.upgrade5_complete
            reason="Requires U5"
        else:
            can_purify=gs.crystalline_5_complete
            reason="Requires C5"
    if not can_purify:
        logging.warning(f"Cannot Purify: {reason}")
        return
    cost = gs.purify_cost / gs.p24_purify_cost_divisor
    if points < cost:
        logging.warning(f"Need {format_number(cost)} points.")
        return
    points -= cost
    apply_purification_effects(gs.purify_times)
    prev_times = gs.purify_times
    gs.purify_times += 1
    reset_for_purify()
    gs.purify_cost = round(gs.purify_cost * (3.0 + prev_times), 2)
    logging.info(f"Purified! Times: {gs.purify_times}/{current_max}. Next Base Cost: {format_number(gs.purify_cost)}")
    recalculate_derived_values()

def crystalline():
    global points, game_state
    gs = game_state
    if not gs.crystalline_unlocked:
        logging.warning("Crystalline locked.")
        return
    eff_max = 5 if gs.purify_times >= 15 else gs.max_crystalline
    if gs.crystalline_times >= eff_max:
        logging.warning(f"Max Crystallines reached.")
        return
    if gs.crystalline_times == 4 and gs.purify_times < 15:
        logging.warning("Need P15 for C5.")
        return
    cost = gs.crystalline_cost
    if points < cost:
        logging.warning(f"Need {format_number(cost)} points.")
        return
    points -= cost
    apply_crystalline_effects(gs.crystalline_times + 1)
    gs.crystalline_times += 1
    reset_for_crystalline()
    costs = {0: 2.5e8, 1: 1e12, 2: 1e15, 3: 1e18, 4: 1e21}
    gs.crystalline_cost = costs.get(gs.crystalline_times, float('inf'))
    logging.info(f"Crystallized! Times: {gs.crystalline_times}/{eff_max}. Next cost: {format_number(gs.crystalline_cost)}")
    recalculate_derived_values()

def ascend():
    global points, game_state
    gs = game_state
    if not gs.ascension_unlocked:
        logging.warning("Ascension locked.")
        return
    cost = gs.ascension_cost
    if points < cost:
        logging.warning(f"Need {format_number(cost)} points.")
        return
    stardust_gain = 0
    relic_sd_boost = RELICS_DATA['relic_sd_gain']['effect'](gs.relic_levels.get('relic_sd_gain', 0))
    try:
        if points >= cost:
            log_arg = max(1, points / cost + 1)
            stardust_gain = ma.floor(0.1 * ma.log10(log_arg) * ma.sqrt(gs.crystalline_times + 1) * gs.challenge_stardust_boost * relic_sd_boost)
            stardust_gain = max(1, stardust_gain)
    except ValueError: pass
    if stardust_gain <= 0:
        logging.warning("Cannot ascend for 0 Stardust.")
        return
    logging.info(f"Ascending for {format_number(stardust_gain)} Stardust!")
    gs.stardust += stardust_gain
    gs.ascension_count += 1
    gs.ascension_cost *= 100
    reset_for_ascension()
    recalculate_derived_values()

# --- Clicking Action ---
def click_power_action():
    global clicks, game_state
    gs = game_state
    if not gs.cry4_unlocked: return
    relic_clk_mult = RELICS_DATA['relic_clk_mult']['effect'](gs.relic_levels.get('relic_clk_mult', 0))
    base_click = gs.click_power * gs.astral_clicks_boost * gs.click_point_scaling_bonus * relic_clk_mult
    final_click = base_click * (gs.click_crit_multiplier if random.random() < gs.click_crit_chance else 1.0)
    clicks += final_click

# --- Autobuyer Logic ---
def autobuy_tick():
    global game_state
    gs = game_state
    try:
        if gs.cry3_unlocked:
            upgrade1()
            upgrade2()
            upgrade3()
        if gs.p12_autobuy_upg4_unlocked: upgrade4()
    except Exception as e: logging.error(f"Error in autobuy_tick: {e}", exc_info=True)

def autobuy_thread_func():
    logging.info("Autobuyer started.")
    gs=game_state
    while is_running:
        if gs.cry3_unlocked or gs.p12_autobuy_upg4_unlocked: autobuy_tick()
        time.sleep(0.1)
    logging.info("Autobuyer finished.")

def start_autobuy_thread_if_needed():
    global autobuy_thread, game_state
    gs = game_state
    if gs.cry3_unlocked or gs.p12_autobuy_upg4_unlocked:
        if not autobuy_thread or not autobuy_thread.is_alive():
            logging.info("Starting autobuy thread.")
            autobuy_thread = th.Thread(target=autobuy_thread_func, daemon=True)
            autobuy_thread.start()

# --- Astral Upgrades ---
def buy_astral_upgrade(upgrade_key):
    global game_state
    gs = game_state
    cost = gs.astral_costs.get(upgrade_key, float('inf'))
    if gs.stardust >= cost:
        gs.stardust -= cost
        lvl = gs.astral_levels.get(upgrade_key, 0) + 1
        gs.astral_levels[upgrade_key] = lvl
        logging.info(f"Bought Astral {upgrade_key} (Lvl {lvl}) for {cost} Stardust.")
        if upgrade_key == 'points': gs.astral_points_boost *= 1.10
        elif upgrade_key == 'clicks': gs.astral_clicks_boost *= 1.15
        elif upgrade_key == 'purify': gs.astral_purify_boost *= 1.05
        elif upgrade_key == 'upg1_start': gs.astral_upg1_start_level += 1
        gs.astral_costs[upgrade_key] = round(cost * 1.5 + lvl, 0)
        recalculate_derived_values()
    else: logging.warning(f"Need {format_number(cost - gs.stardust)} more Stardust.")

# --- Relic Buying Function ---
def buy_relic(relic_id):
    global game_state
    gs = game_state
    if relic_id not in RELICS_DATA:
        logging.warning(f"Unknown relic: {relic_id}")
        return
    data = RELICS_DATA[relic_id]
    lvl = gs.relic_levels.get(relic_id, 0)
    max_lvl = data.get('max_level')
    if max_lvl is not None and lvl >= max_lvl:
        logging.info(f"Relic '{data['name']}' maxed.")
        return
    cost = round(data['cost_base'] * (data['cost_scale'] ** lvl))
    if gs.stardust >= cost:
        gs.stardust -= cost
        gs.relic_levels[relic_id] = lvl + 1
        logging.info(f"Bought Relic '{data['name']}' (Lvl {lvl + 1}) for {cost} Stardust.")
        recalculate_derived_values()
    else: logging.warning(f"Need {format_number(cost - gs.stardust)} SD for '{data['name']}'.")

# --- Challenges ---
def check_challenges():
    global game_state
    gs = game_state
    changed = False
    for cid, chal in CHALLENGES.items():
        lvl = gs.challenge_completions.get(cid, 0)
        max_lvl = chal.get('max_completions')
        if max_lvl is not None and lvl >= max_lvl: continue
        req = chal['requirement_func'](gs, lvl)
        if chal['check_func'](gs, req):
            logging.info(f"Chal Completed: {chal['desc_base']} (Lvl {lvl + 1})")
            chal['apply_reward_func'](gs)
            gs.challenge_completions[cid] = lvl + 1
            changed = True
    if changed: recalculate_derived_values()

# --- Save/Load ---
def save_game():
    global points, clicks, game_state
    logging.info("Saving game...")
    gs = game_state
    try:
        save_data = {k: getattr(gs, k) for k in gs.__dict__ if not k.startswith('_')}
        save_data.update({"version": SAVE_VERSION, "points": points, "clicks": clicks})
        save_data["last_save_time"] = time.time()
        gs.last_save_time = save_data["last_save_time"]
        save_data['challenge_completions'] = repr(gs.challenge_completions)
        save_data['astral_levels'] = repr(gs.astral_levels)
        save_data['astral_costs'] = repr(gs.astral_costs)
        save_data['relic_levels'] = repr(gs.relic_levels) # <<< SAVE RELICS
        json_string = json.dumps(save_data, separators=(',', ':'))
        encoded_bytes = base64.b64encode(json_string.encode('utf-8'))
        encoded_string = encoded_bytes.decode('utf-8')
        with open(SAVE_FILE, "w") as f: f.write(encoded_string)
        logging.info(f"Game saved.")
    except Exception as e: logging.error(f"Save failed: {e}", exc_info=True)

def autosave_thread_func():
    logging.info("Autosave started.")
    while is_running:
        time.sleep(AUTOSAVE_INTERVAL_S)
        save_game()
    logging.info("Autosave finished.")

def load_game():
    global points, clicks, game_state, is_running
    gs = game_state
    if not os.path.exists(SAVE_FILE):
        logging.info("No save file.")
        recalculate_derived_values()
        return
    logging.info(f"Loading game...")
    try:
        with open(SAVE_FILE, "r") as f: encoded_string = f.read()
        decoded_bytes = base64.b64decode(encoded_string.encode('utf-8'))
        json_string = decoded_bytes.decode('utf-8')
        loaded_data = json.loads(json_string)

        loaded_version = loaded_data.get("version", 0)
        if loaded_version != SAVE_VERSION:
            logging.warning(f"Save version mismatch ({loaded_version} vs {SAVE_VERSION}). Resetting.")
            gs = GameState()
            points = 0.0
            clicks = 0.0
            recalculate_derived_values()
            save_game()
            return

        def safe_eval(val_str, default):
            try: return ast.literal_eval(val_str)
            except: return default

        def get_val(k, df, tp): # key, default, type
            v = loaded_data.get(k)
            if v is None: return df
            try:
                if tp == bool: return str(v).lower() == 'true'
                if tp == int and isinstance(v, float): return int(v)
                if tp == float and isinstance(v, int): return float(v)
                if k in ['challenge_completions', 'astral_levels', 'astral_costs', 'relic_levels'] and isinstance(v, str): # <<< LOAD RELICS
                    ev = safe_eval(v, df)
                    return ev if isinstance(ev, dict) else df
                if isinstance(v, tp): return v
                if tp == dict and v is None: return {}
                return tp(v)
            except: return df

        points = get_val("points", 0.0, float)
        clicks = get_val("clicks", 0.0, float)
        last_save = get_val("last_save_time", time.time(), float)
        default_gs = GameState()
        for key in default_gs.__dict__:
            if key.startswith('_'): continue
            dv = getattr(default_gs, key)
            _t = type(dv)
            if key in ['challenge_completions', 'astral_levels', 'astral_costs', 'relic_levels']: _t = dict # <<< LOAD RELICS
            elif isinstance(dv, set): _t = set
            elif isinstance(dv, list): _t = list

            if key in loaded_data:
                lv = get_val(key, dv, _t)
                if _t == dict and not isinstance(lv, dict):
                    logging.warning(f"Load fail '{key}', using default.")
                    lv = dv
                setattr(gs, key, lv)
            else: setattr(gs, key, dv) # Set default for missing keys

        time_offline = max(0, time.time() - last_save)
        if time_offline > 5:
            logging.info("Calculating offline progress...")
            recalculate_derived_values()
            off_pps = point_per_second * 0.5
            off_pts = off_pps * time_offline
            off_cps = gs.auto_clicks_per_sec * 0.5
            off_clicks = off_cps * time_offline
            points += off_pts
            clicks += off_clicks
            logging.info(f"Offline: {time_offline:.1f}s. Gained ~{format_number(off_pts)} pts, ~{format_number(off_clicks)} clicks.")
        gs.last_save_time = time.time()
        logging.info("Save loaded.")
        recalculate_derived_values()

    except Exception as e:
        logging.error(f"Load failed: {e}", exc_info=True)
        logging.info("Starting new game.")
        gs = GameState()
        points = 0.0
        clicks = 0.0
        recalculate_derived_values()
        save_game()

# --- UI Update Function ---
pointlabel=None
ppslabel=None
clicklabel=None
stardustlabel=None
upgrade1costlabel=None
upgrade1explainlabel=None
button1=None
upgrade2costlabel=None
upgrade2explainlabel=None
button2=None
upgrade3costlabel=None
upgrade3explainlabel=None
button3=None
upgrade4costlabel=None
upgrade4explainlabel=None
button4=None
upgrade5costlabel=None
upgrade5explainlabel=None
button5=None
upgrade6costlabel=None
upgrade6explainlabel=None
button6=None
upgrade7costlabel=None
upgrade7explainlabel=None
button7=None
upgrade8costlabel=None
upgrade8explainlabel=None
button8=None
purificationlabel=None
purificationbutton=None
crystalinelabel=None
crystalinebutton=None
ascensionlabel=None
ascensionbutton=None
clickbutton=None
astral_buttons={}
challenge_labels={}
relic_widgets = {}

def update_button_style(button, state):
    if not button or not isinstance(button, ttk.Button): return
    try:
        style = "primary-outline"
        tk_state = tk.NORMAL
        if state == "maxed":
            style = "danger-outline"
            tk_state = tk.DISABLED
        elif state == "buyable": style = "success-outline"
        elif state == "locked":
            style = "secondary-outline"
            tk_state = tk.DISABLED
        button.configure(bootstyle=style, state=tk_state)
    except tk.TclError: pass # Ignore errors if widget destroyed during update
    except Exception as e: logging.error(f"Button style error: {e}")

def updateui():
    global points, clicks, point_per_second, game_state, window, is_running
    gs = game_state
    try:
        if not is_running: return

        # --- Update Top Labels ---
        if pointlabel: pointlabel.configure(text=f"Points: {format_number(points)}")
        if ppslabel: ppslabel.configure(text=f"PPS: {format_number(point_per_second)}")
        if clicklabel: clicklabel.configure(text=f"Clicks: {format_number(clicks)}")
        if stardustlabel: stardustlabel.configure(text=f"Stardust: {format_number(gs.stardust)}")

        # --- Prestige Tab ---
        if purificationlabel and purificationbutton:
            current_max = gs.max_purify
            next_lvl = gs.purify_times + 1
            can, reason, desc = False, "Max", ""
            if gs.purify_times < current_max:
                if next_lvl <= 10:
                    can=True
                    reason=""
                elif next_lvl <= 15:
                    can=gs.upgrade5_complete
                    reason="Requires U5"
                else:
                    can=gs.crystalline_5_complete
                    reason="Requires C5"

                desc = PURIFY_DESCRIPTIONS[gs.purify_times] if gs.purify_times<len(PURIFY_DESCRIPTIONS) else f"P{next_lvl}"
                if not can and reason!="Max": desc=f"({reason}) {desc}"
                cost = gs.purify_cost/gs.p24_purify_cost_divisor
                purificationlabel.configure(text=f"Purify {next_lvl}/{current_max}: {desc}\nCost: {format_number(cost)}")
                status = "buyable" if (can and points>=cost) else ("locked" if not can else "default")
                update_button_style(purificationbutton, status)
            else:
                purificationlabel.configure(text=f"Max Purifications ({gs.purify_times}/{current_max})")
                update_button_style(purificationbutton,"maxed")

        if crystalinelabel and crystalinebutton:
            eff_max = 5 if gs.purify_times>=15 else gs.max_crystalline
            next_lvl = gs.crystalline_times + 1
            can, reason, desc = True, "", ""
            if not gs.crystalline_unlocked: can,reason=False,"Req P10"
            elif gs.crystalline_times >= eff_max: can,reason=False,"Max"
            elif gs.crystalline_times==4 and gs.purify_times<15: can,reason=False,"Req P15"

            if reason=="Req P10":
                crystalinelabel.configure(text="Locked (Req P10)")
                update_button_style(crystalinebutton,"locked")
            elif reason=="Max":
                crystalinelabel.configure(text=f"Max Crystallines ({gs.crystalline_times}/{eff_max})")
                update_button_style(crystalinebutton,"maxed")
            else:
                desc = CRYSTALLINE_DESCRIPTIONS[gs.crystalline_times] if gs.crystalline_times<len(CRYSTALLINE_DESCRIPTIONS) else f"C{next_lvl}"
                if not can and reason: desc = f"({reason}) {desc}"
                cost=gs.crystalline_cost
                crystalinelabel.configure(text=f"Crystalline {next_lvl}/{eff_max}: {desc}\nCost: {format_number(cost)}")
                status = "buyable" if (can and points>=cost) else ("locked" if not can else "default")
                update_button_style(crystalinebutton,status)

        # --- Ascension Tab (Astrals) ---
        if ascensionlabel and ascensionbutton:
            can, reason, desc = True, "", ""
            sd_preview=0
            if not gs.ascension_unlocked: can,reason=False,"Req C5"
            else:
                try:
                    if points >= gs.ascension_cost:
                        log_arg=max(1, points/gs.ascension_cost+1)
                        r_boost=RELICS_DATA['relic_sd_gain']['effect'](gs.relic_levels.get('relic_sd_gain',0))
                        sd_preview = ma.floor(0.1*ma.log10(log_arg)*ma.sqrt(gs.crystalline_times+1)*gs.challenge_stardust_boost*r_boost)
                        sd_preview=max(0,sd_preview)
                except ValueError: pass
            desc = f"Reset ALL non-Astral/Relic progress for Stardust.\nGain approx: {format_number(sd_preview)}"
            if not can: desc = f"({reason}) {desc}"
            cost = gs.ascension_cost
            ascensionlabel.configure(text=f"Ascend {gs.ascension_count+1}: {desc}\nCost: {format_number(cost)} Points")
            status = "buyable" if (can and points>=cost and sd_preview>0) else ("locked" if not can else "default")
            update_button_style(ascensionbutton,status)
            for k, btn in astral_buttons.items():
                if k.endswith('_label'): continue
                cost=gs.astral_costs.get(k,float('inf'))
                update_button_style(btn, "buyable" if gs.stardust>=cost else "default")
                lbl_w = astral_buttons.get(k+'_label')
                if lbl_w:
                    lvl=gs.astral_levels.get(k,0)
                    dsc=ASTRAL_UPGRADE_DESCRIPTIONS.get(k,"???")
                    lbl_w.configure(text=f"{dsc}\nLevel: {lvl} | Cost: {format_number(cost)} Stardust")

        # --- Relics Tab ---
        if gs.ascension_unlocked:
            for rid, data in RELICS_DATA.items():
                widgets = relic_widgets.get(rid)
                if not widgets: continue
                name_lbl, desc_lbl, level_lbl, cost_lbl, buy_btn = widgets
                lvl = gs.relic_levels.get(rid, 0)
                max_lvl = data.get('max_level')
                is_max = (max_lvl is not None and lvl >= max_lvl)
                level_text = f"Level: {lvl}" + (f"/{max_lvl}" if max_lvl is not None else "")
                level_lbl.configure(text=level_text)
                if is_max:
                    cost_lbl.configure(text="Cost: MAX")
                    update_button_style(buy_btn, "maxed")
                else:
                    cost=round(data['cost_base']*(data['cost_scale']**lvl))
                    cost_lbl.configure(text=f"Cost: {format_number(cost)} SD")
                    status="buyable" if gs.stardust>=cost else "default"
                    update_button_style(buy_btn,status)

        # --- Upgrades Tab ---
        def fmt_max(v): return 'Inf' if ma.isinf(v) else int(v)
        if upgrade1costlabel: upgrade1costlabel.configure(text=f"Cost: {format_number(gs.upgrade1_cost)}")
        if upgrade1explainlabel: upgrade1explainlabel.configure(text=f"+1 Base Multi [{gs.upgrade1_level}/{fmt_max(gs.upgrade1_max)}]")
        if button1: update_button_style(button1, "maxed" if gs.upgrade1_level>=gs.upgrade1_max else ("buyable" if points>=gs.upgrade1_cost else "default"))
        if upgrade2costlabel: upgrade2costlabel.configure(text=f"Cost: {format_number(gs.upgrade2_cost)}")
        if upgrade2explainlabel:
            fact=get_upgrade2_factor(gs)
            upgrade2explainlabel.configure(text=f"Strength x{format_number(gs.multiplier_strength)} [{gs.upgrade2_level}/{fmt_max(gs.upgrade2_max)}] (x{fact:.2f})")
        if button2: update_button_style(button2, "maxed" if gs.upgrade2_level>=gs.upgrade2_max else ("buyable" if points>=gs.upgrade2_cost else "default"))
        if upgrade3costlabel: upgrade3costlabel.configure(text=f"Cost: {format_number(gs.upgrade3_cost)}")
        if upgrade3explainlabel: upgrade3explainlabel.configure(text=f"PPS Exp ^{gs.pps_exponent:.3f} [{gs.upgrade3_level}/{fmt_max(gs.upgrade3_max)}]")
        if button3: update_button_style(button3, "maxed" if gs.upgrade3_level>=gs.upgrade3_max else ("buyable" if points>=gs.upgrade3_cost else "default"))
        if button4:
            lock=not gs.cry1_upg4_unlocked
            if upgrade4costlabel: upgrade4costlabel.configure(text="Locked" if lock else f"Cost: {format_number(gs.upgrade4_cost)}")
            if upgrade4explainlabel: upgrade4explainlabel.configure(text="???" if lock else f"+1 Max Upg3 [{gs.upgrade4_level}/{fmt_max(gs.upgrade4_max)}]")
            status="locked" if lock else ("maxed" if gs.upgrade4_level>=gs.upgrade4_max else ("buyable" if points>=gs.upgrade4_cost else "default"))
            update_button_style(button4,status)

        # --- Clicking Tab ---
        if clickbutton:
            lock=not gs.cry4_unlocked
            crit=f" ({gs.click_crit_chance*100:.0f}% Crit, x{gs.click_crit_multiplier:.1f})" if gs.upgrade7_level>0 else ""
            relic_m=RELICS_DATA['relic_clk_mult']['effect'](gs.relic_levels.get('relic_clk_mult',0))
            click_v=gs.click_power*gs.astral_clicks_boost*gs.click_point_scaling_bonus*relic_m
            clickbutton.configure(text=f"Click! (+{format_number(click_v)}{crit})" if not lock else "Locked (Cry 4)", state=tk.NORMAL if not lock else tk.DISABLED)
        if button5:
            lock=not gs.cry4_unlocked
            req=1000.
            st,ct,et="locked","Locked","???"
            if not lock:
                if gs.upgrade5_complete: st,ct,et="maxed","Purchased",f"Max Purify: 15"
                else:
                    st="buyable" if clicks>=req else "default"
                    ct=f"Cost: {format_number(req)} Clicks"
                    et="Unlock P11-15"
                if upgrade5costlabel: upgrade5costlabel.configure(text=ct)
                if upgrade5explainlabel: upgrade5explainlabel.configure(text=et)
                update_button_style(button5,st)
        if button6:
            lock=not gs.cry4_unlocked
            req=1e5
            st,ct,et="locked","Locked","???"
            if not lock:
                if gs.upgrade6_complete: st,ct,et="maxed","Purchased","C5 Effects On"
                else:
                    st="buyable" if clicks>=req else "default"
                    ct=f"Cost: {format_number(req)} Clicks"
                    et="Enable C5 Effects"
                if upgrade6costlabel: upgrade6costlabel.configure(text=ct)
                if upgrade6explainlabel: upgrade6explainlabel.configure(text=et)
                update_button_style(button6,st)
        if button7:
            lock=not gs.cry4_unlocked
            st,ct,et="locked","Locked","???"
            if not lock:
                if gs.upgrade7_level>=gs.upgrade7_max: st,ct,et="maxed","MAXED",f"Crit: {gs.click_crit_chance*100:.0f}% x{gs.click_crit_multiplier:.1f}"
                else:
                    st="buyable" if clicks>=gs.upgrade7_cost else "default"
                    ct=f"Cost: {format_number(gs.upgrade7_cost)} Clicks"
                    et=f"Crit [{gs.upgrade7_level}/{fmt_max(gs.upgrade7_max)}]"
                if upgrade7costlabel: upgrade7costlabel.configure(text=ct)
                if upgrade7explainlabel: upgrade7explainlabel.configure(text=et)
                update_button_style(button7,st)
        if button8:
            lock=not gs.cry4_unlocked
            st,ct,et="locked","Locked","???"
            if not lock:
                auto_s=f"{gs.auto_clicks_per_sec:.2f}/s" if gs.upgrade8_level>0 else f"{gs.p18_passive_click_rate*100:.1f}% passive"
                if gs.upgrade8_level>=gs.upgrade8_max: st,ct,et="maxed","MAXED",f"Auto Click: {auto_s}"
                else:
                    st="buyable" if clicks>=gs.upgrade8_cost else "default"
                    ct=f"Cost: {format_number(gs.upgrade8_cost)} Clicks"
                    et=f"Auto Speed [{gs.upgrade8_level}/{fmt_max(gs.upgrade8_max)}]"
                if upgrade8costlabel: upgrade8costlabel.configure(text=ct)
                if upgrade8explainlabel: upgrade8explainlabel.configure(text=et)
                update_button_style(button8,st)

        # --- Challenges Tab ---
        for cid,lbl in challenge_labels.items():
            chal=CHALLENGES[cid]
            lvl=gs.challenge_completions.get(cid,0)
            max_l=chal.get('max_completions')
            is_mx=(max_l is not None and lvl>=max_l)
            req=chal['requirement_func'](gs,lvl)
            req_d=chal['requirement_desc_func'](req)
            rew_d=chal['reward_desc_func'](gs,lvl)
            cmp_s=f"({lvl}/{max_l})" if max_l is not None else f"({lvl})"
            lbl_txt=f"{chal['desc_base']} {cmp_s}\n{req_d} | {rew_d}"
            can=False
            if not is_mx:
                try: can=chal['check_func'](gs,req)
                except: pass
            style="success" if is_mx else ("info" if can else "default")
            lbl.configure(text=lbl_txt,bootstyle=style)

        # --- Reschedule ---
        if is_running: window.after(UPDATE_INTERVAL_MS, updateui)
    except tk.TclError:
        logging.warning("UI Update TclError.")
        is_running = False
    except Exception as e:
        logging.error(f"UI update error: {e}", exc_info=True)
        # Delay rescheduling slightly on error to prevent rapid error loops
        if is_running: window.after(UPDATE_INTERVAL_MS * 2, updateui)

# --- Admin Panel ---
admin_window = None
admin_widgets = {}
active_admin_threads = []

def log_to_admin_output_threadsafe(m):
    if admin_widgets.get('cmd_output') and window and is_running:
        try:
            window.after(0, lambda msg=m: log_to_admin_output(msg))
        except Exception: pass # Ignore if window/tk is gone

def _execute_single_command(cmd_str, log_out=True):
    global is_running
    if not cmd_str or not is_running: return None
    parts=cmd_str.split()
    cmd=parts[0].lower()
    args=parts[1:]
    res=None
    h=COMMAND_HANDLERS.get(cmd)
    if h:
        try:
            f=h['func']
            # Simplified logic for calling function
            res = f(args)
        except Exception as e:
            res=f"Exec Err '{cmd}': {e}"
            logging.error(f"Admin cmd error: {e}", exc_info=True)
    else:
        res=f"Unknown command: '{cmd}'."

    # Log result unless it's a background task or logging is off
    if log_out and res and h and h['func'] not in [cmd_wait, cmd_repeat, cmd_while]:
        log_to_admin_output_threadsafe(str(res))
    return res

def _evaluate_condition(cond_str):
    global points, clicks, game_state
    gs=game_state
    try:
        parts=cond_str.split()
        assert len(parts)==3
        var,op,val_str=parts[0].lower(),parts[1],parts[2]
        cur=None
        tp=None
        if var in globals(): cur=globals()[var]
        elif hasattr(gs,var): cur=getattr(gs,var)
        else: raise NameError(f"Var '{var}' not found")
        tp=type(cur)
        cmp=None
        if tp==bool: cmp=val_str.lower() in ['true','1','t','y']
        elif tp==int: cmp=int(float(val_str))
        elif tp==float: cmp=float(val_str)
        elif tp==str: cmp=val_str
        elif isinstance(cur,(int,float)):
            try: cmp=float(val_str)
            except: raise TypeError(f"Cannot compare num {tp.__name__} with '{val_str}'")
        else: raise TypeError(f"Unsupported type {tp.__name__}")

        if op=='==': return cur==cmp
        elif op=='!=': return cur!=cmp
        elif isinstance(cur,(int,float)) and isinstance(cmp,(int,float)):
            if op=='>': return cur>cmp
            elif op=='<': return cur<cmp
            elif op=='>=': return cur>=cmp
            elif op=='<=': return cur<=cmp
            else: raise ValueError(f"Unsupported op '{op}' for numbers")
        elif op in ['>','<','>=','<=']: raise TypeError(f"Op '{op}' needs numbers")
        else: raise ValueError(f"Unsupported op '{op}'")

    except Exception as e:
        log_to_admin_output_threadsafe(f"Cond Error: {e}")
        return False

def cmd_setvalue(args): # Applies buffs
    global points, clicks, game_state
    gs=game_state
    if len(args)!=2: return "Usage: set <var> <val>"
    var,val_str=args[0].lower(),args[1]
    tgt=None
    is_g=False
    cur=None
    old=None
    if var in globals():
        tgt=globals()
        is_g=True
        cur=tgt[var]
        old=cur
    elif hasattr(gs,var):
        tgt=gs
        cur=getattr(gs,var)
        old=cur
    else: return f"Error: Var '{var}' not found."
    tp=type(cur)
    new=None
    try:
        if tp==bool: new=val_str.lower() in ['true','1','t','y']
        elif tp==int: new=int(float(val_str))
        elif tp==float: new=float(val_str)
        elif tp==str: new=val_str
        elif tp in [dict,list,set]:
            new=ast.literal_eval(val_str)
            assert isinstance(new,tp)
        else: return f"Error: Unsupported type '{tp.__name__}'"
    except Exception as e: return f"Error parsing '{val_str}' for {tp.__name__}: {e}"

    if is_g: globals()[var]=new
    else: setattr(tgt,var,new)
    buff_msg=""
    if not is_g and var in ['purify_times','crystalline_times'] and isinstance(old,(int,float)) and isinstance(new,int) and new>old:
        try:
            old_i,new_i=int(old),int(new)
            if new_i>old_i:
                log_to_admin_output_threadsafe(f"ADMIN: Buffs {var} {old_i+1}..{new_i}")
                if var=='purify_times':
                    for i in range(old_i,new_i): apply_purification_effects(i)
                    buff_msg=" P buffs applied."
                elif var=='crystalline_times':
                    for i in range(old_i,new_i): apply_crystalline_effects(i+1)
                    buff_msg=" C buffs applied."
        except Exception as e:
            log_to_admin_output_threadsafe(f"Buff Error: {e}")
            logging.error(f"Buff Error: {e}",exc_info=True)

    needs_recalc = (buff_msg!="") or \
                   (not is_g and var not in ['last_save_time','admin_panel_active','total_playtime','challenge_completions','astral_levels','astral_costs','relic_levels']) or \
                   (is_g and var in ['points','clicks','stardust'])
    res=f"Set {var} to {new!r}."
    if needs_recalc:
        recalculate_derived_values()
        res+=" Recalculated."+buff_msg
    return res

def cmd_varinfo(args):
    global game_state
    gs=game_state
    if len(args)!=1: return "Usage: get <var>"
    var=args[0].lower()
    val=None
    tp=None
    if var in globals():
        val=globals().get(var)
        tp=type(val).__name__
    elif hasattr(gs,var):
        val=getattr(gs,var)
        tp=type(val).__name__
    else: return f"Error: Var '{var}' not found."
    return f"{var} ({tp}) = {val!r}"

def cmd_list(args):
    global points,clicks,point_per_second,game_state # Corrected pps variable name
    gs=game_state
    if len(args)==0:
        lines=["--- Game State ---"]
        for k,v in sorted(vars(gs).items()):
             if not k.startswith('_'): lines.append(f"  {k} ({type(v).__name__}) = {v!r}")
        lines.append("\n--- Globals ---")
        lines.append(f"  points={points!r}")
        lines.append(f"  clicks={clicks!r}")
        lines.append(f"  point_per_second={point_per_second!r}") # Corrected pps variable name
        lines.append(f"  is_running={is_running!r}")
        return "\n".join(lines)
    elif len(args)==1: return cmd_varinfo(args)
    else: return "Usage: list [<var>]"

def cmd_type(args):
    global game_state
    gs=game_state
    if len(args)!=1: return "Usage: type <var>"
    var=args[0].lower()
    tp=None
    if var in globals(): tp=type(globals().get(var)).__name__
    elif hasattr(gs,var): tp=type(getattr(gs,var)).__name__
    else: return f"Error: Var '{var}' not found."
    return f"Type of '{var}' is {tp}"

def cmd_limbrk(args):
    global game_state
    gs=game_state
    count=0
    logf=log_to_admin_output if th.current_thread() is th.main_thread() else log_to_admin_output_threadsafe
    targets=[]
    if not args or args[0].lower()=='all':
        targets=[k for k in gs.__dict__ if k.endswith('_max')]
    else:
        var=args[0].lower()
        tgt=None
        if var.startswith("upg") and var[3:].isdigit(): tgt=f"upgrade{var[3:]}_max"
        elif var.startswith("upgrade") and var[7:].isdigit(): tgt=f"{var}_max"
        elif f"{var}_max" in gs.__dict__: tgt=f"{var}_max"
        if tgt and hasattr(gs,tgt): targets.append(tgt)
        else: return f"Error: Cannot find _max var for '{args[0]}'."

    if not targets: return "No _max vars found."
    for t in targets:
        if hasattr(gs,t):
            try:
                if isinstance(getattr(gs,t),(int,float)):
                    setattr(gs,t,float('inf'))
                    count+=1
                else: logf(f"Warn: {t} not numeric")
            except Exception as e: logf(f"Error setting {t}: {e}")

    if count>0:
        recalculate_derived_values()
        return f"Set {count} max limits to inf. Recalculated."
    else: return "No limits changed."

def cmd_settype(args):
    global game_state
    gs=game_state
    if len(args)!=2: return "Usage: settype <var> <type>"
    var,t_str=args[0].lower(),args[1].lower()
    tgt=None
    is_g=False
    cur=None
    if var in globals():
        tgt=globals()
        is_g=True
        cur=tgt[var]
    elif hasattr(gs,var):
        tgt=gs
        cur=getattr(gs,var)
    else: return f"Error: Var '{var}' not found."
    new=None
    try:
        if t_str=='int': new=int(float(str(cur)))
        elif t_str=='float': new=float(str(cur))
        elif t_str=='str': new=str(cur)
        elif t_str=='bool': new=bool(cur)
        else: return f"Error: Unsupported type '{t_str}'."

        if is_g: globals()[var]=new
        else: setattr(tgt,var,new)

        needs_recalc=(not is_g and var not in ['last_save_time','admin_panel_active','total_playtime','challenge_completions','astral_levels','astral_costs','relic_levels']) or \
                     (is_g and var in ['points','clicks','stardust'])
        if needs_recalc: recalculate_derived_values()
        res = f"Set type of '{var}' to {t_str}. New: {new!r}."
        if needs_recalc: res += " Recalculated."
        return res

    except Exception as e: return f"Error converting '{var}' to {t_str}: {e}"

def cmd_buy(args): # Includes Relics
    global game_state, points # Need points for cost checks
    gs = game_state
    if len(args)<1 or len(args)>2: return "Usage: buy <id> [times=1]"
    id_str=args[0].lower()
    times=1
    if len(args)==2:
        try:
            times=int(args[1])
            assert times>0
        except: return "Error: Invalid times."

    funcs={'upg1':upgrade1,'upg2':upgrade2,'upg3':upgrade3,'upg4':upgrade4,'upg5':upgrade5,'upg6':upgrade6,'upg7':upgrade7,'upg8':upgrade8,
           'purify':purify,'crystalline':crystalline,'ascend':ascend}
    for k in ASTRAL_UPGRADE_DESCRIPTIONS: funcs[f'astral_{k}']=lambda k=k:buy_astral_upgrade(k)
    for k in RELICS_DATA: funcs[k]=lambda k=k:buy_relic(k) # Add relics

    func=funcs.get(id_str)
    if not func: return f"Error: Unknown ID '{id_str}'."

    bought=0
    for i in range(times):
        if not is_running: return f"Buy stopped after {bought} due to game closing."
        can=True
        reason="unknown"
        # --- Pre-checks ---
        if id_str.startswith('astral_'):
            key=id_str.split('_',1)[1]
            cost=gs.astral_costs.get(key,float('inf'))
            if gs.stardust<cost: can=False; reason="no SD"
        elif id_str in RELICS_DATA:
            lvl=gs.relic_levels.get(id_str,0)
            max_lvl=RELICS_DATA[id_str].get('max_level')
            if max_lvl is not None and lvl>=max_lvl: can=False; reason="relic max"
            else:
                cost=round(RELICS_DATA[id_str]['cost_base']*(RELICS_DATA[id_str]['cost_scale']**lvl))
                if gs.stardust<cost: can=False; reason="no SD"
        elif id_str=='purify':
            cost=gs.purify_cost/gs.p24_purify_cost_divisor
            cmax=gs.max_purify
            reach=False
            if gs.purify_times<cmax:
                if gs.purify_times<10: reach=True
                elif gs.purify_times<15: reach=gs.upgrade5_complete
                else: reach=gs.crystalline_5_complete
            if not reach: can=False; reason="max/unlock"
            elif points<cost: can=False; reason="no Pts"
        elif id_str=='crystalline':
            emax=5 if gs.purify_times>=15 else gs.max_crystalline
            if not gs.crystalline_unlocked: can=False; reason="locked"
            elif gs.crystalline_times>=emax: can=False; reason="maxed"
            elif gs.crystalline_times==4 and gs.purify_times<15: can=False; reason="needs P15"
            elif points<gs.crystalline_cost: can=False; reason="no Pts"
        elif id_str=='ascend':
            if not gs.ascension_unlocked: can=False; reason="locked"
            elif points<gs.ascension_cost: can=False; reason="no Pts"
            else:
                sd=0
                try:
                    log_a=max(1,points/gs.ascension_cost+1)
                    r_boost=RELICS_DATA['relic_sd_gain']['effect'](gs.relic_levels.get('relic_sd_gain',0))
                    sd=ma.floor(0.1*ma.log10(log_a)*ma.sqrt(gs.crystalline_times+1)*gs.challenge_stardust_boost*r_boost)
                except: pass
                if sd<=0: can=False; reason="0 gain"
        # --- End Pre-checks ---

        if not can:
            res=f"Bought {id_str} {bought}x."
            res+=f" Stopped ({reason})."
            return res
        try:
            func()
            bought+=1
        except Exception as e:
            res=f"Bought {id_str} {bought}x."
            res+=f" Err:{e}"
            return res

        # --- Post-checks basic upgs ---
        is_maxed=False
        if id_str=='upg1' and gs.upgrade1_level>=gs.upgrade1_max: is_maxed=True
        elif id_str=='upg2' and gs.upgrade2_level>=gs.upgrade2_max: is_maxed=True
        elif id_str=='upg3' and gs.upgrade3_level>=gs.upgrade3_max: is_maxed=True
        elif id_str=='upg4' and gs.upgrade4_level>=gs.upgrade4_max: is_maxed=True
        elif id_str=='upg5' and gs.upgrade5_complete: is_maxed=True
        elif id_str=='upg6' and gs.upgrade6_complete: is_maxed=True
        elif id_str=='upg7' and gs.upgrade7_level>=gs.upgrade7_max: is_maxed=True
        elif id_str=='upg8' and gs.upgrade8_level>=gs.upgrade8_max: is_maxed=True

        if is_maxed:
            res=f"Bought {id_str} {bought}x."
            res+=f" Stopped (maxed)."
            return res
            
    return f"Attempted {id_str} x{times}. Succeeded {bought}x."

def cmd_imprint(args):
    if len(args)!=2: return "Usage: imprint <var> <val>"
    res=cmd_setvalue(args)
    if "Error" not in res:
        save_game()
        return f"{res} Saved."
    else: return res

def cmd_stop(args):
    global is_running, window
    save=True
    if args and args[0].lower() in ['f','0','n']: save=False
    log_to_admin_output(f"Shutdown (Save:{save})...")
    if window:
        window.after(50,lambda s=save: on_closing(s))
        return "Shutdown initiated."
    else: return "Err: No window."

def cmd_offline(args):
    global points,clicks,game_state
    gs=game_state
    if len(args)!=1: return "Usage: offline <secs>"
    try:
        secs=float(args[0])
        assert secs>=0
        if secs==0: return "Simulated 0s."
        recalculate_derived_values()
        pps=point_per_second*0.5
        pts=pps*secs
        cps=gs.auto_clicks_per_sec*0.5
        cls=cps*secs
        points+=pts
        clicks+=cls
        return f"Simulated {secs:.1f}s. ~+{format_number(pts)} P, ~+{format_number(cls)} C."
    except Exception as e: return f"Offline err: {e}"

def cmd_recalc(args):
    recalculate_derived_values()
    return "Recalculated."

def cmd_reset(args):
    if len(args)!=1: return "Usage: reset <purify|cryst|asc|save>"
    type=args[0].lower()
    reset_done = False
    if type=="purify":
        reset_for_purify()
        reset_done = True
    elif type=="crystalline" or type=="cryst":
        reset_for_crystalline()
        reset_done = True
    elif type=="ascension" or type=="asc":
        reset_for_ascension()
        reset_done = True
    elif type=="save":
        try:
            if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
            return "Save deleted."
        except Exception as e: return f"Save del err: {e}"
    else: return "Unknown reset type."

    if reset_done: recalculate_derived_values()
    return f"{type.capitalize()} reset done."

def cmd_getchal(args):
    global game_state
    gs=game_state
    if len(args)!=1: return "Usage: getchal <id>"
    cid=args[0].lower()
    if cid not in CHALLENGES: return f"Error: Chal '{cid}' !found."
    chal=CHALLENGES[cid]
    lvl=gs.challenge_completions.get(cid,0)
    max_lvl=chal.get('max_completions')
    is_max=(max_lvl is not None and lvl>=max_lvl)
    req=chal['requirement_func'](gs,lvl)
    req_d=chal['requirement_desc_func'](req)
    rew_d=chal['reward_desc_func'](gs,lvl)
    comp_s=f"({lvl}/{max_lvl})" if max_lvl is not None else f"({lvl})"
    status="MAX"
    if not is_max:
        try:
            status = "OK" if chal['check_func'](gs,req) else "WIP"
        except: status = "ERR" # Handle check function errors
    return f"{cid.upper()}: {chal['desc_base']} {comp_s}\nReq: {req_d}\nRew: {rew_d} ({status})"

def cmd_setchal(args):
    global game_state
    gs=game_state
    logf=log_to_admin_output if th.current_thread() is th.main_thread() else log_to_admin_output_threadsafe
    if len(args)!=2: return "Usage: setchal <id> <count>"
    try:
        cid=args[0].lower()
        count=int(args[1])
        assert cid in CHALLENGES and count>=0
        gs.challenge_completions[cid]=count
        recalculate_derived_values() # Need to recalculate as rewards depend on completions
        logf("NOTE: Rewards recalc on next derived value calc.") # Clarify when reward takes effect
        return f"Set chal '{cid}' to {count}."
    except Exception as e: return f"SetChal Error: {e}"

def cmd_listchal(args):
    global game_state
    gs=game_state
    output="--- Challenges ---\n"
    if not CHALLENGES: return "None."
    for cid,chal in CHALLENGES.items():
        lvl=gs.challenge_completions.get(cid,0)
        max_lvl=chal.get('max_completions')
        comp_s=f"({lvl}/{max_lvl})" if max_lvl is not None else f"({lvl})"
        output+=f"{cid}: {chal['desc_base']} {comp_s}\n"
    return output[:-1] # Remove trailing newline

def cmd_resetchal(args): # Needs careful checking for reward reversal logic
    global game_state
    gs = game_state
    logf=log_to_admin_output if th.current_thread() is th.main_thread() else log_to_admin_output_threadsafe
    if len(args) != 1: return "Usage: resetchal <id|all>"
    target = args[0].lower()
    if target == 'all':
        sbr, cbr, cmr = 1.0, 1.0, 1.0
        # Calculate total reverse multipliers
        if 'c1' in gs.challenge_completions: sbr = (1.02 ** gs.challenge_completions.get('c1',0))
        if 'c2' in gs.challenge_completions: cbr = (1.01 ** gs.challenge_completions.get('c2',0))
        if 'c3' in gs.challenge_completions: cmr = (0.95 ** gs.challenge_completions.get('c3',0))

        gs.challenge_completions.clear()

        # Apply reverse multipliers carefully
        if sbr > 1.0: gs.challenge_stardust_boost /= sbr
        else: gs.challenge_stardust_boost = 1.0 # Reset if no boost or invalid

        if cbr > 1.0: gs.astral_clicks_boost /= cbr
        else: gs.astral_clicks_boost = 1.0 # Reset just in case

        if cmr > 0 and cmr < 1.0 : gs.rank3_cost_multiplier /= cmr
        else: gs.rank3_cost_multiplier = 1.0 # Reset if invalid

        recalculate_derived_values()
        logf("NOTE: Attempted reward reversal.")
        return "Reset all challenges."
    elif target in CHALLENGES:
        lvls = gs.challenge_completions.pop(target, 0)
        if lvls > 0:
            rev=False
            # Reverse individual challenge reward
            if target=='c1' and gs.challenge_stardust_boost > 0:
                try: gs.challenge_stardust_boost /= (1.02 ** lvls); rev=True
                except ZeroDivisionError: gs.challenge_stardust_boost = 1.0 # Handle potential division by zero if base was 0
            if target=='c2' and gs.astral_clicks_boost > 0:
                try: gs.astral_clicks_boost /= (1.01 ** lvls); rev=True
                except ZeroDivisionError: gs.astral_clicks_boost = 1.0
            if target=='c3' and gs.rank3_cost_multiplier != 0:
                try: gs.rank3_cost_multiplier /= (0.95 ** lvls); rev=True
                except ZeroDivisionError: gs.rank3_cost_multiplier = 1.0

            recalculate_derived_values()
            if rev: logf("NOTE: Attempted reward reversal.")
            return f"Reset chal '{target}' to 0."
        else: return f"Chal '{target}' already 0."
    else: return f"Error: Unknown chal ID '{target}'."

def cmd_completechal(args):
    global game_state
    gs=game_state
    if len(args)!=1: return "Usage: completechal <id>"
    cid=args[0].lower()
    if cid not in CHALLENGES: return f"Error: Chal ID '{cid}' not found."
    chal=CHALLENGES[cid]
    lvl=gs.challenge_completions.get(cid,0)
    max_lvl=chal.get('max_completions')
    if max_lvl is not None and lvl>=max_lvl: return f"Chal '{cid}' maxed."
    try:
        chal['apply_reward_func'](gs)
        gs.challenge_completions[cid]=lvl+1
        recalculate_derived_values()
        return f"Completed '{cid}' lvl {lvl+1}."
    except Exception as e:
        # Attempt to revert completion count if reward failed
        gs.challenge_completions[cid]=lvl
        return f"Error applying reward: {e}"

def cmd_help(args):
    text="Available Admin Commands:\n"
    h=COMMAND_HANDLERS
    # Use standard loop instead of walrus in list comprehension for clarity/compatibility
    mc=sorted([c for c,d in h.items() if 'alias' not in d])
    for c in mc:
        text += f"  {c:<15} {h[c]['help']}\n"
    als=sorted([c for c,d in h.items() if 'alias' in d])
    if als:
        text+="\nAliases:\n"
        for c in als:
             # Find the original command name for the alias
             original_cmd = "???" # Default if not found
             for k, v in h.items():
                 if v['func'] == h[c]['func'] and 'alias' not in v:
                     original_cmd = k
                     break
             text += f"  {c:<15} Alias for '{original_cmd}'\n"
    return text.strip()

def _wait_thread_func(s,tid):
    global active_admin_threads
    logf=log_to_admin_output_threadsafe
    logf(f"[{tid}] wait: {s}s...")
    try:
        time.sleep(s)
        logf(f"[{tid}] wait: Done.")
    except Exception as e: logf(f"[{tid}] wait Err: {e}")
    finally:
        if tid in active_admin_threads: active_admin_threads.remove(tid)

def cmd_wait(args):
    global active_admin_threads
    if len(args)!=1: return "Usage: wait <secs>"
    try:
        s=float(args[0])
        assert s>=0
        tid=random.randint(1000,9999)
        t=th.Thread(target=_wait_thread_func,args=(s,tid),daemon=True)
        active_admin_threads.append(tid)
        t.start()
        return f"wait: BG wait (TID {tid})."
    except: return "Error: Invalid time."

def _repeat_thread_func(t,cmd,tid):
    global active_admin_threads,is_running
    logf=log_to_admin_output_threadsafe
    logf(f"[{tid}] repeat {t}x '{cmd}'...")
    ex=0
    try:
        for i in range(t):
            if not is_running:
                logf(f"[{tid}] repeat: Cancelled.")
                break
            _execute_single_command(cmd,log_output=True)
            ex+=1
            time.sleep(0.05) # Small delay between repetitions
        logf(f"[{tid}] repeat: Finished {ex}/{t}.")
    except Exception as e: logf(f"[{tid}] repeat: Err rep {ex+1}: {e}")
    finally:
        if tid in active_admin_threads: active_admin_threads.remove(tid)

def cmd_repeat(args):
    global active_admin_threads
    if len(args)<2: return "Usage: repeat <times> <cmd...>" # Adjusted help slightly
    try:
        t=int(args[0])
        assert t>0
        cmd=" ".join(args[1:])
        if not cmd: return "Error: No cmd."
        tid=random.randint(1000,9999)
        thrd=th.Thread(target=_repeat_thread_func,args=(t,cmd,tid),daemon=True)
        active_admin_threads.append(tid)
        thrd.start()
        return f"repeat: BG repeat (TID {tid})."
    except: return "Error: Invalid times."

def _while_thread_func(cond,cmd,tid):
    global active_admin_threads,is_running
    logf=log_to_admin_output_threadsafe
    logf(f"[{tid}] while: '{cond}'...")
    it=0
    maxit=10000 # Safety break
    try:
        while is_running and _evaluate_condition(cond) and it<maxit:
            it+=1
            _execute_single_command(cmd,log_output=True)
            time.sleep(0.1) # Small delay to prevent busy-waiting

        if not is_running: logf(f"[{tid}] while: Cancelled.")
        elif it>=maxit: logf(f"[{tid}] while: Max iters.")
        else: logf(f"[{tid}] while: Cond false. Finished {it} iters.")

    except Exception as e:
        logf(f"[{tid}] while: Err iter {it+1}: {e}")
        logging.error(f"[{tid}] while: {e}",exc_info=True)
    finally:
        if tid in active_admin_threads: active_admin_threads.remove(tid)

def cmd_while(args):
    global active_admin_threads
    if len(args)<4: return "Usage: while <var op val> <cmd...>"
    try:
        cond=" ".join(args[0:3])
        cmd=" ".join(args[3:])
        init=_evaluate_condition(cond)
        # Check if initial condition evaluation returned error (False but logged)
        if not isinstance(init,bool): return f"Error: Invalid initial condition check."
        if not cmd: return "Error: No cmd."
        tid=random.randint(1000,9999)
        thrd=th.Thread(target=_while_thread_func,args=(cond,cmd,tid),daemon=True)
        active_admin_threads.append(tid)
        thrd.start()
        return f"while: BG loop (TID {tid}). Init: {init}."
    except Exception as e: return f"Error setting up while: {e}"

def cmd_setrelic(args):
    global game_state
    gs = game_state
    if len(args) != 2: return "Usage: setrelic <id> <lvl>"
    rid, lvl_s = args[0].lower(), args[1]
    if rid not in RELICS_DATA: return f"Error: Unknown relic '{rid}'."
    try:
        lvl = int(lvl_s)
        assert lvl >= 0
    except: return "Error: Lvl must be non-neg int."
    max_l = RELICS_DATA[rid].get('max_level')
    if max_l is not None and lvl > max_l: return f"Error: Max lvl {max_l}."
    gs.relic_levels[rid] = lvl
    recalculate_derived_values()
    return f"Set relic '{rid}' to {lvl}. Recalculated."

def cmd_listrelics(args):
    global game_state
    gs = game_state
    output = "--- Relics ---\n"
    if not RELICS_DATA: return "No relics."
    for rid, data in RELICS_DATA.items():
        lvl=gs.relic_levels.get(rid,0)
        max_l=data.get('max_level')
        l_str=f"({lvl}/{max_l})" if max_l is not None else f"({lvl})"
        output += f"{rid} [{data['name']}]: {l_str}\n"
    return output[:-1] # Remove trailing newline

def cmd_resetrelics(args):
    global game_state
    gs=game_state
    gs.relic_levels.clear()
    recalculate_derived_values()
    return "Relic levels reset."

COMMAND_HANDLERS = {
    'set': {'func': cmd_setvalue, 'help': '<var> <val> - Set variable (applies prestige buffs)'},
    'get': {'func': cmd_varinfo, 'help': '<var> - Get variable info (value & type)'},
    'type': {'func': cmd_type, 'help': '<var> - Get variable type'},
    'list': {'func': cmd_list, 'help': '[<var>] - List all vars or info for one var'},
    'limbrk': {'func': cmd_limbrk, 'help': '<upgX|name|all> - Set _max level(s) to infinity'},
    'settype': {'func': cmd_settype, 'help': '<var> <type> - Attempt type conversion'},
    'buy': {'func': cmd_buy, 'help': '<id> [times] - Buy upg/action/relic X times'},
    'imprint': {'func': cmd_imprint, 'help': '<var> <val> - Set value, apply buffs, save'},
    'stop': {'func': cmd_stop, 'help': "[save=T] - Stop game ('stop f' to skip save)"},
    'offline': {'func': cmd_offline, 'help': '<secs> - Simulate offline time (50% gains)'},
    'recalc': {'func': cmd_recalc, 'help': '- Force recalculation of derived stats'},
    'reset': {'func': cmd_reset, 'help': '<type> - Reset progress (purify|cryst|asc|save)'},
    'help': {'func': cmd_help, 'help': '- Show this help message'},
    'getchal': {'func': cmd_getchal, 'help': '<id> - Get challenge details'},
    'setchal': {'func': cmd_setchal, 'help': '<id> <count> - Set challenge completion count'},
    'listchal': {'func': cmd_listchal, 'help': '- List all challenges and completions'},
    'resetchal': {'func': cmd_resetchal, 'help': '<id|all> - Reset challenge completions'},
    'completechal': {'func': cmd_completechal, 'help': '<id> - Force complete next level of challenge'},
    'wait': {'func': cmd_wait, 'help': '<secs> - Pause command execution (background)'},
    'repeat': {'func': cmd_repeat, 'help': '<times> <cmd...> - Repeat command (background)'},
    'while': {'func': cmd_while, 'help': '<var op val> <cmd...> - Loop command while condition true'},
    'setrelic': {'func': cmd_setrelic, 'help': '<id> <level> - Set relic level'},
    'listrelics': {'func': cmd_listrelics, 'help': '- List all relics and levels'},
    'resetrelics': {'func': cmd_resetrelics, 'help': '- Reset all relic levels to 0'},
    # Aliases
    'setvalue': {'func': cmd_setvalue, 'help': 'Alias for set', 'alias': True},
    'varinfo': {'func': cmd_varinfo, 'help': 'Alias for get', 'alias': True},
}

def admin_execute_command(event=None):
    if not DEVELOPER_MODE or not admin_widgets.get('cmd_input'): return
    cmd_text=admin_widgets['cmd_input'].get().strip()
    if not cmd_text: return
    admin_widgets['cmd_input'].delete(0,tk.END)
    log_to_admin_output(f"> {cmd_text}")
    res=_execute_single_command(cmd_text,log_output=False) # Execute handles logging normally now
    if res: log_to_admin_output(res)

def log_to_admin_output(msg):
    if th.current_thread() is not th.main_thread():
        log_to_admin_output_threadsafe(msg)
        return
    if admin_widgets.get('cmd_output') and window and window.winfo_exists():
        try:
            out=admin_widgets['cmd_output']
            s=out.cget("state")
            out.configure(state=tk.NORMAL)
            out.insert(tk.END, str(msg)+"\n")
            out.configure(state=s)
            out.see(tk.END)
        except Exception: pass # Ignore if widget/window gone

def open_admin_panel():
    global admin_window, admin_widgets, game_state # Added game_state
    gs=game_state
    if not DEVELOPER_MODE: return
    if admin_window and admin_window.winfo_exists():
        try:
            admin_window.lift()
            return
        except: admin_window=None # Reset if error lifting

    gs.admin_panel_active=True
    admin_window=ttk.Toplevel(window)
    admin_window.title("Admin")
    admin_window.geometry("600x600")
    admin_window.protocol("WM_DELETE_WINDOW",on_admin_close)

    fr=ttk.Frame(admin_window,padding=10)
    fr.pack(expand=True,fill=tk.BOTH)
    fr.grid_rowconfigure(0,weight=1)
    fr.grid_columnconfigure(0,weight=1)

    out=scrolledtext.ScrolledText(fr,height=20,wrap=tk.WORD,state=tk.DISABLED,font=("Consolas",10))
    out.grid(row=0,column=0,sticky='nsew',padx=5,pady=5)
    admin_widgets['cmd_output']=out

    inp=ttk.Entry(fr,font=("Consolas",10))
    inp.grid(row=1,column=0,sticky='ew',padx=5,pady=(5,10))
    admin_widgets['cmd_input']=inp
    inp.bind("<Return>",admin_execute_command)
    inp.focus_set()

    log_to_admin_output("Admin console initialized.")

def on_admin_close():
    global admin_window, admin_widgets, game_state # Added admin_widgets and game_state
    gs=game_state
    if admin_window:
        try: admin_window.destroy()
        except: pass # Ignore errors during destroy
    admin_window=None
    admin_widgets.clear() # Clear widget references
    gs.admin_panel_active=False
    logging.info("Admin closed.")

def admin_recalculate(): cmd_recalc([]) # Simple wrapper

# ==============================================================================
#                           UI SETUP
# ==============================================================================
window = ttk.Window(themename="darkly")
window.title("Ordinal Ascent")
window.geometry("1000x600")
window.grid_rowconfigure(0, weight=1)
window.grid_columnconfigure(0, weight=1)

notebook = ttk.Notebook(window, bootstyle="primary")
notebook.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

# Create Frames
prestige_frame = ttk.Frame(notebook, padding=(20, 10))
upgrades_frame = ttk.Frame(notebook, padding=(20, 10))
clicking_frame = ttk.Frame(notebook, padding=(20, 10))
ascension_frame = ttk.Frame(notebook, padding=(20, 10))
relics_frame = ttk.Frame(notebook, padding=(20,10))
challenges_frame = ttk.Frame(notebook, padding=(20, 10))

# Configure Frame Grids
prestige_frame.grid_columnconfigure((0,3), weight=1) # Allow labels to expand
upgrades_frame.grid_columnconfigure(1, weight=1) # Allow labels to expand
upgrades_frame.grid_columnconfigure(3, weight=0) # Buttons fixed size
clicking_frame.grid_columnconfigure(1, weight=1) # Allow labels to expand
clicking_frame.grid_rowconfigure(1, weight=1) # Make click button expand vertically
ascension_frame.grid_columnconfigure(0, weight=1) # Allow labels/buttons to expand
relics_frame.grid_columnconfigure(1, weight=1) # Allow desc labels to expand
challenges_frame.grid_columnconfigure(0, weight=1) # Allow labels to expand

# Add Frames to Notebook
notebook.add(prestige_frame, text=" Prestige ")
notebook.add(upgrades_frame, text=" Upgrades ")
notebook.add(clicking_frame, text=" Clicking ")
notebook.add(ascension_frame, text=" Ascension ")
notebook.add(relics_frame, text=" Relics ")
notebook.add(challenges_frame, text=" Challenges ")

# --- UI Helper Functions ---
def create_label(parent, text, row, col, **kwargs):
    # Extract grid options
    grid_opts = {k: kwargs.pop(k) for k in list(kwargs.keys()) if k in ['sticky', 'padx', 'pady', 'columnspan', 'rowspan']}
    grid_opts.setdefault('sticky', 'w') # Default stick to west
    grid_opts.setdefault('padx', 5)
    grid_opts.setdefault('pady', 2)
    # Create label
    lbl = ttk.Label(parent, text=text, **kwargs)
    lbl.grid(row=row, column=col, **grid_opts)
    return lbl

def create_button(parent, text, command, row, col, **kwargs):
    # Extract grid options
    grid_opts = {k: kwargs.pop(k) for k in list(kwargs.keys()) if k in ['sticky', 'padx', 'pady', 'columnspan', 'rowspan']}
    grid_opts.setdefault('sticky', 'ew') # Default stick east-west
    grid_opts.setdefault('padx', 5)
    grid_opts.setdefault('pady', 5)
    # Create button
    bootstyle = kwargs.pop('bootstyle', 'primary-outline')
    width = kwargs.pop('width', 10) # Default width
    btn = ttk.Button(parent, text=text, command=command, bootstyle=bootstyle, width=width, **kwargs)
    btn.grid(row=row, column=col, **grid_opts)
    return btn

# --- Populate Tabs ---

# Prestige Tab
purificationlabel=create_label(prestige_frame,"...",0,0,columnspan=2,sticky='ew',wraplength=350)
purificationbutton=create_button(prestige_frame,"Purify",purify,1,0,columnspan=2)
ttk.Separator(prestige_frame,orient=VERTICAL).grid(row=0,column=2,rowspan=2,sticky='ns',padx=20)
crystalinelabel=create_label(prestige_frame,"...",0,3,columnspan=2,sticky='ew',wraplength=350)
crystalinebutton=create_button(prestige_frame,"Crystalline",crystalline,1,3,columnspan=2)

# Upgrades Tab
pointlabel=create_label(upgrades_frame,"Pts: ...",0,0,columnspan=4)
ppslabel=create_label(upgrades_frame,"PPS: ...",1,0,columnspan=4)
ttk.Separator(upgrades_frame,orient=HORIZONTAL).grid(row=2,column=0,columnspan=4,sticky='ew',pady=10)
# Upg 1
create_label(upgrades_frame,"Upg1:",3,0,sticky='e',font=('-weight','bold'))
upgrade1costlabel=create_label(upgrades_frame,"Cost: ...",3,1)
button1=create_button(upgrades_frame,"Buy",upgrade1,3,2,width=5)
upgrade1explainlabel=create_label(upgrades_frame,"Effect: ...",4,1,columnspan=2)
# Upg 2
create_label(upgrades_frame,"Upg2:",5,0,sticky='e',font=('-weight','bold'))
upgrade2costlabel=create_label(upgrades_frame,"Cost: ...",5,1)
button2=create_button(upgrades_frame,"Buy",upgrade2,5,2,width=5)
upgrade2explainlabel=create_label(upgrades_frame,"Effect: ...",6,1,columnspan=2)
# Upg 3
create_label(upgrades_frame,"Upg3:",7,0,sticky='e',font=('-weight','bold'))
upgrade3costlabel=create_label(upgrades_frame,"Cost: ...",7,1)
button3=create_button(upgrades_frame,"Buy",upgrade3,7,2,width=5)
upgrade3explainlabel=create_label(upgrades_frame,"Effect: ...",8,1,columnspan=2)
# Upg 4
create_label(upgrades_frame,"Upg4:",9,0,sticky='e',font=('-weight','bold'))
upgrade4costlabel=create_label(upgrades_frame,"Cost: ...",9,1)
button4=create_button(upgrades_frame,"Buy",upgrade4,9,2,width=5)
upgrade4explainlabel=create_label(upgrades_frame,"Effect: ...",10,1,columnspan=2)

# Clicking Tab
clicklabel=create_label(clicking_frame,"Clicks: ...",0,0,columnspan=2,sticky='ew',anchor=tk.CENTER)
clickbutton=create_button(clicking_frame,"Click!",click_power_action,1,0,columnspan=2,rowspan=2,sticky='nsew',pady=20)
ttk.Separator(clicking_frame,orient=HORIZONTAL).grid(row=3,column=0,columnspan=2,sticky='ew',pady=15)
# Upg 5
create_label(clicking_frame,"Upg5:",4,0,sticky='e',font=('-weight','bold'))
upgrade5costlabel=create_label(clicking_frame,"Cost: ...",4,1)
button5=create_button(clicking_frame,"Buy",upgrade5,5,0)
upgrade5explainlabel=create_label(clicking_frame,"Effect: ...",5,1)
# Upg 6
create_label(clicking_frame,"Upg6:",6,0,sticky='e',font=('-weight','bold'))
upgrade6costlabel=create_label(clicking_frame,"Cost: ...",6,1)
button6=create_button(clicking_frame,"Buy",upgrade6,7,0)
upgrade6explainlabel=create_label(clicking_frame,"Effect: ...",7,1)
# Upg 7
create_label(clicking_frame,"Upg7:",8,0,sticky='e',font=('-weight','bold'))
upgrade7costlabel=create_label(clicking_frame,"Cost: ...",8,1)
button7=create_button(clicking_frame,"Buy",upgrade7,9,0)
upgrade7explainlabel=create_label(clicking_frame,"Effect: ...",9,1)
# Upg 8
create_label(clicking_frame,"Upg8:",10,0,sticky='e',font=('-weight','bold'))
upgrade8costlabel=create_label(clicking_frame,"Cost: ...",10,1)
button8=create_button(clicking_frame,"Buy",upgrade8,11,0)
upgrade8explainlabel=create_label(clicking_frame,"Effect: ...",11,1)

# Ascension Tab
stardustlabel=create_label(ascension_frame,"Stardust: 0",0,0,columnspan=2,sticky='ew',font=('-weight','bold'))
ascensionlabel=create_label(ascension_frame,"Ascension Locked",1,0,columnspan=2,sticky='ew',wraplength=400)
ascensionbutton=create_button(ascension_frame,"Ascend",ascend,2,0,columnspan=2)
ttk.Separator(ascension_frame,orient=HORIZONTAL).grid(row=3,column=0,columnspan=2,sticky='ew',pady=15)
create_label(ascension_frame,"Astral Upgrades",4,0,columnspan=2,sticky='ew',font=('-weight','bold'))
ar=5 # Start row for astrals
for k in ASTRAL_UPGRADE_DESCRIPTIONS.keys():
    al=create_label(ascension_frame,f"...",ar,0,columnspan=2,sticky='ew',wraplength=400)
    ab=create_button(ascension_frame,f"Buy {k.capitalize()}",lambda k=k: buy_astral_upgrade(k),ar+1,0,sticky='w')
    astral_buttons[k]=ab
    astral_buttons[k+'_label']=al
    ar+=2 # Increment row counter for next pair

# Relics Tab
create_label(relics_frame, "Relics (Spend Stardust)", 0, 0, columnspan=3, sticky='ew', font=('-weight','bold'))
rr=1 # Start row for relics
for rid,data in RELICS_DATA.items():
    nl=create_label(relics_frame,data['name'],rr,0,sticky='e',font=('-weight','bold'))
    dl=create_label(relics_frame,data['desc'],rr,1,sticky='w',wraplength=300)
    ll=create_label(relics_frame,"Lvl: 0",rr+1,1,sticky='w')
    cl=create_label(relics_frame,"Cost: ...",rr+2,1,sticky='w')
    bb=create_button(relics_frame,"Buy",lambda r=rid:buy_relic(r),rr,2,rowspan=3,sticky='ewns')
    relic_widgets[rid]=(nl,dl,ll,cl,bb)
    rr+=3 # Increment row counter for next relic

# Challenges Tab
create_label(challenges_frame,"Challenges",0,0,sticky='ew',font=('-weight','bold'))
cr=1 # Start row for challenges
for cid,chal in CHALLENGES.items():
    cl=create_label(challenges_frame,f"...",cr,0,sticky='ew',wraplength=600)
    challenge_labels[cid]=cl
    cr+=1

# Admin Button (Optional)
if DEVELOPER_MODE:
    admin_button=ttk.Button(window,text="Admin",command=open_admin_panel,bootstyle="info-outline")
    admin_button.grid(row=1,column=0,sticky='sw',padx=10,pady=5)

# ==============================================================================
#                             INITIALIZATION & MAIN LOOP
# ==============================================================================

load_game()
logging.info("Starting threads...")
game_thread=th.Thread(target=game_loop_thread_func,daemon=True)
game_thread.start()
save_thread=th.Thread(target=autosave_thread_func,daemon=True)
save_thread.start()
start_autobuy_thread_if_needed()
updateui()

def on_closing(save=True):
    global is_running, admin_window, active_admin_threads
    if not is_running: return # Prevent double closing

    logging.info("Shutdown...")
    is_running=False # Signal threads to stop

    if admin_window and admin_window.winfo_exists(): on_admin_close() # Close admin panel if open

    # Wait briefly for threads to finish nicely
    timeout=0.3
    threads=[t for t in [game_thread,save_thread,autobuy_thread] if t and t.is_alive()]
    if threads:
        logging.debug(f"Waiting for threads...")
        start=time.monotonic()
        for t in threads: t.join(timeout) # Attempt to join threads
        dur=time.monotonic()-start
        logging.debug(f"Join attempt finished in {dur:.2f}s.")

    if active_admin_threads: logging.info(f"Note: {len(active_admin_threads)} admin threads potentially still active.")

    if save: save_game() # Save game state if requested
    else: logging.info("Skipping save.")

    try:
        if window and window.winfo_exists(): window.destroy() # Destroy the main window
    except tk.TclError: logging.warning("Window already destroyed (TclError).")
    except Exception as e: logging.error(f"Window destroy error: {e}")

    logging.info("Closed.")
    logging.shutdown() # Flush and close log handlers

window.protocol("WM_DELETE_WINDOW", on_closing) # Hook the window close button

try:
    window.mainloop() # Start the Tkinter event loop
except KeyboardInterrupt:
    logging.info("KeyboardInterrupt received.")
    on_closing() # Trigger clean shutdown on Ctrl+C
except Exception as e:
    logging.critical(f"Unhandled exception in main loop: {e}", exc_info=True)
    on_closing(save=False) # Attempt shutdown without saving on critical error

# --- END OF FILE ---
