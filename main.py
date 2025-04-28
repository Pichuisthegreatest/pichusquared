# --- START OF FILE ---

# Required: pip install ttkbootstrap

# -Imports.
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import * # Provides constants like HORIZONTAL, VERTICAL etc.
import threading as th
import time as tm
import datetime as dt
import math as ma
import sys
import os
import logging

# --- Configuration ---
SAVE_FILE = "save.txt"
LOG_FILE = "gamelog.txt"
SAVE_VERSION = 6 # Increment version if save format changes significantly
UPDATE_INTERVAL_MS = 100 # UI update frequency (ms)
TICK_INTERVAL_S = 0.1   # Game logic update frequency (s)
AUTOSAVE_INTERVAL_S = 30 # Autosave frequency (s)
DEVELOPER_MODE = False 
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
    if not isinstance(num, (int, float)) or ma.isnan(num):
        return "NaN"
    if abs(num) < 1000:
        return "{:.2f}".format(round(num, 2))
    if num == 0: return "0.00"

    sign = ""
    if num < 0:
        sign = "-"
        num = abs(num)

    count = 0
    power = 1000.0
    # Determine the correct suffix
    while num >= power and count < len(ENDINGS):
        num /= power
        count += 1

    # Format the number with the suffix
    if count == 0:
         return "{}{:.2f}".format(sign, round(num, 2))
    else:
        suffix_index = count - 1
        # Handle numbers larger than the defined suffixes
        if suffix_index >= len(ENDINGS):
             return "{}{:.2f}{}".format(sign, num, ENDINGS[-1])
        else:
             return "{}{:.2f}{}".format(sign, num, ENDINGS[suffix_index])

# --- Game State Object ---
# Groups related game variables for better organization than pure globals.
class GameState:
    def __init__(self):
        # Point Upgrades
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
        # Click Upgrades
        self.upgrade5_complete = False
        self.upgrade6_complete = False

        # Calculated Modifiers
        self.multiplier = 1.0           # From Upg1
        self.multiplier_strength = 1.0  # From Upg2
        self.mult_raiser = 1.0          # From Upg3
        self.click_power = 1.0          # Base, affected by C4

        # Purification State
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

        # Crystalline State
        self.crystalline_unlocked = False
        self.crystalline_times = 0
        self.max_crystalline = 4
        self.crystalline_cost = 250000000.0
        self.cry1_booster = 1.0
        self.cry1_upg4_unlocked = False
        self.cry2_booster = 1.0 # PPS exponent
        self.cry3_unlocked = False # Autobuy Upg1-3
        self.cry4_unlocked = False # Clicking
        self.crystalline_5_complete = False # C5 flag

        # Synergy/Later Effects
        self.crystalline_completion_bonus = 1.0 # P13
        self.p11_pps_boost_per_clickpower = 0.0 # P11
        self.p12_autobuy_upg4_unlocked = False # P12
        self.p14_upg2_boost = 1.0           # P14
        self.p16_cost_reduction_factor = 1.0  # P16
        self.p17_upg2_boost_from_upg1 = 1.0  # P17
        self.p18_passive_click_rate = 0.0   # P18
        self.p19_boost_multiplier = 1.0     # P19
        self.p20_limit_break_active = False # P20
        self.p24_purify_cost_divisor = 1.0    # P24

        # General State
        self.total_playtime = 0 # seconds
        self.admin_panel_active = False # Tracks if admin window is open

# Instantiate the game state container
game_state = GameState()

# --- Global Variables (Core values updated very frequently) ---
points = 0.0
clicks = 0.0
point_per_second = 0.0 # Calculated based on game_state

# Thread control flag
is_running = True

# --- Prestige Descriptions ---
PURIFY_DESCRIPTIONS = [
    "Triples point gain. Afterwards, doubles point gain.", # P1
    "+1 max level to Upgrades 1 & 2.", # P2
    "Reduce Upgrade 1-3 cost by 5% (mult).", # P3
    "Increase Upgrade 2 base effectiveness x3.", # P4
    "Increase Upgrade 3 base exponent gain by +0.01/lvl.", # P5
    "Gain (1+Purify Times)^2 multiplier to PPS.", # P6
    "No boost.", # P7
    "No boost. Try again?", # P8
    "No boost. Next unlocks something!", # P9
    "Unlock Crystalline layer.", # P10
    "Click Power adds +0.1% base PPS per point.", # P11
    "Autobuy Upgrade 4 if affordable & unlocked.", # P12
    "Each Crystalline completion +5% points (mult).", # P13
    "Increase Upgrade 2 base effectiveness by 50%.", # P14
    "Unlock ability to purchase Crystalline V.", # P15
    "Reduce upgrade cost scaling based on Crystalline completions.", # P16
    "Upgrade 1 levels slightly boost Upgrade 2 effectiveness.", # P17
    "Passively generate Clicks (1% of Click Power/sec).", # P18
    "Boost previous Purifications power by 25%.", # P19
    "LIMIT BREAK: Increase max levels of Upgs 1-4 by 10.", # P20
    "Placeholder P21", "Placeholder P22", "Placeholder P23",
    "Purification cost divided by sqrt(Purify Times).", # P24
]
CRYSTALLINE_DESCRIPTIONS = [
    "Triple point gain. Unlock Upgrade 4.", # C1
    "Point gain raised to ^1.5.", # C2
    "Autobuy Upgrades 1-3.", # C3
    "Unlock Clicking & Click Upgrades.", # C4
    "Unlock Purifications 16-20+. Activate Playtime boost (needs Upg6).", # C5
]

# --- Core Calculation Logic ---

def recalculate_multiplier_strength():
    """Calculates Upgrade 2's effect based on levels and boosts."""
    global game_state
    gs = game_state # Use shorthand for readability

    base_effectiveness = 0.1 * gs.p14_upg2_boost # P14 boost

    # P17 synergy
    gs.p17_upg2_boost_from_upg1 = 1.0 + (gs.upgrade1_level * 0.002) if gs.purify_times >= 17 else 1.0

    # Calculate base value, applying Rank4 boost
    base = (1 + (gs.upgrade2_level * base_effectiveness * gs.p17_upg2_boost_from_upg1)) * gs.rank4_upg2_booster

    # Apply exponentiation from Upgrade 3
    gs.multiplier_strength = round(base ** gs.mult_raiser, 3)

def calculate_point_per_second():
    """Calculates final PPS based on all active multipliers, boosts, and exponents."""
    global point_per_second, game_state
    gs = game_state # Use shorthand

    # Base PPS: Starts at 1, potentially boosted by P11 Click Power synergy
    base_pps_from_clicks = gs.click_power * gs.p11_pps_boost_per_clickpower if gs.purify_times >= 11 else 0.0
    base_pps = 1.0 + base_pps_from_clicks

    # Core multiplier from Upgrade 1 levels and calculated Upgrade 2 strength
    effective_multiplier = gs.multiplier * gs.multiplier_strength

    # Apply flat/multiplicative boosters
    pps = base_pps * effective_multiplier * gs.rank1_booster # P1 boost

    if gs.rank6_unlocked: pps *= gs.rank6_booster # P6 boost
    pps *= gs.cry1_booster # C1 boost
    pps *= gs.crystalline_completion_bonus # P13 boost

    # Apply playtime boost if C5 complete and Upg6 bought
    if gs.crystalline_5_complete and gs.upgrade6_complete:
        pps *= calculate_playtime_multiplier()

    pps *= gs.p19_boost_multiplier # P19 boost

    # Apply exponents
    if gs.cry2_booster != 1.0 and pps > 0: # C2 exponent
        try:
            pps = pps ** gs.cry2_booster
        except (ValueError, OverflowError) as e:
             logging.warning(f"Math error in C2 exponentiation (PPS: {pps}, Exp: {gs.cry2_booster}): {e}")
             pps = 0 # Prevent invalid numbers

    point_per_second = round(pps, 3)

def calculate_playtime_multiplier():
    """Calculates the multiplier based on total playtime (for C5 effect)."""
    global game_state
    minutes_played = game_state.total_playtime // 60
    if minutes_played < 10: return 1.0
    elif minutes_played < 60: return 1.0 + (minutes_played / 10.0)
    else:
        hours_played = minutes_played // 60
        # Calculate base multiplier at 59 minutes and add hours
        return (1.0 + 59.0/10.0) + hours_played

def recalculate_derived_values():
    """Updates calculated values based on current purify/crystalline times. Call after load/prestige."""
    global game_state
    gs = game_state

    # Recalculate dynamic Purification effects based on gs.purify_times
    gs.rank6_booster = (1.0 + gs.purify_times)**2.0 if gs.rank6_unlocked else 1.0
    gs.p11_pps_boost_per_clickpower = 0.001 if gs.purify_times >= 11 else 0.0
    gs.p14_upg2_boost = 1.5 if gs.purify_times >= 14 else 1.0
    reduction_per_cry = 0.005
    gs.p16_cost_reduction_factor = max(0.5, 1.0 - (gs.crystalline_times * reduction_per_cry)) if gs.purify_times >= 16 else 1.0
    gs.p18_passive_click_rate = 0.01 if gs.purify_times >= 18 else 0.0
    gs.p24_purify_cost_divisor = max(1.0, ma.sqrt(gs.purify_times)) if gs.purify_times >= 24 else 1.0

    # Recalculate dynamic Crystalline effects based on gs.crystalline_times
    gs.crystalline_completion_bonus = 1.0 + (gs.crystalline_times * 0.05) if gs.purify_times >= 13 else 1.0

    # Recalculate core point generation (Strength must be calculated before PPS)
    recalculate_multiplier_strength()
    calculate_point_per_second()
    logging.debug("Derived game values recalculated.")

# --- Game Loop Logic ---

def game_tick():
    """Performs calculations for a single game tick."""
    global points, clicks, point_per_second, game_state # Keep game_state global
    try:
        # Generate points
        points += point_per_second * TICK_INTERVAL_S

        # P18: Generate clicks passively if unlocked
        # Use 'game_state' directly instead of 'gs'
        if game_state.purify_times >= 18:
            passive_clicks = (game_state.click_power * game_state.p18_passive_click_rate) * TICK_INTERVAL_S
            clicks += passive_clicks

        # Track playtime
        # Use 'game_state' directly instead of 'gs'
        game_state.total_playtime += TICK_INTERVAL_S

    except Exception as e:
        logging.error(f"Error in game_tick: {e}", exc_info=True)
def game_loop_thread_func():
    """Target function for the main game loop thread."""
    logging.info("Game loop thread started.")
    while is_running:
        start_time = tm.monotonic()
        game_tick()
        # Maintain tick interval accurately
        elapsed = tm.monotonic() - start_time
        sleep_time = max(0, TICK_INTERVAL_S - elapsed)
        tm.sleep(sleep_time)
    logging.info("Game loop thread finished.")

# --- Upgrade Functions ---

def upgrade1():
    global points, game_state
    gs = game_state
    if gs.upgrade1_level < gs.upgrade1_max and points >= gs.upgrade1_cost:
        points -= gs.upgrade1_cost
        gs.upgrade1_level += 1
        gs.multiplier += 1 # Direct effect of this upgrade
        # Calculate next cost applying reductions
        cost_scale = 1.0 + (gs.upgrade1_level * 0.1) # Simplified scaling
        reduction = gs.rank3_cost_multiplier * gs.p16_cost_reduction_factor
        gs.upgrade1_cost = round((gs.upgrade1_cost * cost_scale) * reduction, 2)
        logging.info(f"Upgrade 1 bought! Level: {gs.upgrade1_level}/{gs.upgrade1_max}")
        # Recalculate dependent values
        if gs.purify_times >= 17: recalculate_multiplier_strength() # P17 depends on level
        calculate_point_per_second() # PPS depends on multiplier

def upgrade2():
    global points, game_state
    gs = game_state
    if gs.upgrade2_level < gs.upgrade2_max and points >= gs.upgrade2_cost:
        points -= gs.upgrade2_cost
        gs.upgrade2_level += 1
        cost_scale = 1.0 + (gs.upgrade2_level * 0.1)
        reduction = gs.rank3_cost_multiplier * gs.p16_cost_reduction_factor
        gs.upgrade2_cost = round((gs.upgrade2_cost * cost_scale) * reduction, 2)
        logging.info(f"Upgrade 2 bought! Level: {gs.upgrade2_level}/{gs.upgrade2_max}")
        # Recalculate dependent values (strength and PPS)
        recalculate_multiplier_strength()
        calculate_point_per_second()

def upgrade3():
    global points, game_state
    gs = game_state
    if gs.upgrade3_level < gs.upgrade3_max and points >= gs.upgrade3_cost:
        points -= gs.upgrade3_cost
        gs.upgrade3_level += 1
        # Apply effect: Increase exponent
        exponent_gain = 0.05 + gs.rank5_upg3_booster
        gs.mult_raiser += exponent_gain
        # Calculate next cost
        cost_scale = 1.0 + (gs.upgrade3_level * 0.1)
        reduction = gs.rank3_cost_multiplier * gs.p16_cost_reduction_factor
        gs.upgrade3_cost = round((gs.upgrade3_cost * cost_scale) * reduction, 2)
        logging.info(f"Upgrade 3 bought! Level: {gs.upgrade3_level}/{gs.upgrade3_max}, Raiser: {gs.mult_raiser:.3f}")
        # Recalculate dependent values (strength and PPS)
        recalculate_multiplier_strength()
        calculate_point_per_second()

def upgrade4():
    global points, game_state
    gs = game_state
    if not gs.cry1_upg4_unlocked: # Check unlock condition
        logging.warning("Upgrade 4 is locked (Requires Crystalline 1).")
        return
    if gs.upgrade4_level < gs.upgrade4_max and points >= gs.upgrade4_cost:
        points -= gs.upgrade4_cost
        gs.upgrade4_level += 1
        gs.upgrade3_max += 1 # Direct effect: Increase Upg3 max
        # Calculate next cost (higher base scaling for Upg4)
        cost_scale = 1.25 + (gs.upgrade4_level * 0.1)
        reduction = gs.rank3_cost_multiplier * gs.p16_cost_reduction_factor
        gs.upgrade4_cost = round((gs.upgrade4_cost * cost_scale) * reduction, 2)
        logging.info(f"Upgrade 4 bought! Level: {gs.upgrade4_level}/{gs.upgrade4_max}, Upg3 Max: {gs.upgrade3_max}")
        # No direct PPS recalculation needed here

def upgrade5(): # Click Upgrade: Unlock Purifications 11-15
    global clicks, game_state
    gs = game_state
    if not gs.cry4_unlocked:
         logging.warning("Upgrade 5 locked (Requires Crystalline 4).")
         return
    if gs.upgrade5_complete:
        logging.warning("Upgrade 5 already purchased.")
        return
    required_clicks = 1000.0
    if clicks >= required_clicks:
        clicks -= required_clicks
        gs.max_purify = 15 # Apply effect
        gs.upgrade5_complete = True
        logging.info(f"Upgrade 5 complete! Max Purifications increased to {gs.max_purify}.")
    else:
        logging.info(f"Not enough clicks for Upgrade 5 ({format_number(clicks)}/{format_number(required_clicks)}).")

def upgrade6(): # Click Upgrade: Enable Crystalline 5 Effects
    global clicks, game_state
    gs = game_state
    if not gs.cry4_unlocked:
         logging.warning("Upgrade 6 locked (Requires Crystalline 4).")
         return
    if gs.upgrade6_complete:
        logging.warning("Upgrade 6 already purchased.")
        return
    required_clicks = 100000.0
    if clicks >= required_clicks:
        clicks -= required_clicks
        gs.upgrade6_complete = True
        logging.info("Upgrade 6 complete! Enables Crystalline 5 effects (like playtime boost) when C5 is active.")
        # Recalculate PPS if C5 is already active, as the condition changed
        if gs.crystalline_5_complete:
            calculate_point_per_second()
    else:
        logging.info(f"Not enough clicks for Upgrade 6 ({format_number(clicks)}/{format_number(required_clicks)}).")

# --- Prestige Functions ---

def apply_purification_effects(p_time_achieved):
    """Applies cumulative effects based on the purification level just reached."""
    global game_state
    gs = game_state
    logging.debug(f"Applying Purify effects for level P{p_time_achieved + 1}")

    # Apply effects based on the level index (p_time_achieved)
    if p_time_achieved == 0: gs.rank1_booster = 3.0 # P1: Triple gain first time
    else: gs.rank1_booster *= 2.0 # P1: Double gain after

    if p_time_achieved >= 1: # P2+
        gs.rank2_unlocked = True
        gs.upgrade1_max += 1
        gs.upgrade2_max += 1
    if p_time_achieved >= 2: # P3+
        gs.rank3_unlocked = True
        gs.rank3_cost_multiplier = max(0.1, gs.rank3_cost_multiplier - 0.05) # Apply 5% reduction
    if p_time_achieved >= 3: gs.rank4_upg2_booster = 3.0 # P4
    if p_time_achieved >= 4: gs.rank5_upg3_booster = 0.01 # P5
    if p_time_achieved >= 5: gs.rank6_unlocked = True # P6 (value calculated elsewhere)
    if p_time_achieved >= 9: gs.crystalline_unlocked = True # P10
    if p_time_achieved >= 11: gs.p12_autobuy_upg4_unlocked = True # P12
    if p_time_achieved >= 18: gs.p19_boost_multiplier = 1.25 # P19 (example value)

    # P20: Apply only once per Crystalline cycle if conditions met
    if p_time_achieved >= 19 and gs.crystalline_5_complete and not gs.p20_limit_break_active:
        gs.p20_limit_break_active = True
        levels_to_add = 10
        gs.upgrade1_max += levels_to_add
        gs.upgrade2_max += levels_to_add
        gs.upgrade3_max += levels_to_add
        gs.upgrade4_max += levels_to_add
        logging.info(f"P20 Limit Break Activated! +{levels_to_add} Max Levels.")

    # Note: P11, P13, P14, P16, P17, P18, P24 effects are dynamic, calculated in recalculate_derived_values()

def reset_for_purify():
    """Resets specific game state variables after a Purification."""
    global points, game_state
    gs = game_state
    logging.debug("Resetting state for Purify...")
    points = 0.0

    # Reset point upgrade levels and their base costs
    gs.upgrade1_level = 0; gs.upgrade1_cost = 10.0
    gs.upgrade2_level = 0; gs.upgrade2_cost = 100.0
    gs.upgrade3_level = 0; gs.upgrade3_cost = 10000.0
    gs.upgrade4_level = 0; gs.upgrade4_cost = 10000000.0

    # Reset calculated modifiers derived from point upgrades
    gs.multiplier = 1.0
    gs.multiplier_strength = 1.0
    gs.mult_raiser = 1.0

    # Reset Upg3 max level bonus from Upg4 (P2/P20 effects re-applied via apply_purification_effects)
    gs.upgrade3_max = 10

    # Clicks, click power, click upgrades, and persistent boosts are NOT reset here

def purify():
    """Handles the Purification prestige action."""
    global points, game_state
    gs = game_state

    # Determine if purification is possible
    can_purify_flag = False
    reason = ""
    current_max = gs.max_purify # Get current max based on Upg5/C5
    if gs.purify_times < 10: can_purify_flag = True
    elif gs.purify_times < 15:
        if gs.upgrade5_complete: can_purify_flag = True
        else: reason = "Requires Click Upgrade 1 (U5)"
    elif gs.purify_times < current_max:
        if gs.crystalline_5_complete: can_purify_flag = True
        else: reason = "Requires Crystalline 5 Completion"
    else:
         reason = f"Maximum Purifications Reached ({gs.purify_times}/{current_max})"

    if not can_purify_flag:
        logging.warning(f"Cannot Purify: {reason}")
        return

    # Check cost
    if points < gs.purify_cost:
        logging.warning(f"Cannot Purify: Need {format_number(gs.purify_cost)} points.")
        return

    # Execute Purify
    logging.info("Purifying...")
    points -= gs.purify_cost # Spend points

    apply_purification_effects(gs.purify_times) # Apply effects for the level being achieved (current index)
    reset_for_purify() # Reset progress

    # Increment purify count *before* calculating next cost scaling
    gs.purify_times += 1

    # Calculate next cost based on the *new* count, applying P24 divisor
    cost_scaling = 3.0 + (gs.purify_times - 1) # Scale based on previous count
    next_divisor = max(1.0, ma.sqrt(gs.purify_times)) if gs.purify_times >= 24 else 1.0
    gs.purify_cost = round((gs.purify_cost * cost_scaling) / next_divisor, 2)

    logging.info(f"Purified! Times: {gs.purify_times}/{current_max}. Next cost: {format_number(gs.purify_cost)}")

    # Update all calculated values based on new state
    recalculate_derived_values()

def reset_for_crystalline():
    """Resets specific game state variables after a Crystalline reset."""
    global points, game_state
    gs = game_state
    logging.debug("Resetting state for Crystalline...")

    # Reset core currency
    points = 0.0

    # Reset Purification progress and associated effects/flags
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
    gs.p12_autobuy_upg4_unlocked = False
    gs.p19_boost_multiplier = 1.0
    gs.p20_limit_break_active = False # Reset limit break flag

    # Reset point upgrades (levels, costs, max levels to base)
    gs.multiplier = 1.0
    gs.multiplier_strength = 1.0
    gs.mult_raiser = 1.0
    gs.upgrade1_level = 0; gs.upgrade1_cost = 10.0; gs.upgrade1_max = 25
    gs.upgrade2_level = 0; gs.upgrade2_cost = 100.0; gs.upgrade2_max = 10
    gs.upgrade3_level = 0; gs.upgrade3_cost = 10000.0; gs.upgrade3_max = 10
    gs.upgrade4_level = 0; gs.upgrade4_cost = 10000000.0; gs.upgrade4_max = 5

    # Recalculate max purify based on persistent unlocks (Upg5/C5)
    gs.max_purify = 10
    if gs.upgrade5_complete: gs.max_purify = 15
    if gs.crystalline_5_complete: gs.max_purify = 20 # C5 has higher priority

    # Crystalline unlock status, Crystalline boosts, Crystalline flags (like C5 complete),
    # clicks, click power, and click upgrade completion (Upg5/6) persist across Crystalline resets.
    gs.crystalline_unlocked = True

def crystalline():
    """Handles the Crystalline prestige action."""
    global points, game_state
    gs = game_state

    # Check basic unlock
    if not gs.crystalline_unlocked:
        logging.warning("Crystalline is locked (Requires Purification 10).")
        return

    # Determine effective max Crystalline level (P15 allows targeting 5th)
    effective_max_crystal = gs.max_crystalline
    if gs.purify_times >= 15 and gs.max_crystalline == 4:
         effective_max_crystal = 5

    # Check if max level reached
    if gs.crystalline_times >= effective_max_crystal:
        logging.warning(f"Maximum Crystallines reached ({gs.crystalline_times}/{effective_max_crystal}).")
        return

    # Check specific requirement for Crystalline 5
    is_attempting_c5 = (gs.crystalline_times == 4)
    if is_attempting_c5 and gs.purify_times < 15:
         logging.warning("Cannot attempt Crystalline 5 (Requires Purification 15).")
         return

    # Check cost
    if points < gs.crystalline_cost:
        logging.warning(f"Not enough points to crystallize (Need {format_number(gs.crystalline_cost)}).")
        return

    # Execute Crystalline
    logging.info("Crystallizing...")
    points -= gs.crystalline_cost # Spend points

    # Apply Crystalline Effects (for the level being completed)
    cry_level_completed = gs.crystalline_times + 1
    logging.info(f"Applying Crystalline {cry_level_completed} effects...")
    if cry_level_completed == 1:
        gs.cry1_booster = 3.0
        gs.cry1_upg4_unlocked = True
    elif cry_level_completed == 2:
        gs.cry2_booster = 1.5
    elif cry_level_completed == 3:
        gs.cry3_unlocked = True # Enables autobuy logic
    elif cry_level_completed == 4:
        gs.cry4_unlocked = True # Enables clicking
    elif cry_level_completed == 5:
        gs.crystalline_5_complete = True
        gs.max_purify = 20 # Update max purify as part of C5 effect

    reset_for_crystalline() # Perform the reset of progress

    # Increment Crystalline count *after* applying effects and reset
    gs.crystalline_times += 1

    # Calculate next Crystalline cost based on the *new* count
    if gs.crystalline_times == 1: gs.crystalline_cost = 1e12
    elif gs.crystalline_times == 2: gs.crystalline_cost = 1e15
    elif gs.crystalline_times == 3: gs.crystalline_cost = 1e18
    elif gs.crystalline_times == 4: gs.crystalline_cost = 1e21 # For C5
    else: gs.crystalline_cost = float('inf')

    logging.info(f"Crystallized! Times: {gs.crystalline_times}/{effective_max_crystal}. Next cost: {format_number(gs.crystalline_cost)}")

    recalculate_derived_values() # Update all calculated values

# --- Clicking Action ---
def click_power_action():
    """Increases clicks based on click power if clicking is unlocked."""
    global clicks, game_state
    if gs.cry4_unlocked:
        clicks += gs.click_power
    else:
        logging.warning("Clicking is locked (Requires Crystalline 4).")

# --- Autobuyer Logic ---
def autobuy_tick():
    """Performs a check and buys affordable upgrades if autobuy is active."""
    global points, game_state
    gs = game_state
    try:
        # Autobuy Upg1-3 if C3 is unlocked
        if gs.cry3_unlocked:
            # Buy cheaper upgrades first potentially? Order doesn't matter much with fast checks.
            upgrade1()
            upgrade2()
            upgrade3()

        # Autobuy Upg4 if C1 and P12 are unlocked
        if gs.cry1_upg4_unlocked and gs.p12_autobuy_upg4_unlocked:
            upgrade4()

    except Exception as e:
        # Log errors but allow the thread to continue
        logging.error(f"Error in autobuy_tick: {e}", exc_info=True)

def autobuy_thread_func():
    """Target function for the autobuyer thread."""
    logging.info("Autobuyer thread started.")
    while is_running:
        # Only run the buying logic if an autobuy feature is actually unlocked
        if game_state.cry3_unlocked or game_state.p12_autobuy_upg4_unlocked:
             autobuy_tick()
        tm.sleep(0.1) # Check frequently
    logging.info("Autobuyer thread finished.")

# --- Save/Load ---
def save_game():
    """Saves the current game state to SAVE_FILE."""
    global points, clicks, game_state
    logging.info("Saving game...")
    gs = game_state # shorthand
    try:
        # Consolidate all data to be saved into a dictionary
        save_data = {
            "version": SAVE_VERSION, "points": points, "clicks": clicks,
            "upgrade1_cost": gs.upgrade1_cost, "upgrade1_level": gs.upgrade1_level, "upgrade1_max": gs.upgrade1_max,
            "upgrade2_cost": gs.upgrade2_cost, "upgrade2_level": gs.upgrade2_level, "upgrade2_max": gs.upgrade2_max,
            "upgrade3_cost": gs.upgrade3_cost, "upgrade3_level": gs.upgrade3_level, "upgrade3_max": gs.upgrade3_max,
            "upgrade4_cost": gs.upgrade4_cost, "upgrade4_level": gs.upgrade4_level, "upgrade4_max": gs.upgrade4_max,
            "upgrade5_complete": gs.upgrade5_complete, "upgrade6_complete": gs.upgrade6_complete,
            "multiplier": gs.multiplier, "multiplier_strength": gs.multiplier_strength, "mult_raiser": gs.mult_raiser, "click_power": gs.click_power,
            "purify_times": gs.purify_times, "max_purify": gs.max_purify, "purify_cost": gs.purify_cost,
            "rank1_booster": gs.rank1_booster, "rank2_unlocked": gs.rank2_unlocked, "rank3_unlocked": gs.rank3_unlocked,
            "rank3_cost_multiplier": gs.rank3_cost_multiplier, "rank4_upg2_booster": gs.rank4_upg2_booster,
            "rank5_upg3_booster": gs.rank5_upg3_booster, "rank6_unlocked": gs.rank6_unlocked, "rank6_booster": gs.rank6_booster,
            "crystalline_unlocked": gs.crystalline_unlocked, "crystalline_times": gs.crystalline_times, "max_crystalline": gs.max_crystalline, "crystalline_cost": gs.crystalline_cost,
            "cry1_booster": gs.cry1_booster, "cry1_upg4_unlocked": gs.cry1_upg4_unlocked, "cry2_booster": gs.cry2_booster,
            "cry3_unlocked": gs.cry3_unlocked, "cry4_unlocked": gs.cry4_unlocked, "crystalline_5_complete": gs.crystalline_5_complete,
            "crystalline_completion_bonus": gs.crystalline_completion_bonus, "p11_pps_boost_per_clickpower": gs.p11_pps_boost_per_clickpower,
            "p12_autobuy_upg4_unlocked": gs.p12_autobuy_upg4_unlocked, "p14_upg2_boost": gs.p14_upg2_boost,
            "p16_cost_reduction_factor": gs.p16_cost_reduction_factor, "p17_upg2_boost_from_upg1": gs.p17_upg2_boost_from_upg1,
            "p18_passive_click_rate": gs.p18_passive_click_rate, "p19_boost_multiplier": gs.p19_boost_multiplier,
            "p20_limit_break_active": gs.p20_limit_break_active, "p24_purify_cost_divisor": gs.p24_purify_cost_divisor,
            "total_playtime": gs.total_playtime,
            "save_time": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        # Write data to file, converting bools to strings explicitly
        with open(SAVE_FILE, "w") as f:
            for key, value in save_data.items():
                f.write(f"{key}:{str(value) if isinstance(value, bool) else value}\n")
        logging.info(f"Game saved successfully at {save_data['save_time']}")
    except Exception as e:
        logging.error(f"Failed to save game: {e}", exc_info=True)

def autosave_thread_func():
    """Target function for the autosave thread."""
    logging.info("Autosave thread started.")
    while is_running:
        tm.sleep(AUTOSAVE_INTERVAL_S)
        if is_running: # Ensure game hasn't stopped during sleep
             save_game()
    logging.info("Autosave thread finished.")

def load_game():
    """Loads game state from SAVE_FILE, handling potential errors and version mismatches."""
    global points, clicks, game_state, is_running
    gs = game_state # shorthand

    if not os.path.exists(SAVE_FILE):
        logging.info("No save file found. Starting new game.")
        recalculate_derived_values() # Ensure initial calculation for new game
        return

    logging.info(f"Loading game from {SAVE_FILE}...")
    try:
        loaded_data = {}
        with open(SAVE_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if ':' in line:
                    key, value = line.split(":", 1)
                    loaded_data[key.strip()] = value.strip()

        # Check save version compatibility
        loaded_version = int(loaded_data.get("version", 0))
        if loaded_version != SAVE_VERSION:
            logging.warning(f"Save file version mismatch (Save: {loaded_version}, Game: {SAVE_VERSION}). Loading may be unstable or reset data.")
            # Consider resetting or migrating data here if versions differ significantly
            # For now, will attempt to load anyway

        # Helper for robust type conversion during loading
        def get_val(key, default, _type):
            val_str = loaded_data.get(key)
            if val_str is None: return default
            try:
                if _type == bool: return val_str.lower() == 'true'
                # Handle potential floats saved for integer fields (like playtime)
                elif _type == int and '.' in val_str: return int(float(val_str))
                return _type(val_str)
            except (ValueError, TypeError):
                logging.warning(f"Load Error: Cannot convert '{key}' value '{val_str}' to {_type.__name__}. Using default: {default}")
                return default

        # Load global state
        points = get_val("points", 0.0, float)
        clicks = get_val("clicks", 0.0, float)

        # Load GameState object attributes (explicitly map keys to attributes)
        gs.upgrade1_cost = get_val("upgrade1_cost", 10.0, float); gs.upgrade1_level = get_val("upgrade1_level", 0, int); gs.upgrade1_max = get_val("upgrade1_max", 25, int)
        gs.upgrade2_cost = get_val("upgrade2_cost", 100.0, float); gs.upgrade2_level = get_val("upgrade2_level", 0, int); gs.upgrade2_max = get_val("upgrade2_max", 10, int)
        gs.upgrade3_cost = get_val("upgrade3_cost", 10000.0, float); gs.upgrade3_level = get_val("upgrade3_level", 0, int); gs.upgrade3_max = get_val("upgrade3_max", 10, int)
        gs.upgrade4_cost = get_val("upgrade4_cost", 10000000.0, float); gs.upgrade4_level = get_val("upgrade4_level", 0, int); gs.upgrade4_max = get_val("upgrade4_max", 5, int)
        gs.upgrade5_complete = get_val("upgrade5_complete", False, bool); gs.upgrade6_complete = get_val("upgrade6_complete", False, bool)
        gs.multiplier = get_val("multiplier", 1.0, float); gs.mult_raiser = get_val("mult_raiser", 1.0, float); gs.click_power = get_val("click_power", 1.0, float)
        gs.purify_times = get_val("purify_times", 0, int); gs.max_purify = get_val("max_purify", 10, int); gs.purify_cost = get_val("purify_cost", 1000.0, float)
        gs.rank1_booster = get_val("rank1_booster", 1.0, float); gs.rank2_unlocked = get_val("rank2_unlocked", False, bool); gs.rank3_unlocked = get_val("rank3_unlocked", False, bool)
        gs.rank3_cost_multiplier = get_val("rank3_cost_multiplier", 1.0, float); gs.rank4_upg2_booster = get_val("rank4_upg2_booster", 1.0, float)
        gs.rank5_upg3_booster = get_val("rank5_upg3_booster", 0.0, float); gs.rank6_unlocked = get_val("rank6_unlocked", False, bool)
        gs.crystalline_unlocked = get_val("crystalline_unlocked", False, bool); gs.crystalline_times = get_val("crystalline_times", 0, int)
        gs.max_crystalline = get_val("max_crystalline", 4, int); gs.crystalline_cost = get_val("crystalline_cost", 250000000.0, float)
        gs.cry1_booster = get_val("cry1_booster", 1.0, float); gs.cry1_upg4_unlocked = get_val("cry1_upg4_unlocked", False, bool)
        gs.cry2_booster = get_val("cry2_booster", 1.0, float); gs.cry3_unlocked = get_val("cry3_unlocked", False, bool); gs.cry4_unlocked = get_val("cry4_unlocked", False, bool); gs.crystalline_5_complete = get_val("crystalline_5_complete", False, bool)
        gs.p12_autobuy_upg4_unlocked = get_val("p12_autobuy_upg4_unlocked", False, bool); gs.p19_boost_multiplier = get_val("p19_boost_multiplier", 1.0, float)
        gs.p20_limit_break_active = get_val("p20_limit_break_active", False, bool); gs.total_playtime = get_val("total_playtime", 0, int)
        # Note: strength, rank6_booster, p11, p13, p14, p16, p17, p18, p24 values are recalculated below

        logging.info("Save data loaded successfully.")
        recalculate_derived_values() # IMPORTANT: Recalculate dependent stats

    except Exception as e:
        logging.error(f"Failed to load or parse save file: {e}", exc_info=True)
        logging.info("Starting a new game due to load error.")
        game_state = GameState() # Reset state
        points = 0.0
        clicks = 0.0
        recalculate_derived_values() # Calculate initial values

# --- UI Update Function ---
# Define global widget variables (simplifies access in updateui)
pointlabel = None; ppslabel = None; clicklabel = None
upgrade1costlabel = None; upgrade1explainlabel = None; button1 = None
upgrade2costlabel = None; upgrade2explainlabel = None; button2 = None
upgrade3costlabel = None; upgrade3explainlabel = None; button3 = None
upgrade4costlabel = None; upgrade4explainlabel = None; button4 = None
upgrade5costlabel = None; upgrade5explainlabel = None; button5 = None
upgrade6costlabel = None; upgrade6explainlabel = None; button6 = None
purificationlabel = None; purificationbutton = None
crystalinelabel = None; crystalinebutton = None
clickbutton = None

def update_button_style(button, state):
    """Updates button style and state based on game logic."""
    if not button or not isinstance(button, ttk.Button): return
    try:
        style = "primary-outline" # default
        tk_state = tk.NORMAL
        if state == "maxed":
            style = "danger-outline"; tk_state = tk.DISABLED
        elif state == "buyable":
            style = "success-outline"
        elif state == "locked":
            style = "secondary-outline"; tk_state = tk.DISABLED
        button.configure(bootstyle=style, state=tk_state)
    except tk.TclError as e: # Handle errors if widget is destroyed during update
        logging.warning(f"TclError configuring button: {e}")
    except Exception as e:
        logging.error(f"Error updating button style: {e}")

def updateui():
    """Updates all UI elements based on current game state."""
    global points, clicks, point_per_second, game_state, window
    gs = game_state # Use shorthand
    try:
        # Update main resource labels
        if pointlabel: pointlabel.configure(text=f"Points: {format_number(points)}")
        if ppslabel: ppslabel.configure(text=f"PPS: {format_number(point_per_second)}")
        if clicklabel: clicklabel.configure(text=f"Clicks: {format_number(clicks)}")

        # Update Prestige Tab
        if purificationlabel and purificationbutton:
            can_purify, reason, p_desc = False, "Max Reached", ""
            current_max = gs.max_purify
            next_level = gs.purify_times + 1

            if gs.purify_times < current_max:
                if next_level <= 10: can_purify, reason = True, ""
                elif next_level <= 15: can_purify, reason = (True, "") if gs.upgrade5_complete else (False, "Requires U5")
                else: can_purify, reason = (True, "") if gs.crystalline_5_complete else (False, "Requires C5")

                if gs.purify_times < len(PURIFY_DESCRIPTIONS): p_desc = PURIFY_DESCRIPTIONS[gs.purify_times]
                else: p_desc = "No description available."
                if not can_purify and reason != "Max Reached": p_desc = f"({reason}) {p_desc}"

                purificationlabel.configure(text=f"Purify {next_level}/{current_max}: {p_desc}\nCost: {format_number(gs.purify_cost)}")
                status = "buyable" if (can_purify and points >= gs.purify_cost) else ("locked" if not can_purify else "default")
                update_button_style(purificationbutton, status)
            else:
                purificationlabel.configure(text=f"Maximum Purifications Reached ({gs.purify_times}/{current_max})")
                update_button_style(purificationbutton, "maxed")

        if crystalinelabel and crystalinebutton:
            can_crystal, reason, c_desc = True, "", ""
            effective_max = gs.max_crystalline
            if gs.purify_times >= 15 and gs.max_crystalline == 4: effective_max = 5
            next_level = gs.crystalline_times + 1

            if not gs.crystalline_unlocked: can_crystal, reason = False, "Requires P10"
            elif gs.crystalline_times >= effective_max: can_crystal, reason = False, "Max Reached"
            elif gs.crystalline_times == 4 and gs.purify_times < 15: can_crystal, reason = False, "Requires P15"

            if reason == "Requires P10":
                 crystalinelabel.configure(text="Locked (Requires Purification 10)")
                 update_button_style(crystalinebutton, "locked")
            elif reason == "Max Reached":
                 crystalinelabel.configure(text=f"Maximum Crystallines Reached ({gs.crystalline_times}/{effective_max})")
                 update_button_style(crystalinebutton, "maxed")
            else:
                 if gs.crystalline_times < len(CRYSTALLINE_DESCRIPTIONS): c_desc = CRYSTALLINE_DESCRIPTIONS[gs.crystalline_times]
                 else: c_desc = "No description."
                 if not can_crystal and reason: c_desc = f"({reason}) {c_desc}"

                 crystalinelabel.configure(text=f"Crystalline {next_level}/{effective_max}: {c_desc}\nCost: {format_number(gs.crystalline_cost)}")
                 status = "buyable" if (can_crystal and points >= gs.crystalline_cost) else ("locked" if not can_crystal else "default")
                 update_button_style(crystalinebutton, status)

        # Update Upgrades Tab (Point Upgrades)
        if upgrade1costlabel: upgrade1costlabel.configure(text=f"Cost: {format_number(gs.upgrade1_cost)}")
        if upgrade1explainlabel: upgrade1explainlabel.configure(text=f"+1 Base Multiplier [{gs.upgrade1_level}/{gs.upgrade1_max}]")
        if button1: update_button_style(button1, "maxed" if gs.upgrade1_level >= gs.upgrade1_max else ("buyable" if points >= gs.upgrade1_cost else "default"))

        if upgrade2costlabel: upgrade2costlabel.configure(text=f"Cost: {format_number(gs.upgrade2_cost)}")
        if upgrade2explainlabel: upgrade2explainlabel.configure(text=f"Strength x{format_number(gs.multiplier_strength)} [{gs.upgrade2_level}/{gs.upgrade2_max}]")
        if button2: update_button_style(button2, "maxed" if gs.upgrade2_level >= gs.upgrade2_max else ("buyable" if points >= gs.upgrade2_cost else "default"))

        if upgrade3costlabel: upgrade3costlabel.configure(text=f"Cost: {format_number(gs.upgrade3_cost)}")
        if upgrade3explainlabel: upgrade3explainlabel.configure(text=f"Strength Exponent ^{gs.mult_raiser:.2f} [{gs.upgrade3_level}/{gs.upgrade3_max}]")
        if button3: update_button_style(button3, "maxed" if gs.upgrade3_level >= gs.upgrade3_max else ("buyable" if points >= gs.upgrade3_cost else "default"))

        if button4: # Update Upgrade 4 based on lock status
            is_locked = not gs.cry1_upg4_unlocked
            if upgrade4costlabel: upgrade4costlabel.configure(text="Locked (Cry 1)" if is_locked else f"Cost: {format_number(gs.upgrade4_cost)}")
            if upgrade4explainlabel: upgrade4explainlabel.configure(text="???" if is_locked else f"+1 Max Lvl for Upg 3 [{gs.upgrade4_level}/{gs.upgrade4_max}]")
            status = "locked" if is_locked else ("maxed" if gs.upgrade4_level >= gs.upgrade4_max else ("buyable" if points >= gs.upgrade4_cost else "default"))
            update_button_style(button4, status)

        # Update Clicking Tab
        if clickbutton:
            is_locked = not gs.cry4_unlocked
            clickbutton.configure(
                text=f"Click! (+{format_number(gs.click_power)})" if not is_locked else "Clicking Locked (Cry 4)",
                state=tk.NORMAL if not is_locked else tk.DISABLED
            )

        # Update Click Upgrade 5
        if button5:
            is_locked = not gs.cry4_unlocked
            req_clicks_5 = 1000.0
            status = "locked"
            cost_text = "Locked (Cry 4)"
            explain_text = "???"
            if not is_locked:
                if gs.upgrade5_complete:
                    status = "maxed"
                    cost_text = "Purchased"
                    explain_text = f"Max Purify: {gs.max_purify}"
                else:
                    status = "buyable" if clicks >= req_clicks_5 else "default"
                    cost_text = f"Cost: {format_number(req_clicks_5)} Clicks"
                    explain_text = "Unlock Purifications 11-15"
            if upgrade5costlabel: upgrade5costlabel.configure(text=cost_text)
            if upgrade5explainlabel: upgrade5explainlabel.configure(text=explain_text)
            update_button_style(button5, status)

        # Update Click Upgrade 6
        if button6:
            is_locked = not gs.cry4_unlocked
            req_clicks_6 = 100000.0
            status = "locked"
            cost_text = "Locked (Cry 4)"
            explain_text = "???"
            if not is_locked:
                if gs.upgrade6_complete:
                    status = "maxed"
                    cost_text = "Purchased"
                    explain_text = "Crystalline 5 Effects Enabled"
                else:
                    status = "buyable" if clicks >= req_clicks_6 else "default"
                    cost_text = f"Cost: {format_number(req_clicks_6)} Clicks"
                    explain_text = "Enable Crystalline 5 Effects"
            if upgrade6costlabel: upgrade6costlabel.configure(text=cost_text)
            if upgrade6explainlabel: upgrade6explainlabel.configure(text=explain_text)
            update_button_style(button6, status)

        # Schedule next UI update if game is still running
        if is_running:
             window.after(UPDATE_INTERVAL_MS, updateui)

    except Exception as e:
        logging.error(f"Error during UI update: {e}", exc_info=True)
        # Schedule retry after a delay if an error occurs
        if is_running:
             window.after(UPDATE_INTERVAL_MS * 2, updateui)

# --- Admin Panel Functions ---
admin_window = None
admin_widgets = {}

def open_admin_panel():
    global admin_window, admin_widgets, game_state
    # Only allow opening if in developer mode
    if not DEVELOPER_MODE:
        logging.warning("Admin panel is disabled.")
        return

    # Prevent multiple admin windows
    if admin_window is not None and admin_window.winfo_exists():
        admin_window.lift() # Bring existing window to front
        return

    game_state.admin_panel_active = True
    admin_window = ttk.Toplevel(window)
    admin_window.title("Admin Controls")
    admin_window.geometry("380x280")
    admin_window.protocol("WM_DELETE_WINDOW", on_admin_close) # Set close behavior

    admin_frame = ttk.Frame(admin_window, padding=10)
    admin_frame.pack(expand=True, fill=tk.BOTH)
    admin_frame.grid_columnconfigure(1, weight=1) # Allow entry fields to expand

    # Helper to create admin widgets efficiently
    def create_admin_widget(w_type, text, row, col, key, **kwargs):
        # Decide widget type and options
        is_entry = w_type == ttk.Entry
        options = {'width': 20} if is_entry else {}
        options.update(kwargs)
        widget = w_type(admin_frame, **options)

        # Configure text/command if applicable
        if isinstance(widget, ttk.Button): widget.configure(text=text, command=options.get('command'))
        elif isinstance(widget, ttk.Label): widget.configure(text=text)

        # Grid the widget
        sticky = options.get('sticky', 'ew' if is_entry else 'w')
        widget.grid(row=row, column=col, padx=5, pady=3, sticky=sticky, columnspan=options.get('span',1))
        admin_widgets[key] = widget # Store reference

    # Create admin panel elements
    create_admin_widget(ttk.Label, "Set Points:", 0, 0, 'lbl_pts')
    create_admin_widget(ttk.Entry, "", 0, 1, 'ent_pts')
    create_admin_widget(ttk.Button, "Set", 0, 2, 'btn_pts', command=admin_set_points)

    create_admin_widget(ttk.Label, "Set Clicks:", 1, 0, 'lbl_clk')
    create_admin_widget(ttk.Entry, "", 1, 1, 'ent_clk')
    create_admin_widget(ttk.Button, "Set", 1, 2, 'btn_clk', command=admin_set_clicks)

    create_admin_widget(ttk.Label, "Set Purify Times:", 2, 0, 'lbl_pur')
    create_admin_widget(ttk.Entry, "", 2, 1, 'ent_pur')
    create_admin_widget(ttk.Button, "Set", 2, 2, 'btn_pur', command=admin_set_purify)

    create_admin_widget(ttk.Label, "Set Crys Times:", 3, 0, 'lbl_cry')
    create_admin_widget(ttk.Entry, "", 3, 1, 'ent_cry')
    create_admin_widget(ttk.Button, "Set", 3, 2, 'btn_cry', command=admin_set_crystalline)

    create_admin_widget(ttk.Button, "Recalculate Stats", 4, 0, 'btn_recalc', span=3, command=admin_recalculate)
    create_admin_widget(ttk.Button, "DELETE SAVE FILE", 5, 0, 'btn_del', span=3, command=admin_delete_save, bootstyle="danger")
    create_admin_widget(ttk.Button, "Close", 6, 0, 'btn_close', span=3, command=on_admin_close, bootstyle="secondary")

def on_admin_close():
    """Callback function when the admin window is closed."""
    global admin_window, game_state
    if admin_window:
        admin_window.destroy() # Ensure window is destroyed
    admin_window = None
    admin_widgets.clear() # Clear references to widgets
    game_state.admin_panel_active = False
    logging.info("Admin panel closed.")

# --- Admin Action Functions (with DEVELOPER_MODE check) ---

def admin_set_points():
    global points
    if not DEVELOPER_MODE: return
    try:
        points = float(admin_widgets['ent_pts'].get())
        logging.info(f"ADMIN: Set points to {format_number(points)}")
    except ValueError: logging.warning("ADMIN: Invalid points value.")
    except Exception as e: logging.error(f"ADMIN Error setting points: {e}")

def admin_set_clicks():
    global clicks
    if not DEVELOPER_MODE: return
    try:
        clicks = float(admin_widgets['ent_clk'].get())
        logging.info(f"ADMIN: Set clicks to {format_number(clicks)}")
    except ValueError: logging.warning("ADMIN: Invalid clicks value.")
    except Exception as e: logging.error(f"ADMIN Error setting clicks: {e}")

def admin_set_purify():
    global game_state
    gs = game_state # shorthand
    if not DEVELOPER_MODE: return
    try:
        new_p_times = int(admin_widgets['ent_pur'].get())
        if new_p_times < 0: raise ValueError("Purification times cannot be negative")
        gs.purify_times = new_p_times
        # Approximate cost calculation after setting times
        gs.purify_cost = 1000.0
        for i in range(gs.purify_times):
             divisor = max(1.0, ma.sqrt(i+1)) if (i+1) >= 24 else 1.0
             scale = 3.0 + i
             gs.purify_cost = round((gs.purify_cost * scale) / divisor, 2)
        admin_recalculate() # Recalculate all effects based on new times
        logging.info(f"ADMIN: Set purify times to {gs.purify_times}. Recalculated. Approx Next Cost: {format_number(gs.purify_cost)}")
    except ValueError: logging.warning("ADMIN: Invalid purification value.")
    except Exception as e: logging.error(f"ADMIN Error setting purify times: {e}")

def admin_set_crystalline():
    global game_state
    gs = game_state
    if not DEVELOPER_MODE: return
    try:
        new_c_times = int(admin_widgets['ent_cry'].get())
        if new_c_times < 0: raise ValueError("Crystalline times cannot be negative")
        gs.crystalline_times = new_c_times
        # Apply relevant persistent flags/boosters based on new count
        gs.cry1_booster = 3.0 if new_c_times >= 1 else 1.0
        gs.cry1_upg4_unlocked = new_c_times >= 1
        gs.cry2_booster = 1.5 if new_c_times >= 2 else 1.0
        gs.cry3_unlocked = new_c_times >= 3
        gs.cry4_unlocked = new_c_times >= 4
        gs.crystalline_5_complete = new_c_times >= 5
        # Approximate cost calculation
        costs = {0: 2.5e8, 1: 1e12, 2: 1e15, 3: 1e18, 4: 1e21}
        gs.crystalline_cost = costs.get(new_c_times, float('inf'))
        admin_recalculate() # Recalculate all effects
        logging.info(f"ADMIN: Set crystalline times to {gs.crystalline_times}. Recalculated. Approx Next Cost: {format_number(gs.crystalline_cost)}")
    except ValueError: logging.warning("ADMIN: Invalid crystalline value.")
    except Exception as e: logging.error(f"ADMIN Error setting crystalline times: {e}")

def admin_recalculate():
    """Forces recalculation of all game stats (useful after admin changes)."""
    if not DEVELOPER_MODE: return
    logging.info("ADMIN: Forcing recalculation of derived stats.")
    recalculate_derived_values()
    logging.info("ADMIN: Recalculation complete.")

def admin_delete_save():
    """Deletes the save file if in developer mode."""
    if not DEVELOPER_MODE: return
    logging.warning("ADMIN: Attempting to delete save file...")
    try:
         if os.path.exists(SAVE_FILE):
             os.remove(SAVE_FILE)
             logging.info(f"ADMIN: Save file '{SAVE_FILE}' deleted. Restart game for fresh start.")
         else:
             logging.info("ADMIN: No save file found to delete.")
    except Exception as e:
         logging.error(f"ADMIN ERROR: Could not delete save file: {e}", exc_info=True)


# ==============================================================================
#                           UI SETUP
# ==============================================================================

# --- Main Window ---
window = ttk.Window(themename="darkly")
window.title("pleasesendhelpivebeencodingforlike6hoursitdoesntworkkk") 
window.geometry("1000x700")
window.grid_rowconfigure(0, weight=1) # Row for notebook (expands)
window.grid_rowconfigure(1, weight=0) # Row for admin button (fixed height)
window.grid_columnconfigure(0, weight=1) # Column for notebook (expands)

# --- Main Notebook ---
notebook = ttk.Notebook(window, bootstyle="primary")
notebook.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

# --- Create Tab Frames ---
prestige_frame = ttk.Frame(notebook, padding=(20, 10))
upgrades_frame = ttk.Frame(notebook, padding=(20, 10))
clicking_frame = ttk.Frame(notebook, padding=(20, 10))

# Configure column weights within tabs for better resizing
prestige_frame.grid_columnconfigure(0, weight=1); prestige_frame.grid_columnconfigure(3, weight=1)
upgrades_frame.grid_columnconfigure(1, weight=1) # Let explanation labels expand
clicking_frame.grid_columnconfigure(0, weight=1); clicking_frame.grid_columnconfigure(1, weight=1)

# Add tabs to notebook
notebook.add(prestige_frame, text=" Prestige ")
notebook.add(upgrades_frame, text=" Upgrades ")
notebook.add(clicking_frame, text=" Clicking ")

# --- UI Widget Creation Helper Functions (Corrected) ---
def create_label(parent, text, row, col, **kwargs):
    """Creates and grids a ttk.Label."""
    grid_opts = {k: kwargs.pop(k) for k in list(kwargs.keys()) if k in ['sticky', 'padx', 'pady', 'columnspan', 'rowspan']}
    grid_opts.setdefault('sticky', 'w'); grid_opts.setdefault('padx', 5); grid_opts.setdefault('pady', 2)
    label = ttk.Label(parent, text=text, **kwargs) # Pass remaining kwargs (font, wraplength)
    label.grid(row=row, column=col, **grid_opts)
    return label

def create_button(parent, text, command, row, col, **kwargs):
    """Creates and grids a ttk.Button."""
    grid_opts = {k: kwargs.pop(k) for k in list(kwargs.keys()) if k in ['sticky', 'padx', 'pady', 'columnspan', 'rowspan']}
    grid_opts.setdefault('sticky', 'ew'); grid_opts.setdefault('padx', 5); grid_opts.setdefault('pady', 5)
    # Ensure bootstyle is passed to constructor if provided
    button = ttk.Button(parent, text=text, command=command, bootstyle=kwargs.get('bootstyle', 'primary-outline'), width=kwargs.get('width'))
    button.grid(row=row, column=col, **grid_opts)
    return button

# --- Populate Prestige Tab --- (Assign widgets to global variables)
purificationlabel = create_label(prestige_frame, "Loading...", 0, 0, columnspan=2, sticky='ew', wraplength=350)
purificationbutton = create_button(prestige_frame, "Purify", purify, 1, 0, columnspan=2)
ttk.Separator(prestige_frame, orient=VERTICAL).grid(row=0, column=2, rowspan=2, sticky='ns', padx=20)
crystalinelabel = create_label(prestige_frame, "Loading...", 0, 3, columnspan=2, sticky='ew', wraplength=350)
crystalinebutton = create_button(prestige_frame, "Crystalline", crystalline, 1, 3, columnspan=2)

# --- Populate Upgrades Tab ---
pointlabel = create_label(upgrades_frame, "Points: Loading...", 0, 0, columnspan=3)
ppslabel = create_label(upgrades_frame, "PPS: Loading...", 1, 0, columnspan=3)
ttk.Separator(upgrades_frame, orient=HORIZONTAL).grid(row=2, column=0, columnspan=3, sticky='ew', pady=10)

# Upgrade 1
create_label(upgrades_frame, "Upgrade 1:", 3, 0, sticky='e', font=('-weight', 'bold'))
upgrade1costlabel = create_label(upgrades_frame, "Cost: ...", 3, 1)
button1 = create_button(upgrades_frame, "Buy", upgrade1, 3, 2)
upgrade1explainlabel = create_label(upgrades_frame, "Effect: ...", 4, 1, columnspan=2)
# Upgrade 2
create_label(upgrades_frame, "Upgrade 2:", 5, 0, sticky='e', font=('-weight', 'bold'))
upgrade2costlabel = create_label(upgrades_frame, "Cost: ...", 5, 1)
button2 = create_button(upgrades_frame, "Buy", upgrade2, 5, 2)
upgrade2explainlabel = create_label(upgrades_frame, "Effect: ...", 6, 1, columnspan=2)
# Upgrade 3
create_label(upgrades_frame, "Upgrade 3:", 7, 0, sticky='e', font=('-weight', 'bold'))
upgrade3costlabel = create_label(upgrades_frame, "Cost: ...", 7, 1)
button3 = create_button(upgrades_frame, "Buy", upgrade3, 7, 2)
upgrade3explainlabel = create_label(upgrades_frame, "Effect: ...", 8, 1, columnspan=2)
# Upgrade 4
create_label(upgrades_frame, "Upgrade 4:", 9, 0, sticky='e', font=('-weight', 'bold'))
upgrade4costlabel = create_label(upgrades_frame, "Cost: ...", 9, 1)
button4 = create_button(upgrades_frame, "Buy", upgrade4, 9, 2)
upgrade4explainlabel = create_label(upgrades_frame, "Effect: ...", 10, 1, columnspan=2)

# --- Populate Clicking Tab ---
clicklabel = create_label(clicking_frame, "Clicks: Loading...", 0, 0, columnspan=2, sticky='ew', anchor=tk.CENTER)
clickbutton = create_button(clicking_frame, "Click!", click_power_action, 1, 0, columnspan=2, rowspan=2, sticky='nsew', pady=20)
clicking_frame.grid_rowconfigure(1, weight=1); clicking_frame.grid_rowconfigure(2, weight=1) # Allow click button to expand
ttk.Separator(clicking_frame, orient=HORIZONTAL).grid(row=3, column=0, columnspan=2, sticky='ew', pady=15)
# Click Upgrade 5
create_label(clicking_frame, "Click Upgrade 1 (U5):", 4, 0, sticky='e', font=('-weight', 'bold'))
upgrade5costlabel = create_label(clicking_frame, "Cost: ...", 4, 1)
button5 = create_button(clicking_frame, "Buy", upgrade5, 5, 0)
upgrade5explainlabel = create_label(clicking_frame, "Effect: ...", 5, 1)
# Click Upgrade 6
create_label(clicking_frame, "Click Upgrade 2 (U6):", 6, 0, sticky='e', font=('-weight', 'bold'))
upgrade6costlabel = create_label(clicking_frame, "Cost: ...", 6, 1)
button6 = create_button(clicking_frame, "Buy", upgrade6, 7, 0)
upgrade6explainlabel = create_label(clicking_frame, "Effect: ...", 7, 1)

# --- Admin Panel Button (Conditionally Created) ---
if DEVELOPER_MODE:
    admin_button = ttk.Button(window, text="Admin", command=open_admin_panel, bootstyle="info-outline")
    admin_button.grid(row=1, column=0, sticky='sw', padx=10, pady=5)
    logging.info("Developer mode active. Admin button created.")
else:
    logging.info("Developer mode inactive. Admin button skipped.")

# ==============================================================================
#                             INITIALIZATION & MAIN LOOP
# ==============================================================================

# Load saved game data (or initialize state for a new game)
load_game()

# Start background threads for game logic and autosaving
logging.info("Starting background threads...")
game_thread = th.Thread(target=game_loop_thread_func, daemon=True)
save_thread = th.Thread(target=autosave_thread_func, daemon=True)
game_thread.start()
save_thread.start()

# Start autobuy thread *only* if required features are unlocked
autobuy_thread = None
if game_state.cry3_unlocked or game_state.p12_autobuy_upg4_unlocked:
     autobuy_thread = th.Thread(target=autobuy_thread_func, daemon=True)
     autobuy_thread.start()

# Start the UI update loop
updateui()

# --- Window Closing Behavior ---
def on_closing():
    """Handles window close event gracefully."""
    global is_running, admin_window
    logging.info("Shutdown initiated...")
    is_running = False # Signal threads to stop

    # Close admin panel if it's open
    if admin_window is not None and admin_window.winfo_exists():
        on_admin_close()

    # Optional: Wait briefly for threads to finish current task (daemons will exit anyway)
    # Consider joining threads here if crucial final operations needed in them
    # game_thread.join(0.2)
    # save_thread.join(0.2) # Make sure save finishes if needed

    save_game() # Perform a final save before exiting
    window.destroy() # Close the main window
    logging.info("Application closed.")
    logging.shutdown() # Flush and close logging handlers

# Assign the closing protocol
window.protocol("WM_DELETE_WINDOW", on_closing)

# Start the Tkinter event loop
window.mainloop()

# --- END OF FILE ---
