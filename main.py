# --- START OF FILE main.py ---

# Required: pip install ttkbootstrap

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
import ast 
import json 
import base64 
import time 
from tkinter import messagebox 

try:
    from ttkbootstrap.scrolled import ScrolledText as ttkScrolledText
except ImportError:
    ttkScrolledText = scrolledtext.ScrolledText 

# --- Configuration ---
SAVE_FILE = "save_encoded.dat" # New save file for major changes
LOG_FILE = "gamelog.txt"
SAVE_VERSION = 31 # Incremented for fixes/updates
UPDATE_INTERVAL_MS = 100
TICK_INTERVAL_S = 0.1
AUTOSAVE_INTERVAL_S = 30
ADMINPANELACTIVATION = False #access to admin panel :3
DEVELOPER_MODE = False #debug
POINT_THRESHOLD_SP = 1e24
RELIC_MAX_LEVEL = 10 

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'), 
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
    # Corrected loop logic for very large numbers
    max_iterations = 100 # Safety break
    iterations = 0
    while num_div >= power and count < len(ENDINGS) and iterations < max_iterations:
        try:
            # Check for potential overflow before division
            if num_div / power == float('inf'):
                 break # Stop if division would result in infinity
            num_div /= power
            count += 1
            iterations += 1
        except OverflowError:
            logging.warning(f"OverflowError during format_number loop for num: {num}")
            break # Exit loop on overflow

    if iterations >= max_iterations:
        logging.warning(f"format_number reached max iterations for num: {num}")
        return f"{sign}{num:.2e}" # Fallback to scientific notation

    if count == 0: return "{}{:.2f}".format(sign, round(num_abs, 2))
    else:
        # Ensure index is within bounds
        idx = min(count - 1, len(ENDINGS) - 1)
        # Ensure num_div is finite before formatting
        if ma.isinf(num_div) or ma.isnan(num_div):
             return f"{sign}{num:.2e}" # Fallback if num_div is problematic
        return "{}{:.2f}{}".format(sign, round(num_div, 2), ENDINGS[idx])

# Task 3: Obfuscation Function
def obfuscate(text):
  """Obfuscates text, replacing letters with '?' but keeping spaces/punctuation."""
  return ''.join('?' if c.isalpha() else c for c in text)

# --- Game State Object (Shortened Variables - Task 4) ---
class GameState:
    def __init__(self):
        # --- Point Upgrades ---
        self.upg1_cost = 10.0
        self.upg1_lvl = 0
        self.upg1_max = 25.0 # Use float for Inf compatibility
        self.upg2_cost = 100.0
        self.upg2_lvl = 0
        self.upg2_max = 10.0
        self.upg3_cost = 10000.0
        self.upg3_lvl = 0
        self.upg3_max = 10.0
        self.upg4_cost = 10000000.0
        self.upg4_lvl = 0
        self.upg4_max = 5.0
        # --- Click Upgrades ---
        self.upg5_comp = False # upgrade5_complete
        self.upg6_comp = False # upgrade6_complete
        self.upg7_cost = 1e6
        self.upg7_lvl = 0
        self.upg7_max = 50.0
        self.upg8_cost = 1e9
        self.upg8_lvl = 0
        self.upg8_max = 100.0
        # --- Calculated Modifiers ---
        self.mult = 1.0 # multiplier
        self.mult_str = 1.0 # multiplier_strength
        self.pps_exp = 1.0 # pps_exponent
        self.clk_pow = 1.0 # click_power
        self.clk_crit_c = 0.0 # click_crit_chance
        self.clk_crit_m = 2.0 # click_crit_multiplier
        self.auto_cps = 0.0 # auto_clicks_per_sec
        self.clk_pt_scale = 1.0 # click_point_scaling_bonus
        # --- Purification State ---
        self.pur_cnt = 0 # purify_times
        self.pur_max = 10 # max_purify (can be dynamically updated)
        self.pur_cost = 1000.0 # purify_cost
        self.r1_boost = 1.0 # rank1_booster
        self.r2_unl = False # rank2_unlocked
        self.r3_unl = False # rank3_unlocked
        self.r3_cost_m = 1.0 # rank3_cost_multiplier
        self.r4_u2_boost = 1.0 # rank4_upg2_booster
        self.r5_u3_boost = 0.0 # rank5_upg3_booster
        self.r6_unl = False # rank6_unlocked
        self.r6_boost = 1.0 # rank6_booster
        # --- Crystalline State ---
        self.cryst_unl = False # crystalline_unlocked
        self.cryst_cnt = 0 # crystalline_times
        self.cryst_max = 4 # max_crystalline (can be dynamically updated)
        self.cryst_cost = 2.5e8 # crystalline_cost
        self.cr1_boost = 1.0 # cry1_booster
        self.cr1_u4_unl = False # cry1_upg4_unlocked
        self.cr2_boost = 1.0 # cry2_booster
        self.cr3_unl = False # cry3_unlocked
        self.cr4_unl = False # cry4_unlocked
        self.cr5_comp = False # crystalline_5_complete
        # --- Ascension State (Task 2) ---
        self.asc_unl = False # ascension_unlocked
        self.asc_cnt = 0 # ascension_count
        self.sd = 0.0 # stardust
        self.asc_cost = 1e27 # ascension_cost
        self.asc_lvl = 0 # NEW: Ascension Level
        self.asc_xp = 0.0 # NEW: Ascension Experience
        self.asc_first = False # NEW: has_ascended_once
        # --- Relics (Task 1: Keep, remove Astrals) ---
        self.relic_lvls = {} # relic_levels (Stores {relic_id: level})
        # --- Synergy/Later Effects ---
        self.cryst_comp_bonus = 1.0 # crystalline_completion_bonus
        self.p11_pps_boost = 0.0 # p11_pps_boost_per_clickpower
        self.p12_auto_u4 = False # p12_autobuy_upg4_unlocked
        self.p14_u2_boost = 1.0 # p14_upg2_boost
        self.p16_cost_reduc = 1.0 # p16_cost_reduction_factor
        self.p17_u1_boost = 1.0 # p17_upg1_boost_to_rank4 (This is the boost factor itself)
        self.p18_pass_clk = 0.0 # p18_passive_click_rate
        self.p19_boost = 1.0 # p19_boost_multiplier (This is the boost factor itself)
        self.p20_lim_brk = False # p20_limit_break_active
        self.p24_pur_cost_div = 1.0 # p24_purify_cost_divisor
        # --- Challenges (Task 5 & 6) ---
        self.chal_comps = {} # challenge_completions
        self.chal_sd_boost = 1.0 # challenge_stardust_boost (from c1 originally)
        self.chal_perm_clk_boost = 1.0 # NEW: Permanent click boost from potential challenge
        self.chal_upg_cost_scale_mult = 1.0 # NEW: Modifies upgrade cost scaling
        self.active_chal = None # NEW: ID of the currently active challenge (e.g., 'c1')
        # --- General State ---
        self.playtime = 0.0 # total_playtime (Resets on challenge entry/ascension)
        self.admin_panel_active = False
        self.last_save_time = time.time()
        # --- Scaling ---
        self.pps_pt_scale_exp = 1.0 # pps_point_scaling_exponent
        self.chal_eff_pps_exp_mod = 1.0 # NEW: Challenge effect modifier for PPS exponent
        self.chal_eff_cost_exp_mod = 1.0 # NEW: Challenge effect modifier for cost exponent

    # Task 2: Ascension XP/Level Helpers
    def get_xp_for_level(self, level):
        """Calculates XP needed for a given ascension level."""
        if level < 0: return 0 # Avoid issues with negative levels
        # Exponential scaling, adjust base/exponent as needed
        try:
             return 1000 * (1.8 ** level)
        except OverflowError:
             return float('inf') # Return infinity if calculation overflows

    def check_ascension_level_up(self):
        """Checks and processes ascension level ups."""
        leveled_up = False
        # Use max(0, self.asc_lvl) to handle potential negative level state during load/admin
        current_level = max(0, self.asc_lvl)
        needed = self.get_xp_for_level(current_level + 1)
        # Prevent infinite loops if needed is somehow zero or negative or inf
        while 0 < needed < float('inf') and self.asc_xp >= needed:
            self.asc_xp -= needed
            self.asc_lvl += 1 # Increment level directly
            current_level = self.asc_lvl # Update current level for next check
            leveled_up = True
            logging.info(f"Ascension Level Up! Reached Level {self.asc_lvl}")
            needed = self.get_xp_for_level(current_level + 1) # Check for next level
        if leveled_up:
            recalculate_derived_values() # Recalculate boosts after level up

    def get_asc_pt_boost(self): # get_ascension_point_boost
        """Calculates point boost from ascension level."""
        # Example: +10% multiplicative per level
        # Use max(0, self.asc_lvl) to avoid issues if level is negative
        try:
             base_boost = (1.10 ** max(0, self.asc_lvl))
        except OverflowError:
             base_boost = float('inf')
        return base_boost * self.get_chal_asc_pt_boost() # Factor in challenge rewards

    def get_asc_clk_boost(self): # get_ascension_click_boost
        """Calculates click boost from ascension level."""
        # Example: +5% multiplicative per level
        try:
            base_boost = (1.05 ** max(0, self.asc_lvl))
        except OverflowError:
            base_boost = float('inf')
        return base_boost * self.get_chal_asc_clk_boost() # Factor in challenge rewards

    # --- Challenge Reward Helpers (Examples - Expand as needed) ---
    def get_chal_asc_pt_boost(self):
        """Calculates challenge-based boost to Ascension Point Boost."""
        boost = 1.0
        # Example: Reward from C6
        c6_completions = self.chal_comps.get('c6', 0)
        if c6_completions > 0:
            # Example: +1% effectiveness per completion (multiplicative)
            boost *= (1.0 + 0.01 * c6_completions)
        return boost

    def get_chal_asc_clk_boost(self):
        """Calculates challenge-based boost to Ascension Click Boost."""
        boost = 1.0
        # Example: Could add a reward from another challenge here
        # cX_completions = self.chal_comps.get('cX', 0)
        # if cX_completions > 0:
        #     boost *= (1.0 + YYY * cX_completions)
        return boost

    def get_chal_relic_eff_boost(self, relic_id):
        """Calculates challenge-based boost to specific relic effectiveness."""
        boost = 1.0
        # Example: Reward from C7 affecting pt/clk relics
        c7_completions = self.chal_comps.get('c7', 0)
        if c7_completions > 0 and relic_id in ['relic_pt_mult', 'relic_clk_mult']:
             # Example: Make the base multiplier X% more effective (multiplicative)
             boost *= (1 + 0.002 * c7_completions) # Increases effectiveness by 0.2% per level
        return boost


# --- Global Variables ---
g = GameState() # Use shortened 'g' for game_state
points = 0.0
clicks = 0.0
pps = 0.0 # point_per_second
is_running = True
autobuy_thread = None

# --- Relic Definitions (Task 1: Max Level Applied) ---
RELICS_DATA = {
    # ID: { name, desc, cost_base, cost_scale, max_level, effect_func(level), Optional: effect_desc_func(level) }
    'relic_pt_mult': { 'name': "Star Prism", 'desc': "+5% Points per level (mult)", 'cost_base': 5, 'cost_scale': 1.8, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 1.05 ** lvl },
    'relic_clk_mult': { 'name': "Kinetic Shard", 'desc': "+8% Effective Clicks per level (mult)", 'cost_base': 5, 'cost_scale': 1.8, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 1.08 ** lvl },
    'relic_u1_str': { 'name': "Amplifying Lens", 'desc': "Upg1 base multiplier gain +0.02 per level", 'cost_base': 10, 'cost_scale': 2.0, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 0.02 * lvl }, # Capped
    'relic_p6_exp': { 'name': "Echoing Chamber", 'desc': "P6 Purify Boost ^(1 + 0.01*Lvl)", 'cost_base': 25, 'cost_scale': 2.5, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 1.0 + 0.01 * lvl }, # Capped
    'relic_sd_gain': { 'name': "Cosmic Magnet", 'desc': "+2% Stardust gain per level (mult)", 'cost_base': 50, 'cost_scale': 3.0, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 1.02 ** lvl },
    # Add more relics if desired
    'relic_u3_eff': { 'name': "Exponent Crystal", 'desc': "Upg3 Exponent Gain +1% per level (mult)", 'cost_base': 100, 'cost_scale': 2.2, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 1.01 ** lvl },
    'relic_crit_c': { 'name': "Focusing Matrix", 'desc': "+0.5% Crit Chance (additive)", 'cost_base': 30, 'cost_scale': 1.9, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 0.005 * lvl },
}

# Helper to get relic effect safely
def get_relic_effect(relic_id, default=1.0):
    """Gets the calculated effect of a relic at its current level, including challenge boosts."""
    global g
    lvl = g.relic_lvls.get(relic_id, 0)
    data = RELICS_DATA.get(relic_id)
    if data and 'effect' in data:
        try:
            # Apply challenge boosts to relic effectiveness
            eff_boost = g.get_chal_relic_eff_boost(relic_id)
            base_effect = data['effect'](lvl)

            # How the boost applies depends on the effect type
            if relic_id == 'relic_u1_str': # Additive base effect
                return base_effect * eff_boost # Assume boost multiplies the additive gain
            elif relic_id == 'relic_crit_c': # Additive base effect
                # Does C7 boost additive crit chance? Assume yes for now.
                return base_effect * eff_boost
            elif eff_boost != 1.0: # Multiplicative base effect, apply boost carefully
                # Boost the *percentage* increase: (Base - 1) * Boost + 1
                # Example: Base = 1.05, Boost = 1.1 => (1.05-1)*1.1 + 1 = 0.05*1.1 + 1 = 0.055 + 1 = 1.055
                # Ensure base_effect is a number
                if isinstance(base_effect, (int, float)):
                    return (base_effect - 1.0) * eff_boost + 1.0
                else:
                    logging.warning(f"Non-numeric base_effect {base_effect} for relic {relic_id}")
                    return default # Fallback
            else: # No boost, just return base effect
                return base_effect
        except Exception as e:
             logging.error(f"Error calculating effect for relic {relic_id}: {e}")
             return default # Fallback on error
    return default


# --- Prestige Descriptions / Challenges ---
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
    "Upg 2 base factor +50%.", # P14 (Index 13) (Description simplified)
    "Unlock buying Crystalline V.", # P15 (Index 14)
    "Reduce upgrade cost scaling per Crystalline.", # P16 (Index 15)
    "Upg 1 levels slightly boost Rank 4 effect.", # P17 (Index 16)
    "Passive Clicks (1% of Click Power/sec).", # P18 (Index 17)
    "Boost previous Purifications power x1.25.", # P19 (Index 18)
    "LIMIT BREAK: +10 Max Levels Upgs 1 & 2.", # P20 (Index 19)
    "P21: Faster Crystalline Autobuyer (if unlocked)", # P21 (Index 20) - Example new
    "P22: Stardust gain x1.1", # P22 (Index 21) - Example new
    "P23: Reduce Relic costs by 5%", # P23 (Index 22) - Example new
    "Purify cost / sqrt(Purify Times).", # P24 (Index 23)
]
CRYSTALLINE_DESCRIPTIONS = [
    "x3 point gain. Unlock Upgrade 4.", # C1 (Index 0)
    "Point gain ^1.5.", # C2 (Index 1)
    "Autobuy Upgrades 1-3.", # C3 (Index 2)
    "Unlock Clicking & Click Upgs.", # C4 (Index 3)
    "Unlock P16-20+. Activate Playtime boost (needs Upg6). Unlock Ascension.", # C5 (Index 4)
]

# --- Task 5 & 6: New Challenge Definitions ---
CHALLENGES = {
    # --- Existing Challenges (Modified) ---
    'c1': {
        'desc_base': "No Upg2: Reach High Points",
        'max_completions': 100,
        'requirement_func': lambda g, comp: 1e9 * (1000**(comp + 1)), # Much harder scaling
        'requirement_desc_func': lambda req: f"Req: {format_number(req)} Points",
        'check_func': lambda g, req: ( g.active_chal == 'c1' and not ma.isinf(points) and points >= req and g.upg2_lvl == 0 ),
        'reward_desc_func': lambda g, comp: f"Reward: +{1 + comp * 0.5:.1f}% Stardust Gain (Mult)", # Slower reward scaling
        # Reward is based on *current* completions AFTER this one would be finished
        # Ensure chal_comps lookup is safe
        'apply_reward_func': lambda g: setattr(g, 'chal_sd_boost', g.chal_sd_boost * (1.01 + g.chal_comps.get('c1', 0) * 0.005)),
        'restrictions_desc': "Cannot buy Upgrade 2.", # For UI
        'effect_func': None, # No active effect needed, just restriction check
        'reset_level': 'crystalline', # Reset needed to enter
    },
    'c2': {
        'desc_base': "Fast Clicks: Reach Clicks in 2 Mins",
        'max_completions': 100,
        'requirement_func': lambda g, comp: 1e7 * (15**(comp + 1)), # Harder click req
        'requirement_desc_func': lambda req: f"Req: {format_number(req)} Clicks",
        'check_func': lambda g, req: ( g.active_chal == 'c2' and clicks >= req and g.playtime <= 120 ), # Shorter time
        'reward_desc_func': lambda g, comp: f"Reward: +{0.2 + comp * 0.02:.2f}% Perm. Click Power (Mult)", # Less % gain per level (Corrected reward scaling)
        'apply_reward_func': lambda g: setattr(g, 'chal_perm_clk_boost', g.chal_perm_clk_boost * (1.002 + g.chal_comps.get('c2', 0) * 0.0002)), # Very slow scaling boost
        'restrictions_desc': "Complete within 120 seconds of starting challenge.",
        'effect_func': None,
        'reset_level': 'crystalline',
    },
    'c3': {
        'desc_base': "No Upg3: Reach Crystalline Count",
        'max_completions': 100,
        'requirement_func': lambda g, comp: comp + 1, # Keep simple req (req C1, C2, C3...)
        'requirement_desc_func': lambda req: f"Req: Reach Crystalline {req}",
        'check_func': lambda g, req: ( g.active_chal == 'c3' and g.cryst_cnt >= req and g.upg3_lvl == 0 ), # Cryst count within challenge
        'reward_desc_func': lambda g, comp: f"Reward: Upg3 Cost x{0.99** (comp+1):.3f}", # Much smaller cost reduction (Show effect for *next* completion)
        'apply_reward_func': lambda g: setattr(g, 'r3_cost_m', g.r3_cost_m * 0.99), # Apply 1% reduction each time
        'restrictions_desc': "Cannot buy Upgrade 3.",
        'effect_func': None,
        'reset_level': 'ascension', # Need full reset to attempt multiple crystallines
    },
    # --- New Challenges (Examples) ---
    'c4': {
        'desc_base': "Power Limit: Reach Points with PPS^0.9",
        'max_completions': 50,
        'requirement_func': lambda g, comp: 1e20 * (100**(comp + 1)), # High point req due to nerf
        'requirement_desc_func': lambda req: f"Req: {format_number(req)} Points",
        'check_func': lambda g, req: ( g.active_chal == 'c4' and points >= req ),
        'reward_desc_func': lambda g, comp: f"Reward: Improve PPS Point Scaling Exponent Floor by {0.001 * (comp+1):.3f}", # Affects min exponent in recalc
        # This reward needs to be applied within recalculate_derived_values based on chal_comps['c4']
        'apply_reward_func': lambda g: None, # No direct state change, effect is passive based on completions
        'restrictions_desc': "All Point Gain is raised to the power of 0.9.",
        'effect_func': lambda g: setattr(g, 'chal_eff_pps_exp_mod', 0.9), # Apply effect
        'reset_level': 'crystalline',
    },
    'c5': {
        'desc_base': "Expensive Growth: Reach Points with Faster Cost Scaling",
        'max_completions': 50,
        'requirement_func': lambda g, comp: 1e15 * (50**(comp + 1)),
        'requirement_desc_func': lambda req: f"Req: {format_number(req)} Points",
        'check_func': lambda g, req: ( g.active_chal == 'c5' and points >= req ),
        'reward_desc_func': lambda g, comp: f"Reward: Upg 1-4 Base Cost Scaling reduced by {(comp+1)*0.1:.1f}% (Mult)", # Reduce base scaling factor slightly
        # This applies multiplicatively: Cost *= (BaseFactor * ChalEffect * ChalReward)**Level
        'apply_reward_func': lambda g: setattr(g, 'chal_upg_cost_scale_mult', 1.0 / (1.0 + 0.001 * (g.chal_comps.get('c5',0)+1))), # Reduces the scaling factor towards 1
        'restrictions_desc': "Upg 1-4 base cost scaling factor increased by 25%.",
        'effect_func': lambda g: setattr(g, 'chal_eff_cost_exp_mod', 1.25), # Apply effect
        'reset_level': 'crystalline',
    },
    'c6': {
        'desc_base': "No Purify: Reach Crystalline",
        'max_completions': 10, # Limited completions make sense here
        'requirement_func': lambda g, comp: 1, # Always req Crystalline 1
        'requirement_desc_func': lambda req: f"Req: Reach Crystalline 1",
        'check_func': lambda g, req: ( g.active_chal == 'c6' and g.cryst_cnt >= req and g.pur_cnt == 0 ),
        'reward_desc_func': lambda g, comp: f"Reward: +{(comp+1)}% effectiveness to Ascension Level Point Boost", # Additive % boost
        'apply_reward_func': lambda g: None, # Passive effect applied in get_chal_asc_pt_boost based on completions
        'restrictions_desc': "Cannot Purify.",
        'effect_func': None, # Handled by checking pur_cnt in purify() potentially, or just UI disable
        'reset_level': 'ascension', # Needs full reset
    },
     'c7': {
        'desc_base': "Manual Only: Reach High Clicks",
        'max_completions': 25,
        'requirement_func': lambda g, comp: 1e8 * (20**(comp + 1)),
        'requirement_desc_func': lambda req: f"Req: {format_number(req)} Clicks", # Requirement is total clicks, but source is restricted
        'check_func': lambda g, req: ( g.active_chal == 'c7' and clicks >= req and g.upg8_lvl == 0 and g.p18_pass_clk == 0), # Check no auto-clickers active
        'reward_desc_func': lambda g, comp: f"Reward: +{0.2 + comp * 0.02:.2f}% Effectiveness for Point/Click Relics", # Reward based on *next* completion
        'apply_reward_func': lambda g: None, # Passive effect applied in get_relic_effect via get_chal_relic_eff_boost
        'restrictions_desc': "Cannot buy Upg8. P18 disabled.",
        # Effect func ensures P18 is off during the challenge recalc checks
        'effect_func': lambda g: setattr(g, 'p18_pass_clk', 0) if g.active_chal == 'c7' else None,
        'reset_level': 'crystalline',
    },
}

# --- Core Calculation Logic ---
def calculate_click_point_bonus():
    """Calculates click bonus based on points > 1 Sp, with diminishing returns."""
    global points, g
    current_points = points if isinstance(points, (int, float)) and not ma.isnan(points) and not ma.isinf(points) else 0.0
    if current_points <= POINT_THRESHOLD_SP: return 1.0
    try:
        # Prevent log errors with 0 or negative points
        if current_points <= 0: return 1.0
        # Use max with a small positive number to prevent log10(<=0)
        orders = ma.log10(max(1e-300, current_points / POINT_THRESHOLD_SP))

        # C4 reward doesn't affect this scaling, it affects the PPS scaling exponent floor
        # Ensure log10 arg > 0 by using max(0, orders)
        dampened_exponent = ma.log10(max(0, orders) + 1.0) * 2.0 # Soft cap exponent
        return max(1.0, 2.0 ** dampened_exponent)
    except (ValueError, OverflowError) as e:
        logging.warning(f"Click point bonus calculation error: {e}")
        return 1.0

def get_upgrade_cost_scale_mult():
    """Combined cost scaling multiplier factor from temporary challenge effects."""
    # This returns the *temporary* increase from C5 effect
    return g.chal_eff_cost_exp_mod # Only return temporary effect here

def get_upgrade2_factor(g_state): # Pass g_state to avoid potential global issues
    """Calculates the base multiplier factor for Upgrade 2."""
    base = 1.10
    # P14 boost effect is multiplicative on the base factor's *gain* (e.g. 1.1 -> 1.15)
    gain = 0.10
    if g_state.pur_cnt >= 14:
         p_boost = g_state.p19_boost if g_state.pur_cnt >= 19 else 1.0 # P19 boosts P14
         # P14 adds +50% gain, potentially boosted by P19
         gain *= (1.0 + 0.5 * p_boost)

    return 1.0 + gain


def recalculate_multiplier_strength():
    """Recalculates the strength multiplier from Upg2 levels."""
    global g
    factor = get_upgrade2_factor(g) # Use the helper function

    # P17 effect: Boosts R4 effect based on Upg1 levels
    p17_eff_boost = 1.0
    if g.pur_cnt >= 17:
         # Use g.p17_u1_boost which holds the P19 adjusted boost factor
         # Example: Each Upg1 adds 0.2% effectiveness to R4 boost, factor included in p17_u1_boost
         p17_eff_boost = (1.0 + g.upg1_lvl * 0.002 * g.p17_u1_boost) # Apply P17 boost factor here

    # Apply P17 boost to the Rank 4 multiplier (g.r4_u2_boost is base R4 effect)
    effective_r4_boost = g.r4_u2_boost * p17_eff_boost

    try:
        g.mult_str = (factor ** g.upg2_lvl) * effective_r4_boost
    except OverflowError:
        g.mult_str = float('inf')
        logging.warning("Overflow calculating multiplier strength.")

def calculate_point_per_second():
    global pps, g
    _pps = 0.0
    try:
        # --- Calculate Relic Bonuses First ---
        relic_point_mult = get_relic_effect('relic_pt_mult', 1.0)
        relic_p6_exp_mult = get_relic_effect('relic_p6_exp', 1.0)
        relic_click_mult = get_relic_effect('relic_clk_mult', 1.0)

        # --- Ascension Boosts ---
        asc_point_boost = g.get_asc_pt_boost()
        asc_click_boost = g.get_asc_clk_boost() # Needed for click contribution

        # --- Calculate Base PPS ---
        # P11 adds based on effective click power
        effective_click_power = g.clk_pow * g.chal_perm_clk_boost * asc_click_boost * g.clk_pt_scale * relic_click_mult
        base_pps_from_clicks = effective_click_power * g.p11_pps_boost if g.pur_cnt >= 11 else 0.0
        base_pps = 1.0 + base_pps_from_clicks

        # --- Apply Multipliers ---
        effective_multiplier = g.mult * g.mult_str
        _pps = base_pps * effective_multiplier * g.r1_boost

        # P6 effect: raise boost to relic exponent
        if g.r6_unl:
             try: _pps *= (g.r6_boost ** relic_p6_exp_mult)
             except OverflowError: _pps = float('inf')

        _pps *= g.cr1_boost # C1 boost
        _pps *= g.cryst_comp_bonus # P13 boost

        # P19 boost (applied here multiplicatively to previous P effects implicitly included)
        if g.pur_cnt >= 19: _pps *= g.p19_boost

        # Playtime boost (C5 + Upg6)
        if g.cr5_comp and g.upg6_comp: _pps *= calculate_playtime_multiplier()

        # Apply major multipliers last
        _pps *= asc_point_boost # Ascension Level Boost
        _pps *= relic_point_mult # Relic Point Multiplier

        # Check for infinity before applying exponents
        if ma.isinf(_pps):
             pps = float('inf')
             return # Skip exponents if already infinite

        # --- Apply Exponents ---
        # C2 exponent
        if g.cr2_boost != 1.0: _pps = _pps ** g.cr2_boost if _pps > 0 else 0
        # Upg3 exponent
        if g.pps_exp != 1.0: _pps = _pps ** g.pps_exp if _pps > 0 else 0
        # Point scaling exponent (soft cap)
        if g.pps_pt_scale_exp < 1.0: _pps = _pps ** g.pps_pt_scale_exp if _pps > 0 else 0

        # --- Apply Challenge Effects Last ---
        # C4 power limit
        if g.chal_eff_pps_exp_mod != 1.0:
             _pps = _pps ** g.chal_eff_pps_exp_mod if _pps > 0 else 0

    except (ValueError, OverflowError) as e:
        logging.warning(f"PPS calculation error: {e}. PPS intermediate value={_pps}")
        _pps = float('inf') if isinstance(e, OverflowError) else 0.0 # Assume Inf on overflow, 0 otherwise
    except Exception as e:
         logging.error(f"Unexpected error in PPS calculation: {e}", exc_info=True)
         _pps = 0.0

    # Final PPS assignment
    pps = _pps if isinstance(_pps, (int, float)) and not ma.isnan(_pps) else 0.0
    # Cap PPS reasonably if needed? For now, allow infinity.
    # pps = min(pps, 1e308) # Example cap


def calculate_playtime_multiplier():
    """Calculates the multiplier based on playtime (logarithmic)."""
    global g
    playtime_sec = g.playtime if isinstance(g.playtime, (int, float)) else 0
    if playtime_sec <= 0: return 1.0
    try:
        # Ensure argument to log is positive
        minutes_played = max(1e-9, playtime_sec / 60.0) # Use small positive if playtime is tiny
        bonus = ma.log(minutes_played + 1) + 1.0 # Use log(minutes+1)
        return max(1.0, round(bonus, 3))
    except (ValueError, OverflowError) as e:
        logging.warning(f"Playtime multiplier calculation error: {e}")
        return 1.0


def recalculate_derived_values():
    """Recalculates all game values that depend on multiple base stats or upgrades."""
    global g, points

    # Reset temporary challenge effects before recalculating
    g.chal_eff_pps_exp_mod = 1.0
    g.chal_eff_cost_exp_mod = 1.0 # Reset cost exponent mod
    if g.active_chal and g.active_chal in CHALLENGES:
        effect_func = CHALLENGES[g.active_chal].get('effect_func')
        if effect_func:
            try:
                effect_func(g) # Apply active challenge effect (e.g., sets chal_eff_pps_exp_mod for C4)
            except Exception as e:
                logging.error(f"Error applying challenge {g.active_chal} effect: {e}")

    # --- Calculate Relic Bonuses ---
    relic_p6_exp_mult = get_relic_effect('relic_p6_exp', 1.0)
    relic_clk_mult = get_relic_effect('relic_clk_mult', 1.0)
    relic_crit_c_bonus = get_relic_effect('relic_crit_c', 0.0) # Additive crit chance

    # --- Ascension Boosts ---
    asc_point_boost = g.get_asc_pt_boost()
    asc_click_boost = g.get_asc_clk_boost()

    # --- Purify Based Effects ---
    # P19 boost factor - used by other P effects
    p19_boost_factor = g.p19_boost if g.pur_cnt >= 19 else 1.0

    # P6 base effect
    g.r6_boost = ((1.0 + g.pur_cnt)**2.0) if g.r6_unl else 1.0

    # Apply P19 boost to relevant P-rewards *factors* where applicable
    g.p11_pps_boost = 0.001 * p19_boost_factor if g.pur_cnt >= 11 else 0.0
    g.cryst_comp_bonus = 1.0 + (g.cryst_cnt * 0.05 * p19_boost_factor) if g.pur_cnt >= 13 else 1.0
    g.p14_u2_boost = 1.0 + (0.5 * p19_boost_factor) if g.pur_cnt >= 14 else 1.0 # Boosts the gain part (+50%)
    g.p16_cost_reduc = max(0.5, 1.0 - (g.cryst_cnt * 0.005 * p19_boost_factor)) if g.pur_cnt >= 16 else 1.0
    g.p17_u1_boost = p19_boost_factor if g.pur_cnt >= 17 else 1.0 # This factor boosts the P17 effect in mult_str calc
    g.p18_pass_clk = 0.01 * p19_boost_factor if g.pur_cnt >= 18 else 0.0
    # Disable P18 if in C7 (handled by effect_func now)
    # if g.active_chal == 'c7': g.p18_pass_clk = 0.0
    g.p24_pur_cost_div = max(1.0, ma.sqrt(max(0,g.pur_cnt)) * p19_boost_factor) if g.pur_cnt >= 24 else 1.0


    # --- Point Scaling Exponent (Soft Cap) ---
    g.clk_pt_scale = calculate_click_point_bonus() # Click scaling based on points
    current_points_safe = points if isinstance(points, (int, float)) and not ma.isnan(points) and not ma.isinf(points) else 0.0
    g.pps_pt_scale_exp = 1.0 # Default exponent

    # C4 reward improves the *floor* of the exponent, not the reduction strength
    c4_completions = g.chal_comps.get('c4', 0)
    c4_floor_bonus = 0.001 * c4_completions # +0.001 to floor per C4 completion

    if current_points_safe > POINT_THRESHOLD_SP:
        try:
            if current_points_safe <= 0: # Avoid log error
                 orders = -300 # Arbitrarily large negative order
            else:
                 orders = ma.log10(max(1e-300, current_points_safe / POINT_THRESHOLD_SP))

            red_str = 0.05 if g.p20_lim_brk else 0.02 # Reduction strength
            base_min_exp = 0.3 if g.p20_lim_brk else 0.5 # Base floor
            final_min_exp = min(1.0, base_min_exp + c4_floor_bonus) # Apply C4 reward to floor

            # Calculate target exponent based on reduction
            target_exp = 1.0 - (ma.log10(max(0, orders) + 1.0) * red_str)
            g.pps_pt_scale_exp = max(final_min_exp, target_exp) # Apply floor

        except (ValueError, OverflowError): pass # Keep 1.0 on error


    # --- Click Effects ---
    g.clk_crit_c = min(1.0, (0.05 * g.upg7_lvl) + relic_crit_c_bonus ) # Add relic bonus
    g.clk_crit_m = 2.0 + (0.2 * g.upg7_lvl)
    # Use clk_pow, chal_perm_clk_boost, asc_click_boost, clk_pt_scale
    effective_base_click = g.clk_pow * g.chal_perm_clk_boost * asc_click_boost * g.clk_pt_scale * relic_clk_mult
    base_auto_click = effective_base_click * (0.01 * g.upg8_lvl)
    passive_click_from_p18 = effective_base_click * g.p18_pass_clk if g.p18_pass_clk > 0 else 0.0
    # Disable auto-clickers if in C7 (Handled by effect_func setting p18_pass_clk to 0)
    g.auto_cps = base_auto_click + passive_click_from_p18
    if g.active_chal == 'c7': g.auto_cps = 0.0


    # --- Recalc Dependent Values ---
    recalculate_multiplier_strength() # Depends on Upg1/2 levels, R4, P17
    calculate_point_per_second() # Depends on almost everything

    # --- Update Max Purify/Crystalline ---
    g.pur_max = 20 if g.cr5_comp else (15 if g.upg5_comp else 10)
    g.cryst_max = 5 if g.pur_cnt >= 15 else 4 # C5 requires P15

    logging.debug(f"Derived recalculated (PPS Scale Exp: {g.pps_pt_scale_exp:.3f}, Asc Lvl: {g.asc_lvl}, Chal: {g.active_chal})")


# --- Game Loop Logic ---
def game_tick():
    global points, clicks, pps, g
    try:
        # Ensure values are numeric and finite before calculations
        _pps = pps if isinstance(pps, (int, float)) and ma.isfinite(pps) else 0.0
        current_points = points if isinstance(points, (int, float)) and ma.isfinite(points) else 0.0
        current_clicks = clicks if isinstance(clicks, (int, float)) and ma.isfinite(clicks) else 0.0
        _cps = g.auto_cps if isinstance(g.auto_cps, (int, float)) and ma.isfinite(g.auto_cps) else 0.0

        # Add gains, check for overflow
        try:
            points = min(float('inf'), current_points + _pps * TICK_INTERVAL_S)
        except OverflowError: points = float('inf')
        try:
             clicks = min(float('inf'), current_clicks + _cps * TICK_INTERVAL_S)
        except OverflowError: clicks = float('inf')

        g.playtime += TICK_INTERVAL_S

        # Check active challenge completion (throttled)
        if g.active_chal and int(g.playtime * 10) % 10 == 0: # Check roughly every second
            check_challenge_completion()

    except Exception as e: logging.error(f"Error in game_tick: {e}", exc_info=True)

def game_loop_thread_func():
    logging.info("Game loop thread started.")
    while is_running:
        start = time.monotonic()
        try:
            game_tick()
        except Exception as e:
             logging.error(f"Unhandled exception in game_tick caught by loop: {e}", exc_info=True)
             # Potentially add a small delay here to prevent tight error loops
             time.sleep(1)

        elapsed = time.monotonic() - start
        # Ensure sleep time is non-negative
        sleep_duration = max(0, TICK_INTERVAL_S - elapsed)
        time.sleep(sleep_duration)
    logging.info("Game loop thread finished.")


# --- Upgrade Functions (Apply Cost Scaling Multiplier) ---
def get_effective_cost_factor(base_factor):
     """Applies challenge cost scaling modifications."""
     # C5 Temporary effect increases the factor
     temp_factor_mult = get_upgrade_cost_scale_mult() # From chal_eff_cost_exp_mod
     # C5 Permanent reward decreases the factor (g.chal_upg_cost_scale_mult is < 1)
     perm_factor_mult = g.chal_upg_cost_scale_mult
     return base_factor * temp_factor_mult * perm_factor_mult

def upgrade1():
    global points, g
    cost = g.upg1_cost
    # Check level against float max
    if g.upg1_lvl >= g.upg1_max or points < cost: return

    # Avoid issues if cost is inf
    if ma.isinf(cost): return

    points -= cost
    g.upg1_lvl += 1
    relic_u1_bonus = get_relic_effect('relic_u1_str', 0.0) # Additive bonus
    g.mult += (1.0 + relic_u1_bonus) # Apply additive bonus from relic
    level_factor = get_effective_cost_factor(1.15) # Base factor 1.15, modified by C5 stuff
    # Use r3_cost_m, p16_cost_reduc
    reduction = g.r3_cost_m * g.p16_cost_reduc
    try:
        g.upg1_cost = round(10.0 * (level_factor ** g.upg1_lvl) * reduction, 2)
    except OverflowError:
        g.upg1_cost = float('inf')
    recalculate_derived_values()

def upgrade2():
    global points, g
    # Check challenge restrictions (C1)
    if g.active_chal == 'c1': return
    cost = g.upg2_cost
    if g.upg2_lvl >= g.upg2_max or points < cost: return
    if ma.isinf(cost): return

    points -= cost
    g.upg2_lvl += 1
    level_factor = get_effective_cost_factor(1.25) # Base factor 1.25
    reduction = g.r3_cost_m * g.p16_cost_reduc
    try:
        g.upg2_cost = round(100.0 * (level_factor ** g.upg2_lvl) * reduction, 2)
    except OverflowError:
        g.upg2_cost = float('inf')
    recalculate_derived_values()

def upgrade3():
    global points, g
    # Check challenge restrictions (C3)
    if g.active_chal == 'c3': return
    cost = g.upg3_cost
    if g.upg3_lvl >= g.upg3_max or points < cost: return
    if ma.isinf(cost): return

    points -= cost
    g.upg3_lvl += 1
    # Use r5_u3_boost
    base_gain = 0.05 + g.r5_u3_boost
    relic_u3_mult = get_relic_effect('relic_u3_eff', 1.0) # Multiplicative bonus from relic
    base_gain *= relic_u3_mult

    threshold = 2.0
    reduction_factor = 0.1
    effective_gain = base_gain
    if g.pps_exp > threshold: effective_gain *= reduction_factor
    if g.p20_lim_brk: effective_gain *= reduction_factor # Double reduction
    g.pps_exp += max(0.001, effective_gain) # Apply soft-capped gain
    level_factor = get_effective_cost_factor(1.35) # Base factor 1.35
    reduction = g.r3_cost_m * g.p16_cost_reduc
    try:
        g.upg3_cost = round(10000.0 * (level_factor ** g.upg3_lvl) * reduction, 2)
    except OverflowError:
        g.upg3_cost = float('inf')
    recalculate_derived_values()

def upgrade4():
    global points, g
    cost = g.upg4_cost
    if not g.cr1_u4_unl: return # Use cr1_u4_unl
    if g.upg4_lvl >= g.upg4_max or points < cost: return
    if ma.isinf(cost): return

    points -= cost
    g.upg4_lvl += 1
    g.upg3_max += 1.0 # Still increases Upg3 max
    level_factor = get_effective_cost_factor(1.50) # Base factor 1.5
    reduction = g.p16_cost_reduc # No R3 mult here
    try:
        g.upg4_cost = round(10000000.0 * (level_factor ** g.upg4_lvl) * reduction, 2)
    except OverflowError:
        g.upg4_cost = float('inf')
    # No recalc needed? Upg4 effect is passive on Upg3 max, cost update is enough.
    # Let's add recalc just in case future effects depend on Upg4 level.
    recalculate_derived_values()


def upgrade5(): # Click Upg
    global clicks, g
    req = 100.0
    if not g.cr4_unl or g.upg5_comp: return # Use cr4_unl, upg5_comp
    if clicks >= req:
        # clicks -= req # Typically click upgrades don't consume clicks? Keep if intended.
        g.upg5_comp = True
        g.pur_max = 15 # Still unlocks P11-15
        logging.info("Upg5 Done!")
        recalculate_derived_values() # Update pur_max etc.
    else: logging.debug(f"Need {format_number(req - clicks)} clicks for Upg5")

def upgrade6(): # Click Upg
    global clicks, g
    req = 100000.0
    if not g.cr4_unl or g.upg6_comp: return # Use cr4_unl, upg6_comp
    if clicks >= req:
        # clicks -= req
        g.upg6_comp = True
        logging.info("Upg6 Done!")
        recalculate_derived_values() # Enables C5 playtime effect application
    else: logging.debug(f"Need {format_number(req - clicks)} clicks for Upg6")

def upgrade7(): # Click Upg - Crit
    global clicks, g
    cost = g.upg7_cost
    if not g.cr4_unl: return
    if g.upg7_lvl >= g.upg7_max or clicks < cost: return
    if ma.isinf(cost): return

    clicks -= cost # Consumes clicks
    g.upg7_lvl += 1
    try:
        # Cost doesn't use the general factor, only upgrade 1-4 per C5 desc
        g.upg7_cost *= 1.5
    except OverflowError:
        g.upg7_cost = float('inf')
    recalculate_derived_values()

def upgrade8(): # Click Upg - Auto
    global clicks, g
    # Check challenge restrictions (C7)
    if g.active_chal == 'c7': return
    cost = g.upg8_cost
    if not g.cr4_unl: return
    if g.upg8_lvl >= g.upg8_max or clicks < cost: return
    if ma.isinf(cost): return

    clicks -= cost # Consumes clicks
    g.upg8_lvl += 1
    try:
         # Cost doesn't use the general factor
        g.upg8_cost *= 2.0
    except OverflowError:
        g.upg8_cost = float('inf')
    recalculate_derived_values()

# --- Prestige Functions ---
def apply_purification_effects(p_level_index):
    global g, autobuy_thread # Use 'g'
    p_num = p_level_index + 1

    # --- Apply P effects based on p_num ---
    if p_num == 1: g.r1_boost = 3.0
    elif p_num > 1: g.r1_boost *= 2.0 # Subsequent purifies still boost Rank 1

    if p_num == 2:
        g.r2_unl = True
        g.upg1_max += 1.0
        g.upg2_max += 1.0
    if p_num == 3:
        g.r3_unl = True
        g.r3_cost_m *= 0.95
    if p_num == 4: g.r4_u2_boost = 3.0 # Base R4 effect
    if p_num == 5: g.r5_u3_boost = 0.01
    if p_num == 6: g.r6_unl = True
    if p_num == 10: g.cryst_unl = True
    if p_num == 12:
        g.p12_auto_u4 = True
        start_autobuy_thread_if_needed()
    if p_num == 19: g.p19_boost = 1.25 # Set the P19 boost factor
    if p_num == 20 and g.cr5_comp and not g.p20_lim_brk:
        g.p20_lim_brk = True
        levels_to_add = 10.0
        g.upg1_max += levels_to_add
        g.upg2_max += levels_to_add
        logging.info(f"P20 Limit Break Activated! (+{int(levels_to_add)} Max Lvl Upg1 & Upg2)")
    # P21 (Autobuy speed), P22 (SD Gain), P23 (Relic Cost) are applied elsewhere

def apply_crystalline_effects(cry_level_achieved):
    global g, autobuy_thread # Use 'g'
    if cry_level_achieved == 1:
        g.cr1_boost = 3.0
        g.cr1_u4_unl = True
    elif cry_level_achieved == 2: g.cr2_boost = 1.5
    elif cry_level_achieved == 3:
        g.cr3_unl = True
        start_autobuy_thread_if_needed()
    elif cry_level_achieved == 4: g.cr4_unl = True
    elif cry_level_achieved == 5:
        g.cr5_comp = True
        g.asc_unl = True # Unlock Ascension

# --- Reset Functions ---
def reset_for_purify(keep_challenge_progress=False):
    global points, g # Use 'g'
    points = 0.0
    # Reset upgrades
    g.upg1_lvl = 0
    g.upg1_cost = 10.0
    g.upg2_lvl = 0
    g.upg2_cost = 100.0
    g.upg3_lvl = 0
    g.upg3_cost = 10000.0
    g.upg4_lvl = 0
    g.upg4_cost = 10000000.0
    # Reset multipliers/exponents
    g.mult = 1.0
    g.pps_exp = 1.0
    # Reset playtime unless specified otherwise (e.g., during challenge)
    if not keep_challenge_progress: g.playtime = 0.0

    # Apply starting Upg1 levels if any (e.g. future source)
    start_lvl1 = 0 # Placeholder for now
    if start_lvl1 > 0:
        temp_cost = 10.0
        reduction = g.r3_cost_m * g.p16_cost_reduc
        factor = get_effective_cost_factor(1.15)
        relic_u1_bonus = get_relic_effect('relic_u1_str', 0.0)
        for i in range(start_lvl1):
            if g.upg1_lvl >= g.upg1_max: break # Respect max level
            g.upg1_lvl += 1
            g.mult += (1.0 + relic_u1_bonus)
            try:
                temp_cost = round(10.0 * (factor ** g.upg1_lvl) * reduction, 2)
            except OverflowError:
                temp_cost = float('inf')
                break # Stop if cost becomes infinite
        g.upg1_cost = temp_cost

def reset_for_crystalline(keep_challenge_progress=False):
    global points, g # Use 'g'
    # Reset Purify progress
    g.pur_cnt = 0
    g.pur_cost = 1000.0
    g.r1_boost = 1.0
    g.r2_unl = False
    g.r3_unl = False
    # Keep permanent challenge reward for r3_cost_m if needed, or reset? Assuming reset for now.
    g.r3_cost_m = 1.0 # Reset unless C3 reward logic changes
    g.r4_u2_boost = 1.0
    g.r5_u3_boost = 0.0
    g.r6_unl = False
    g.r6_boost = 1.0
    # Reset P-based effects that are not permanent boosts
    g.p11_pps_boost = 0.0
    g.p12_auto_u4 = False
    g.cryst_comp_bonus = 1.0
    g.p14_u2_boost = 1.0 # Base value, recalculate applies boost
    g.p16_cost_reduc = 1.0
    g.p17_u1_boost = 1.0 # Base factor, recalculate applies boost
    g.p18_pass_clk = 0.0
    g.p19_boost = 1.0 # Base factor, recalculate applies boost
    g.p20_lim_brk = False # Limit break is reset on Crystalline/Ascension
    g.p24_pur_cost_div = 1.0
    # Reset upgrade max levels (respect P2/P20 limit breaks)
    # Max levels are reset to base, P2/P20 applied by Purify/Crystalline funcs if re-achieved
    g.upg1_max = 25.0
    g.upg2_max = 10.0
    g.upg3_max = 10.0 # Upg4 additions reset here
    g.upg4_max = 5.0
    # Perform Purify reset
    reset_for_purify(keep_challenge_progress=keep_challenge_progress)
    # Keep Crystalline unlocked status
    g.cryst_unl = True

def reset_for_ascension(keep_challenge_progress=False):
    global points, clicks, g # Use 'g'
    logging.info("Resetting for Ascension...")
    points = 0.0
    clicks = 0.0
    # Reset Crystalline progress
    g.cryst_cnt = 0
    g.cryst_cost = 2.5e8
    g.cr1_boost = 1.0
    g.cr1_u4_unl = False
    g.cr2_boost = 1.0
    g.cr3_unl = False
    g.cr4_unl = False
    g.cr5_comp = False
    # Reset Click Upgrades
    g.upg5_comp = False
    g.upg6_comp = False
    g.upg7_lvl = 0
    g.upg7_cost = 1e6
    g.upg7_max = 50.0
    g.upg8_lvl = 0
    g.upg8_cost = 1e9
    g.upg8_max = 100.0
    g.clk_pow = 1.0 # Reset base click power
    g.clk_crit_c = 0.0
    g.clk_crit_m = 2.0
    g.auto_cps = 0.0
    # Perform Crystalline reset (which includes Purify reset)
    reset_for_crystalline(keep_challenge_progress=keep_challenge_progress)
    # Keep Ascension unlocked status
    g.asc_unl = True
    # Keep Challenge completions and active challenge state unless specified
    if not keep_challenge_progress:
        g.active_chal = None # Exit challenge on Ascension typically

# --- Task 6: Challenge Reset ---
def reset_for_challenge(challenge_id):
    global g
    chal_data = CHALLENGES.get(challenge_id)
    if not chal_data:
        logging.error(f"Attempted to reset for unknown challenge: {challenge_id}")
        return

    reset_type = chal_data.get('reset_level', 'ascension') # Default to full reset
    logging.info(f"Entering Challenge '{challenge_id}'. Performing '{reset_type}' reset.")

    # Preserve state that should NOT be reset by challenges
    _asc_lvl = g.asc_lvl
    _asc_xp = g.asc_xp
    _asc_first = g.asc_first
    _relic_lvls = g.relic_lvls.copy()
    _chal_comps = g.chal_comps.copy() # Keep permanent completions
    _chal_sd_boost = g.chal_sd_boost
    _chal_perm_clk_boost = g.chal_perm_clk_boost
    _chal_upg_cost_scale_mult = g.chal_upg_cost_scale_mult
    # Add other permanent challenge rewards here if needed

    # Perform the requested reset level
    if reset_type == 'purify':
        reset_for_purify(keep_challenge_progress=True) # Keep playtime etc. for chal check
    elif reset_type == 'crystalline':
        reset_for_crystalline(keep_challenge_progress=True)
    elif reset_type == 'ascension':
        reset_for_ascension(keep_challenge_progress=True)
    else: # Default to ascension reset if invalid type specified
        logging.warning(f"Unknown reset level '{reset_type}' for challenge, defaulting to ascension.")
        reset_for_ascension(keep_challenge_progress=True)

    # Restore persistent state
    g.asc_lvl = _asc_lvl
    g.asc_xp = _asc_xp
    g.asc_first = _asc_first
    g.relic_lvls = _relic_lvls
    g.chal_comps = _chal_comps
    g.chal_sd_boost = _chal_sd_boost
    g.chal_perm_clk_boost = _chal_perm_clk_boost
    g.chal_upg_cost_scale_mult = _chal_upg_cost_scale_mult
    # Restore other permanent rewards if added

    # Set the active challenge and reset playtime for this challenge run
    g.active_chal = challenge_id
    g.playtime = 0.0 # Start timer for this challenge attempt

    # Recalculate values with challenge effects potentially applied
    recalculate_derived_values()
    logging.info(f"Challenge '{challenge_id}' started.")

# --- Action Functions (Purify, Crystalline, Ascend) ---
def purify():
    global points, g # Use 'g'
    # Check challenge restrictions
    if g.active_chal == 'c6':
        logging.warning("Cannot Purify while in Challenge C6.")
        return

    # Recalculate max purify based on current state *before* checking
    recalculate_derived_values() # Ensures g.pur_max is up-to-date
    current_max = g.pur_max

    can_purify, reason = False, "Max Reached"
    next_p_num = g.pur_cnt + 1
    if g.pur_cnt < current_max:
        if next_p_num <= 10: can_purify=True
        elif next_p_num <= 15:
            can_purify=g.upg5_comp
            reason="Requires Upg5"
        else: # P16+
            can_purify=g.cr5_comp
            reason="Requires C5"

    if not can_purify:
        logging.warning(f"Cannot Purify: {reason}")
        return

    cost = g.pur_cost / g.p24_pur_cost_div # Apply P24 divisor
    if points < cost:
        logging.warning(f"Need {format_number(cost)} points for Purify {next_p_num}.")
        return

    # Apply effects *before* incrementing count
    apply_purification_effects(g.pur_cnt)
    prev_times = g.pur_cnt
    g.pur_cnt += 1
    # Don't subtract points if points are infinite (avoids NaN issues)
    if not ma.isinf(points):
        points = max(0, points - cost) # Prevent negative points
    reset_for_purify(keep_challenge_progress=(g.active_chal is not None)) # Keep playtime if in challenge
    # Calculate next cost based on previous count
    try:
        g.pur_cost = round(g.pur_cost * (3.0 + prev_times), 2)
    except OverflowError:
        g.pur_cost = float('inf')
    logging.info(f"Purified! Times: {g.pur_cnt}/{int(current_max)}. Next Base Cost: {format_number(g.pur_cost)}")
    recalculate_derived_values()

def crystalline():
    global points, g # Use 'g'
    # Check challenge restrictions
    # if g.active_chal == 'some_chal_blocking_cryst': return

    if not g.cryst_unl:
        logging.warning("Crystalline locked (Requires P10).")
        return

    # Recalculate max based on current P count *before* check
    recalculate_derived_values() # Ensures g.cryst_max is correct
    eff_max = g.cryst_max

    next_c_num = g.cryst_cnt + 1
    if g.cryst_cnt >= eff_max:
        logging.warning(f"Max Crystallines reached ({int(eff_max)}).")
        return
    if g.cryst_cnt == 4 and g.pur_cnt < 15: # Check specific C5 requirement
        logging.warning("Need P15 to perform Crystalline 5.")
        return

    cost = g.cryst_cost
    if points < cost:
        logging.warning(f"Need {format_number(cost)} points for Crystalline {next_c_num}.")
        return

    # Apply effect for the level being achieved
    apply_crystalline_effects(next_c_num)
    g.cryst_cnt += 1
    # Don't subtract points if points are infinite
    if not ma.isinf(points):
        points = max(0, points - cost)
    reset_for_crystalline(keep_challenge_progress=(g.active_chal is not None)) # Keep playtime if in challenge
    # Define Crystalline costs
    costs = {0: 2.5e8, 1: 1e12, 2: 1e15, 3: 1e18, 4: 1e21} # Costs for C1 to C5
    g.cryst_cost = costs.get(g.cryst_cnt, float('inf')) # Get cost for *next* Crystalline
    logging.info(f"Crystallized! Times: {g.cryst_cnt}/{int(eff_max)}. Next cost: {format_number(g.cryst_cost)}")
    recalculate_derived_values()

def ascend():
    global points, g # Use 'g'
    if not g.asc_unl:
        logging.warning("Ascension locked (Requires C5).")
        return
    # Cannot ascend while in a challenge
    if g.active_chal:
         logging.warning(f"Cannot Ascend while in Challenge '{g.active_chal}'. Exit first.")
         return

    cost = g.asc_cost
    if points < cost:
        logging.warning(f"Need {format_number(cost)} points to Ascend.")
        return

    # Calculate Stardust Gain
    sd_gain = 0
    relic_sd_boost = get_relic_effect('relic_sd_gain', 1.0)
    p22_boost = 1.1 if g.pur_cnt >= 22 else 1.0 # Apply P22 boost

    try:
        if points >= cost and not ma.isinf(points) and points > 0:
            # Logarithmic scaling based on points over cost, sqrt of crystalline count
            log_arg = max(1, points / max(1, cost)) # Prevent division by zero if cost is 0 somehow
            # Base gain + scaling factors
            sd_gain = ma.floor(
                (1 + 0.5 * ma.log10(log_arg)) # Base 1 + log scaling
                * ma.sqrt(g.cryst_cnt + 1) # Boost from crystalline count
                * g.chal_sd_boost # Boost from C1 reward
                * relic_sd_boost # Boost from Relic
                * p22_boost # Boost from P22
            )
            sd_gain = max(1, sd_gain) # Ensure at least 1 SD gain if cost is met
    except (ValueError, OverflowError) as e:
         logging.warning(f"Stardust gain calculation error: {e}")
         sd_gain = 0 # Default to 0 on error

    if sd_gain <= 0:
        logging.warning("Cannot ascend for 0 Stardust (requires more points).")
        return

    # Calculate Ascension XP Gain (Task 2)
    xp_gain = 0.0
    try:
         if points >= cost and not ma.isinf(points) and points > 0:
            base_xp = 100 # Minimum XP for ascending
            # Scaled XP - adjust formula as needed for balance
            scaled_xp = 50 * ma.log10(max(1, points / 1e40)) # Scale based on log of points (adjust divisor 1e40)
            # Bonus XP based on Stardust gained
            sd_xp_bonus = sd_gain * 10 # e.g., 10 XP per stardust
            xp_gain = base_xp + scaled_xp + sd_xp_bonus
            xp_gain = max(0, xp_gain) # Ensure non-negative XP
    except (ValueError, OverflowError) as e:
        logging.warning(f"Ascension XP gain calculation error: {e}")
        xp_gain = 0.0

    logging.info(f"Ascending! Gaining {format_number(sd_gain)} Stardust and {format_number(xp_gain)} Ascension XP.")
    g.sd += sd_gain
    g.asc_xp += xp_gain # Add XP
    g.asc_cnt += 1

    # Set flag for first ascension (Task 3)
    if not g.asc_first:
        g.asc_first = True
        logging.info("First Ascension Complete! Challenge text revealed.")

    # Perform reset (will reset playtime)
    reset_for_ascension(keep_challenge_progress=False) # Full reset, exit any challenge state implicitly

    # Check for level up AFTER resetting and adding XP
    g.check_ascension_level_up()

    # Recalculate values after reset and potential level up
    recalculate_derived_values()


# --- Clicking Action ---
def click_power_action():
    global clicks, g # Use 'g'
    if not g.cr4_unl: return # Still need C4 for clicking

    # Base click power modified by permanent challenge boosts, ascension, scaling, relics
    relic_clk_mult = get_relic_effect('relic_clk_mult', 1.0)
    asc_click_boost = g.get_asc_clk_boost()
    # Use clk_pow, chal_perm_clk_boost, asc_click_boost, clk_pt_scale
    base_click = g.clk_pow * g.chal_perm_clk_boost * asc_click_boost * g.clk_pt_scale * relic_clk_mult

    # Apply crit chance/multiplier
    final_click = base_click * (g.clk_crit_m if random.random() < g.clk_crit_c else 1.0)

    try:
        clicks = min(float('inf'), clicks + final_click)
    except OverflowError:
        clicks = float('inf')


# --- Autobuyer Logic ---
def autobuy_tick():
    global g # Use 'g'
    try:
        # C3 autobuys Upg 1-3
        if g.cr3_unl:
            # Add small random delay to spread out purchases slightly
            if random.random() < 0.8: upgrade1()
            if random.random() < 0.6: upgrade2()
            if random.random() < 0.4: upgrade3()
        # P12 autobuys Upg 4
        if g.p12_auto_u4:
            if random.random() < 0.5: upgrade4()
        # P21 might make this faster or more efficient (e.g., buy max) - requires more logic
    except Exception as e: logging.error(f"Error in autobuy_tick: {e}", exc_info=True)

def autobuy_thread_func():
    logging.info("Autobuyer started.")
    base_sleep = 0.1
    p21_speed_factor = 0.5 if g.pur_cnt >= 21 else 1.0 # Example P21 effect
    while is_running:
        sleep_time = base_sleep * p21_speed_factor
        if g.cr3_unl or g.p12_auto_u4:
             autobuy_tick()
        time.sleep(sleep_time)
    logging.info("Autobuyer finished.")

def start_autobuy_thread_if_needed():
    global autobuy_thread, g # Use 'g'
    if g.cr3_unl or g.p12_auto_u4:
        if not autobuy_thread or not autobuy_thread.is_alive():
            logging.info("Starting autobuy thread.")
            autobuy_thread = th.Thread(target=autobuy_thread_func, daemon=True)
            autobuy_thread.start()

# --- Relic Buying Function ---
def buy_relic(relic_id):
    global g # Use 'g'
    if relic_id not in RELICS_DATA:
        logging.warning(f"Unknown relic: {relic_id}")
        return

    data = RELICS_DATA[relic_id]
    lvl = g.relic_lvls.get(relic_id, 0)
    # Use constant RELIC_MAX_LEVEL (Task 1)
    max_lvl = data.get('max_level', RELIC_MAX_LEVEL) # Fallback to global max if specific not set

    if max_lvl is not None and lvl >= max_lvl:
        logging.info(f"Relic '{data['name']}' is at max level ({max_lvl}).")
        return

    # Calculate cost
    try:
        cost = round(data['cost_base'] * (data['cost_scale'] ** lvl))
    except OverflowError:
        cost = float('inf') # Cost is infinite if scaling overflows

    if ma.isinf(cost):
         logging.warning(f"Cannot afford Relic '{data['name']}' (Lvl {lvl+1}) - Cost overflowed.")
         return


    # Apply P23 cost reduction
    p23_reduction = 0.95 if g.pur_cnt >= 23 else 1.0
    final_cost = round(cost * p23_reduction)

    if g.sd >= final_cost:
        g.sd -= final_cost
        g.relic_lvls[relic_id] = lvl + 1
        logging.info(f"Bought Relic '{data['name']}' (Lvl {lvl + 1}) for {format_number(final_cost)} Stardust.")
        recalculate_derived_values() # Recalculate stats after buying relic
    else:
        needed = final_cost - g.sd
        logging.warning(f"Need {format_number(needed)} more Stardust for '{data['name']}' (Lvl {lvl+1}). Cost: {format_number(final_cost)}")


# --- Challenge Management Functions (Task 6) ---

challenge_buttons = {} # To store Enter/Exit buttons for UI update

def enter_challenge(challenge_id):
    """Initiates entering a challenge after confirmation."""
    global g
    if g.active_chal:
        messagebox.showwarning("Challenge Active", f"You are already in Challenge '{g.active_chal}'.\nExit the current challenge first.")
        return
    if not g.asc_first:
         messagebox.showwarning("Locked", "Challenges are locked until you Ascend for the first time.")
         return

    chal_data = CHALLENGES.get(challenge_id)
    if not chal_data:
        logging.error(f"Invalid challenge ID for enter: {challenge_id}")
        return

    # Check max completions
    current_completions = g.chal_comps.get(challenge_id, 0)
    max_completions = chal_data.get('max_completions')
    if max_completions is not None and current_completions >= max_completions:
        messagebox.showinfo("Maxed Out", f"You have already maxed out completions for Challenge '{challenge_id}' ({int(max_completions)}).")
        return

    # Confirmation dialog
    reset_level = chal_data.get('reset_level', 'ascension').capitalize()
    restrictions = chal_data.get('restrictions_desc', 'Standard rules apply.')
    msg = (f"Enter Challenge: {chal_data['desc_base']}?\n\n"
           f"This will perform a full **{reset_level} Reset** (keeping Ascension/Relics/Completions).\n\n"
           f"Restrictions: {restrictions}\n\n"
           f"Are you sure?")
    confirmed = messagebox.askyesno("Enter Challenge Confirmation", msg)

    if confirmed:
        reset_for_challenge(challenge_id)
        # Update UI immediately after starting
        updateui()

def exit_challenge():
    """Exits the current challenge."""
    global g
    if not g.active_chal:
        logging.info("Not currently in a challenge.")
        return

    exiting_chal_id = g.active_chal
    logging.info(f"Exiting Challenge '{exiting_chal_id}' manually.")
    g.active_chal = None
    # Perform a standard ascension reset when exiting a challenge
    # This ensures a clean state regardless of the challenge's internal reset level
    reset_for_ascension(keep_challenge_progress=False) # Perform full reset, clear playtime
    recalculate_derived_values()
    logging.info("Exited challenge. Performed Ascension reset.")
    # Update UI
    updateui()

def complete_challenge(challenge_id):
    """Called when challenge requirements are met."""
    global g
    if g.active_chal != challenge_id:
        logging.warning(f"Attempted to complete challenge {challenge_id}, but not active.")
        return

    chal_data = CHALLENGES.get(challenge_id)
    if not chal_data:
        logging.error(f"Invalid challenge ID for complete: {challenge_id}")
        g.active_chal = None # Clear invalid state
        recalculate_derived_values()
        updateui()
        return

    # Check max completions again (safety)
    current_completions = g.chal_comps.get(challenge_id, 0)
    max_completions = chal_data.get('max_completions')
    if max_completions is not None and current_completions >= max_completions:
        logging.warning(f"Challenge {challenge_id} already maxed upon completion check.")
        g.active_chal = None # Exit challenge state
        recalculate_derived_values()
        updateui()
        return

    logging.info(f"Challenge Completed: {chal_data['desc_base']} (Level {current_completions + 1})")

    # Apply reward before incrementing count, so reward func sees correct 'current' level
    try:
        # Pass the *next* completion level to the reward function if needed
        apply_func = chal_data.get('apply_reward_func')
        if apply_func:
            apply_func(g) # Apply the reward
            g.chal_comps[challenge_id] = current_completions + 1 # Increment permanent completion count *after* applying reward
            logging.info(f"Applied reward for {challenge_id}. Total completions: {g.chal_comps[challenge_id]}")
        else:
             g.chal_comps[challenge_id] = current_completions + 1 # Increment even if no reward func
             logging.info(f"Incremented completions for {challenge_id} (no specific reward func). Total: {g.chal_comps[challenge_id]}")

    except Exception as e:
        logging.error(f"Error applying reward for challenge {challenge_id}: {e}", exc_info=True)
        # Don't increment completions if reward failed? Decide policy.
        # For now, we log the error but still increment completions and reset.

    # Exit the challenge state and perform reset
    g.active_chal = None
    reset_for_ascension(keep_challenge_progress=False) # Full reset after completion
    recalculate_derived_values() # Recalculate with new reward potentially active
    # Show completion message *after* reset and recalc
    messagebox.showinfo("Challenge Complete!", f"You successfully completed:\n{chal_data['desc_base']} (Level {g.chal_comps.get(challenge_id, '??')})")
    updateui() # Update UI to reflect challenge completion and reset


def check_challenge_completion():
    """Checks if the *currently active* challenge's completion criteria are met."""
    global g
    if not g.active_chal:
        return # Not in a challenge

    chal_id = g.active_chal
    chal_data = CHALLENGES.get(chal_id)
    if not chal_data:
        logging.error(f"Active challenge '{chal_id}' not found in definitions.")
        g.active_chal = None # Clear invalid state
        return

    # Check if already maxed (shouldn't happen if entry logic is correct, but safety check)
    lvl = g.chal_comps.get(chal_id, 0)
    max_lvl = chal_data.get('max_completions')
    if max_lvl is not None and lvl >= max_lvl:
        # This case should ideally be handled by enter_challenge preventing entry
        logging.warning(f"Max completions reached for active challenge {chal_id} during check.")
        # Force exit if somehow entered maxed challenge
        exit_challenge()
        return

    try:
        req = chal_data['requirement_func'](g, lvl)
        if chal_data['check_func'](g, req):
            # Completion criteria met!
            complete_challenge(chal_id)
    except Exception as e:
        logging.error(f"Error checking completion for challenge {chal_id}: {e}", exc_info=True)
        # Optionally exit challenge on error? Or just log? Logging for now.


# --- Save/Load (Updated for new state variables) ---
def save_game():
    global points, clicks, g # Use 'g'
    logging.info("Saving game...")
    try:
        # Dynamically get attributes from GameState instance 'g'
        save_data = {k: getattr(g, k) for k in g.__dict__ if not k.startswith('_')}

        # Add global variables explicitly
        save_data.update({
            "version": SAVE_VERSION,
            "points": points,
            "clicks": clicks,
            "last_save_time": time.time() # Update last save time here
        })
        g.last_save_time = save_data["last_save_time"] # Update in-memory state too

        # Convert potentially problematic types (like Inf) to strings for JSON
        def convert_inf_nan(o):
            if isinstance(o, float):
                if ma.isinf(o):
                    return "__Infinity__" if o > 0 else "__-Infinity__"
                elif ma.isnan(o):
                    return "__NaN__"
            return o # Keep other types as is

        # Use default=convert_inf_nan to handle special float values
        json_string = json.dumps(save_data, separators=(',', ':'), default=convert_inf_nan)
        encoded_bytes = base64.b64encode(json_string.encode('utf-8'))
        encoded_string = encoded_bytes.decode('utf-8')
        with open(SAVE_FILE, "w", encoding='utf-8') as f: f.write(encoded_string) # Specify encoding
        logging.info(f"Game saved to {SAVE_FILE}")
    except Exception as e: logging.error(f"Save failed: {e}", exc_info=True)

def autosave_thread_func():
    logging.info("Autosave started.")
    while is_running:
        time.sleep(AUTOSAVE_INTERVAL_S)
        if is_running: # Check again before saving, in case of fast shutdown
            save_game()
    logging.info("Autosave finished.")

def load_game():
    global points, clicks, g, is_running # Use 'g'
    if not os.path.exists(SAVE_FILE):
        logging.info("No save file found. Starting new game.")
        g = GameState() # Initialize new state
        points = 0.0
        clicks = 0.0
        recalculate_derived_values()
        return
    logging.info(f"Loading game from {SAVE_FILE}...")
    try:
        with open(SAVE_FILE, "r", encoding='utf-8') as f: encoded_string = f.read() # Specify encoding
        decoded_bytes = base64.b64decode(encoded_string.encode('utf-8'))
        json_string = decoded_bytes.decode('utf-8')

        # Hook to convert special string values back to float representations
        def decode_inf_nan(dct):
            for k, v in dct.items():
                if isinstance(v, str):
                    if v == "__Infinity__":
                        dct[k] = float('inf')
                    elif v == "__-Infinity__":
                        dct[k] = float('-inf')
                    elif v == "__NaN__":
                        dct[k] = float('nan')
            return dct

        # Load JSON with the object_hook to handle Inf/NaN strings
        loaded_data = json.loads(json_string, object_hook=decode_inf_nan)

        loaded_version = loaded_data.get("version", 0)
        if loaded_version != SAVE_VERSION:
            logging.warning(f"Save version mismatch (Save: {loaded_version}, Game: {SAVE_VERSION}). Starting new game to prevent errors.")
            # Optional: Implement migration logic here if feasible/desired
            g = GameState()
            points = 0.0
            clicks = 0.0
            recalculate_derived_values()
            save_game() # Save the new state immediately
            return

        # Create a default state to get expected types and default values
        default_g = GameState()

        # Load global vars first
        points = loaded_data.get("points", 0.0)
        clicks = loaded_data.get("clicks", 0.0)
        # Ensure types are correct (JSON loads numbers as float/int, hook handles Inf/NaN)
        if not isinstance(points, (int, float)): points = 0.0
        if not isinstance(clicks, (int, float)): clicks = 0.0

        # Load GameState attributes
        for key, default_value in default_g.__dict__.items():
            if key.startswith('_'): continue # Skip private attributes
            loaded_value = loaded_data.get(key) # Get value from loaded data dict
            expected_type = type(default_value)

            # Type checking and conversion (handle potential None from missing keys)
            final_value = default_value # Start with default
            if loaded_value is not None:
                # Attempt conversion or assignment if type matches or is compatible
                try:
                    if expected_type == float and isinstance(loaded_value, (int, float)):
                        final_value = float(loaded_value)
                    elif expected_type == int and isinstance(loaded_value, (int, float)) and ma.isfinite(loaded_value): # Ensure finite for int conversion
                        final_value = int(loaded_value)
                    elif expected_type == bool: # Handle bool explicitly
                        final_value = bool(loaded_value)
                    elif expected_type == dict and isinstance(loaded_value, dict):
                         final_value = loaded_value # Assume dict structure is okay if type matches
                    elif expected_type == str and isinstance(loaded_value, str):
                         final_value = loaded_value
                    # Add list, set etc. if needed here
                    # Fallback check if types already match
                    elif isinstance(loaded_value, expected_type):
                        final_value = loaded_value
                    else:
                         # Log type mismatch if conversion wasn't handled above
                         logging.warning(f"Load type mismatch for '{key}' (Expected {expected_type.__name__}, Got {type(loaded_value).__name__}). Using default.")
                         final_value = default_value # Revert to default
                except Exception as type_e:
                    logging.warning(f"Load error converting '{key}' (Value: {loaded_value}): {type_e}. Using default.")
                    final_value = default_value # Revert to default on conversion error
            else:
                # Key was missing in save file, use default value
                final_value = default_value

            # Set the attribute on the actual game state 'g'
            setattr(g, key, final_value)


        # Offline progress calculation
        last_save = g.last_save_time if isinstance(g.last_save_time, (int, float)) else time.time()
        time_offline = max(0, time.time() - last_save)

        # Only calculate significant offline time, and not if in a challenge
        # Also skip if core values are infinite
        if time_offline > 5 and not g.active_chal and ma.isfinite(points) and ma.isfinite(clicks):
            logging.info("Calculating offline progress...")
            # Recalculate PPS/CPS *before* adding offline gains
            recalculate_derived_values()
            # Use lower offline rates (ensure calculated pps/cps are finite)
            off_pps = pps * 0.5 if ma.isfinite(pps) else 0.0
            off_pts = off_pps * time_offline
            off_cps = g.auto_cps * 0.5 if ma.isfinite(g.auto_cps) else 0.0
            off_clicks = off_cps * time_offline

            # Add offline gains safely, checking for overflow
            try:
                points = min(float('inf'), points + off_pts)
            except OverflowError: points = float('inf')
            try:
                clicks = min(float('inf'), clicks + off_clicks)
            except OverflowError: clicks = float('inf')

            logging.info(f"Offline: {time_offline:.1f}s. Gained approx ~{format_number(off_pts)} pts, ~{format_number(off_clicks)} clicks.")

        # Ensure core values are not NaN after load/offline calc
        if ma.isnan(points): points = 0.0
        if ma.isnan(clicks): clicks = 0.0

        g.last_save_time = time.time() # Update last save time after load/offline calc
        logging.info("Save loaded successfully.")
        recalculate_derived_values() # Final recalculation after load

    except json.JSONDecodeError as e:
        logging.error(f"Load failed: Invalid JSON data in save file. {e}", exc_info=True)
        logging.info("Starting new game.")
        g = GameState()
        points = 0.0
        clicks = 0.0
        recalculate_derived_values()
        save_game()
    except base64.binascii.Error as e:
         logging.error(f"Load failed: Invalid Base64 data. {e}", exc_info=True)
         logging.info("Starting new game.")
         g = GameState()
         points = 0.0
         clicks = 0.0
         recalculate_derived_values()
         save_game()
    except Exception as e:
        logging.error(f"Load failed: {e}", exc_info=True)
        logging.info("Starting new game due to load error.")
        g = GameState()
        points = 0.0
        clicks = 0.0
        recalculate_derived_values()
        save_game()


# --- UI Update Function (Major Changes Needed) ---
# Declare UI elements globally (or pass them around)
pointlabel=None
ppslabel=None
clicklabel=None
stardustlabel=None
asc_lvl_label=None # New label for Ascension Level
asc_prog_label=None # New label for Ascension Progress
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
# astral_buttons REMOVED
challenge_widgets = {} # Stores labels and buttons for each challenge
relic_widgets = {}
exit_challenge_button = None # Button to exit current challenge
relic_title = None # Keep track of relic title label


def update_button_style(button, state):
    """Updates button bootstyle and tk state."""
    if not button or not isinstance(button, ttk.Button): return
    try:
        style = "primary-outline" # Default
        tk_state = tk.NORMAL
        if state == "maxed":
            style = "secondary-outline" # Less prominent than danger for maxed
            tk_state = tk.DISABLED
        elif state == "buyable": style = "success" # Solid color for buyable
        elif state == "locked":
            style = "secondary-outline"
            tk_state = tk.DISABLED
        elif state == "disabled": # General disabled state
             style = "secondary-outline"
             tk_state = tk.DISABLED
        elif state == "active": # For active challenge button
             style = "warning" # Yellow for active
             tk_state = tk.DISABLED
        button.configure(bootstyle=style, state=tk_state)
    except tk.TclError: pass # Ignore errors if widget destroyed during update
    except Exception as e: logging.error(f"Button style error: {e}")

def updateui():
    global points, clicks, pps, g, window, is_running # Use global 'g'
    try:
        if not is_running or not window.winfo_exists(): return

        # --- Helper ---
        def fmt_max(v): return 'Inf' if ma.isinf(v) else int(v)

        # --- Update Top Labels ---
        if pointlabel: pointlabel.configure(text=f"Points: {format_number(points)}")
        if ppslabel: ppslabel.configure(text=f"PPS: {format_number(pps)}")
        if clicklabel: clicklabel.configure(text=f"Clicks: {format_number(clicks)}")
        if stardustlabel: stardustlabel.configure(text=f"Stardust: {format_number(g.sd)}")

        # --- Prestige Tab ---
        if purificationlabel and purificationbutton:
            # Recalculate max purify here to ensure it reflects current state
            current_pur_max = 20.0 if g.cr5_comp else (15.0 if g.upg5_comp else 10.0)

            next_lvl = g.pur_cnt + 1
            can, reason, desc = False, "Max", ""
            cost = g.pur_cost / g.p24_pur_cost_div # Use P24 divisor

            # Challenge C6 Restriction
            chal_c6_active = (g.active_chal == 'c6')

            if chal_c6_active:
                 can, reason = False, "In C6"
            elif g.pur_cnt < current_pur_max:
                if next_lvl <= 10: can=True
                elif next_lvl <= 15:
                    can=g.upg5_comp
                    reason="Req Upg5"
                else: # P16+
                    can=g.cr5_comp
                    reason="Req C5"

                # Check affordability only if otherwise possible
                if can and points < cost:
                     can = False
                     reason = "Need Pts"

                desc_idx = g.pur_cnt
                desc = PURIFY_DESCRIPTIONS[desc_idx] if desc_idx < len(PURIFY_DESCRIPTIONS) else f"P{next_lvl}"
                if not can and reason!="Max": desc = f"({reason}) {desc}"
                purificationlabel.configure(text=f"Purify {next_lvl}/{int(current_pur_max)}: {desc}\nCost: {format_number(cost)}")

            else: # Max reached
                purificationlabel.configure(text=f"Max Purifications ({g.pur_cnt}/{int(current_pur_max)})")

            # Determine button state
            if chal_c6_active: status = "disabled"
            elif g.pur_cnt >= current_pur_max: status = "maxed"
            elif can: status = "buyable"
            elif reason in ["Req Upg5", "Req C5", "Need Pts"]: status = "default" # Not buyable, but unlockable
            else: status = "locked" # Maxed or other reason
            update_button_style(purificationbutton, status)


        if crystalinelabel and crystalinebutton:
            # Recalculate max cryst here
            current_cryst_max = 5.0 if g.pur_cnt >= 15 else 4.0

            next_lvl = g.cryst_cnt + 1
            can, reason, desc = True, "", ""
            cost=g.cryst_cost

            if not g.cryst_unl: can,reason=False,"Req P10"
            elif g.cryst_cnt >= current_cryst_max: can,reason=False,"Max"
            elif g.cryst_cnt == 4 and g.pur_cnt < 15: can,reason=False,"Req P15"
            # Check affordability only if otherwise possible
            elif points < cost: can, reason = False, "Need Pts"

            if reason=="Req P10":
                crystalinelabel.configure(text="Locked (Requires P10)")
                status = "locked"
            elif reason=="Max":
                crystalinelabel.configure(text=f"Max Crystallines ({g.cryst_cnt}/{int(current_cryst_max)})")
                status = "maxed"
            else:
                desc_idx = g.cryst_cnt
                desc = CRYSTALLINE_DESCRIPTIONS[desc_idx] if desc_idx < len(CRYSTALLINE_DESCRIPTIONS) else f"C{next_lvl}"
                if not can and reason: desc = f"({reason}) {desc}"
                crystalinelabel.configure(text=f"Crystalline {next_lvl}/{int(current_cryst_max)}: {desc}\nCost: {format_number(cost)}")
                if can: status="buyable"
                elif reason in ["Req P15", "Need Pts"]: status="default"
                else: status="locked" # Should not happen if logic above is correct

            update_button_style(crystalinebutton, status)

        # --- Ascension Tab ---
        if asc_lvl_label: asc_lvl_label.configure(text=f"Ascension Level: {g.asc_lvl}")
        if asc_prog_label:
            xp_needed = g.get_xp_for_level(g.asc_lvl + 1)
            xp_curr = g.asc_xp
            # Handle edge case where needed is 0 or inf
            if xp_needed <= 0 or ma.isinf(xp_needed): prog_perc = 0.0
            else: prog_perc = min(100.0, (xp_curr / xp_needed * 100)) # Cap at 100%
            asc_prog_label.configure(text=f"XP: {format_number(xp_curr)} / {format_number(xp_needed)} ({prog_perc:.1f}%)")

        if ascensionlabel and ascensionbutton:
            can, reason, desc = True, "", ""
            sd_preview=0
            cost = g.asc_cost

            if not g.asc_unl: can,reason=False,"Req C5"
            elif g.active_chal: can, reason=False, f"In Chal {g.active_chal}"
            elif points < cost: can, reason = False, "Need Pts"
            else: # Calculate SD preview if possible
                try:
                    if points >= cost and not ma.isinf(points) and points > 0 :
                         log_arg=max(1, points / max(1, cost)) # Prevent div by zero
                         r_boost=get_relic_effect('relic_sd_gain', 1.0)
                         p22_b = 1.1 if g.pur_cnt >= 22 else 1.0
                         sd_preview = ma.floor( (1 + 0.5*ma.log10(log_arg)) * ma.sqrt(g.cryst_cnt+1) * g.chal_sd_boost * r_boost * p22_b )
                         sd_preview=max(0,sd_preview) # Ensure non-negative
                         if sd_preview == 0: reason = "Need More Pts for SD" # Reason why it's not buyable even if cost met
                except (ValueError, OverflowError) as e:
                     logging.debug(f"SD preview calc error: {e}")
                     pass # Keep sd_preview as 0

            desc = f"Reset ALL non-permanent progress for Stardust & XP.\nGain approx: {format_number(sd_preview)} SD"
            if not can: desc = f"({reason}) {desc}"

            ascensionlabel.configure(text=f"Ascend #{g.asc_cnt+1}: {desc}\nCost: {format_number(cost)} Points")

            # Determine button state
            if not g.asc_unl: status = "locked"
            elif g.active_chal: status = "disabled" # Can't ascend in challenge
            elif can and sd_preview > 0 : status = "buyable"
            elif reason == "Need Pts": status = "default" # Affordability issue
            elif reason == "Need More Pts for SD": status = "default" # Affordability issue (indirect)
            else: status = "locked" # Other reason (e.g. Req C5)

            update_button_style(ascensionbutton,status)

        # --- Relics Tab ---
        # Show/Hide entire tab content based on asc_first
        if relic_title: # Check if title label exists
             if g.asc_first:
                 relic_title.grid() # Show title
                 for rid, data in RELICS_DATA.items():
                     widgets = relic_widgets.get(rid)
                     if not widgets: continue
                     name_lbl, desc_lbl, level_lbl, cost_lbl, buy_btn = widgets

                     # Show relic widgets
                     for w in widgets: w.grid() # Use grid() to show

                     lvl = g.relic_lvls.get(rid, 0)
                     max_lvl = data.get('max_level', RELIC_MAX_LEVEL)
                     is_max = (max_lvl is not None and lvl >= max_lvl)

                     level_text = f"Level: {lvl}" + (f"/{max_lvl}" if max_lvl is not None else f"/{RELIC_MAX_LEVEL}")
                     level_lbl.configure(text=level_text)

                     if is_max:
                         cost_lbl.configure(text="Cost: MAX")
                         update_button_style(buy_btn, "maxed")
                     else:
                         try:
                             cost=round(data['cost_base']*(data['cost_scale']**lvl))
                         except OverflowError:
                             cost = float('inf')

                         p23_reduction = 0.95 if g.pur_cnt >= 23 else 1.0
                         final_cost = round(cost * p23_reduction) if ma.isfinite(cost) else float('inf')

                         cost_str = f"Cost: {format_number(final_cost)} SD"
                         if p23_reduction < 1.0 and ma.isfinite(final_cost): cost_str += " (P23)" # Shorten discount text
                         elif ma.isinf(final_cost): cost_str = "Cost: ---" # Indicate overflow

                         cost_lbl.configure(text=cost_str)
                         status="buyable" if ma.isfinite(final_cost) and g.sd >= final_cost else "default"
                         update_button_style(buy_btn,status)
             else:
                 # Hide all relic widgets if not ascended yet
                  relic_title.grid_remove() # Hide title too
                  for rid in RELICS_DATA:
                     widgets = relic_widgets.get(rid)
                     if widgets:
                         for w in widgets: w.grid_remove()


        # --- Upgrades Tab ---
        # Upg 1
        cost1 = g.upg1_cost
        can_buy1 = points >= cost1 and g.upg1_lvl < g.upg1_max
        if upgrade1costlabel: upgrade1costlabel.configure(text=f"Cost: {format_number(cost1)}")
        if upgrade1explainlabel: upgrade1explainlabel.configure(text=f"+{(1.0+get_relic_effect('relic_u1_str',0.0)):.2f} Base Mult [{int(g.upg1_lvl)}/{fmt_max(g.upg1_max)}]")
        if button1: update_button_style(button1, "maxed" if g.upg1_lvl>=g.upg1_max else ("buyable" if can_buy1 else "default"))
        # Upg 2
        cost2 = g.upg2_cost
        chal_c1_active = (g.active_chal == 'c1')
        can_buy2 = points >= cost2 and g.upg2_lvl < g.upg2_max and not chal_c1_active
        if upgrade2costlabel: upgrade2costlabel.configure(text=f"Cost: {format_number(cost2)}")
        if upgrade2explainlabel:
            fact=get_upgrade2_factor(g)
            upgrade2explainlabel.configure(text=f"Strength x{format_number(g.mult_str)} [{int(g.upg2_lvl)}/{fmt_max(g.upg2_max)}] (x{fact:.2f})") # Format strength
        if button2:
            status = "disabled" if chal_c1_active else ("maxed" if g.upg2_lvl>=g.upg2_max else ("buyable" if can_buy2 else "default"))
            update_button_style(button2, status)
        # Upg 3
        cost3 = g.upg3_cost
        chal_c3_active = (g.active_chal == 'c3')
        can_buy3 = points >= cost3 and g.upg3_lvl < g.upg3_max and not chal_c3_active
        if upgrade3costlabel: upgrade3costlabel.configure(text=f"Cost: {format_number(cost3)}")
        if upgrade3explainlabel: upgrade3explainlabel.configure(text=f"PPS Exp ^{g.pps_exp:.3f} [{int(g.upg3_lvl)}/{fmt_max(g.upg3_max)}]")
        if button3:
            status = "disabled" if chal_c3_active else ("maxed" if g.upg3_lvl>=g.upg3_max else ("buyable" if can_buy3 else "default"))
            update_button_style(button3, status)
        # Upg 4
        cost4 = g.upg4_cost
        lock4=not g.cr1_u4_unl
        can_buy4 = points >= cost4 and g.upg4_lvl < g.upg4_max and not lock4
        if upgrade4costlabel: upgrade4costlabel.configure(text="Locked (C1)" if lock4 else f"Cost: {format_number(cost4)}")
        if upgrade4explainlabel: upgrade4explainlabel.configure(text="???" if lock4 else f"+1 Max Upg3 [{int(g.upg4_lvl)}/{fmt_max(g.upg4_max)}]")
        if button4:
            status="locked" if lock4 else ("maxed" if g.upg4_lvl>=g.upg4_max else ("buyable" if can_buy4 else "default"))
            update_button_style(button4, status)

        # --- Clicking Tab ---
        lock_click = not g.cr4_unl
        if clickbutton:
            crit_eff = get_relic_effect('relic_crit_c', 0.0) # Get additive relic crit
            crit=f" ({ (g.clk_crit_c)*100:.1f}% Crit, x{g.clk_crit_m:.1f})" if g.upg7_lvl > 0 or crit_eff > 0 else ""
            relic_m=get_relic_effect('relic_clk_mult', 1.0)
            asc_clk_m=g.get_asc_clk_boost()
            # Click value shown should reflect boosts
            click_v = g.clk_pow * g.chal_perm_clk_boost * asc_clk_m * g.clk_pt_scale * relic_m
            clickbutton.configure(text=f"Click! (+{format_number(click_v)}{crit})" if not lock_click else "Locked (C4)", state=tk.NORMAL if not lock_click else tk.DISABLED)

        # Click Upg 5, 6, 7, 8
        lock_click_upgs = not g.cr4_unl
        # Upg5
        req5 = 1000.0
        st5, ct5, et5 = "locked", "Locked (C4)", "???"
        if not lock_click_upgs:
            if g.upg5_comp: st5, ct5, et5 = "maxed", "Purchased", f"Max Purify: 15"
            else:
                # Click upgrades requiring clicks check current clicks
                st5 = "buyable" if clicks >= req5 else "default"
                ct5 = f"Cost: {format_number(req5)} Clicks"
                et5 = "Unlock P11-15"
        if upgrade5costlabel: upgrade5costlabel.configure(text=ct5)
        if upgrade5explainlabel: upgrade5explainlabel.configure(text=et5)
        if button5: update_button_style(button5, st5)
        # Upg6
        req6 = 100000.0
        st6, ct6, et6 = "locked", "Locked (C4)", "???"
        if not lock_click_upgs:
            if g.upg6_comp: st6, ct6, et6 = "maxed", "Purchased", "C5 Effects Active"
            else:
                st6 = "buyable" if clicks >= req6 else "default"
                ct6 = f"Cost: {format_number(req6)} Clicks"
                et6 = "Enable C5 Effects"
        if upgrade6costlabel: upgrade6costlabel.configure(text=ct6)
        if upgrade6explainlabel: upgrade6explainlabel.configure(text=et6)
        if button6: update_button_style(button6, st6)
        # Upg7 (Crit)
        cost7 = g.upg7_cost
        st7, ct7, et7 = "locked", "Locked (C4)", "???"
        if not lock_click_upgs:
            if g.upg7_lvl >= g.upg7_max: st7, ct7, et7 = "maxed", "MAXED", f"Crit: {g.clk_crit_c*100:.1f}% x{g.clk_crit_m:.1f}"
            else:
                st7 = "buyable" if clicks >= cost7 else "default"
                ct7 = f"Cost: {format_number(cost7)} Clicks"
                et7 = f"Crit Chance/Mult [{int(g.upg7_lvl)}/{fmt_max(g.upg7_max)}]"
        if upgrade7costlabel: upgrade7costlabel.configure(text=ct7)
        if upgrade7explainlabel: upgrade7explainlabel.configure(text=et7)
        if button7: update_button_style(button7, st7)
        # Upg8 (Auto)
        cost8 = g.upg8_cost
        chal_c7_active = (g.active_chal == 'c7')
        st8, ct8, et8 = "locked", "Locked (C4)", "???"
        if not lock_click_upgs:
            # Show combined auto click speed
            auto_s = f"{g.auto_cps:.2f}/s" if g.auto_cps > 0 else ("Passive" if g.p18_pass_clk > 0 else "0/s")

            if chal_c7_active: st8, ct8, et8 = "disabled", "Disabled (C7)", "Auto Click Disabled"
            elif g.upg8_lvl >= g.upg8_max: st8, ct8, et8 = "maxed", "MAXED", f"Auto Click: {auto_s}"
            else:
                st8 = "buyable" if clicks >= cost8 else "default"
                ct8 = f"Cost: {format_number(cost8)} Clicks"
                et8 = f"Auto Click Speed [{int(g.upg8_lvl)}/{fmt_max(g.upg8_max)}]"

        if upgrade8costlabel: upgrade8costlabel.configure(text=ct8)
        if upgrade8explainlabel: upgrade8explainlabel.configure(text=et8)
        if button8: update_button_style(button8, st8)

        # --- Challenges Tab (Task 3 & 6 UI) ---
        show_obfuscated = not g.asc_first # Obfuscate if not ascended once

        # Update Exit Challenge button visibility
        if exit_challenge_button:
            if g.active_chal:
                exit_challenge_button.grid() # Show button
                exit_challenge_button.configure(text=f"Exit Challenge '{g.active_chal}'")
            else:
                exit_challenge_button.grid_remove() # Hide button

        for cid, widgets in challenge_widgets.items():
            chal=CHALLENGES[cid]
            lbl, enter_btn = widgets # Unpack label and button

            lvl=g.chal_comps.get(cid,0)
            max_l=chal.get('max_completions')
            is_max=(max_l is not None and lvl>=max_l)
            is_active = (g.active_chal == cid)
            can_enter = (g.active_chal is None and g.asc_first and not is_max)

            # --- Build Text ---
            desc_base = chal['desc_base']
            req_desc = "???"
            rew_desc = "???"
            restrict_desc = chal.get('restrictions_desc', '???')

            if not show_obfuscated or is_max or is_active: # Show details if completed, active, or ascended
                try:
                    req=chal['requirement_func'](g,lvl)
                    req_desc=chal['requirement_desc_func'](req)
                except Exception as e: req_desc = f"Req Error: {e}" # Show error in UI
                try:
                     # Show reward for *next* level if not maxed
                     rew_desc=chal['reward_desc_func'](g, lvl + (0 if is_max else 1))
                except Exception as e: rew_desc = f"Reward Error: {e}"
            else: # Obfuscate if not ascended and not completed/active
                desc_base = obfuscate(desc_base)
                req_desc = obfuscate(req_desc)
                rew_desc = obfuscate(rew_desc)
                restrict_desc = obfuscate(restrict_desc)

            comp_s=f" ({lvl}/{max_l})" if max_l is not None else f" ({lvl})"
            status_text = ""
            if is_active: status_text = " [ACTIVE]"
            elif is_max: status_text = " [MAXED]"
            elif not g.asc_first: status_text = " [LOCKED]"

            lbl_txt=f"{desc_base}{comp_s}{status_text}\n"
            if is_active:
                 # Show current progress towards requirement
                 try:
                     req = chal['requirement_func'](g, lvl)
                     # This part needs custom logic per challenge type
                     prog = "..." # Default progress string
                     if 'Points' in req_desc: prog = f"{format_number(points)} / {format_number(req)}"
                     elif 'Clicks' in req_desc: prog = f"{format_number(clicks)} / {format_number(req)}"
                     elif 'Crystalline' in req_desc: prog = f"{g.cryst_cnt} / {req}"
                     # Add time limit display for C2
                     elif cid == 'c2': prog = f"{format_number(clicks)} / {format_number(req)} Clicks ({g.playtime:.0f}/120s)"

                     lbl_txt += f"Progress: {prog}\n"
                 except Exception as e: lbl_txt += f"Progress Error: {e}\n"
            else:
                 lbl_txt += f"Next Req: {req_desc}\n"

            lbl_txt += f"Reward: {rew_desc}\nRestrictions: {restrict_desc}"
            lbl.configure(text=lbl_txt)

            # --- Update Button State ---
            if is_active:
                enter_btn.grid_remove() # Hide enter button when active
            else:
                enter_btn.grid() # Show enter button
                enter_btn.configure(text=f"Enter C{cid[1:]}") # Shorten text e.g. Enter C1
                if is_max: btn_state = "maxed"
                elif can_enter: btn_state = "primary" # Use solid primary to invite click
                else: btn_state = "locked" # Cannot enter (in another chal or not ascended)
                update_button_style(enter_btn, btn_state)

        # --- Reschedule ---
        if is_running: window.after(UPDATE_INTERVAL_MS, updateui)
    except tk.TclError:
        logging.warning("UI Update TclError (likely window closed).")
        is_running = False # Stop loops if UI fails critically
    except Exception as e:
        logging.error(f"UI update error: {e}", exc_info=True)
        # Delay rescheduling slightly on error to prevent rapid error loops
        if is_running: window.after(UPDATE_INTERVAL_MS * 5, updateui)

admin_window = None
admin_widgets = {}
active_admin_threads = [] # Stores TIDs of running background commands

# --- Admin Panel Helpers ---

def log_to_admin_output_threadsafe(m):
    """Safely logs a message to the admin output widget from any thread."""
    # Assumes 'window' is the main tk root window defined elsewhere
    if admin_widgets.get('cmd_output') and window and is_running:
        try:
            # Use window.after to schedule the UI update on the main thread
            window.after(0, lambda msg=m: log_to_admin_output(msg))
        except Exception: pass # Ignore if window/tk is gone

def _execute_single_command(cmd_str, log_output=True):
    """Executes a single admin command string. Internal use."""
    global is_running, COMMAND_HANDLERS # Need handlers dict
    if not cmd_str or not is_running: return None

    parts = cmd_str.split()
    cmd = parts[0].lower()
    args = parts[1:]
    res = None
    handler_data = COMMAND_HANDLERS.get(cmd)

    if handler_data:
        try:
            # Call the function associated with the command
            func = handler_data['func']
            res = func(args) # Pass the arguments list
        except Exception as e:
            res = f"Exec Error '{cmd}': {e}"
            logging.error(f"Admin cmd '{cmd}' error: {e}", exc_info=True)
    else:
        res = f"Unknown command: '{cmd}'."

    # Log the result unless it's a background task or logging is off
    # Check if the function is one known to run in the background
    background_funcs = [cmd_wait, cmd_repeat, cmd_while]
    should_log = log_output and res and (handler_data is None or handler_data['func'] not in background_funcs)

    if should_log:
        # Ensure logging happens on the main thread if needed
        log_to_admin_output_threadsafe(str(res))
    return res # Return result for potential chaining or internal use

def _evaluate_condition(cond_str):
    """Evaluates a simple condition string 'var op val'. Internal use."""
    global points, clicks, g # Need access to game state
    try:
        parts = cond_str.split()
        if len(parts) != 3: raise ValueError("Condition must be 'var op val'")
        var, op, val_str = parts[0].lower(), parts[1], parts[2]

        current_value = None
        value_source = None

        # Check globals first
        if var in ['points', 'clicks', 'pps']:
            current_value = globals().get(var)
            value_source = "Global"
        # Check GameState 'g'
        elif hasattr(g, var):
            current_value = getattr(g, var)
            value_source = "GameState"
        else:
            raise NameError(f"Variable '{var}' not found.")

        if current_value is None:
            # Treat None as 0 for comparisons, might need adjustment
            current_value = 0

        # Determine the type for comparison
        target_type = type(current_value)
        compare_value = None

        # Convert val_str to the appropriate type
        try:
            if target_type == bool:
                compare_value = val_str.lower() in ['true', '1', 't', 'y']
            elif target_type == int:
                compare_value = int(float(val_str)) # Allow scientific notation
            elif target_type == float:
                compare_value = float(val_str)
            elif target_type == str:
                compare_value = val_str
            elif isinstance(current_value, (int, float)): # Handle cases where type is int/float but loaded differently
                 compare_value = float(val_str)
            else:
                raise TypeError(f"Unsupported type '{target_type.__name__}' for comparison.")
        except ValueError:
             raise TypeError(f"Cannot convert '{val_str}' to expected type '{target_type.__name__}'.")


        # Perform comparison
        if op == '==': return current_value == compare_value
        elif op == '!=': return current_value != compare_value
        # Numerical comparisons require numbers
        elif isinstance(current_value, (int, float)) and isinstance(compare_value, (int, float)):
            if op == '>': return current_value > compare_value
            elif op == '<': return current_value < compare_value
            elif op == '>=': return current_value >= compare_value
            elif op == '<=': return current_value <= compare_value
            else: raise ValueError(f"Unsupported operator '{op}' for numbers.")
        elif op in ['>', '<', '>=', '<=']: # Tried numerical op on non-numerical type
            raise TypeError(f"Operator '{op}' requires numerical types (got {target_type.__name__}).")
        else:
            raise ValueError(f"Unsupported operator '{op}'.")

    except Exception as e:
        log_to_admin_output_threadsafe(f"Condition Error: {e}")
        logging.warning(f"Condition eval error '{cond_str}': {e}")
        return False # Default to False on any error

# --- Admin Command Functions ---

def cmd_setvalue(args): # Updated for 'g' and new vars
    global points, clicks, g # Use 'g'
    if len(args)!=2: return "Usage: set <var> <val>"
    var,val_str=args[0].lower(),args[1]
    tgt=None
    is_g=False # Is it a global variable like points/clicks?
    cur=None
    old=None

    # Check globals first
    if var in ['points', 'clicks', 'pps', 'is_running']: # Add other globals if needed
        tgt=globals()
        is_g=True
        cur=tgt.get(var) # Use get for safety
        old=cur
    # Check GameState 'g' attributes
    elif hasattr(g, var):
        tgt=g
        cur=getattr(g, var)
        old=cur
    else: return f"Error: Var '{var}' not found in globals or game state."

    if cur is None and not is_g: # Safety check if getattr returned None unexpectedly
        # Allow setting None values if needed, maybe? For now, assume we want a type.
         logging.warning(f"Var '{var}' exists but is None. Attempting to set anyway.")
         # pass

    tp=type(cur) if cur is not None else None # Get type from current value if possible
    new=None

    try:
        # Explicit type checks for known state variables
        if var in ['asc_first', 'p20_lim_brk', 'upg5_comp', 'upg6_comp', 'cryst_unl', 'asc_unl', 'r2_unl', 'r3_unl', 'r6_unl', 'cr1_u4_unl', 'cr3_unl', 'cr4_unl', 'cr5_comp', 'p12_auto_u4']:
             new = val_str.lower() in ['true', '1', 't', 'y']; tp = bool
        elif var in ['asc_lvl', 'asc_cnt', 'pur_cnt', 'cryst_cnt', 'upg1_lvl', 'upg2_lvl', 'upg3_lvl', 'upg4_lvl', 'upg7_lvl', 'upg8_lvl']:
            new = int(float(val_str)); tp = int
        elif var in ['upg1_max','upg2_max','upg3_max','upg4_max','upg7_max','upg8_max']: # Handle float max levels
            if val_str.lower() in ['inf', 'infinity']: new = float('inf'); tp = float
            else: new = float(val_str); tp = float
        elif var in ['asc_xp', 'sd', 'pps_exp', 'clk_pow', 'mult', 'mult_str', 'r1_boost', 'r3_cost_m', 'r4_u2_boost', 'r5_u3_boost', 'r6_boost', 'cr1_boost', 'cr2_boost', 'cryst_comp_bonus', 'p11_pps_boost', 'p14_u2_boost', 'p16_cost_reduc', 'p17_u1_boost', 'p18_pass_clk', 'p19_boost', 'p24_pur_cost_div', 'chal_sd_boost', 'chal_perm_clk_boost', 'chal_upg_cost_scale_mult', 'points', 'clicks', 'pps', 'upg1_cost', 'upg2_cost', 'upg3_cost', 'upg4_cost', 'upg7_cost', 'upg8_cost', 'pur_cost', 'cryst_cost', 'asc_cost', 'auto_cps', 'clk_pt_scale', 'pps_pt_scale_exp', 'chal_eff_pps_exp_mod', 'chal_eff_cost_exp_mod', 'clk_crit_c', 'clk_crit_m']:
            new = float(val_str); tp = float
        elif var == 'active_chal': # Handle setting active_chal to None
            new = None if val_str.lower() == 'none' else val_str
            tp = str if new is not None else type(None)
        elif var in ['relic_lvls', 'chal_comps']:
            new = ast.literal_eval(val_str) # Use literal_eval for safety
            if not isinstance(new, dict): raise TypeError("Parsed value is not a dict")
            tp = dict
        # Fallback for other types or unknown variables
        elif tp is not None:
            if tp == bool: new=val_str.lower() in ['true','1','t','y']
            elif tp == int: new=int(float(val_str))
            elif tp == float: new=float(val_str)
            elif tp == str: new=val_str
            elif tp == dict:
                 new=ast.literal_eval(val_str)
                 if not isinstance(new,dict): raise TypeError("Parsed value is not a dict")
            # Add list, set etc. if needed
            else: raise TypeError(f"Unsupported type '{tp.__name__}' for auto-conversion.")
        else: # Type is None (variable might not have been initialized yet or was None)
            # Attempt literal_eval or default to string
            try: new = ast.literal_eval(val_str); tp = type(new)
            except: new = val_str; tp = str
            log_to_admin_output_threadsafe(f"Warning: Type for '{var}' was None, guessed type '{tp.__name__}'.")

    except Exception as e: return f"Error parsing '{val_str}' for {var} (Expected ~{tp.__name__ if tp else 'Unknown'}): {e}"

    # Apply the change
    if is_g: globals()[var]=new
    else: setattr(tgt, var, new)

    buff_msg=""
    # Apply buffs if prestige counts increased (check correct vars: pur_cnt, cryst_cnt)
    if not is_g and var in ['pur_cnt','cryst_cnt'] and isinstance(old,(int,float)) and isinstance(new,int) and new>old:
        try:
            old_i,new_i=int(old),int(new)
            if new_i>old_i:
                log_to_admin_output_threadsafe(f"ADMIN: Applying buffs for {var} from {old_i+1} to {new_i}")
                if var=='pur_cnt':
                    for i in range(old_i,new_i): apply_purification_effects(i)
                    buff_msg=" P buffs applied."
                elif var=='cryst_cnt':
                    for i in range(old_i,new_i): apply_crystalline_effects(i+1) # Cryst levels are 1-based
                    buff_msg=" C buffs applied."
        except Exception as e:
            log_to_admin_output_threadsafe(f"Buff Error: {e}")
            logging.error(f"Buff Error: {e}",exc_info=True)

    # Determine if recalculation is needed
    needs_recalc = True # Default to true
    vars_no_recalc_g = ['is_running'] # Globals not needing recalc
    vars_no_recalc_gs = ['last_save_time','admin_panel_active', 'playtime'] # GS vars not needing recalc

    if is_g and var in vars_no_recalc_g: needs_recalc = False
    if not is_g and var in vars_no_recalc_gs: needs_recalc = False
    # Special case: If setting asc_lvl/xp, level up check handles recalc
    if var in ['asc_lvl', 'asc_xp'] and not is_g:
         needs_recalc = False # check_ascension_level_up will trigger recalc if needed
         g.check_ascension_level_up()
    # Special case: Setting active_chal might need recalc depending on challenge effects
    if var == 'active_chal' and not is_g:
        needs_recalc = True # Assume recalc needed to apply/remove challenge effects


    res=f"Set {var} to {new!r}."
    if needs_recalc:
        recalculate_derived_values()
        res+=" Recalculated."+buff_msg
    elif buff_msg: # Buffs were applied, but recalc wasn't needed for the set var itself
        recalculate_derived_values() # Still need recalc for buff effect
        res+=buff_msg + " Recalculated (for buffs)."

    return res


def cmd_varinfo(args): # Updated for 'g'
    global g
    if len(args)!=1: return "Usage: get <var>"
    var=args[0].lower()
    val=None
    tp=None
    source = "Not Found"
    if var in globals():
        val=globals().get(var)
        source = "Global"
    elif hasattr(g, var):
        val=getattr(g, var)
        source = "GameState"
    else: return f"Error: Var '{var}' not found."

    tp=type(val).__name__
    # Format inf/nan nicely
    if isinstance(val, float):
        if ma.isinf(val): val_repr = "Infinity" if val > 0 else "-Infinity"
        elif ma.isnan(val): val_repr = "NaN"
        else: val_repr = repr(val)
    else: val_repr = repr(val)
    return f"{var} ({tp}) [{source}] = {val_repr}"


def cmd_list(args): # Updated for 'g', 'pps'
    global points, clicks, pps, g # Use 'g', 'pps'
    if len(args)==0:
        lines=["--- Game State (g) ---"]
        # Sort attributes for consistent output
        for k,v in sorted(vars(g).items()):
             if not k.startswith('_'):
                 # Format inf/nan nicely
                 if isinstance(v, float):
                     if ma.isinf(v): v_repr = "Infinity" if v > 0 else "-Infinity"
                     elif ma.isnan(v): v_repr = "NaN"
                     else: v_repr = repr(v)
                 else: v_repr = repr(v)
                 lines.append(f"  {k} ({type(v).__name__}) = {v_repr}")
        lines.append("\n--- Globals ---")
        lines.append(f"  points={repr(points)}")
        lines.append(f"  clicks={repr(clicks)}")
        lines.append(f"  pps={repr(pps)}") # Corrected global var name
        lines.append(f"  is_running={repr(is_running)}")
        return "\n".join(lines)
    elif len(args)==1: return cmd_varinfo(args)
    else: return "Usage: list [<var>]"


def cmd_type(args): # Updated for 'g'
    global g
    if len(args)!=1: return "Usage: type <var>"
    var=args[0].lower()
    tp=None
    if var in globals(): tp=type(globals().get(var)).__name__
    elif hasattr(g, var): tp=type(getattr(g, var)).__name__
    else: return f"Error: Var '{var}' not found."
    return f"Type of '{var}' is {tp}"

def cmd_limbrk(args): # Updated for 'g' and shortened vars
    global g
    count=0
    logf=log_to_admin_output if th.current_thread() is th.main_thread() else log_to_admin_output_threadsafe
    targets=[]
    target_vars = [k for k in g.__dict__ if k.endswith('_max')] # Find all vars ending in _max

    if not args or args[0].lower()=='all':
        targets=target_vars
    else:
        var=args[0].lower()
        tgt=None
        # Try matching common patterns
        if f"{var}_max" in target_vars: tgt=f"{var}_max"
        elif var in target_vars: tgt = var # Allow providing full name like 'upg1_max'
        # Add more specific checks if needed (e.g., 'upg1' -> 'upg1_max')
        elif var.startswith("upg") and var[3:].isdigit() and f"upg{var[3:]}_max" in target_vars:
            tgt = f"upg{var[3:]}_max"

        if tgt: targets.append(tgt)
        else: return f"Error: Cannot find a '_max' var related to '{args[0]}'."

    if not targets: return "No _max vars found or matched."
    for t in targets:
        if hasattr(g,t):
            try:
                current_val = getattr(g,t)
                # Check if it's numeric before setting to inf
                if isinstance(current_val,(int,float)):
                    setattr(g,t,float('inf'))
                    count+=1
                    logf(f"Set {t} to Inf.")
                else: logf(f"Warn: {t} is not numeric ({type(current_val).__name__}), skipped.")
            except Exception as e: logf(f"Error setting {t} to inf: {e}")
        else: logf(f"Warn: Attribute {t} not found on 'g' (should not happen).")


    if count>0:
        recalculate_derived_values() # Max levels affect calculations
        return f"Set {count} max limits to inf. Recalculated."
    else: return "No limits changed."

def cmd_settype(args): # Updated for 'g'
    global g
    if len(args)!=2: return "Usage: settype <var> <type>"
    var,t_str=args[0].lower(),args[1].lower()
    tgt=None
    is_g=False
    cur=None
    if var in globals():
        tgt=globals()
        is_g=True
        cur=tgt.get(var)
    elif hasattr(g, var):
        tgt=g
        cur=getattr(g, var)
    else: return f"Error: Var '{var}' not found."

    new=None
    try:
        current_val_str = str(cur) # Convert current value to string for conversion
        if t_str=='int': new=int(float(current_val_str))
        elif t_str=='float': new=float(current_val_str)
        elif t_str=='str': new=str(current_val_str)
        elif t_str=='bool': new=bool(cur) # Bool conversion uses truthiness
        elif t_str=='dict': new=ast.literal_eval(current_val_str); assert isinstance(new,dict)
        elif t_str=='list': new=ast.literal_eval(current_val_str); assert isinstance(new,list)
        # Add 'set' if needed
        else: return f"Error: Unsupported target type '{t_str}'."

        if is_g: globals()[var]=new
        else: setattr(tgt, var, new)

        # Check if recalc needed based on variable name (similar to setvalue)
        needs_recalc = True
        vars_no_recalc_g = ['is_running']
        vars_no_recalc_gs = ['last_save_time','admin_panel_active', 'playtime', 'active_chal']
        if is_g and var in vars_no_recalc_g: needs_recalc = False
        if not is_g and var in vars_no_recalc_gs: needs_recalc = False

        res = f"Set type of '{var}' to {t_str}. New value: {new!r}."
        if needs_recalc:
             recalculate_derived_values()
             res += " Recalculated."
        return res

    except Exception as e: return f"Error converting '{var}' (value: {cur!r}) to type {t_str}: {e}"

def cmd_buy(args): # Updated for 'g', relics max level, challenges, pre-checks
    global g, points, clicks # Use 'g', needs points/clicks for checks
    if len(args)<1 or len(args)>2: return "Usage: buy <id> [times=1]"
    id_str=args[0].lower()
    times=1
    if len(args)==2:
        try:
            times=int(args[1])
            assert times>0
        except: return "Error: Invalid times."

    # Map IDs to functions
    funcs={'upg1':upgrade1,'upg2':upgrade2,'upg3':upgrade3,'upg4':upgrade4,'upg5':upgrade5,'upg6':upgrade6,'upg7':upgrade7,'upg8':upgrade8,
           'purify':purify,'crystalline':crystalline,'ascend':ascend}
    # Add relics to buyable map
    for k in RELICS_DATA: funcs[k]=lambda k=k:buy_relic(k)

    func=funcs.get(id_str)
    if not func: return f"Error: Unknown Buy ID '{id_str}'."

    bought=0
    for i in range(times):
        if not is_running: return f"Buy stopped after {bought} due to game closing."
        # Pre-checks (can we even attempt the purchase due to restrictions, max levels, costs?)
        can_attempt = True
        reason="unknown"

        # Challenge Restrictions first
        if id_str == 'upg2' and g.active_chal == 'c1': can_attempt = False; reason = "in C1"
        elif id_str == 'upg3' and g.active_chal == 'c3': can_attempt = False; reason = "in C3"
        elif id_str == 'upg8' and g.active_chal == 'c7': can_attempt = False; reason = "in C7"
        elif id_str == 'purify' and g.active_chal == 'c6': can_attempt = False; reason = "in C6"
        elif id_str == 'ascend' and g.active_chal: can_attempt = False; reason = f"in Chal {g.active_chal}"

        # Max Level / Resource / Unlock Checks (Only if not blocked by challenge)
        if can_attempt:
            if id_str in RELICS_DATA:
                lvl=g.relic_lvls.get(id_str,0); data=RELICS_DATA[id_str]
                max_l=data.get('max_level', RELIC_MAX_LEVEL)
                if max_l is not None and lvl>=max_l: can_attempt=False; reason="relic max"
                else:
                    try: cost=round(data['cost_base']*(data['cost_scale']**lvl))
                    except OverflowError: cost = float('inf')
                    p23_reduction = 0.95 if g.pur_cnt >= 23 else 1.0
                    final_cost = round(cost * p23_reduction) if ma.isfinite(cost) else float('inf')
                    if g.sd < final_cost: can_attempt = False; reason="no SD"
            elif id_str=='purify':
                 cost = g.pur_cost / g.p24_pur_cost_div; current_max = 20.0 if g.cr5_comp else (15.0 if g.upg5_comp else 10.0)
                 if g.pur_cnt >= current_max: can_attempt = False; reason = "max purify"
                 elif g.pur_cnt >= 10 and not g.upg5_comp: can_attempt = False; reason = "req Upg5"
                 elif g.pur_cnt >= 15 and not g.cr5_comp: can_attempt = False; reason = "req C5"
                 elif points < cost: can_attempt = False; reason = "no points"
            elif id_str=='crystalline':
                 cost = g.cryst_cost; current_max = 5.0 if g.pur_cnt >= 15 else 4.0
                 if not g.cryst_unl: can_attempt = False; reason = "locked P10"
                 elif g.cryst_cnt >= current_max: can_attempt = False; reason = "max cryst"
                 elif g.cryst_cnt == 4 and g.pur_cnt < 15: can_attempt = False; reason = "req P15"
                 elif points < cost: can_attempt = False; reason = "no points"
            elif id_str=='ascend':
                 cost = g.asc_cost
                 if not g.asc_unl: can_attempt = False; reason = "locked C5"
                 elif points < cost: can_attempt = False; reason = "no points"
                 # Add 0 SD gain check? Could be slow. Function itself checks this.
            elif id_str=='upg1' and (g.upg1_lvl>=g.upg1_max or points < g.upg1_cost): can_attempt=False; reason="max/cost upg1"
            elif id_str=='upg2' and (g.upg2_lvl>=g.upg2_max or points < g.upg2_cost): can_attempt=False; reason="max/cost upg2"
            elif id_str=='upg3' and (g.upg3_lvl>=g.upg3_max or points < g.upg3_cost): can_attempt=False; reason="max/cost upg3"
            elif id_str=='upg4' and (g.upg4_lvl>=g.upg4_max or points < g.upg4_cost or not g.cr1_u4_unl): can_attempt=False; reason="max/cost/lock upg4"
            elif id_str=='upg5' and (g.upg5_comp or clicks < 1000 or not g.cr4_unl): can_attempt=False; reason="comp/cost/lock upg5"
            elif id_str=='upg6' and (g.upg6_comp or clicks < 100000 or not g.cr4_unl): can_attempt=False; reason="comp/cost/lock upg6"
            elif id_str=='upg7' and (g.upg7_lvl>=g.upg7_max or clicks < g.upg7_cost or not g.cr4_unl): can_attempt=False; reason="max/cost/lock upg7"
            elif id_str=='upg8' and (g.upg8_lvl>=g.upg8_max or clicks < g.upg8_cost or not g.cr4_unl): can_attempt=False; reason="max/cost/lock upg8"

        if not can_attempt:
            # Only show message if trying to buy multiple times or first attempt failed
            if times > 1 or bought == 0:
                res=f"Bought {id_str} {bought}x."
                res+=f" Stopped (Pre-check: {reason})."
                return res
            else: # If buying once and failed precheck, function itself likely handled message
                 return f"Buy {id_str} failed ({reason})."


        # Attempt the purchase
        try:
            # Store state before buying to detect change more reliably
            state_before_json = json.dumps({k: getattr(g, k) for k in g.__dict__ if not k.startswith('_')}, default=str) # Use default=str for non-serializable
            points_before, clicks_before, sd_before = points, clicks, g.sd
            func() # Execute the buy function
            state_after_json = json.dumps({k: getattr(g, k) for k in g.__dict__ if not k.startswith('_')}, default=str)
            points_after, clicks_after, sd_after = points, clicks, g.sd

            # Check if relevant state changed
            succeeded = False
            if state_before_json != state_after_json: succeeded = True
            elif points_before != points_after: succeeded = True
            elif clicks_before != clicks_after: succeeded = True
            elif sd_before != sd_after: succeeded = True

            if succeeded:
                bought+=1
            else: # Function executed but state didn't change (means couldn't afford or hit max internally)
                 # Don't return error if buying just once, function likely handled it
                 if times == 1: return f"Buy {id_str}: No change detected (Afford/Max/Unlock check failed)."
                 else:
                     res=f"Bought {id_str} {bought}x."
                     res+=f" Stopped (No change detected - Afford/Max/Unlock check failed inside function)."
                     return res

        except Exception as e:
            res=f"Bought {id_str} {bought}x."
            res+=f" Error on attempt {bought+1}: {e}"
            logging.error(f"Buy Error during {id_str}: {e}", exc_info=True)
            return res

        # Post-checks (did we hit a max level defined in GameState?)
        # This is mainly useful when buying multiple times to stop early
        is_maxed=False
        if id_str=='upg1' and g.upg1_lvl>=g.upg1_max: is_maxed=True
        elif id_str=='upg2' and g.upg2_lvl>=g.upg2_max: is_maxed=True
        elif id_str=='upg3' and g.upg3_lvl>=g.upg3_max: is_maxed=True
        elif id_str=='upg4' and g.upg4_lvl>=g.upg4_max: is_maxed=True
        elif id_str=='upg5' and g.upg5_comp: is_maxed=True # Completion flag
        elif id_str=='upg6' and g.upg6_comp: is_maxed=True # Completion flag
        elif id_str=='upg7' and g.upg7_lvl>=g.upg7_max: is_maxed=True
        elif id_str=='upg8' and g.upg8_lvl>=g.upg8_max: is_maxed=True
        elif id_str in RELICS_DATA:
            lvl=g.relic_lvls.get(id_str,0)
            max_l=RELICS_DATA[id_str].get('max_level', RELIC_MAX_LEVEL)
            if max_l is not None and lvl>=max_l:
                is_maxed=True

        if is_maxed and i < (times - 1): # Check if maxed before last iteration
            res=f"Bought {id_str} {bought}x."
            res+=f" Stopped (Maxed)."
            return res

    return f"Attempted {id_str} x{times}. Succeeded {bought}x."

def cmd_imprint(args):
    global g
    if len(args)!=2: return "Usage: imprint <var> <val>"
    res=cmd_setvalue(args)
    if "Error" not in res: save_game(); return f"{res} Saved."
    else: return res

def cmd_stop(args):
    global is_running, window
    save=True
    if args and args[0].lower() in ['f','0','n', 'nosave']: save=False
    msg = f"Shutdown initiated (Save: {save})..."; log_to_admin_output(msg); logging.info(msg)
    if window: window.after(100, lambda s=save: on_closing(s)); return "Shutdown scheduled."
    else: return "Error: Main window not found."

def cmd_offline(args):
    global points, clicks, g, pps
    if len(args)!=1: return "Usage: offline <secs>"
    try:
        secs=float(args[0]); assert secs>=0
        if secs==0: return "Simulated 0s offline."
        recalculate_derived_values()
        offline_pps = pps * 0.5 if ma.isfinite(pps) else 0.0
        offline_pts = offline_pps * secs
        offline_cps = g.auto_cps * 0.5 if ma.isfinite(g.auto_cps) else 0.0
        offline_cls = offline_cps * secs
        try: points = min(float('inf'), points + offline_pts)
        except OverflowError: points = float('inf')
        try: clicks = min(float('inf'), clicks + offline_cls)
        except OverflowError: clicks = float('inf')
        return f"Simulated {secs:.1f}s offline. ~+{format_number(offline_pts)} P, ~+{format_number(offline_cls)} C."
    except Exception as e: return f"Offline error: {e}"

def cmd_recalc(args): recalculate_derived_values(); return "Recalculated values."

def cmd_reset(args):
    global g, points, clicks, window
    if len(args)!=1: return "Usage: reset <purify|cryst|asc|save>"
    type=args[0].lower(); reset_done = False
    if type=="purify": reset_for_purify(); reset_done = True
    elif type=="crystalline" or type=="cryst": reset_for_crystalline(); reset_done = True
    elif type=="ascension" or type=="asc": reset_for_ascension(); reset_done = True
    elif type=="save":
        log_to_admin_output("Performing save reset...")
        try:
            if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE); log_to_admin_output_threadsafe(f"Deleted {SAVE_FILE}")
            else: log_to_admin_output_threadsafe("No save file found.")
            g = GameState(); points = 0.0; clicks = 0.0
            recalculate_derived_values(); save_game()
            log_to_admin_output_threadsafe("Game reset & new save created.")
            return "Save reset complete." # Return sync message
        except Exception as e: return f"Save reset error: {e}"
    else: return "Unknown reset type: purify, cryst, asc, save."
    if reset_done: recalculate_derived_values(); return f"{type.capitalize()} reset. Recalculated."
    else: return "Reset command finished (no action taken)."

def cmd_getchal(args):
    global g
    if len(args)!=1: return "Usage: getchal <id>"
    cid=args[0].lower()
    if cid not in CHALLENGES:
        return f"Error: Chal '{cid}' not found."
    chal=CHALLENGES[cid]
    lvl=g.chal_comps.get(cid,0)
    max_lvl=chal.get('max_completions')
    is_max=(max_lvl is not None and lvl>=max_lvl)
    status="WIP"
    req_d = "Error"
    rew_d = "Error"
    req_val = None # Define req_val before try block
    try:
        req_val=chal['requirement_func'](g,lvl)
        req_d=chal['requirement_desc_func'](req_val)
    except Exception as e: req_d = f"ReqERR:{e}"
    try:
        rew_d=chal['reward_desc_func'](g, lvl + (0 if is_max else 1)) # Show next reward
    except Exception as e: rew_d = f"RewERR:{e}"
    if is_max: status="MAX"
    elif g.active_chal == cid:
         status="ACTIVE"
         if req_val is not None: # Check if req_val was successfully calculated
             try:
                 if chal['check_func'](g,req_val): status="COMPLETABLE" # Can be completed now
             except Exception as e: status = f"ACTIVE(ChkERR:{e})"
         else: status = "ACTIVE(ReqERR)" # Indicate req calculation failed
    else:
         if req_val is not None: # Check if req_val was successfully calculated
             try:
                 if chal['check_func'](g,req_val): status="COMPLETABLE(Not Active)"
             except Exception: pass # Ignore check error here, just means WIP
         # If req_val is None, status remains "WIP"
    comp_s=f"({lvl}/{max_lvl})" if max_lvl is not None else f"({lvl})"
    restrict = chal.get('restrictions_desc', 'N/A'); reset_lvl = chal.get('reset_level', 'ascension')
    return f"{cid.upper()}: {chal['desc_base']} {comp_s} [{status}]\nReq: {req_d}\nRew: {rew_d}\nRestrict: {restrict} | Reset: {reset_lvl}"

def cmd_setchal(args):
    global g; logf=log_to_admin_output_threadsafe
    if len(args)!=2: return "Usage: setchal <id> <count>"
    try:
        cid=args[0].lower()
        if cid not in CHALLENGES: return f"Error: Chal ID '{cid}' not found."
        count=int(args[1]); assert count>=0
        max_c = CHALLENGES[cid].get('max_completions')
        if max_c is not None and count > max_c: logf(f"Warn: Setting {count} > max {max_c}. Clamping."); count = max_c
        old_count = g.chal_comps.get(cid, 0); g.chal_comps[cid]=count
        recalculate_derived_values()
        logf(f"NOTE: Set chal '{cid}' comps to {count}. Recalculated.")
        logf(f"NOTE: Does NOT retroactively apply level-based rewards {old_count+1}..{count}.")
        return f"Set chal '{cid}' comps to {count}. Recalculated."
    except Exception as e: return f"SetChal Error: {e}"

def cmd_resetchal(args):
    global g; logf=log_to_admin_output_threadsafe
    if len(args) != 1: return "Usage: resetchal <id|all>"
    target = args[0].lower()
    if target == 'all':
        if not g.chal_comps: return "No chal comps to reset."
        g.chal_comps.clear(); recalculate_derived_values()
        logf("NOTE: All chal comps reset to 0. Recalculated."); return "Reset all chal comps."
    elif target in CHALLENGES:
        if target in g.chal_comps:
            del g.chal_comps[target]; recalculate_derived_values()
            logf(f"NOTE: Reset chal '{target}' comps to 0. Recalculated."); return f"Reset chal '{target}' comps."
        else: return f"Chal '{target}' already 0 comps."
    else: return f"Error: Unknown chal ID '{target}'."

def cmd_forcechal(args):
    global g
    if len(args) < 1: return "Usage: forcechal <enter|exit> [id]"
    action = args[0].lower()
    if action == 'enter':
        if len(args) != 2: return "Usage: forcechal enter <id>"
        cid = args[1].lower() 
        if cid not in CHALLENGES: return f"Error: Unknown chal ID '{cid}'"
        if g.active_chal: return f"Error: Already in chal '{g.active_chal}'"
        reset_for_challenge(cid); return f"Forced entry into challenge '{cid}'."
    elif action == 'exit':
        if not g.active_chal: return "Error: Not in a challenge."
        exiting_chal = g.active_chal # Store ID before exiting
        exit_challenge(); return f"Forced exit from challenge '{exiting_chal}'."
    else: return "Error: Unknown action: 'enter' or 'exit'."

def cmd_completechal(args):
    global g
    if len(args)!=0: return "Usage: completechal (Completes active challenge)"
    if not g.active_chal: return "Error: Not in a challenge."
    cid = g.active_chal; chal_data = CHALLENGES.get(cid)
    if not chal_data: return f"Error: Active challenge '{cid}' invalid."
    lvl = g.chal_comps.get(cid, 0); max_lvl = chal_data.get('max_completions')
    if max_lvl is not None and lvl >= max_lvl: return f"Chal '{cid}' already maxed."
    complete_challenge(cid); return f"Attempted force completion of '{cid}'."

def cmd_help(args):
    global COMMAND_HANDLERS; text="Available Admin Commands:\n"
    h=COMMAND_HANDLERS; main_cmds=sorted([c for c,d in h.items() if 'alias' not in d])
    for c in main_cmds: text += f"  {c:<15} {h[c]['help']}\n"
    aliases=sorted([c for c,d in h.items() if 'alias' in d])
    if aliases:
        text+="\nAliases:\n"
        for c in aliases:
             original_cmd = next((k for k, v in h.items() if v['func'] == h[c]['func'] and 'alias' not in v), "???")
             text += f"  {c:<15} Alias for '{original_cmd}'\n"
    return text.strip()

def _wait_thread_func(s,tid):
    global active_admin_threads; logf=log_to_admin_output_threadsafe
    logf(f"[{tid}] wait: Starting {s}s sleep...")
    try: time.sleep(s); logf(f"[{tid}] wait: Finished.")
    except Exception as e: logf(f"[{tid}] wait Error: {e}")
    finally:
        if tid in active_admin_threads: active_admin_threads.remove(tid)

def cmd_wait(args):
    global active_admin_threads
    if len(args)!=1: return "Usage: wait <secs>"
    try:
        s=float(args[0]); assert s>=0; tid=f"wait-{random.randint(1000,9999)}"
        t=th.Thread(target=_wait_thread_func,args=(s,tid),daemon=True); active_admin_threads.append(tid); t.start()
        return f"wait: BG wait started (TID {tid})."
    except: return "Error: Invalid time specified."

def _repeat_thread_func(t,cmd,tid):
    global active_admin_threads,is_running; logf=log_to_admin_output_threadsafe
    logf(f"[{tid}] repeat: Starting '{cmd}' x{t}..."); executed_count=0
    try:
        for i in range(t):
            if not is_running: logf(f"[{tid}] repeat: Cancelled."); break
            _execute_single_command(cmd,log_output=False); executed_count+=1; time.sleep(0.05)
        logf(f"[{tid}] repeat: Finished {executed_count}/{t}.")
    except Exception as e: logf(f"[{tid}] repeat: Error on rep {executed_count+1}: {e}")
    finally:
        if tid in active_admin_threads: active_admin_threads.remove(tid)

def cmd_repeat(args):
    global active_admin_threads
    if len(args)<2: return "Usage: repeat <times> <cmd...>"
    try:
        t=int(args[0]); assert t>0; cmd=" ".join(args[1:])
        if not cmd: return "Error: No command to repeat."
        tid=f"repeat-{random.randint(1000,9999)}"
        thrd=th.Thread(target=_repeat_thread_func,args=(t,cmd,tid),daemon=True); active_admin_threads.append(tid); thrd.start()
        return f"repeat: BG repeat started (TID {tid})."
    except: return "Error: Invalid times specified."

def _while_thread_func(cond,cmd,tid):
    global active_admin_threads,is_running; logf=log_to_admin_output_threadsafe
    logf(f"[{tid}] while: Starting loop '{cond}' -> '{cmd}'..."); iterations=0; max_iterations=10000
    try:
        while is_running and _evaluate_condition(cond) and iterations < max_iterations:
            iterations+=1; _execute_single_command(cmd,log_output=False); time.sleep(0.1)
        if not is_running: logf(f"[{tid}] while: Cancelled.")
        elif iterations>=max_iterations: logf(f"[{tid}] while: Max iters ({max_iterations}).")
        else: logf(f"[{tid}] while: Cond false. Finished {iterations} iters.")
    except Exception as e: logf(f"[{tid}] while: Error iter {iterations+1}: {e}"); logging.error(f"[{tid}] while: {e}",exc_info=True)
    finally:
        if tid in active_admin_threads: active_admin_threads.remove(tid)

def cmd_while(args):
    global active_admin_threads
    if len(args)<4: return "Usage: while <var op val> <cmd...>"
    try:
        condition_str=" ".join(args[0:3]); command_str=" ".join(args[3:])
        initial_check = _evaluate_condition(condition_str)
        if not command_str: return "Error: No command specified."
        tid=f"while-{random.randint(1000,9999)}"
        thrd=th.Thread(target=_while_thread_func,args=(condition_str,command_str,tid),daemon=True); active_admin_threads.append(tid); thrd.start()
        return f"while: BG loop started (TID {tid}). Init: {initial_check}."
    except Exception as e: return f"Error setting up while: {e}"

def cmd_setrelic(args):
    global g
    if len(args) != 2: return "Usage: setrelic <id> <lvl>"
    rid, lvl_s = args[0].lower(), args[1]
    if rid not in RELICS_DATA: return f"Error: Unknown relic '{rid}'."
    try: lvl = int(lvl_s); assert lvl >= 0
    except: return "Error: Lvl must be non-neg int."
    max_l = RELICS_DATA[rid].get('max_level', RELIC_MAX_LEVEL)
    if max_l is not None and lvl > max_l: return f"Error: Max lvl {max_l}."
    g.relic_lvls[rid] = lvl; recalculate_derived_values(); return f"Set relic '{rid}' to {lvl}. Recalculated."

def cmd_listrelics(args):
    global g; output = "--- Relics ---\n"; owned_relics = g.relic_lvls
    if not RELICS_DATA: return "No relics defined."
    all_relic_ids = sorted(list(RELICS_DATA.keys()))
    for rid in all_relic_ids:
        data = RELICS_DATA[rid]; lvl=owned_relics.get(rid, 0); owned_str = "(Owned)" if rid in owned_relics else "(Not Owned)"
        max_l=data.get('max_level', RELIC_MAX_LEVEL)
        l_str=f"Lvl: {lvl}/{max_l}" if max_l is not None else f"Lvl: {lvl}"
        output += f"{rid} [{data.get('name','Unknown')}]: {l_str} {owned_str}\n"
    return output.strip()

def cmd_resetrelics(args):
    global g
    if not g.relic_lvls: return "No relic levels to reset."
    g.relic_lvls.clear(); recalculate_derived_values(); return "Relic levels reset. Recalculated."

COMMAND_HANDLERS = {
    'set': {'func': cmd_setvalue, 'help': '<var> <val> - Set variable (applies prestige buffs)'},
    'get': {'func': cmd_varinfo, 'help': '<var> - Get variable info (value & type)'},
    'type': {'func': cmd_type, 'help': '<var> - Get variable type'},
    'list': {'func': cmd_list, 'help': '[<var>] - List all vars or info for one var'},
    'limbrk': {'func': cmd_limbrk, 'help': '<upgX|name|all> - Set _max level(s) to infinity'},
    'settype': {'func': cmd_settype, 'help': '<var> <type> - Attempt type conversion (int,float,str,bool,dict,list)'},
    'buy': {'func': cmd_buy, 'help': '<id> [times] - Buy upg/action/relic X times (checks restrictions)'},
    'imprint': {'func': cmd_imprint, 'help': '<var> <val> - Set value, apply buffs, save game'},
    'stop': {'func': cmd_stop, 'help': "[nosave] - Stop game ('stop nosave' to skip save)"},
    'offline': {'func': cmd_offline, 'help': '<secs> - Simulate offline time (50% gains)'},
    'recalc': {'func': cmd_recalc, 'help': '- Force recalculation of derived stats'},
    'reset': {'func': cmd_reset, 'help': '<type> - Reset progress (purify|cryst|asc|save)'},
    'help': {'func': cmd_help, 'help': '- Show this help message'},
    'getchal': {'func': cmd_getchal, 'help': '<id> - Get challenge details and status'},
    'setchal': {'func': cmd_setchal, 'help': '<id> <count> - Set challenge *completion count* (rewards update on recalc)'},
    'resetchal': {'func': cmd_resetchal, 'help': '<id|all> - Reset challenge *completion count* to 0 (rewards update on recalc)'},
    'forcechal': {'func': cmd_forcechal, 'help': '<enter|exit> [id] - Force enter/exit challenge (bypasses checks)'},
    'completechal': {'func': cmd_completechal, 'help': '- Force complete the currently active challenge'},
    'wait': {'func': cmd_wait, 'help': '<secs> - Pause command execution (background)'},
    'repeat': {'func': cmd_repeat, 'help': '<times> <cmd...> - Repeat command (background)'},
    'while': {'func': cmd_while, 'help': '<var op val> <cmd...> - Loop command while condition true (background)'},
    'setrelic': {'func': cmd_setrelic, 'help': '<id> <level> - Set relic level'},
    'listrelics': {'func': cmd_listrelics, 'help': '- List all relics (owned and defined) and levels'},
    'resetrelics': {'func': cmd_resetrelics, 'help': '- Reset all relic levels to 0'},
    'setvalue': {'func': cmd_setvalue, 'help': 'Alias for set', 'alias': True}, # Example Alias
    'varinfo': {'func': cmd_varinfo, 'help': 'Alias for get', 'alias': True},   # Example Alias
}

def admin_execute_command(event=None):
    if not DEVELOPER_MODE or not admin_widgets.get('cmd_input'): return
    cmd_text=admin_widgets['cmd_input'].get().strip()
    if not cmd_text: return
    admin_widgets['cmd_input'].delete(0,tk.END)
    log_to_admin_output(f"> {cmd_text}")
    _execute_single_command(cmd_text, log_output=True)

def log_to_admin_output(msg):
    """Logs a message to the admin output widget (must run on main thread)."""
    if th.current_thread() is not th.main_thread():
        log_to_admin_output_threadsafe(msg)
        return

    output_widget = admin_widgets.get('cmd_output')
    if output_widget and window and window.winfo_exists():
        try:
            # --- Attempt to get the underlying tk.Text widget ---
            # ttkbootstrap.scrolled.ScrolledText often stores the text widget
            # in an attribute named 'text'. Check for its existence.
            text_widget_to_configure = None
            if hasattr(output_widget, 'text') and isinstance(output_widget.text, tk.Text):
                text_widget_to_configure = output_widget.text
                # logging.debug("Configuring internal 'text' widget.") # Optional debug log
            elif isinstance(output_widget, tk.Text): # Maybe it IS the Text widget directly?
                 text_widget_to_configure = output_widget
                 # logging.debug("Configuring widget directly (assumed tk.Text).") # Optional
            elif isinstance(output_widget, scrolledtext.ScrolledText): # Handle tkinter fallback
                 # tkinter.scrolledtext *is* the frame, the text is internal, but configure might be forwarded?
                 # Let's try configuring the wrapper first for the fallback case.
                 # If this fails, one might need to dig deeper into ScrolledText internals, but
                 # configure *should* work.
                 text_widget_to_configure = output_widget
                 # logging.debug("Configuring tkinter.scrolledtext directly.") # Optional

            if text_widget_to_configure is None:
                # Fallback if we couldn't find the text widget - configure the main widget
                # This might be the source of the error if output_widget isn't a Text widget
                # or doesn't properly delegate the state config.
                text_widget_to_configure = output_widget
                logging.warning("Could not reliably find internal Text widget, configuring main output_widget.")


            # --- Configure the identified widget ---
            # Use the 'state=' keyword argument, which is correct syntax.
            text_widget_to_configure.configure(state=tk.NORMAL)
            text_widget_to_configure.insert(tk.END, str(msg)+"\n")
            text_widget_to_configure.configure(state=tk.DISABLED)

            # Scroll the main ScrolledText widget (if different) or the text widget itself
            # ScrolledText handles scrolling automatically usually when inserting at END
            # but calling see() on the text widget is also common.
            text_widget_to_configure.see(tk.END)

        except tk.TclError as e:
             # Log specific TclErrors if they still occur
             logging.warning(f"TclError logging to admin output (widget: {type(output_widget)}, configuring: {type(text_widget_to_configure)}): {e}")
             pass # Avoid crashing the application
        except Exception as e:
             logging.warning(f"Failed to log to admin output (widget: {type(output_widget)}): {e}")
             pass # Avoid crashing the application

def open_admin_panel():
    global admin_window, admin_widgets, g
    if not DEVELOPER_MODE: logging.warning("Admin disabled."); return
    if admin_window and admin_window.winfo_exists():
        try: admin_window.lift(); admin_window.focus_force(); return
        except tk.TclError: admin_window=None
    g.admin_panel_active=True
    admin_window=ttk.Toplevel(window); admin_window.title("Admin Console"); admin_window.geometry("700x500")
    admin_window.protocol("WM_DELETE_WINDOW", on_admin_close)
    main_frame=ttk.Frame(admin_window,padding=10); main_frame.pack(expand=True,fill=tk.BOTH)
    main_frame.grid_rowconfigure(0,weight=1); main_frame.grid_columnconfigure(0,weight=1)
    output_area=ttkScrolledText(main_frame,height=20,wrap=tk.WORD,state=tk.DISABLED,autohide=True, font=("Consolas", 10))
    output_area.grid(row=0,column=0,sticky='nsew',padx=5,pady=5); admin_widgets['cmd_output']=output_area
    input_entry=ttk.Entry(main_frame,font=("Consolas",10))
    input_entry.grid(row=1,column=0,sticky='ew',padx=5,pady=(5,10)); admin_widgets['cmd_input']=input_entry
    input_entry.bind("<Return>",admin_execute_command); input_entry.focus_set()
    log_to_admin_output("Admin console initialized. Type 'help' for commands.")

def on_admin_close():
    global admin_window, admin_widgets, g, active_admin_threads
    if not DEVELOPER_MODE: return
    g.admin_panel_active=False
    if active_admin_threads: log_to_admin_output(f"Closing admin. {len(active_admin_threads)} BG tasks may continue.")
    if admin_window:
        try: admin_window.destroy()
        except: pass
    admin_window=None; admin_widgets.clear(); logging.info("Admin panel closed.")

def admin_recalculate(): log_to_admin_output("> recalc"); result = cmd_recalc([]); log_to_admin_output(result)


# ==============================================================================
#                           UI SETUP
# ==============================================================================
# --- UI Helper Functions ---
def create_label(parent, text, row, col, **kwargs):
    grid_opts = {k: kwargs.pop(k) for k in list(kwargs.keys()) if k in ['sticky', 'padx', 'pady', 'columnspan', 'rowspan']}
    grid_opts.setdefault('sticky', 'w'); grid_opts.setdefault('padx', 5); grid_opts.setdefault('pady', 2)
    lbl = ttk.Label(parent, text=text, **kwargs)
    lbl.grid(row=row, column=col, **grid_opts)
    return lbl

def create_button(parent, text, command, row, col, **kwargs):
    grid_opts = {k: kwargs.pop(k) for k in list(kwargs.keys()) if k in ['sticky', 'padx', 'pady', 'columnspan', 'rowspan']}
    grid_opts.setdefault('sticky', 'ew'); grid_opts.setdefault('padx', 5); grid_opts.setdefault('pady', 5)
    bootstyle = kwargs.pop('bootstyle', 'primary-outline'); width = kwargs.pop('width', 10)
    btn = ttk.Button(parent, text=text, command=command, bootstyle=bootstyle, width=width, **kwargs)
    btn.grid(row=row, column=col, **grid_opts)
    return btn

# --- Main Window and Notebook ---
window = ttk.Window(themename="darkly"); window.title("Ordinal Ascent II"); window.geometry("1000x700")
window.grid_rowconfigure(0, weight=1); window.grid_columnconfigure(0, weight=1)
notebook = ttk.Notebook(window, bootstyle="primary"); notebook.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

# --- Create Frames ---
prestige_frame = ttk.Frame(notebook, padding=(20, 10)); upgrades_frame = ttk.Frame(notebook, padding=(20, 10))
clicking_frame = ttk.Frame(notebook, padding=(20, 10)); ascension_frame = ttk.Frame(notebook, padding=(20, 10))
relics_frame = ttk.Frame(notebook, padding=(20,10)); challenges_frame = ttk.Frame(notebook, padding=(20, 10))

# --- Configure Frame Grids ---
prestige_frame.grid_columnconfigure((0,3), weight=1); upgrades_frame.grid_columnconfigure(1, weight=1)
upgrades_frame.grid_columnconfigure(3, weight=0); clicking_frame.grid_columnconfigure(1, weight=1)
clicking_frame.grid_rowconfigure(1, weight=1); ascension_frame.grid_columnconfigure(0, weight=1)
relics_frame.grid_columnconfigure(1, weight=1); challenges_frame.grid_columnconfigure(0, weight=1)
challenges_frame.grid_rowconfigure(1, weight=0); challenges_frame.grid_rowconfigure(2, weight=1)

# --- Add Frames to Notebook ---
notebook.add(prestige_frame, text=" Prestige "); notebook.add(upgrades_frame, text=" Upgrades ")
notebook.add(clicking_frame, text=" Clicking "); notebook.add(ascension_frame, text=" Ascension ")
notebook.add(relics_frame, text=" Relics "); notebook.add(challenges_frame, text=" Challenges ")

# --- Populate Tabs ---
# Prestige Tab
purificationlabel=create_label(prestige_frame,"...",0,0,columnspan=2,sticky='ew',wraplength=350)
purificationbutton=create_button(prestige_frame,"Purify",purify,1,0,columnspan=2)
ttk.Separator(prestige_frame,orient=VERTICAL).grid(row=0,column=2,rowspan=2,sticky='ns',padx=20)
crystalinelabel=create_label(prestige_frame,"...",0,3,columnspan=2,sticky='ew',wraplength=350)
crystalinebutton=create_button(prestige_frame,"Crystalline",crystalline,1,3,columnspan=2)
# Upgrades Tab
pointlabel=create_label(upgrades_frame,"Pts: ...",0,0,columnspan=4); ppslabel=create_label(upgrades_frame,"PPS: ...",1,0,columnspan=4)
ttk.Separator(upgrades_frame,orient=HORIZONTAL).grid(row=2,column=0,columnspan=4,sticky='ew',pady=10)
create_label(upgrades_frame,"Upg1:",3,0,sticky='e',font=('-weight','bold')); upgrade1costlabel=create_label(upgrades_frame,"Cost: ...",3,1); button1=create_button(upgrades_frame,"Buy",upgrade1,3,2,width=5); upgrade1explainlabel=create_label(upgrades_frame,"Effect: ...",4,1,columnspan=2)
create_label(upgrades_frame,"Upg2:",5,0,sticky='e',font=('-weight','bold')); upgrade2costlabel=create_label(upgrades_frame,"Cost: ...",5,1); button2=create_button(upgrades_frame,"Buy",upgrade2,5,2,width=5); upgrade2explainlabel=create_label(upgrades_frame,"Effect: ...",6,1,columnspan=2)
create_label(upgrades_frame,"Upg3:",7,0,sticky='e',font=('-weight','bold')); upgrade3costlabel=create_label(upgrades_frame,"Cost: ...",7,1); button3=create_button(upgrades_frame,"Buy",upgrade3,7,2,width=5); upgrade3explainlabel=create_label(upgrades_frame,"Effect: ...",8,1,columnspan=2)
create_label(upgrades_frame,"Upg4:",9,0,sticky='e',font=('-weight','bold')); upgrade4costlabel=create_label(upgrades_frame,"Cost: ...",9,1); button4=create_button(upgrades_frame,"Buy",upgrade4,9,2,width=5); upgrade4explainlabel=create_label(upgrades_frame,"Effect: ...",10,1,columnspan=2)
# Clicking Tab
clicklabel=create_label(clicking_frame,"Clicks: ...",0,0,columnspan=2,sticky='ew',anchor=tk.CENTER)
clickbutton=create_button(clicking_frame,"Click!",click_power_action,1,0,columnspan=2,rowspan=2,sticky='nsew',pady=20)
ttk.Separator(clicking_frame,orient=HORIZONTAL).grid(row=3,column=0,columnspan=2,sticky='ew',pady=15)
create_label(clicking_frame,"Upg5:",4,0,sticky='e',font=('-weight','bold')); upgrade5costlabel=create_label(clicking_frame,"Cost: ...",4,1); button5=create_button(clicking_frame,"Buy",upgrade5,5,0); upgrade5explainlabel=create_label(clicking_frame,"Effect: ...",5,1)
create_label(clicking_frame,"Upg6:",6,0,sticky='e',font=('-weight','bold')); upgrade6costlabel=create_label(clicking_frame,"Cost: ...",6,1); button6=create_button(clicking_frame,"Buy",upgrade6,7,0); upgrade6explainlabel=create_label(clicking_frame,"Effect: ...",7,1)
create_label(clicking_frame,"Upg7:",8,0,sticky='e',font=('-weight','bold')); upgrade7costlabel=create_label(clicking_frame,"Cost: ...",8,1); button7=create_button(clicking_frame,"Buy",upgrade7,9,0); upgrade7explainlabel=create_label(clicking_frame,"Effect: ...",9,1)
create_label(clicking_frame,"Upg8:",10,0,sticky='e',font=('-weight','bold')); upgrade8costlabel=create_label(clicking_frame,"Cost: ...",10,1); button8=create_button(clicking_frame,"Buy",upgrade8,11,0); upgrade8explainlabel=create_label(clicking_frame,"Effect: ...",11,1)
# Ascension Tab
stardustlabel=create_label(ascension_frame,"Stardust: 0",0,0,columnspan=2,sticky='ew',font=('-weight','bold'))
asc_lvl_label = create_label(ascension_frame, "Ascension Level: 0", 1, 0, columnspan=2, sticky='ew')
asc_prog_label = create_label(ascension_frame, "XP: 0 / 1000 (0.0%)", 2, 0, columnspan=2, sticky='ew')
ascensionlabel=create_label(ascension_frame,"Ascension Locked",3,0,columnspan=2,sticky='ew',wraplength=400)
ascensionbutton=create_button(ascension_frame,"Ascend",ascend,4,0,columnspan=2)
# Relics Tab
relic_title = create_label(relics_frame, "Relics (Spend Stardust)", 0, 0, columnspan=3, sticky='ew', font=('-weight','bold'))
rr=1
for rid,data in RELICS_DATA.items():
    nl=create_label(relics_frame,data['name'],rr,0,sticky='e',font=('-weight','bold')); dl=create_label(relics_frame,data['desc'],rr,1,sticky='w',wraplength=300)
    ll=create_label(relics_frame,"Lvl: 0",rr+1,1,sticky='w'); cl=create_label(relics_frame,"Cost: ...",rr+2,1,sticky='w')
    bb=create_button(relics_frame,"Buy",lambda r=rid:buy_relic(r),rr,2,rowspan=3,sticky='ewns'); relic_widgets[rid]=(nl,dl,ll,cl,bb); rr+=3
    for w in relic_widgets[rid]: w.grid_remove() # Initially hidden
relic_title.grid_remove()
# Challenges Tab
create_label(challenges_frame,"Challenges",0,0,sticky='ew',font=('-weight','bold'))
exit_challenge_button = create_button(challenges_frame, "Exit Challenge", exit_challenge, 1, 0, sticky='ew', bootstyle="danger-outline")
exit_challenge_button.grid_remove()
challenge_scroll_frame = ttk.Frame(challenges_frame); challenge_scroll_frame.grid(row=2, column=0, sticky='nsew', pady=(10,0))
challenge_scroll_frame.grid_rowconfigure(0, weight=1); challenge_scroll_frame.grid_columnconfigure(0, weight=1)
challenge_canvas = tk.Canvas(challenge_scroll_frame, borderwidth=0, highlightthickness=0) # Remove border
challenge_list_frame = ttk.Frame(challenge_canvas); challenge_scrollbar = ttk.Scrollbar(challenge_scroll_frame, orient="vertical", command=challenge_canvas.yview, bootstyle="round")
challenge_canvas.configure(yscrollcommand=challenge_scrollbar.set); challenge_scrollbar.grid(row=0, column=1, sticky='ns'); challenge_canvas.grid(row=0, column=0, sticky='nsew')
challenge_canvas_window = challenge_canvas.create_window((0, 0), window=challenge_list_frame, anchor="nw")
def _configure_challenge_list_frame(event): challenge_canvas.configure(scrollregion=challenge_canvas.bbox("all"))
def _configure_challenge_canvas(event): challenge_canvas.itemconfig(challenge_canvas_window, width=event.width)
challenge_list_frame.bind("<Configure>", _configure_challenge_list_frame); challenge_canvas.bind('<Configure>', _configure_challenge_canvas)
challenge_list_frame.grid_columnconfigure(0, weight=1)
cr=0
for cid,chal in CHALLENGES.items():
    chal_frame = ttk.Frame(challenge_list_frame, padding=(5, 5), borderwidth=1, relief="solid")
    chal_frame.grid(row=cr, column=0, sticky='ew', pady=5); chal_frame.grid_columnconfigure(0, weight=1); chal_frame.grid_columnconfigure(1, weight=0)
    cl=create_label(chal_frame,f"...",0,0,sticky='nw',wraplength=550)
    cb=create_button(chal_frame,f"Enter C{cid[1:]}",lambda c=cid: enter_challenge(c),0,1,sticky='ne'); challenge_widgets[cid]=(cl, cb); cr+=1

# Admin Button
if DEVELOPER_MODE:
    admin_button=ttk.Button(window,text="Admin",command=open_admin_panel,bootstyle="info-outline")
    admin_button.grid(row=1,column=0,sticky='sw',padx=10,pady=5)

# ==============================================================================
#                             INITIALIZATION & MAIN LOOP
# ==============================================================================
load_game()
logging.info("Starting threads...")
game_thread=th.Thread(target=game_loop_thread_func,daemon=True); game_thread.start()
save_thread=th.Thread(target=autosave_thread_func,daemon=True); save_thread.start()
start_autobuy_thread_if_needed()
updateui()

def on_closing(save=True):
    global is_running, admin_window, active_admin_threads
    if not is_running: return
    logging.info("Shutdown initiated...")
    is_running=False
    if admin_window and admin_window.winfo_exists(): on_admin_close()
    timeout=0.3; threads=[t for t in [game_thread, save_thread, autobuy_thread] if t and t.is_alive()]
    if threads:
        logging.debug(f"Waiting for threads ({len(threads)})..."); start=time.monotonic()
        for t in threads: t.join(timeout)
        logging.debug(f"Join attempt finished in {time.monotonic()-start:.2f}s.")
    if active_admin_threads: logging.info(f"Note: {len(active_admin_threads)} admin threads active.")
    if save: save_game()
    else: logging.info("Skipping final save.")
    try:
        if window and window.winfo_exists(): window.destroy()
    except tk.TclError: logging.warning("Window already destroyed (TclError).")
    except Exception as e: logging.error(f"Window destroy error: {e}")
    logging.info("Shutdown complete."); logging.shutdown()

window.protocol("WM_DELETE_WINDOW", on_closing)

try:
    window.mainloop()
except KeyboardInterrupt:
    logging.info("KeyboardInterrupt received.")
    on_closing()
except Exception as e:
    logging.critical(f"Unhandled exception in main loop: {e}", exc_info=True)
    on_closing(save=False)

# --- END OF FILE ---
