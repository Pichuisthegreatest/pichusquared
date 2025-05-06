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
from tkinter import messagebox, PanedWindow

# --- ttkScrolledText Fallback ---
try:
    from ttkbootstrap.scrolled import ScrolledText as ttkScrolledText
except ImportError:
    class ttkScrolledText(tk.Frame):
        """Basic ScrolledText fallback if ttkbootstrap.scrolled is unavailable."""
        def __init__(self, master=None, **kw):
            tk.Frame.__init__(self, master)
            autohide = kw.pop('autohide', True)
            scrollbar_style = kw.pop('bootstyle', None) # Pass bootstyle to scrollbar
            text_font = kw.pop('font', None) # Handle font separately

            self.text = tk.Text(self, wrap=kw.pop('wrap', tk.WORD), state=kw.pop('state', tk.NORMAL), font=text_font)
            self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            sb_style = f"{scrollbar_style}.Vertical.TScrollbar" if scrollbar_style else "Vertical.TScrollbar"
            self.scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview, style=sb_style)

            self._autohide = autohide
            self._scroll_visible = False

            if not autohide:
                self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                self._scroll_visible = True

            self.text.configure(yscrollcommand=self._scroll_manager)

        def _scroll_manager(self, *args):
            # Set scrollbar position
            self.scrollbar.set(*args)
            # Manage visibility if autohide is on
            if self._autohide:
                if float(args[0]) <= 0.0 and float(args[1]) >= 1.0:
                    if self._scroll_visible:
                        self.scrollbar.pack_forget()
                        self._scroll_visible = False
                else:
                    if not self._scroll_visible:
                        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                        self._scroll_visible = True

        def insert(self, index, chars, *args): self.text.insert(index, chars, *args)
        def delete(self, index1, index2=None): self.text.delete(index1, index2)
        def get(self, index1, index2=None): return self.text.get(index1, index2)
        def see(self, index): self.text.see(index)
        def bind(self, sequence=None, func=None, add=None): self.text.bind(sequence, func, add)

        def configure(self, **kw):
            state = kw.pop('state', None)
            if state is not None: self.text.configure(state=state)
            try: tk.Frame.configure(self, **kw)
            except tk.TclError:
                 try: self.text.configure(**kw)
                 except tk.TclError: logging.warning(f"Failed to configure fallback ScrolledText: {kw}")

        @property
        def state(self): return self.text['state']
        @state.setter
        def state(self, value): self.text.configure(state=value)
        @property
        def yscrollcommand(self): return self.text['yscrollcommand']
        @yscrollcommand.setter
        def yscrollcommand(self, command): self.text['yscrollcommand'] = command

# --- Configuration ---
SAVE_FILE = "save_encoded.dat"
LOG_FILE = "gamelog.txt"
SAVE_VERSION = 36 # Incremented for NF changes and full celestial reset
UPDATE_INTERVAL_MS = 100
TICK_INTERVAL_S = 0.1
AUTOSAVE_INTERVAL_S = 30
DEVELOPER_MODE = False
POINT_THRESHOLD_SP = 1e21
RELIC_MAX_LEVEL = 10
MAX_BUY_ITERATIONS = 100
CELESTIALITY_REQ_ASC_LVL = 20
CELESTIALITY_REQ_PTS = 1e37 # 10 Ud
CELESTIALITY_REQ_CRYST = 5
CELESTIALITY_REQ_PUR = 20
NEBULA_FRAG_BASE_REQ_PTS = 1e37
NEBULA_FRAG_BASE_REQ_SD = 1e12
NEBULA_FRAG_BASE_REQ_ASC = 20

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logging.info("--- Game Start ---")

# --- Utility Functions ---
ENDINGS = ["K","M","B","T","Qa","Qi","Sx","Sp","Oc","No","Dc","Ud","Dd","Td","Qad","Qid","Sxd","Spd","Ocd","Nod","Vg"]
def format_number(num):
    if isinstance(num, bool): return str(num)
    if not isinstance(num, (int, float)) or num is None or ma.isnan(num): return str(num)
    if ma.isinf(num): return "Infinity" if num > 0 else "-Infinity"
    if abs(num) < 1000: return "{:.2f}".format(round(num, 2))
    if num == 0: return "0.00"
    sign = "-" if num < 0 else ""
    num_abs = abs(num)
    if ma.isinf(num_abs): return f"{sign}Infinity" # Handle early inf case
    count = 0
    power = 1000.0
    num_div = num_abs
    max_iterations = 100
    iterations = 0
    while num_div >= power and count < len(ENDINGS) and iterations < max_iterations:
        try:
            next_val = num_div / power
            if ma.isinf(next_val): break
            num_div = next_val
            count += 1
            iterations += 1
        except OverflowError: break
    if iterations >= max_iterations: return f"{sign}{num:.2e}"
    if count == 0: return "{}{:.2f}".format(sign, round(num_abs, 2))
    else:
        idx = min(count - 1, len(ENDINGS) - 1)
        if ma.isinf(num_div) or ma.isnan(num_div): return f"{sign}{num:.2e}"
        return "{}{:.2f}{}".format(sign, round(num_div, 2), ENDINGS[idx])

def obfuscate(text):
    return ''.join('?' if c.isalpha() else c for c in text)

# --- Game State Object ---
class GameState:
    def __init__(self):
        # Point Upgrades
        self.upg1_cst = 10.0; self.upg1_lvl = 0; self.upg1_max = 25.0
        self.upg2_cst = 100.0; self.upg2_lvl = 0; self.upg2_max = 10.0
        self.upg3_cst = 10000.0; self.upg3_lvl = 0; self.upg3_max = 10.0
        self.upg4_cst = 10000000.0; self.upg4_lvl = 0; self.upg4_max = 5.0
        # Click Upgrades
        self.upg5_comp = False; self.upg6_comp = False
        self.upg7_cst = 1e4; self.upg7_lvl = 0; self.upg7_max = 50.0
        self.upg8_cst = 1e7; self.upg8_lvl = 0; self.upg8_max = 100.0
        self.needs_recalc_from_click_xp = False
        # Calculated Modifiers
        self.mult = 1.0; self.mult_str = 1.0; self.pps_exp = 1.0
        self.clk_pow = 1.0; self.clk_crit_c = 0.0; self.clk_crit_m = 2.0
        self.auto_cps = 0.0; self.clk_pt_scale = 1.0
        # Purification State
        self.pur_cnt = 0; self.pur_max = 10; self.pur_cst = 1000.0
        self.r1_bst = 1.0; self.r2_unl = False; self.r3_unl = False
        self.r3_cst_m = 1.0; self.r4_u2_bst = 1.0; self.r5_u3_bst = 0.0
        self.r6_unl = False; self.r6_bst = 1.0
        # Crystalline State
        self.cryst_unl = False; self.cryst_cnt = 0; self.cryst_max = 4
        self.cryst_cst = 2.5e8; self.cr1_bst = 1.0; self.cr1_u4_unl = False
        self.cr2_bst = 1.0; self.cr3_unl = False; self.cr4_unl = False
        self.cr5_comp = False
        # Ascension State
        self.asc_unl = False; self.asc_cnt = 0; self.sd = 0.0
        self.asc_cst = 1e27; self.asc_lvl = 0; self.asc_xp = 0.0
        self.asc_first = False
        # Celestiality State
        self.celest_unl = False; self.celest_cnt = 0; self.nebula_fragments = 0.0
        self.celest_cst = CELESTIALITY_REQ_PTS
        # Relics
        self.relic_lvls = {}
        # Synergy/Later Effects
        self.cryst_comp_bst = 1.0; self.p11_pps_bst = 0.0; self.p12_auto_u4 = False
        self.p14_u2_bst = 1.0; self.p16_cst_reduc = 1.0; self.p17_u1_bst = 1.0
        self.p18_pass_clk = 0.0; self.p19_bst = 1.0; self.p20_lim_brk = False
        self.p24_pur_cst_div = 1.0
        # Challenges
        self.chal_comps = {}; self.chal_sd_bst = 1.0; self.chal_perm_clk_bst = 1.0
        self.chal_upg_cst_scale_mult = 1.0; self.active_chal = None
        # General State
        self.playtime = 0.0; self.admin_panel_active = False; self.last_save_time = time.time()
        # Scaling
        self.pps_pt_scale_exp = 1.0
        self.chal_eff_pps_exp_mod = 1.0
        self.chal_eff_cst_exp_mod = 1.0

    def get_xp_for_level(self, level):
        if level < 0: return 0
        try: return 1000 * (1.8 ** level)
        except OverflowError: return float('inf')

    def check_ascension_level_up(self, from_click=False):
        leveled_up = False
        current_lvl = int(max(0, self.asc_lvl))
        needed = self.get_xp_for_level(current_lvl + 1)
        if ma.isinf(self.asc_xp):
            while 0 < needed < float('inf'):
                self.asc_lvl += 1
                current_lvl = int(self.asc_lvl)
                leveled_up = True
                logging.info(f"Ascension Level Up! Reached Level {self.asc_lvl} (Infinite XP)")
                needed = self.get_xp_for_level(current_lvl + 1)
        elif ma.isfinite(self.asc_xp):
             while 0 < needed < float('inf') and self.asc_xp >= needed:
                if ma.isinf(needed): break
                if ma.isinf(self.asc_xp): break
                self.asc_xp -= needed
                self.asc_lvl += 1
                current_lvl = int(self.asc_lvl)
                leveled_up = True
                logging.info(f"Ascension Level Up! Reached Level {self.asc_lvl}")
                needed = self.get_xp_for_level(current_lvl + 1)
        if leveled_up:
            if from_click:
                self.needs_recalc_from_click_xp = True
            else:
                recalculate_derived_values()
            self.check_celestiality_unlock()
        return leveled_up

    def get_asc_pt_boost(self):
        lvl = int(max(0, self.asc_lvl))
        try: return (1.10 ** lvl)
        except OverflowError: return float('inf')

    def get_asc_clk_boost(self):
        lvl = int(max(0, self.asc_lvl))
        try: return (1.05 ** lvl)
        except OverflowError: return float('inf')

    def get_chal_relic_eff_boost(self, rid): return 1.0 # Chal 7 removed

    def check_celestiality_unlock(self):
        if not self.celest_unl and \
           int(self.asc_lvl) >= CELESTIALITY_REQ_ASC_LVL and \
           self.cr5_comp and \
           self.pur_cnt >= CELESTIALITY_REQ_PUR:
            self.celest_unl = True
            logging.info("Celestiality Unlocked!")

    def get_nf_point_boost(self):
        if self.nebula_fragments <= 0: return 1.0
        try:
            boost = (ma.log10(self.nebula_fragments + 1) + 1) ** 2 # Example formula
            return max(1.0, boost)
        except (ValueError, OverflowError): return float('inf')

    def get_nf_stardust_boost(self):
        if self.nebula_fragments <= 0: return 1.0
        try:
            boost = (ma.log10(self.nebula_fragments + 1) * 2 + 1) # Example formula
            return max(1.0, boost)
        except (ValueError, OverflowError): return float('inf')

    def get_nf_relic_boost(self):
        if self.nebula_fragments <= 0: return 1.0
        try:
            boost = (ma.log10(self.nebula_fragments + 1) * 0.5 + 1) # Example formula
            return max(1.0, boost)
        except (ValueError, OverflowError): return float('inf')

# --- Global Variables ---
g = GameState(); pts = 0.0; clks = 0.0; pps = 0.0
is_running = True; autobuy_thd = None

# --- Relic Definitions ---
RELICS_DATA = {
    'relic_pt_mult': { 'name': "Star Prism", 'desc': "+100% Points per level (mult)", 'cost_base': 1, 'cost_scale': 1.2, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 2.0 ** lvl },
    'relic_clk_mult': { 'name': "Kinetic Shard", 'desc': "+100% Effective Clicks per level (mult)", 'cost_base': 1, 'cost_scale': 1.2, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 2.0 ** lvl },
    'relic_u1_str': { 'name': "Amplifying Lens", 'desc': "Upg1 base multiplier gain +0.02 per level", 'cost_base': 8, 'cost_scale': 1.8, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 0.02 * lvl },
    'relic_p6_exp': { 'name': "Echoing Chamber", 'desc': "P6 Purify Boost ^(1 + 0.01*Lvl)", 'cost_base': 15, 'cost_scale': 2.0, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 1.0 + 0.01 * lvl },
    'relic_sd_gain': { 'name': "Cosmic Magnet", 'desc': "+2% Stardust gain per level (mult)", 'cost_base': 20, 'cost_scale': 2.2, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 1.02 ** lvl },
    'relic_u3_eff': { 'name': "Exponent Crystal", 'desc': "Upg3 Exponent Gain +1% per level (mult)", 'cost_base': 50, 'cost_scale': 1.9, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 1.01 ** lvl },
    'relic_crit_c': { 'name': "Focusing Matrix", 'desc': "+0.5% Crit Chance (additive)", 'cost_base': 10, 'cost_scale': 1.5, 'max_level': RELIC_MAX_LEVEL, 'effect': lambda lvl: 0.005 * lvl },
}

def get_relic_effect(rid, default=1.0):
    lvl = g.relic_lvls.get(rid, 0); data = RELICS_DATA.get(rid)
    if data and 'effect' in data:
        try:
            base_eff = data['effect'](lvl)
            if ma.isinf(base_eff) or base_eff == default: return base_eff
            nf_boost = g.get_nf_relic_boost()
            if ma.isinf(nf_boost): return float('inf')

            if rid in ['relic_u1_str', 'relic_crit_c']:
                 effective_eff = base_eff * nf_boost
            elif isinstance(base_eff, (int, float)) and base_eff > 0:
                 effective_eff = ((base_eff - 1.0) * nf_boost) + 1.0
            else: effective_eff = base_eff # No boost otherwise

            return effective_eff
        except OverflowError: return float('inf')
        except Exception as e: logging.error(f"Relic effect error {rid}: {e}"); return default
    return default

# --- Prestige Descriptions / Challenges / Help ---
PURIFY_DESCRIPTIONS = ["x3 point gain. Afterwards, x2 point gain.", "+1 max level to Upgs 1 & 2.", "Upg 1-3 cost x0.95 (mult).", "Upg 2 Strength base multiplier x3.", "Upg 3 base exponent gain +0.01/lvl.", "Gain (1+Purify Times)^2 PPS multiplier.", "No boost.", "No boost. Try again?", "No boost. Next unlocks something!", "Unlock Crystalline layer.", "Click Power adds +0.1% base PPS per point.", "Autobuy Upgrade 4.", "Each Crystalline +5% points (mult).", "Upg 2 base factor +50%.", "Unlock buying Crystalline V.", "Reduce upgrade cost scaling per Crystalline.", "Upg 1 levels slightly boost Rank 4 effect.", "Passive Clicks (1% of Click Power/sec).", "Boost previous Purifications power x1.25.", "LIMIT BREAK: +10 Max Levels Upgs 1 & 2.", "P21: Faster Crystalline Autobuyer (if unlocked)", "P22: Stardust gain x1.1", "P23: Reduce Relic costs by 5%", "Purify cost / sqrt(Purify Times)."]
CRYSTALLINE_DESCRIPTIONS = ["x3 point gain. Unlock Upgrade 4.", "Point gain ^1.5.", "Autobuy Upgrades 1-3.", "Unlock Clicking & Click Upgs. Base Click Power x100.", "Unlock P16-20+. Activate Playtime boost (needs Upg6). Unlock Ascension."]
CELESTIALITY_DESCRIPTIONS = ["Perform a full reset (keeps Celestiality progress). Gain Nebula Fragments based on prior progress, boosting Points, Stardust, and Relics."]

CHALLENGES = { # Renamed and strengthened challenges
    'c1': { 'db': "No Upg2: Reach High Points", 'mc': 100, 'rf': lambda g, c: 1e9*(2000**(c+1)), 'rd': lambda r: f"Req: {format_number(r)} Pts", 'cf': lambda g, r: (g.active_chal=='c1' and pts>=r and g.upg2_lvl==0), 'rwd': lambda g, c: f"R: +{(20.0 + c*10.0):.1f}% SD Gain (Mult)", 'arf': lambda g: setattr(g,'chal_sd_bst',g.chal_sd_bst*(1.20 + g.chal_comps.get('c1',0)*0.10)), 'restr': "No Upg2.", 'ef': None, 'rl': 'cryst'},
    'c2': { 'db': "No Upg3: Reach Crystalline Count", 'mc': 100, 'rf': lambda g, c: c+1, 'rd': lambda r: f"Req: Cryst {r}", 'cf': lambda g, r: (g.active_chal=='c2' and g.cryst_cnt>=r and g.upg3_lvl==0), 'rwd': lambda g, c: f"R: Upg3 Cost x{0.98**(c+1):.4f}", 'arf': lambda g: setattr(g,'r3_cst_m',g.r3_cst_m * 0.98), 'restr': "No Upg3.", 'ef': None, 'rl': 'asc'},
    'c3': { 'db': "Expensive Growth: Reach Points", 'mc': 50, 'rf': lambda g, c: 1e15*(75**(c+1)), 'rd': lambda r: f"Req: {format_number(r)} Pts", 'cf': lambda g, r: (g.active_chal=='c3' and pts>=r), 'rwd': lambda g, c: f"R: Upg1-4 Scale x{(1.0/(1.0+0.002*(c+1))):.4f}", 'arf': lambda g: setattr(g,'chal_upg_cst_scale_mult', 1.0 / (1.0 + 0.002 * (g.chal_comps.get('c3', 0) + 1))), 'restr': "Upg1-4 cost scale +25%.", 'ef': lambda g: setattr(g,'chal_eff_cst_exp_mod',1.25), 'rl': 'cryst'},
}

HELP_CONTENT = { # Edit the triple-quoted strings below to change help text
    'points': """**Points**
Points are the primary currency in the early game. You generate Points Per Second (PPS) based on your upgrades. You can also spend Points on upgrades to increase your PPS or unlock new mechanics.""",
    'purify': """**Purification**
Purification is the first prestige layer, unlocked by reaching the point requirement.
- **Reset:** Resets Points, Point Upgrades (1-4), and Playtime (unless in a challenge). Keeps Crystalline progress, Ascension progress, Relics, etc.
- **Reward:** Each Purification grants a unique, permanent bonus listed on the Purify button. These boosts stack and some synergize with later layers or get boosted themselves. Reaching certain Purify milestones unlocks new game layers like Crystalline.
- **Cost:** Increases with each Purification.""",
    'crystalline': """**Crystalline**
Crystalline is the second prestige layer, unlocked at Purification 10.
- **Reset:** Resets everything Purify resets, PLUS Purification progress and Purify bonuses. Keeps Ascension progress, Relics, Challenges, etc.
- **Reward:** Each Crystalline level grants a powerful permanent bonus, such as point multipliers, unlocking Upgrade 4, unlocking Autobuyers, unlocking Clicking, or unlocking Ascension.
- **Cost:** Increases significantly with each Crystalline level.""",
    'clicking': """**Clicking**
Unlocked at Crystalline 4. Allows manual clicking and introduces Click upgrades.
- **Clicks:** A new currency generated by clicking the 'Click!' button or by the Auto Clicker (Upg 8).
- **Click Power:** Determines how many Clicks you get per manual click. Affected by base power, relics, ascension, and point scaling.
- **Click Upgrades:** Spend Clicks to improve clicking (Crit Chance/Multiplier - Upg7) or automate clicks (Auto Clicker - Upg8). Upg5 and Upg6 unlock more Purify levels and enable Crystalline 5 effects.
- **Interaction:** Some Purify bonuses use Click Power to boost PPS.""",
    'ascension': """**Ascension**
The third prestige layer, unlocked at Crystalline 5. This is a major reset.
- **Reset:** Resets everything Crystalline resets, PLUS Crystalline progress/bonuses, Clicking progress/upgrades, and Clicks. Keeps Stardust, Ascension Level/XP, Relics, and Challenge completions.
- **Reward:** Gain Stardust (SD) based on Points and Crystalline count at the time of Ascending. Stardust is used to buy powerful Relics. Gain Ascension XP based on Points and SD gain, which increases your Ascension Level.
- **Ascension Level:** Each level provides permanent passive boosts to Point Gain and Click Power.
- **Cost:** Requires a high amount of Points.""",
    'relics': """**Relics**
Unlocked after your first Ascension. Purchased with Stardust (SD).
- **Stardust:** Earned by Ascending. Gain is boosted by specific challenges, relics, and the amount of progress made before Ascending. Can be boosted further by Celestiality.
- **Purchase:** Relics provide powerful, permanent passive bonuses that affect various game mechanics (Points, Clicks, Upgrade effects, etc.). Their effectiveness can be further boosted by Celestiality.
- **Levels:** Each Relic can be leveled up multiple times, increasing its effect but also its Stardust cost. Costs scale exponentially. Some Purify bonuses can reduce Relic costs.""",
    'challenges': """**Challenges**
Unlocked after your first Ascension. Offer unique rewards for completing specific goals under restrictions.
- **Entry:** Entering a challenge forces a reset specific to that challenge (usually Crystalline or Ascension level) and applies its restrictions. You cannot Purify, Crystalline, Ascend, or enter another challenge while in one.
- **Completion:** Meet the goal shown (e.g., reach X points, Y clicks) while respecting the restrictions.
- **Reward:** Completing a challenge grants a permanent, stacking bonus. Each challenge can be completed multiple times (up to its cap) for increasingly powerful rewards.
- **Exit:** You can exit a challenge early without reward via the 'Exit Challenge' button, which performs an Ascension reset.""",
    'celestiality': """**Celestiality** (Very Late Game)
The fourth prestige layer, unlocked after reaching Ascension Level 20, Crystalline 5, and Purify 20.
- **Reset:** Performs a **FULL** reset of previous layers, including Points, Clicks, Purify, Crystalline, Ascension (Level/XP), and Stardust. Relics and Challenges are also reset. Only Celestiality progress (Nebula Fragments, Celestiality Count) is kept.
- **Reward:** Gain **Nebula Fragments** (NF) based on your Points, Stardust, and Ascension Level at the time of reset. Nebula Fragments provide powerful, scaling bonuses:
    - Significantly boosts Point gain.
    - Significantly boosts Stardust gain on Ascension.
    - Increases the effectiveness of all Relics.
- **Cost:** Requires an immense amount of Points (starting at 10 Undecillion) and increases dramatically with each Celestiality.""",
}

# --- Core Calculation Logic ---
def calculate_click_point_bonus():
    cur_pts = pts if ma.isfinite(pts) else 0.0
    if cur_pts <= POINT_THRESHOLD_SP: return 1.0
    try:
        if cur_pts <= 0: return 1.0
        orders = ma.log10(max(1e-300, cur_pts / POINT_THRESHOLD_SP))
        damp_exp = ma.log10(max(0, orders) + 1.0) * 2.0
        try:
            bonus = 2.0 ** damp_exp
            return max(1.0, bonus)
        except OverflowError: return float('inf')
    except (ValueError, OverflowError): return 1.0

def get_upgrade_cost_scale_mult():
    base_scale = g.chal_eff_cst_exp_mod
    reward_scale = g.chal_upg_cst_scale_mult
    return base_scale * reward_scale

def get_upgrade2_factor():
    gain = 0.10
    if g.pur_cnt >= 14:
        p19_factor = g.p19_bst if g.pur_cnt >= 19 else 1.0
        gain *= (1.0 + 0.5 * p19_factor)
    return 1.0 + gain

def recalculate_multiplier_strength():
    factor = get_upgrade2_factor()
    p17_bst = (1.0 + g.upg1_lvl * 0.002 * g.p17_u1_bst) if g.pur_cnt >= 17 else 1.0
    eff_r4_bst = g.r4_u2_bst * p17_bst
    try:
        lvl = int(g.upg2_lvl)
        g.mult_str = (factor ** lvl) * eff_r4_bst
    except OverflowError: g.mult_str = float('inf')
    except ValueError: g.mult_str = 1.0 # Fallback if level is invalid

def calculate_point_per_second():
    global pps, g; _pps = 0.0
    try:
        relic_pt_m = get_relic_effect('relic_pt_mult')
        relic_p6_exp_m = get_relic_effect('relic_p6_exp')
        relic_clk_m = get_relic_effect('relic_clk_mult')
        asc_pt_bst = g.get_asc_pt_boost()
        asc_clk_bst = g.get_asc_clk_boost()
        nf_pt_bst = g.get_nf_point_boost()

        eff_clk_pow = float('inf')
        if not any(ma.isinf(v) for v in [g.clk_pow, g.chal_perm_clk_bst, asc_clk_bst, g.clk_pt_scale, relic_clk_m]):
            try: eff_clk_pow = g.clk_pow * g.chal_perm_clk_bst * asc_clk_bst * g.clk_pt_scale * relic_clk_m
            except OverflowError: pass # Stays inf

        base_pps_clk = 0.0
        if g.pur_cnt >= 11 and g.p11_pps_bst > 0:
            if ma.isinf(eff_clk_pow): base_pps_clk = float('inf')
            else:
                 try: base_pps_clk = eff_clk_pow * g.p11_pps_bst
                 except OverflowError: base_pps_clk = float('inf')

        base_pps = 1.0 + base_pps_clk
        eff_mult = g.mult * g.mult_str

        _pps = base_pps
        multipliers = [eff_mult, g.r1_bst, nf_pt_bst, asc_pt_bst, relic_pt_m]

        if g.r6_unl:
            try:
                 bst_r6 = (g.r6_bst ** relic_p6_exp_m) if not (ma.isinf(g.r6_bst) or ma.isinf(relic_p6_exp_m)) else float('inf')
                 multipliers.append(bst_r6)
            except OverflowError: multipliers.append(float('inf'))

        multipliers.extend([g.cr1_bst, g.cryst_comp_bst])
        if g.pur_cnt >= 19: multipliers.append(g.p19_bst)

        if g.cr5_comp and g.upg6_comp:
            multipliers.append(calculate_playtime_multiplier())

        for m in multipliers:
            if ma.isinf(_pps) or ma.isinf(m):
                 _pps = float('inf'); break
            try: _pps *= m
            except OverflowError: _pps = float('inf'); break
        if ma.isinf(_pps): pps = float('inf'); return

        if _pps > 0:
            try:
                total_exp = 1.0
                exponents = [g.cr2_bst, g.pps_exp, g.pps_pt_scale_exp, g.chal_eff_pps_exp_mod]
                for e in exponents:
                    if e != 1.0: total_exp *= e

                if total_exp != 1.0:
                     if _pps <= 0: _pps = 0.0
                     else: _pps **= total_exp
            except OverflowError: _pps = float('inf')
            except ValueError: _pps = 0.0
        elif _pps < 0: _pps = 0.0

    except Exception as e:
         logging.error(f"PPS calc error: {e}", exc_info=True)
         _pps = 0.0

    pps = _pps if ma.isfinite(_pps) else (float('inf') if _pps > 0 else 0.0)
    # logging.debug(f"Calculated PPS: {pps}") # DEBUG Line

def calculate_playtime_multiplier():
    play_s = g.playtime if isinstance(g.playtime,(int,float)) else 0
    if play_s <= 0: return 1.0
    try:
        mins = max(1e-9, play_s / 60.0)
        bonus = ma.log10(mins + 1) + 1.0
        return max(1.0, round(bonus, 3))
    except (ValueError, OverflowError): return 1.0

def recalculate_derived_values():
    global g, pts
    g.chal_eff_pps_exp_mod, g.chal_eff_cst_exp_mod = 1.0, 1.0
    if g.active_chal and g.active_chal in CHALLENGES:
        eff_func = CHALLENGES[g.active_chal].get('ef')
        if eff_func:
            try: eff_func(g)
            except Exception as e: logging.error(f"Chal {g.active_chal} effect error: {e}")

    p19f = g.p19_bst if g.pur_cnt >= 19 else 1.0
    g.r6_bst = ((1.0 + g.pur_cnt)**2.0) if g.r6_unl else 1.0
    g.p11_pps_bst = 0.001 * p19f if g.pur_cnt >= 11 else 0.0
    g.cryst_comp_bst = 1.0 + (g.cryst_cnt * 0.05 * p19f) if g.pur_cnt >= 13 else 1.0
    g.p16_cst_reduc = max(0.5, 1.0 - (g.cryst_cnt * 0.005 * p19f)) if g.pur_cnt >= 16 else 1.0
    g.p17_u1_bst = p19f if g.pur_cnt >= 17 else 1.0
    g.p18_pass_clk = 0.01 * p19f if g.pur_cnt >= 18 else 0.0
    g.p24_pur_cst_div = max(1.0, ma.sqrt(max(0,g.pur_cnt)) * p19f) if g.pur_cnt >= 24 else 1.0

    g.clk_pt_scale = calculate_click_point_bonus()
    cur_pts_safe = pts if ma.isfinite(pts) else 0.0
    g.pps_pt_scale_exp = 1.0
    if cur_pts_safe > POINT_THRESHOLD_SP:
        try:
            orders = ma.log10(max(1e-300, cur_pts_safe / POINT_THRESHOLD_SP)) if cur_pts_safe > 0 else -300
            red_str = 0.05 if g.p20_lim_brk else 0.02
            base_min = 0.3 if g.p20_lim_brk else 0.5
            target_exp = 1.0 - (ma.log10(max(0, orders) + 1.0) * red_str)
            g.pps_pt_scale_exp = max(base_min, target_exp) # Use base_min directly
        except (ValueError, OverflowError):
            g.pps_pt_scale_exp = 0.3 if g.p20_lim_brk else 0.5

    relic_crit_c = get_relic_effect('relic_crit_c', 0.0) # NF boost included
    g.clk_crit_c = min(1.0, (0.05 * g.upg7_lvl) + relic_crit_c)
    g.clk_crit_m = 2.0 + (0.2 * g.upg7_lvl)

    relic_clk_m = get_relic_effect('relic_clk_mult') # NF boost included
    asc_clk_bst = g.get_asc_clk_boost()
    eff_base_clk = float('inf')
    if not any(ma.isinf(v) for v in [g.clk_pow, g.chal_perm_clk_bst, asc_clk_bst, g.clk_pt_scale, relic_clk_m]):
        try: eff_base_clk = g.clk_pow * g.chal_perm_clk_bst * asc_clk_bst * g.clk_pt_scale * relic_clk_m
        except OverflowError: pass

    base_auto, pass_auto = 0.0, 0.0
    if ma.isinf(eff_base_clk):
        base_auto = float('inf') if (0.01 * g.upg8_lvl) > 0 else 0.0
        pass_auto = float('inf') if g.p18_pass_clk > 0 else 0.0
    else:
        try: base_auto = eff_base_clk * (0.01 * g.upg8_lvl)
        except OverflowError: base_auto = float('inf')
        try: pass_auto = eff_base_clk * g.p18_pass_clk if g.p18_pass_clk > 0 else 0.0
        except OverflowError: pass_auto = float('inf')
    g.auto_cps = float('inf') if ma.isinf(base_auto) or ma.isinf(pass_auto) else base_auto + pass_auto

    recalculate_multiplier_strength()
    calculate_point_per_second()

    g.pur_max = 20 if g.cr5_comp else (15 if g.upg5_comp else 10)
    g.cryst_max = 5 if g.pur_cnt >= 15 else 4
    g.check_celestiality_unlock()
    # Removed debug log for cleaner output, re-enable if needed

# --- Game Loop Logic ---
def game_tick():
    global pts, clks, pps, g
    try:
        _pps = pps if ma.isfinite(pps) else 0.0
        cur_pts = pts if ma.isfinite(pts) else 0.0
        cur_clks = clks if ma.isfinite(clks) else 0.0
        _cps = g.auto_cps if ma.isfinite(g.auto_cps) else 0.0

        pts_gain = _pps * TICK_INTERVAL_S
        clks_gain = _cps * TICK_INTERVAL_S

        try:
            if ma.isinf(cur_pts) and cur_pts > 0: pts = float('inf')
            elif ma.isinf(pts_gain) and pts_gain > 0: pts = float('inf')
            elif ma.isfinite(cur_pts) and ma.isfinite(pts_gain):
                 next_pts = cur_pts + pts_gain
                 pts = float('inf') if ma.isinf(next_pts) else next_pts
            else: pts = cur_pts
        except OverflowError: pts = float('inf')

        try:
            if ma.isinf(cur_clks) and cur_clks > 0: clks = float('inf')
            elif ma.isinf(clks_gain) and clks_gain > 0: clks = float('inf')
            elif ma.isfinite(cur_clks) and ma.isfinite(clks_gain):
                 next_clks = cur_clks + clks_gain
                 clks = float('inf') if ma.isinf(next_clks) else next_clks
            else: clks = cur_clks
        except OverflowError: clks = float('inf')

        g.playtime += TICK_INTERVAL_S

        if g.needs_recalc_from_click_xp:
            recalculate_derived_values()
            g.needs_recalc_from_click_xp = False

        if g.active_chal and int(g.playtime / TICK_INTERVAL_S) % int(1/TICK_INTERVAL_S) == 0:
             check_challenge_completion()

    except Exception as e: logging.error(f"Tick error: {e}", exc_info=True)

def game_loop_thread_func():
    logging.info("Game loop thread started.")
    while is_running:
        start = time.monotonic()
        try: game_tick()
        except Exception as e:
             logging.error(f"Tick loop error: {e}", exc_info=True)
             time.sleep(1)
        elapsed = time.monotonic() - start
        sleep_duration = max(0, TICK_INTERVAL_S - elapsed)
        time.sleep(sleep_duration)
    logging.info("Game loop thread finished.")

# --- Upgrade Functions ---
def get_effective_cost_factor(base):
    chal_eff_scale = g.chal_eff_cst_exp_mod
    chal_rew_scale = g.chal_upg_cst_scale_mult
    return base * chal_eff_scale * chal_rew_scale

def upgrade1():
    global pts, g; cst = g.upg1_cst
    try: lvl = int(g.upg1_lvl); max_lvl = int(g.upg1_max)
    except ValueError: return # Invalid level/max
    if lvl >= max_lvl or pts < cst or ma.isinf(cst): return
    pts -= cst; g.upg1_lvl += 1; g.mult += (1.0 + get_relic_effect('relic_u1_str', 0.0))
    factor = get_effective_cost_factor(1.15)
    reduc = g.r3_cst_m * g.p16_cst_reduc
    try: g.upg1_cst = round(10.0 * (factor ** g.upg1_lvl) * reduc, 2)
    except OverflowError: g.upg1_cst = float('inf')
    recalculate_derived_values()

def upgrade2():
    global pts, g; cst = g.upg2_cst
    try: lvl = int(g.upg2_lvl); max_lvl = int(g.upg2_max)
    except ValueError: return
    if g.active_chal == 'c1' or lvl >= max_lvl or pts < cst or ma.isinf(cst): return
    pts -= cst; g.upg2_lvl += 1
    factor = get_effective_cost_factor(1.25)
    reduc = g.r3_cst_m * g.p16_cst_reduc
    try: g.upg2_cst = round(100.0 * (factor ** g.upg2_lvl) * reduc, 2)
    except OverflowError: g.upg2_cst = float('inf')
    recalculate_derived_values()

def upgrade3():
    global pts, g; cst = g.upg3_cst
    try: lvl = int(g.upg3_lvl); max_lvl = int(g.upg3_max)
    except ValueError: return
    if g.active_chal == 'c2' or lvl >= max_lvl or pts < cst or ma.isinf(cst): return
    pts -= cst; g.upg3_lvl += 1
    gain = 0.05 + g.r5_u3_bst
    relic_m = get_relic_effect('relic_u3_eff', 1.0) # NF boost included
    if ma.isinf(relic_m): gain = float('inf')
    elif ma.isfinite(relic_m): gain *= relic_m
    eff_gain = gain
    softcap_exponent = 2.0
    diminishing_factor = 0.1
    limit_break_factor = 0.1
    if g.pps_exp > softcap_exponent: eff_gain *= diminishing_factor
    if g.p20_lim_brk: eff_gain *= limit_break_factor
    if ma.isinf(eff_gain): g.pps_exp = float('inf')
    elif ma.isfinite(g.pps_exp): g.pps_exp += max(0.001, eff_gain)
    factor = get_effective_cost_factor(1.35)
    reduc = g.r3_cst_m * g.p16_cst_reduc
    try: g.upg3_cst = round(10000.0 * (factor ** g.upg3_lvl) * reduc, 2)
    except OverflowError: g.upg3_cst = float('inf')
    recalculate_derived_values()

def upgrade4():
    global pts, g; cst = g.upg4_cst
    try: lvl = int(g.upg4_lvl); max_lvl = int(g.upg4_max)
    except ValueError: return
    if not g.cr1_u4_unl or lvl >= max_lvl or pts < cst or ma.isinf(cst): return
    pts -= cst; g.upg4_lvl += 1; g.upg3_max += 1.0
    factor = get_effective_cost_factor(1.50)
    reduc = g.p16_cst_reduc
    try: g.upg4_cst = round(10000000.0 * (factor ** g.upg4_lvl) * reduc, 2)
    except OverflowError: g.upg4_cst = float('inf')
    recalculate_derived_values()

def upgrade5():
    global clks, g; req = 10.0
    if not g.cr4_unl or g.upg5_comp or clks < req: return
    g.upg5_comp = True; g.pur_max = 15; logging.info("Upg5 Done! Purify Max -> 15.")
    recalculate_derived_values()

def upgrade6():
    global clks, g; req = 1000.0
    if not g.cr4_unl or g.upg6_comp or clks < req: return
    g.upg6_comp = True; logging.info("Upg6 Done! C5 Playtime Boost Active.")
    recalculate_derived_values()

def upgrade7():
    global clks, g; cst = g.upg7_cst
    try: lvl = int(g.upg7_lvl); max_lvl = int(g.upg7_max)
    except ValueError: return
    if not g.cr4_unl or lvl >= max_lvl or clks < cst or ma.isinf(cst): return
    clks -= cst; g.upg7_lvl += 1
    try: g.upg7_cst *= 1.5
    except OverflowError: g.upg7_cst = float('inf')
    recalculate_derived_values()

def upgrade8():
    global clks, g; cst = g.upg8_cst
    try: lvl = int(g.upg8_lvl); max_lvl = int(g.upg8_max)
    except ValueError: return
    if not g.cr4_unl or lvl >= max_lvl or clks < cst or ma.isinf(cst): return
    clks -= cst; g.upg8_lvl += 1
    try: g.upg8_cst *= 2.0
    except OverflowError: g.upg8_cst = float('inf')
    recalculate_derived_values()

# --- Prestige Functions ---
def apply_purification_effects(p_idx):
    global g; p_num = p_idx + 1
    if p_num == 1: g.r1_bst = 3.0
    elif p_num > 1: g.r1_bst *= 2.0
    if p_num == 2: g.r2_unl=True; g.upg1_max+=1.0; g.upg2_max+=1.0
    if p_num == 3: g.r3_unl=True; g.r3_cst_m*=0.95
    if p_num == 4: g.r4_u2_bst=3.0;
    if p_num == 5: g.r5_u3_bst=0.01;
    if p_num == 6: g.r6_unl=True;
    if p_num == 10: g.cryst_unl=True;
    if p_num == 12: g.p12_auto_u4=True; start_autobuy_thread_if_needed()
    # P15 unlocks C5 requirement, no direct state change
    if p_num == 19: g.p19_bst=1.25;
    if p_num == 20 and g.cr5_comp and not g.p20_lim_brk:
        g.p20_lim_brk=True; add=10.0; g.upg1_max+=add; g.upg2_max+=add
        logging.info(f"P20 Limit Break! (+{int(add)} Max Upg1/2)")
    g.check_celestiality_unlock()

def apply_crystalline_effects(cry_lvl):
    global g
    if cry_lvl == 1: g.cr1_bst=3.0; g.cr1_u4_unl=True
    elif cry_lvl == 2: g.cr2_bst=1.5
    elif cry_lvl == 3: g.cr3_unl=True; start_autobuy_thread_if_needed()
    elif cry_lvl == 4: g.cr4_unl=True; g.clk_pow=100.0; logging.info(f"C4! Click Power -> {format_number(g.clk_pow)}")
    elif cry_lvl == 5: g.cr5_comp=True; g.asc_unl=True
    g.check_celestiality_unlock()

# --- Reset Functions ---
def reset_for_purify(keep_chal=False):
    global pts, g; pts = 0.0
    g.upg1_lvl, g.upg1_cst = 0, 10.0
    g.upg2_lvl, g.upg2_cst = 0, 100.0
    g.upg3_lvl, g.upg3_cst = 0, 10000.0
    g.upg4_lvl, g.upg4_cst = 0, 10000000.0
    g.mult = 1.0
    g.pps_exp = 1.0 # Base exponent resets
    if not keep_chal: g.playtime = 0.0

def reset_for_crystalline(keep_chal=False):
    global pts, g
    g.pur_cnt, g.pur_cst, g.r1_bst, g.r2_unl, g.r3_unl = 0, 1000.0, 1.0, False, False
    g.r3_cst_m, g.r4_u2_bst, g.r5_u3_bst, g.r6_unl, g.r6_bst = 1.0, 1.0, 0.0, False, 1.0
    g.p11_pps_bst, g.p12_auto_u4, g.cryst_comp_bst = 0.0, False, 1.0
    g.p16_cst_reduc, g.p17_u1_bst, g.p18_pass_clk, g.p19_bst = 1.0, 1.0, 0.0, 1.0
    g.p20_lim_brk, g.p24_pur_cst_div = False, 1.0
    g.upg1_max, g.upg2_max, g.upg3_max, g.upg4_max = 25.0, 10.0, 10.0, 5.0
    reset_for_purify(keep_chal)
    g.cryst_unl = True

def reset_for_ascension(keep_chal=False):
    global pts, clks, g; logging.info("Resetting for Ascension...")
    pts, clks = 0.0, 0.0
    g.cryst_cnt, g.cryst_cst, g.cr1_bst, g.cr1_u4_unl = 0, 2.5e8, 1.0, False
    g.cr2_bst, g.cr3_unl, g.cr4_unl, g.cr5_comp = 1.0, False, False, False
    g.upg5_comp, g.upg6_comp = False, False
    g.upg7_lvl, g.upg7_cst = 0, 1e4
    g.upg8_lvl, g.upg8_cst = 0, 1e7
    g.clk_pow, g.clk_crit_c, g.clk_crit_m, g.auto_cps = 1.0, 0.0, 2.0, 0.0
    reset_for_crystalline(keep_chal)
    g.asc_unl = True
    if not keep_chal: g.active_chal = None

def reset_for_celestiality(keep_chal=False):
    global g, pts, clks; logging.info("Resetting for Celestiality (Full Reset)...")
    # Reset Ascension
    g.sd = 0.0; g.asc_lvl = 0; g.asc_xp = 0.0; g.asc_cnt = 0; g.asc_first = False
    # Reset Relics & Challenges
    g.relic_lvls.clear(); g.chal_comps.clear()
    g.chal_sd_bst = 1.0; g.chal_perm_clk_bst = 1.0; g.chal_upg_cst_scale_mult = 1.0
    # Reset C2 reward affecting Upg3 cost
    g.r3_cst_m = 1.0
    # Perform lower resets
    reset_for_ascension(keep_chal)
    # Ensure Celestiality stays unlocked but keep NF/Count
    g.celest_unl = True
    logging.info("Celestiality Reset: SD, Asc Lvl/XP/Count, Relics, Challenges reset.")

def reset_for_challenge(cid):
    global g; chal_data = CHALLENGES.get(cid)
    if not chal_data: return
    reset_type = chal_data.get('rl', 'asc').lower()
    logging.info(f"Entering Chal '{cid}'. Reset: '{reset_type}'.")
    # Preserve state surviving the reset
    _celest_cnt, _neb_frag, _celest_cst, _celest_unl = g.celest_cnt, g.nebula_fragments, g.celest_cst, g.celest_unl
    _lvl, _xp, _first, _sd, _asc_cnt = g.asc_lvl, g.asc_xp, g.asc_first, g.sd, g.asc_cnt
    _rl, _cc = g.relic_lvls.copy(), g.chal_comps.copy()
    _sb, _cb, _cm = g.chal_sd_bst, g.chal_perm_clk_bst, g.chal_upg_cst_scale_mult

    # Perform reset
    if reset_type == 'purify': reset_for_purify(True)
    elif reset_type in ['crystalline', 'cryst']: reset_for_crystalline(True)
    elif reset_type in ['ascension', 'asc']: reset_for_ascension(True)
    else: reset_for_ascension(True) # Default

    # Restore state
    g.celest_cnt, g.nebula_fragments, g.celest_cst, g.celest_unl = _celest_cnt, _neb_frag, _celest_cst, _celest_unl
    if reset_type in ['purify', 'crystalline', 'cryst', 'ascension', 'asc']:
        g.asc_lvl, g.asc_xp, g.asc_first, g.sd, g.asc_cnt = _lvl, _xp, _first, _sd, _asc_cnt
        g.relic_lvls, g.chal_comps = _rl, _cc
        g.chal_sd_bst, g.chal_perm_clk_bst, g.chal_upg_cst_scale_mult = _sb, _cb, _cm

    g.active_chal, g.playtime = cid, 0.0
    recalculate_derived_values()
    logging.info(f"Challenge '{cid}' started.")

# --- Action Functions ---
def purify():
    global pts, g
    recalculate_derived_values()
    cur_max = g.pur_max; can, reason = False, "Max Level"
    next_p = g.pur_cnt + 1
    if g.pur_cnt < cur_max:
        if next_p <= 10: can=True
        elif next_p <= 15: can=g.upg5_comp; reason="Req Upg5"
        else: can=g.cr5_comp; reason="Req C5"
    if not can: return
    cst = g.pur_cst / g.p24_pur_cst_div
    if pts < cst: return
    apply_purification_effects(g.pur_cnt)
    prev_pur_cnt = g.pur_cnt; g.pur_cnt += 1
    if not ma.isinf(pts): pts = max(0, pts - cst)
    reset_for_purify(g.active_chal is not None)
    try: g.pur_cst = round(g.pur_cst * (3.0 + prev_pur_cnt), 2)
    except OverflowError: g.pur_cst = float('inf')
    logging.info(f"Purified! {g.pur_cnt}/{int(cur_max)}. NextCost: {format_number(g.pur_cst / g.p24_pur_cst_div)}")
    recalculate_derived_values()

def crystalline():
    global pts, g
    if not g.cryst_unl: return
    recalculate_derived_values(); eff_max = g.cryst_max
    next_c = g.cryst_cnt + 1
    if g.cryst_cnt >= eff_max or (next_c == 5 and g.pur_cnt < 15): return
    cst = g.cryst_cst
    if pts < cst: return
    apply_crystalline_effects(next_c); g.cryst_cnt += 1
    if not ma.isinf(pts): pts = max(0, pts - cst)
    reset_for_crystalline(g.active_chal is not None)
    costs = {0: 2.5e8, 1: 1e12, 2: 1e15, 3: 1e18, 4: 1e21}
    g.cryst_cst = costs.get(g.cryst_cnt, float('inf'))
    logging.info(f"Crystallized! {g.cryst_cnt}/{int(eff_max)}. NextCost: {format_number(g.cryst_cst)}")
    recalculate_derived_values()

def ascend():
    global pts, g
    if not g.asc_unl or g.active_chal or pts < g.asc_cst: return
    sd_gain = 0
    try:
        if pts >= g.asc_cst and ma.isfinite(pts) and pts > 0:
            log_ratio = ma.log10(max(1, pts / max(1, g.asc_cst))); base_sd = 1 + 0.5 * log_ratio
            cryst_mult = ma.sqrt(g.cryst_cnt + 1)
            relic_bst = get_relic_effect('relic_sd_gain') # NF incl
            chal_bst = g.chal_sd_bst; p22_bst = 1.1 if g.pur_cnt >= 22 else 1.0
            nf_bst = g.get_nf_stardust_boost()
            all_boosts = cryst_mult * relic_bst * chal_bst * p22_bst * nf_bst
            if ma.isinf(all_boosts) or ma.isinf(base_sd): sd_gain = float('inf')
            else: sd_gain = ma.floor(base_sd * all_boosts); sd_gain = max(1, sd_gain)
    except (ValueError, OverflowError, TypeError) as e: sd_gain = 0; logging.error(f"SD Gain Calc Err: {e}")
    if sd_gain <= 0 and not ma.isinf(sd_gain): return
    xp_gain = 0.0
    try:
        if pts >= g.asc_cst and ma.isfinite(pts) and pts > 0:
             base_xp = 100.0; point_scale_xp = 0.0
             if pts > 1e40: point_scale_xp = 50 * ma.log10(max(1, pts / 1e40))
             sd_bonus_xp = float('inf') if ma.isinf(sd_gain) else (sd_gain * 10.0 if sd_gain > 0 else 0.0)
             if ma.isinf(sd_bonus_xp) or ma.isinf(point_scale_xp): xp_gain = float('inf')
             else: xp_gain = max(0.0, base_xp + point_scale_xp + sd_bonus_xp)
    except (ValueError, OverflowError, TypeError) as e: xp_gain = 0.0; logging.error(f"XP Gain Calc Err: {e}")
    logging.info(f"Ascending! Gain: {format_number(sd_gain)} SD, {format_number(xp_gain)} XP.")
    if ma.isinf(g.sd) or ma.isinf(sd_gain): g.sd = float('inf')
    elif ma.isfinite(g.sd) and ma.isfinite(sd_gain): g.sd += sd_gain
    if ma.isinf(g.asc_xp) or ma.isinf(xp_gain): g.asc_xp = float('inf')
    elif ma.isfinite(g.asc_xp) and ma.isfinite(xp_gain): g.asc_xp += xp_gain
    g.asc_cnt += 1
    if not g.asc_first: g.asc_first=True; logging.info("First Ascension! Relics and Challenges unlocked.")
    reset_for_ascension()
    g.check_ascension_level_up()
    recalculate_derived_values()

def celestiality():
    global pts, g
    if not g.celest_unl or g.active_chal: return
    req_met = (int(g.asc_lvl) >= CELESTIALITY_REQ_ASC_LVL and
               int(g.cryst_cnt) >= CELESTIALITY_REQ_CRYST and
               int(g.pur_cnt) >= CELESTIALITY_REQ_PUR)
    if not req_met or pts < g.celest_cst: return
    logging.info(f"Performing Celestiality {g.celest_cnt + 1}...")
    nf_gain = 0.0
    try:
        point_factor = ma.log10(max(1.0, pts / NEBULA_FRAG_BASE_REQ_PTS)) if ma.isfinite(pts) and pts > 0 else 0.0
        sd_factor = ma.log10(max(1.0, g.sd / NEBULA_FRAG_BASE_REQ_SD)) if ma.isfinite(g.sd) and g.sd > 0 else 0.0
        asc_factor = ma.sqrt(max(0, g.asc_lvl / NEBULA_FRAG_BASE_REQ_ASC)) if ma.isfinite(g.asc_lvl) and g.asc_lvl > 0 else 0.0
        base_gain = max(0.0, point_factor) + max(0.0, sd_factor) + max(0.0, asc_factor)
        nf_gain = ma.floor(base_gain * 1.0) # Adjust multiplier for balance
        nf_gain = max(0.0, nf_gain)
    except (ValueError, OverflowError, TypeError) as e: nf_gain = 0.0; logging.error(f"NF Gain Calc Err: {e}")
    logging.info(f"Gaining {format_number(nf_gain)} Nebula Fragments.")
    g.celest_cnt += 1
    if ma.isinf(g.nebula_fragments) or ma.isinf(nf_gain): g.nebula_fragments = float('inf')
    elif ma.isfinite(g.nebula_fragments) and ma.isfinite(nf_gain): g.nebula_fragments += nf_gain
    if not ma.isinf(pts): pts = max(0, pts - g.celest_cst)
    try: g.celest_cst *= 1000 # Increase cost by 1000x
    except OverflowError: g.celest_cst = float('inf')
    reset_for_celestiality() # Full reset
    recalculate_derived_values()
    logging.info(f"Celestiality complete! Reached {g.celest_cnt}. Total NF: {format_number(g.nebula_fragments)}. Next Cost: {format_number(g.celest_cst)}")

# --- Clicking Action ---
def click_power_action():
    global clks, g
    if not g.cr4_unl: return
    relic_m = get_relic_effect('relic_clk_mult') # NF included
    asc_m = g.get_asc_clk_boost()
    chal_perm_m = g.chal_perm_clk_bst
    point_scale_m = g.clk_pt_scale
    base_clk = float('inf')
    if not any(ma.isinf(v) for v in [g.clk_pow, chal_perm_m, asc_m, point_scale_m, relic_m]):
        try: base_clk = g.clk_pow * chal_perm_m * asc_m * point_scale_m * relic_m
        except OverflowError: pass
    crit_m = g.clk_crit_m if random.random() < g.clk_crit_c else 1.0
    final_clk = float('inf')
    if not (ma.isinf(base_clk) or ma.isinf(crit_m)):
        try: final_clk = base_clk * crit_m
        except OverflowError: pass
    if g.asc_first and ma.isfinite(final_clk) and final_clk > 0:
        try:
            xp_gain = final_clk / 10.0
            if ma.isinf(g.asc_xp) or ma.isinf(xp_gain): g.asc_xp = float('inf')
            elif ma.isfinite(g.asc_xp) and ma.isfinite(xp_gain): g.asc_xp += xp_gain
            g.check_ascension_level_up(from_click=True)
        except OverflowError: g.asc_xp = float('inf'); logging.warning("Overflow calculating click XP gain.")
        except Exception as e: logging.error(f"Error calculating click XP: {e}")
    try:
        current_clks = clks if ma.isfinite(clks) else 0.0
        if ma.isinf(current_clks) or ma.isinf(final_clk): clks = float('inf')
        else: clks = min(float('inf'), current_clks + final_clk)
    except OverflowError: clks = float('inf')

# --- Autobuyer Logic ---
def buy_upgrade_max(upg_func, cost_attr, level_attr, max_attr):
    global pts
    bought_count = 0
    for _ in range(MAX_BUY_ITERATIONS):
        try:
             lvl = int(getattr(g, level_attr, 0))
             max_lvl_raw = getattr(g, max_attr, 0)
             max_lvl = float('inf') if ma.isinf(max_lvl_raw) else int(max_lvl_raw)
        except ValueError: break
        if lvl >= max_lvl: break
        cost = getattr(g, cost_attr, float('inf'))
        if pts < cost or ma.isinf(cost): break
        state_before = { 'pts': pts, 'lvl': lvl, 'cost': cost }
        upg_func()
        state_after = { 'pts': pts, 'lvl': getattr(g, level_attr, 0), 'cost': getattr(g, cost_attr, float('inf')) }
        if state_after['lvl'] > state_before['lvl'] or \
           state_after['cost'] != state_before['cost'] or \
           state_after['pts'] < state_before['pts']:
            bought_count += 1
        else: break

def autobuy_tick():
    global g
    try:
        max_buy_active = g.p20_lim_brk
        if g.cr3_unl:
            if max_buy_active:
                buy_upgrade_max(upgrade1, 'upg1_cst', 'upg1_lvl', 'upg1_max')
                buy_upgrade_max(upgrade2, 'upg2_cst', 'upg2_lvl', 'upg2_max')
                buy_upgrade_max(upgrade3, 'upg3_cst', 'upg3_lvl', 'upg3_max')
            else:
                if random.random() < 0.8: upgrade1()
                if random.random() < 0.6: upgrade2()
                if random.random() < 0.4: upgrade3()
        if g.p12_auto_u4:
            if max_buy_active:
                buy_upgrade_max(upgrade4, 'upg4_cst', 'upg4_lvl', 'upg4_max')
            else:
                if random.random() < 0.5: upgrade4()
    except Exception as e: logging.error(f"Error in autobuy_tick: {e}", exc_info=True)

def autobuy_thread_func():
    logging.info("Autobuyer started.")
    base_sleep = 0.1
    while is_running:
        p21_speed_f = 0.5 if g.pur_cnt >= 21 else 1.0
        sleep_t = base_sleep * p21_speed_f
        if g.cr3_unl or g.p12_auto_u4: autobuy_tick()
        time.sleep(sleep_t)
    logging.info("Autobuyer finished.")

def start_autobuy_thread_if_needed():
    global autobuy_thd, g
    if g.cr3_unl or g.p12_auto_u4:
        if not autobuy_thd or not autobuy_thd.is_alive():
            logging.info("Starting autobuy thread.")
            autobuy_thd = th.Thread(target=autobuy_thread_func, daemon=True)
            autobuy_thd.start()

# --- Relic Buying Function ---
def buy_relic(rid):
    global g; data = RELICS_DATA.get(rid)
    if not data: return
    lvl = g.relic_lvls.get(rid, 0); max_lvl = data.get('max_level', RELIC_MAX_LEVEL)
    try: lvl_int = int(lvl); max_lvl_int = int(max_lvl) if max_lvl is not None else float('inf')
    except ValueError: return
    if lvl_int >= max_lvl_int: return
    try: cst = round(data['cost_base'] * (data['cost_scale'] ** lvl_int))
    except OverflowError: cst = float('inf')
    if ma.isinf(cst): return
    p23_reduc = 0.95 if g.pur_cnt >= 23 else 1.0
    final_cst = round(cst * p23_reduc) if ma.isfinite(cst) else float('inf')
    can_afford = False
    if ma.isinf(g.sd) and ma.isfinite(final_cst): can_afford = True; final_cst = 0
    elif ma.isfinite(g.sd) and ma.isfinite(final_cst) and g.sd >= final_cst: can_afford = True
    if can_afford:
        if ma.isfinite(g.sd): g.sd -= final_cst
        g.relic_lvls[rid] = lvl_int + 1
        logging.info(f"Bought Relic '{data['name']}' (Lvl {lvl_int+1}) for {format_number(final_cst)} SD.")
        recalculate_derived_values()

# --- Challenge Management Functions ---
chal_btns = {}
def enter_challenge(cid):
    global g
    if g.active_chal or not g.asc_first: return
    chal_data = CHALLENGES.get(cid)
    if not chal_data: return
    cur_comp = g.chal_comps.get(cid, 0); max_comp = chal_data.get('mc')
    if max_comp is not None and cur_comp >= max_comp: return
    reset_lvl = chal_data.get('rl', 'asc').capitalize(); restr = chal_data.get('restr', 'N/A')
    msg = (f"Enter Challenge: {chal_data['db']}?\n\n"
           f"Reset Type: **{reset_lvl}**\nRestrictions: {restr}\n\nAre you sure?")
    if messagebox.askyesno("Enter Challenge?", msg):
        reset_for_challenge(cid); updateui()

def exit_challenge():
    global g
    if not g.active_chal: return
    exiting_chal = g.active_chal; g.active_chal = None
    reset_for_ascension(False); recalculate_derived_values()
    logging.info(f"Exited challenge {exiting_chal}."); updateui()

def complete_challenge(cid):
    global g
    if g.active_chal != cid: return
    chal_data = CHALLENGES.get(cid)
    if not chal_data: g.active_chal = None; recalculate_derived_values(); updateui(); return
    cur_comp = g.chal_comps.get(cid, 0); max_comp = chal_data.get('mc')
    if max_comp is not None and cur_comp >= max_comp:
        g.active_chal = None; reset_for_ascension(False); recalculate_derived_values(); updateui(); return
    new_comp_level = cur_comp + 1
    logging.info(f"Challenge Completed: {chal_data['db']} (Level {new_comp_level})")
    try:
        apply_func = chal_data.get('arf');
        if apply_func: apply_func(g)
        g.chal_comps[cid] = new_comp_level
        logging.info(f"Applied reward & incremented {cid} completions -> {g.chal_comps[cid]}")
    except Exception as e: logging.error(f"Reward/Increment error for {cid}: {e}", exc_info=True)
    g.active_chal = None; reset_for_ascension(False); recalculate_derived_values()
    messagebox.showinfo("Challenge Complete!", f"Completed:\n{chal_data['db']} (Level {new_comp_level})"); updateui()

def check_challenge_completion():
    global g
    if not g.active_chal: return
    cid = g.active_chal; chal_data = CHALLENGES.get(cid)
    if not chal_data: exit_challenge(); return
    lvl = g.chal_comps.get(cid, 0); max_lvl = chal_data.get('mc')
    if max_lvl is not None and lvl >= max_lvl: exit_challenge(); return
    try:
        req_func = chal_data['rf']; comp_func = chal_data['cf']
        requirement = req_func(g, lvl)
        if comp_func(g, requirement): complete_challenge(cid)
    except Exception as e: logging.error(f"Completion check error {cid}: {e}", exc_info=True)

# --- Save/Load ---
def save_game():
    global pts, clks, g; logging.info("Saving...")
    try:
        s_data = {k: getattr(g, k) for k in g.__dict__ if not k.startswith('_')}
        s_data.update({"v": SAVE_VERSION, "p": pts, "c": clks, "nf": g.nebula_fragments, "lst": time.time()})
        g.last_save_time = s_data["lst"]
        def convert_inf_nan(o):
            if isinstance(o, float):
                if ma.isinf(o): return "__Infinity__" if o > 0 else "__-Infinity__"
                elif ma.isnan(o): return "__NaN__"
            return o
        json_string = json.dumps(s_data, separators=(',', ':'), default=convert_inf_nan)
        encoded_string = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
        with open(SAVE_FILE, "w", encoding='utf-8') as f: f.write(encoded_string)
    except TypeError as e:
        logging.error(f"Save failed - Type Error: {e}. Data:", exc_info=True)
        for k, v in s_data.items():
            try: json.dumps({k: v}, default=convert_inf_nan)
            except TypeError: logging.error(f"Unserializable type in key '{k}': {type(v)}")
    except Exception as e: logging.error(f"Save failed: {e}", exc_info=True)

def autosave_thread_func():
    logging.info("Autosave started.")
    while is_running:
        time.sleep(AUTOSAVE_INTERVAL_S)
        if is_running: save_game()
    logging.info("Autosave finished.")

def load_game():
    global pts, clks, g, is_running
    if not os.path.exists(SAVE_FILE):
        logging.info("No save file found. Starting new game.");
        g=GameState(); pts,clks=0.0,0.0; recalculate_derived_values(); return
    logging.info(f"Loading game from {SAVE_FILE}...")
    try:
        with open(SAVE_FILE, "r", encoding='utf-8') as f: encoded_string = f.read()
        json_string = base64.b64decode(encoded_string.encode('utf-8')).decode('utf-8')
        def decode_inf_nan(dct):
            for k, v in dct.items():
                if isinstance(v, str):
                    if v == "__Infinity__": dct[k] = float('inf')
                    elif v == "__-Infinity__": dct[k] = float('-inf')
                    elif v == "__NaN__": dct[k] = float('nan')
            return dct
        loaded_data = json.loads(json_string, object_hook=decode_inf_nan)

        loaded_version = loaded_data.get("v", 0)
        if loaded_version != SAVE_VERSION:
            logging.warning(f"Save version mismatch ({loaded_version} vs {SAVE_VERSION}). New game.")
            # backup?
            g=GameState(); pts,clks=0.0,0.0; recalculate_derived_values(); save_game(); return

        pts = loaded_data.get("p", 0.0); clks = loaded_data.get("c", 0.0)
        g.nebula_fragments = loaded_data.get("nf", 0.0)
        if not isinstance(pts,(int,float)) or ma.isnan(pts) or (ma.isinf(pts) and pts < 0): pts=0.0
        if not isinstance(clks,(int,float)) or ma.isnan(clks) or (ma.isinf(clks) and clks < 0): clks=0.0
        if not isinstance(g.nebula_fragments,(int,float)) or ma.isnan(g.nebula_fragments) or (ma.isinf(g.nebula_fragments) and g.nebula_fragments < 0): g.nebula_fragments=0.0

        default_g = GameState()
        for key, default_value in default_g.__dict__.items():
            if key.startswith('_') or key == 'nebula_fragments': continue
            loaded_value = loaded_data.get(key)
            expected_type = type(default_value)
            final_value = default_value
            if loaded_value is not None:
                try:
                    if expected_type is float:
                         if isinstance(loaded_value, (int, float)): final_value = float(loaded_value)
                         else: raise TypeError("Expected float")
                    elif expected_type is int:
                         if isinstance(loaded_value, (int, float)) and ma.isfinite(loaded_value): final_value = int(loaded_value)
                         else: raise TypeError("Expected finite int/float")
                    elif expected_type is bool: final_value = bool(loaded_value)
                    elif expected_type is dict:
                         if isinstance(loaded_value, dict):
                             if key in ['relic_lvls', 'chal_comps']: final_value = {str(k): v for k, v in loaded_value.items()}
                             else: final_value = loaded_value
                         else: raise TypeError("Expected dict")
                    elif expected_type is str:
                         if isinstance(loaded_value, str): final_value = loaded_value
                         else: raise TypeError("Expected str")
                    elif isinstance(loaded_value, expected_type): final_value = loaded_value
                    else: logging.warning(f"Load type mismatch '{key}'. Exp {expected_type.__name__}, got {type(loaded_value).__name__}. Using default."); final_value = default_value
                    if isinstance(final_value, (int, float)):
                        if ma.isnan(final_value): final_value = default_value
                        elif ma.isinf(final_value) and final_value < 0 and not (isinstance(default_value, float) and ma.isinf(default_value)): final_value = default_value
                except (TypeError, ValueError, KeyError, AssertionError) as conv_e:
                     logging.warning(f"Load conversion error '{key}' (Val: {loaded_value!r}): {conv_e}. Using default."); final_value = default_value
            setattr(g, key, final_value)

        last_save_time = loaded_data.get("lst", time.time()); g.last_save_time = last_save_time
        offline_time_s = max(0, time.time() - last_save_time)
        if offline_time_s > 5 and not g.active_chal and ma.isfinite(pts) and ma.isfinite(clks):
            logging.info(f"Calculating offline progress for {offline_time_s:.1f} seconds...")
            recalculate_derived_values()
            offline_pps = pps * 0.5 if ma.isfinite(pps) else 0.0
            offline_cps = g.auto_cps * 0.5 if ma.isfinite(g.auto_cps) else 0.0
            offline_pts_gain = offline_pps * offline_time_s
            offline_clks_gain = offline_cps * offline_time_s
            try: pts = min(float('inf'), pts + offline_pts_gain)
            except OverflowError: pts = float('inf')
            try: clks = min(float('inf'), clks + offline_clks_gain)
            except OverflowError: clks = float('inf')
            logging.info(f"Offline Progress: Gained ~{format_number(offline_pts_gain)} P, ~{format_number(offline_clks_gain)} C.")
        elif offline_time_s > 5: logging.info(f"Skipping offline progress (In chal/non-finite). Offline time: {offline_time_s:.1f}s")

        recalculate_derived_values()
        g.check_celestiality_unlock()
        g.last_save_time = time.time()
        logging.info("Load successful.")

    except FileNotFoundError: logging.error(f"Load fail: {SAVE_FILE} disappeared."); g=GameState(); pts,clks=0.0,0.0; recalculate_derived_values(); save_game()
    except (json.JSONDecodeError, base64.binascii.Error) as decode_e: logging.error(f"Load fail: Corrupt save - {decode_e}. New game."); g=GameState(); pts,clks=0.0,0.0; recalculate_derived_values(); save_game()
    except Exception as e: logging.error(f"Load failed: Unexpected error - {e}", exc_info=True); g=GameState(); pts,clks=0.0,0.0; recalculate_derived_values(); save_game()

# --- UI Update Function ---
ptslbl, ppslbl, clkslbl, sdlbl, asclvllbl, ascproglbl = (None,) * 6
upg1cstlbl, upg1explbl, btn1, upg2cstlbl, upg2explbl, btn2 = (None,) * 6
upg3cstlbl, upg3explbl, btn3, upg4cstlbl, upg4explbl, btn4 = (None,) * 6
upg5cstlbl, upg5explbl, btn5, upg6cstlbl, upg6explbl, btn6 = (None,) * 6
upg7cstlbl, upg7explbl, btn7, upg8cstlbl, upg8explbl, btn8 = (None,) * 6
purlbl, purbtn, crylbl, crybtn, asclbl, ascbtn, clkbtn = (None,) * 7
nf_lbl, celestlbl, celestbtn = None, None, None
chal_wdgs, relic_wdgs = {}, {}; exitchalbtn, relic_title_lbl = None, None
stats_text = None
help_text, help_buttons = None, {}
notebook_ref = None # Reference to the main notebook widget
tab_frames = {} # Map tab name/index to frame widget and unlock check function

def update_button_style(btn, state):
    if not btn or not isinstance(btn, ttk.Button): return
    try:
        style = "primary-outline"; tk_state = tk.NORMAL
        if state == "maxed": style = "secondary-outline"; tk_state = tk.DISABLED
        elif state == "buyable": style = "success"
        elif state == "locked": style = "secondary-outline"; tk_state = tk.DISABLED
        elif state == "disabled": style = "secondary-outline"; tk_state = tk.DISABLED
        elif state == "active": style = "warning"; tk_state = tk.DISABLED
        elif state == "info": style = "info"; # Used for active help button
        btn.configure(bootstyle=style, state=tk_state)
    except tk.TclError: pass
    except Exception as e: logging.error(f"Button style error: {e}")

def updateui():
    global pts, clks, pps, g, window, is_running, notebook_ref, tab_frames
    try:
        if not is_running or not window.winfo_exists(): return
        fmt_max = lambda v: 'Inf' if ma.isinf(v) else int(v)

        # --- Update Tab Visibility/Names ---
        if notebook_ref and tab_frames:
            for i, tab_id in enumerate(notebook_ref.tabs()):
                tab_info = tab_frames.get(i)
                if tab_info:
                    frame_widget, unlock_func, base_name = tab_info
                    is_unlocked = unlock_func() if unlock_func else True
                    tab_text = base_name if is_unlocked else obfuscate(base_name)
                    try: notebook_ref.tab(tab_id, text=tab_text)
                    except tk.TclError: pass # Ignore if tab doesn't exist

        # --- Prestige Tab ---
        if purlbl and purbtn:
            max_p = g.pur_max; next_l = g.pur_cnt + 1; can, reason = False, "Max Level"
            cst = g.pur_cst / g.p24_pur_cst_div; status = "default"
            if g.pur_cnt < max_p:
                if next_l <= 10: can=True
                elif next_l <= 15: can=g.upg5_comp; reason="Req Upg5"
                else: can=g.cr5_comp; reason="Req C5"
                if can and pts < cst: can, reason = False, "Need Points"
                elif can: reason = ""
                idx=g.pur_cnt; desc=PURIFY_DESCRIPTIONS[idx] if idx<len(PURIFY_DESCRIPTIONS) else f"P{next_l} Effect"
                if not can and reason not in ["Max Level", ""]: desc=f"({reason}) {desc}"
                purlbl.configure(text=f"Purify ({g.pur_cnt}/{int(max_p)}): {desc}\nCost: {format_number(cst)} Points")
                status = "buyable" if can else "default"
            else: purlbl.configure(text=f"Purify ({g.pur_cnt}/{int(max_p)}): Max Level Reached"); status = "maxed"
            update_button_style(purbtn, status)
        if crylbl and crybtn:
            max_c = g.cryst_max; next_l = g.cryst_cnt + 1; can, reason = False, "Locked"
            cst=g.cryst_cst; status = "locked"
            if g.cryst_unl:
                reason = "Max Level"; status = "default"
                if g.cryst_cnt < max_c:
                    if next_l == 5 and g.pur_cnt < 15: reason = "Req P15"
                    else:
                         can = True
                         if pts < cst: can, reason = False, "Need Points"
                         else: reason = ""
                    idx=g.cryst_cnt; desc=CRYSTALLINE_DESCRIPTIONS[idx] if idx<len(CRYSTALLINE_DESCRIPTIONS) else f"C{next_l} Effect"
                    if not can and reason not in ["Max Level", ""]: desc=f"({reason}) {desc}"
                    crylbl.configure(text=f"Crystalline ({g.cryst_cnt}/{int(max_c)}): {desc}\nCost: {format_number(cst)} Points")
                    status = "buyable" if can else "default"
                else: crylbl.configure(text=f"Crystalline ({g.cryst_cnt}/{int(max_c)}): Max Level Reached"); status = "maxed"
            else: crylbl.configure(text="Crystalline: Locked (Requires P10)")
            update_button_style(crybtn, status)

        # --- Upgrades Tab ---
        if ptslbl: ptslbl.configure(text=f"Points: {format_number(pts)}")
        if ppslbl: ppslbl.configure(text=f"PPS: {format_number(pps)}")
        c1=g.upg1_cst; max1=g.upg1_max; lvl1=g.upg1_lvl
        can1=pts>=c1 and int(lvl1)<int(max1) and not ma.isinf(c1)
        if upg1cstlbl: upg1cstlbl.configure(text=f"Cost: {format_number(c1)}")
        if upg1explbl: upg1explbl.configure(text=f"+{(1.0+get_relic_effect('relic_u1_str',0.0)):.2f} Base Mult [{int(lvl1)}/{fmt_max(max1)}]")
        if btn1: update_button_style(btn1, "maxed" if int(lvl1)>=int(max1) else ("buyable" if can1 else "default"))
        c2=g.upg2_cst; max2=g.upg2_max; lvl2=g.upg2_lvl
        chal1_active=(g.active_chal=='c1'); can2=pts>=c2 and int(lvl2)<int(max2) and not chal1_active and not ma.isinf(c2)
        if upg2cstlbl: upg2cstlbl.configure(text=f"Cost: {format_number(c2)}")
        if upg2explbl: f=get_upgrade2_factor(); upg2explbl.configure(text=f"Mult Strength x{format_number(g.mult_str)} [{int(lvl2)}/{fmt_max(max2)}] (Base x{f:.2f})")
        if btn2: s="disabled" if chal1_active else ("maxed" if int(lvl2)>=int(max2) else ("buyable" if can2 else "default")); update_button_style(btn2,s)
        c3=g.upg3_cst; max3=g.upg3_max; lvl3=g.upg3_lvl
        chal2_active=(g.active_chal=='c2'); can3=pts>=c3 and int(lvl3)<int(max3) and not chal2_active and not ma.isinf(c3)
        if upg3cstlbl: upg3cstlbl.configure(text=f"Cost: {format_number(c3)}")
        if upg3explbl: upg3explbl.configure(text=f"PPS Exponent ^{g.pps_exp:.3f} [{int(lvl3)}/{fmt_max(max3)}]") # Removed NF display here for space
        if btn3: s="disabled" if chal2_active else ("maxed" if int(lvl3)>=int(max3) else ("buyable" if can3 else "default")); update_button_style(btn3,s)
        c4=g.upg4_cst; max4=g.upg4_max; lvl4=g.upg4_lvl
        lock4=not g.cr1_u4_unl; can4=pts>=c4 and int(lvl4)<int(max4) and not lock4 and not ma.isinf(c4)
        if upg4cstlbl: upg4cstlbl.configure(text="Locked (Requires C1)" if lock4 else f"Cost: {format_number(c4)}")
        if upg4explbl: upg4explbl.configure(text="???" if lock4 else f"+1 Max Upg3 [{int(lvl4)}/{fmt_max(max4)}]")
        if btn4: s="locked" if lock4 else ("maxed" if int(lvl4)>=int(max4) else ("buyable" if can4 else "default")); update_button_style(btn4,s)

        # --- Clicking Tab ---
        if clkslbl: clkslbl.configure(text=f"Clicks: {format_number(clks)}")
        lock_click_mech = not g.cr4_unl
        if clkbtn:
            clk_val_str = "???"; crit_str = ""; btn_state = tk.DISABLED
            if not lock_click_mech:
                btn_state = tk.NORMAL
                relic_m=get_relic_effect('relic_clk_mult'); asc_m=g.get_asc_clk_boost()
                chal_p_m = g.chal_perm_clk_bst; scale_m = g.clk_pt_scale; click_val = 0.0
                if any(ma.isinf(v) for v in [g.clk_pow, chal_p_m, asc_m, scale_m, relic_m]): click_val = float('inf')
                else:
                    try: click_val = g.clk_pow * chal_p_m * asc_m * scale_m * relic_m
                    except OverflowError: click_val = float('inf')
                clk_val_str = format_number(click_val)
                crit_chance = min(1.0, (0.05 * g.upg7_lvl) + get_relic_effect('relic_crit_c', 0.0))
                crit_mult = 2.0 + (0.2 * g.upg7_lvl)
                if crit_chance > 0: crit_str = f" ({crit_chance*100:.1f}% Crit, x{crit_mult:.1f})"
            clkbtn.configure(text=f"Click! (+{clk_val_str}{crit_str})" if not lock_click_mech else "Locked (Requires C4)", state=btn_state)
        lock_click_upgs = not g.cr4_unl
        r5=10.0; c5_str=f"Cost:{format_number(r5)} Clicks"; e5_str="Unlock P11-15"; s5="locked"
        if not lock_click_upgs:
            if g.upg5_comp: s5, c5_str, e5_str = "maxed", "Purchased", "Max Purify -> 15"
            else: s5 = "buyable" if clks>=r5 else "default"
        else: c5_str, e5_str = "Locked(C4)", "???"
        if upg5cstlbl: upg5cstlbl.configure(text=c5_str)
        if upg5explbl: upg5explbl.configure(text=e5_str)
        if btn5: update_button_style(btn5, s5)
        r6=1000.0; c6_str=f"Cost:{format_number(r6)} Clicks"; e6_str="Enable C5 Effects"; s6="locked"
        if not lock_click_upgs:
            if g.upg6_comp: s6, c6_str, e6_str = "maxed", "Purchased", "Playtime Boost Active"
            else: s6 = "buyable" if clks>=r6 else "default"
        else: c6_str, e6_str = "Locked(C4)", "???"
        if upg6cstlbl: upg6cstlbl.configure(text=c6_str)
        if upg6explbl: upg6explbl.configure(text=e6_str)
        if btn6: update_button_style(btn6, s6)
        c7=g.upg7_cst; max7=g.upg7_max; lvl7=g.upg7_lvl
        ct7_str=f"Cost:{format_number(c7)} Clicks"; e7_str=f"Crit Chance/Mult [{int(lvl7)}/{fmt_max(max7)}]"; s7="locked"
        if not lock_click_upgs:
            crit_chance = min(1.0,(0.05*lvl7)+get_relic_effect('relic_crit_c',0.0))
            crit_mult = 2.0+(0.2*lvl7)
            if int(lvl7)>=int(max7): s7, ct7_str, e7_str = "maxed", "MAXED", f"Crit: {crit_chance*100:.1f}% x{crit_mult:.1f}"
            else: s7="buyable" if clks>=c7 and not ma.isinf(c7) else "default"
        else: ct7_str, e7_str = "Locked(C4)", "???"
        if upg7cstlbl: upg7cstlbl.configure(text=ct7_str)
        if upg7explbl: upg7explbl.configure(text=e7_str)
        if btn7: update_button_style(btn7, s7)
        c8=g.upg8_cst; max8=g.upg8_max; lvl8=g.upg8_lvl
        ct8_str=f"Cost:{format_number(c8)} Clicks"; e8_str=f"Auto Click CPS [{int(lvl8)}/{fmt_max(max8)}]"; s8="locked"
        if not lock_click_upgs:
            auto_cps_str = format_number(g.auto_cps)
            if int(lvl8)>=int(max8): s8, ct8_str, e8_str = "maxed", "MAXED", f"Auto Click: {auto_cps_str}/s"
            else: s8="buyable" if clks>=c8 and not ma.isinf(c8) else "default"
        else: ct8_str, e8_str = "Locked(C4)", "???"
        if upg8cstlbl: upg8cstlbl.configure(text=ct8_str)
        if upg8explbl: upg8explbl.configure(text=e8_str)
        if btn8: update_button_style(btn8, s8)

        # --- Ascension Tab ---
        if sdlbl: sdlbl.configure(text=f"Stardust: {format_number(g.sd)}")
        if asclvllbl: asclvllbl.configure(text=f"Ascension Level: {int(g.asc_lvl)}")
        if ascproglbl:
            current_xp = g.asc_xp; needed_xp = g.get_xp_for_level(int(g.asc_lvl) + 1); prog_perc = 0.0
            if needed_xp > 0 and not ma.isinf(needed_xp):
                if ma.isinf(current_xp): prog_perc = 100.0
                elif ma.isfinite(current_xp): prog_perc = min(100.0, (current_xp / needed_xp * 100.0))
            ascproglbl.configure(text=f"Ascension XP: {format_number(current_xp)} / {format_number(needed_xp)} ({prog_perc:.1f}%)")
        if asclbl and ascbtn:
            can_asc, reason = False, "Locked"; status = "locked"; sd_preview = 0; cst = g.asc_cst
            if g.asc_unl:
                reason = ""; status = "default"
                if g.active_chal: reason = f"In Challenge {g.active_chal}"; status = "disabled"
                elif pts < cst: reason = "Need Points"
                else:
                    try:
                        if pts >= cst and ma.isfinite(pts) and pts > 0:
                             log_a=ma.log10(max(1, pts/max(1,cst))); base_sd=1+0.5*log_a
                             c_m=ma.sqrt(g.cryst_cnt+1); r_b=get_relic_effect('relic_sd_gain'); c_b=g.chal_sd_bst
                             p22=1.1 if g.pur_cnt>=22 else 1.0; nf_b = g.get_nf_stardust_boost()
                             all_b = c_m*r_b*c_b*p22*nf_b
                             if ma.isinf(all_b) or ma.isinf(base_sd): sd_preview = float('inf')
                             else: sd_preview = ma.floor(base_sd * all_b); sd_preview=max(0,sd_preview)
                             if sd_preview > 0: can_asc = True; status = "buyable"
                             else: reason = "Need More Points for SD"
                    except Exception as e: logging.error(f"SD preview calc error: {e}"); reason = "Preview Error"
            desc = f"Reset Crystalline, Purify, Points, Clicks, etc.\nGain ~{format_number(sd_preview)} Stardust & Ascension XP.\nCost: {format_number(cst)} Points"
            if not can_asc and reason: desc = f"({reason}) {desc}"
            asclbl.configure(text=f"Ascend ({g.asc_cnt}): {desc}")
            update_button_style(ascbtn,status)

        # --- Relics Tab ---
        show_relics = g.asc_first
        if relic_f and relic_f.winfo_exists(): # Check frame exists
            if show_relics:
                 # Make sure the frame itself is visible if needed
                 # This assumes relic_f is directly added to the notebook
                 # If it's inside another container, adjust accordingly
                 # if not relic_f.winfo_ismapped(): relic_f.grid() # Or pack() depending on layout

                 if relic_title_lbl and not relic_title_lbl.winfo_ismapped(): relic_title_lbl.grid()
                 for rid, data in RELICS_DATA.items():
                     wdgs = relic_wdgs.get(rid)
                     if not wdgs: continue
                     nl, dl, ll, cl, bb = wdgs
                     for w in wdgs:
                         if w and w.winfo_exists() and not w.winfo_ismapped(): w.grid() # Show widgets if hidden

                     lvl = g.relic_lvls.get(rid, 0); max_l = data.get('max_level', RELIC_MAX_LEVEL)
                     is_max = (max_l is not None and int(lvl) >= int(max_l))
                     eff_power = get_relic_effect(rid, '?'); eff_power_str = format_number(eff_power) if eff_power != '?' else '?'
                     dl.configure(text=f"{data['desc']} (Eff: {eff_power_str})")
                     ll.configure(text=f"Level: {int(lvl)}" + (f"/{int(max_l)}" if max_l is not None else f"/{int(RELIC_MAX_LEVEL)}"))
                     if is_max: cl.configure(text="Cost: MAX"); update_button_style(bb, "maxed")
                     else:
                         try: base_cost=round(data['cost_base']*(data['cost_scale']**lvl))
                         except OverflowError: base_cost = float('inf')
                         p23_reduc=0.95 if g.pur_cnt>=23 else 1.0
                         final_cost = round(base_cost * p23_reduc) if ma.isfinite(base_cost) else float('inf')
                         cost_str = f"Cost: {format_number(final_cost)} SD"
                         if p23_reduc < 1.0 and ma.isfinite(final_cost): cost_str += " (P23)"
                         elif ma.isinf(final_cost): cost_str = "Cost: ---"
                         cl.configure(text=cost_str)
                         can_afford = ma.isinf(g.sd) or (ma.isfinite(final_cost) and g.sd >= final_cost)
                         update_button_style(bb, "buyable" if can_afford else "default")
            else: # Hide relics
                 if relic_title_lbl and relic_title_lbl.winfo_ismapped(): relic_title_lbl.grid_remove()
                 for rid in RELICS_DATA:
                     if rid in relic_wdgs:
                         for w in relic_wdgs[rid]:
                             if w and w.winfo_exists() and w.winfo_ismapped(): w.grid_remove()

        # --- Challenges Tab ---
        show_chals = g.asc_first
        # Use the frame defined during setup (chal_frame)
        if chal_frame and chal_frame.winfo_exists():
            if show_chals:
                 if not chal_frame.winfo_ismapped(): chal_frame.grid() # Show challenges frame
                 if exitchalbtn:
                     if g.active_chal:
                         if not exitchalbtn.winfo_ismapped(): exitchalbtn.grid()
                         exitchalbtn.configure(text=f"Exit Challenge '{g.active_chal}'")
                     else: exitchalbtn.grid_remove()
                 for cid, wdgs in chal_wdgs.items():
                     chal_data = CHALLENGES.get(cid);
                     if not chal_data: continue
                     lbl, btn = wdgs
                     if not lbl.winfo_exists() or not btn.winfo_exists(): continue
                     lvl = g.chal_comps.get(cid, 0); max_l = chal_data.get('mc')
                     is_max = (max_l is not None and int(lvl) >= int(max_l)); is_active = (g.active_chal == cid)
                     can_enter = (g.active_chal is None and not is_max)
                     db = chal_data['db']; rd_str = "???"; rwd_str = "???"; rst_str = chal_data.get('restr', '???')
                     try: req_val = chal_data['rf'](g, lvl); rd_str = chal_data['rd'](req_val)
                     except Exception as e: rd_str = f"ReqErr:{e}"
                     try: rwd_lvl = lvl if is_max else lvl + 1; rwd_str = chal_data['rwd'](g, rwd_lvl)
                     except Exception as e: rwd_str = f"RewErr:{e}"
                     comp_s = f" (Comps: {int(lvl)}/{int(max_l)})" if max_l is not None else f" (Comps: {int(lvl)})"
                     stat_s = " [ACTIVE]" if is_active else (" [MAXED]" if is_max else "")
                     lbl_t = f"{db}{comp_s}{stat_s}\n"
                     if is_active:
                          try:
                              req = chal_data['rf'](g, lvl); prog = "..."
                              if 'Points' in rd_str: prog = f"{format_number(pts)} / {format_number(req)}"
                              elif 'Clicks' in rd_str: prog = f"{format_number(clks)} / {format_number(req)}"
                              elif 'Cryst' in rd_str: prog = f"{g.cryst_cnt} / {req}"
                              lbl_t += f"Progress: {prog}\n"
                          except Exception as e: lbl_t += f"ProgErr:{e}\n"
                     else: lbl_t += f"Next Req: {rd_str}\n"
                     lbl_t += f"Reward: {rwd_str}\nRestrictions: {rst_str}"; lbl.configure(text=lbl_t)
                     if is_active:
                         if btn.winfo_ismapped(): btn.grid_remove()
                     else:
                         if not btn.winfo_ismapped(): btn.grid()
                         btn.configure(text=f"Enter C{cid[1:]}")
                         status = "maxed" if is_max else ("primary" if can_enter else "locked")
                         update_button_style(btn, status)
            else: # Hide challenges
                 if chal_frame.winfo_ismapped(): chal_frame.grid_remove()

        # --- Celestiality Tab ---
        show_celest = g.celest_unl
        if celest_f and celest_f.winfo_exists():
             # Check g.celest_unl before showing elements
             if nf_lbl:
                 nf_lbl.configure(text=f"Nebula Fragments: {format_number(g.nebula_fragments)}")
                 nf_lbl.grid() if show_celest else nf_lbl.grid_remove()
             if celestlbl:
                 # (Label text generation logic from previous step)
                 can_cel, reason = False, "Locked"; status = "locked"; cst = g.celest_cst
                 req_met = (int(g.asc_lvl) >= CELESTIALITY_REQ_ASC_LVL and int(g.cryst_cnt) >= CELESTIALITY_REQ_CRYST and int(g.pur_cnt) >= CELESTIALITY_REQ_PUR)
                 if g.celest_unl:
                     reason = ""; status = "default"
                     if not req_met: reason = f"Req: Asc{CELESTIALITY_REQ_ASC_LVL}, C{CELESTIALITY_REQ_CRYST}, P{CELESTIALITY_REQ_PUR}"; status = "locked"
                     elif g.active_chal: reason = f"In Challenge {g.active_chal}"; status = "disabled"
                     elif pts < cst: reason = "Need Points"
                     else: can_cel = True; status = "buyable"
                 elif req_met: g.celest_unl = True; reason = ""; status = "default"
                 if pts < cst: reason = "Need Points"
                 else: can_cel = True; status = "buyable"
                 nf_pt_boost = g.get_nf_point_boost(); nf_sd_boost = g.get_nf_stardust_boost(); nf_relic_boost = g.get_nf_relic_boost(); nf_gain_preview = 0.0
                 if can_cel:
                      try:
                          point_factor = ma.log10(max(1.0, pts / NEBULA_FRAG_BASE_REQ_PTS)) if ma.isfinite(pts) and pts > 0 else 0.0
                          sd_factor = ma.log10(max(1.0, g.sd / NEBULA_FRAG_BASE_REQ_SD)) if ma.isfinite(g.sd) and g.sd > 0 else 0.0
                          asc_factor = ma.sqrt(max(0, g.asc_lvl / NEBULA_FRAG_BASE_REQ_ASC)) if ma.isfinite(g.asc_lvl) and g.asc_lvl > 0 else 0.0
                          base_gain = max(0.0, point_factor) + max(0.0, sd_factor) + max(0.0, asc_factor); nf_gain_preview = ma.floor(base_gain * 1.0); nf_gain_preview = max(0.0, nf_gain_preview)
                      except: nf_gain_preview = 0.0
                 desc = (f"Perform a FULL reset (Points...SD, Relics, Chals).\n"
                         f"Current Boosts: Pts x{format_number(nf_pt_boost)}, SD x{format_number(nf_sd_boost)}, Relics x{format_number(nf_relic_boost)}\n"
                         f"Gain ~{format_number(nf_gain_preview)} Nebula Fragments on reset.\n"
                         f"Cost: {format_number(cst)} Points")
                 if not can_cel and reason: desc = f"({reason}) {desc}"
                 celestlbl.configure(text=f"Celestiality ({g.celest_cnt}): {desc}")
                 celestlbl.grid() if show_celest else celestlbl.grid_remove()
             if celestbtn:
                 update_button_style(celestbtn, status if show_celest else "locked")
                 celestbtn.grid() if show_celest else celestbtn.grid_remove()

        # --- Statistics Tab ---
        # Stats tab should always be visible, just update content
        if stats_text and stats_text.winfo_exists():
            stats_content = "--- Game State ---\n"
            stats_content += f"Playtime: {dt.timedelta(seconds=int(g.playtime))}\n"
            stats_content += f"Points (p): {format_number(pts)}\n"
            stats_content += f"PPS (pps): {format_number(pps)}\n"
            stats_content += f"Clicks (c): {format_number(clks)}\n"
            stats_content += f"Auto CPS (auto_cps): {format_number(g.auto_cps)}\n"
            stats_content += f"Click Power Base (clk_pow): {format_number(g.clk_pow)}\n"
            stats_content += f"Click Point Scale (clk_pt_scale): {format_number(g.clk_pt_scale)}\n"
            stats_content += f"Click Crit Chance (clk_crit_c): {g.clk_crit_c*100:.1f}%\n"
            stats_content += f"Click Crit Multi (clk_crit_m): x{format_number(g.clk_crit_m)}\n"
            stats_content += "\n--- Prestige ---\n"
            stats_content += f"Purify Count (pur_cnt): {int(g.pur_cnt)} / {int(g.pur_max)}\n"
            stats_content += f"Purify Cost (pur_cst): {format_number(g.pur_cst / g.p24_pur_cst_div)}\n"
            stats_content += f"Crystalline Count (cryst_cnt): {int(g.cryst_cnt)} / {int(g.cryst_max)}\n"
            stats_content += f"Crystalline Cost (cryst_cst): {format_number(g.cryst_cst)}\n"
            stats_content += f"Ascension Count (asc_cnt): {int(g.asc_cnt)}\n"
            stats_content += f"Ascension Cost (asc_cst): {format_number(g.asc_cst)}\n"
            stats_content += f"Stardust (sd): {format_number(g.sd)}\n"
            stats_content += f"Ascension Level (asc_lvl): {int(g.asc_lvl)}\n"
            current_xp = g.asc_xp; needed_xp = g.get_xp_for_level(int(g.asc_lvl) + 1)
            stats_content += f"Ascension XP (asc_xp): {format_number(current_xp)} / {format_number(needed_xp)}\n"
            stats_content += f"Celestiality Count (celest_cnt): {int(g.celest_cnt)}\n"
            stats_content += f"Nebula Fragments (nebula_fragments): {format_number(g.nebula_fragments)}\n"
            stats_content += f"Celestiality Cost (celest_cst): {format_number(g.celest_cst)}\n"
            stats_content += "\n--- Core Modifiers ---\n"
            stats_content += f"Base Multiplier (mult): x{format_number(g.mult)}\n"
            stats_content += f"Multiplier Strength (mult_str): x{format_number(g.mult_str)}\n"
            stats_content += f"PPS Exponent (pps_exp): ^{format_number(g.pps_exp)}\n"
            stats_content += f"PPS Point Scale Exp (pps_pt_scale_exp): ^{format_number(g.pps_pt_scale_exp)}\n"
            stats_content += "\n--- Upgrade Levels & Costs ---\n"
            stats_content += f"Upg1: {int(g.upg1_lvl)}/{fmt_max(g.upg1_max)} | Cost: {format_number(g.upg1_cst)}\n"
            stats_content += f"Upg2: {int(g.upg2_lvl)}/{fmt_max(g.upg2_max)} | Cost: {format_number(g.upg2_cst)}\n"
            stats_content += f"Upg3: {int(g.upg3_lvl)}/{fmt_max(g.upg3_max)} | Cost: {format_number(g.upg3_cst)}\n"
            stats_content += f"Upg4: {int(g.upg4_lvl)}/{fmt_max(g.upg4_max)} | Cost: {format_number(g.upg4_cst)}\n"
            stats_content += f"Upg5 (P11-15): {'Yes' if g.upg5_comp else 'No'} | Cost: {format_number(10.0)} C\n"
            stats_content += f"Upg6 (C5 Boost): {'Yes' if g.upg6_comp else 'No'} | Cost: {format_number(1000.0)} C\n"
            stats_content += f"Upg7 (Crit): {int(g.upg7_lvl)}/{fmt_max(g.upg7_max)} | Cost: {format_number(g.upg7_cst)} C\n"
            stats_content += f"Upg8 (Auto): {int(g.upg8_lvl)}/{fmt_max(g.upg8_max)} | Cost: {format_number(g.upg8_cst)} C\n"
            stats_content += "\n--- Relics ---\n"
            if not g.relic_lvls: stats_content += "(None)\n"
            else:
                for rid, data in RELICS_DATA.items():
                    lvl = g.relic_lvls.get(rid, 0)
                    if lvl > 0: stats_content += f"{data['name']} (Lvl {int(lvl)})\n"
            stats_content += "\n--- Challenges ---\n"
            if not g.chal_comps: stats_content += "(None Completed)\n"
            else:
                for cid, data in CHALLENGES.items():
                    comps = g.chal_comps.get(cid, 0)
                    if comps > 0: stats_content += f"{data['db']} (Comps: {int(comps)})\n"
            stats_content += "\n--- Internal Flags ---\n"
            stats_content += f"Crystalline Unl (cryst_unl): {g.cryst_unl}\n"
            stats_content += f"Ascension Unl (asc_unl): {g.asc_unl}\n"
            stats_content += f"First Ascension (asc_first): {g.asc_first}\n"
            stats_content += f"Celestiality Unl (celest_unl): {g.celest_unl}\n"
            stats_content += f"Limit Break (p20_lim_brk): {g.p20_lim_brk}\n"
            stats_content += f"Active Challenge (active_chal): {g.active_chal}\n"

            try:
                 current_state = stats_text.state
                 stats_text.state = tk.NORMAL
                 stats_text.delete('1.0', tk.END)
                 stats_text.insert('1.0', stats_content)
                 stats_text.state = tk.DISABLED
            except tk.TclError: pass # Ignore errors if widget is destroyed

        # --- Help Tab ---
        # Help tab should always be visible, update button states/text
        if help_buttons and help_text:
            for topic, button in help_buttons.items():
                if not button.winfo_exists(): continue
                unlocked = False
                if topic == 'points': unlocked = True
                elif topic == 'purify': unlocked = g.pur_cnt > 0 or g.cryst_unl
                elif topic == 'crystalline': unlocked = g.cryst_cnt > 0 or g.asc_unl
                elif topic == 'clicking': unlocked = g.cr4_unl
                elif topic == 'ascension': unlocked = g.asc_first
                elif topic == 'relics': unlocked = g.asc_first
                elif topic == 'challenges': unlocked = g.asc_first
                elif topic == 'celestiality': unlocked = g.celest_unl

                btn_text = topic.replace('_', ' ').title()
                button.configure(text=btn_text if unlocked else obfuscate(btn_text))

                if _active_help_topic == topic:
                     # Keep active style if unlocked, otherwise force locked style
                     update_button_style(button, "info" if unlocked else "locked")
                else:
                     # Set normal or locked style
                     update_button_style(button, "primary" if unlocked else "locked")

        # Schedule next update
        if is_running: window.after(UPDATE_INTERVAL_MS, updateui)

    except tk.TclError as e: is_running = False # Stop if UI fails critically
    except Exception as e:
        logging.error(f"UI update error: {e}", exc_info=True)
        if is_running: window.after(UPDATE_INTERVAL_MS * 5, updateui) # Retry after delay

# --- Admin Panel ---
admin_window = None; admin_wdgs = {}; active_admin_thds = []
def log_admin_ts(m):
    if admin_wdgs.get('cmd_output') and window and is_running:
        try: window.after(0, lambda msg=m: log_admin(msg))
        except: pass
def _exec_cmd(cmd_str, log_out=True):
    if not cmd_str or not is_running: return None
    parts=cmd_str.split(); cmd=parts[0].lower(); args=parts[1:]; res=None; h=COMMAND_HANDLERS.get(cmd)
    if h:
        try: res = h['func'](args)
        except Exception as e: res=f"Exec Error '{cmd}': {e}"; logging.error(f"Admin err '{cmd}': {e}", exc_info=True)
    else: res = f"Unknown cmd: '{cmd}'. Type 'help'."
    bg=[cmd_wait,cmd_repeat,cmd_while]; log=log_out and res and (h is None or h['func'] not in bg)
    if log: log_admin_ts(str(res)); return res
def _eval_cond(cond_s):
    try:
        parts = cond_s.split(maxsplit=2);
        if len(parts) != 3: raise ValueError("Condition must be 'variable operator value'")
        var, op, val_s = parts; var = var.lower(); cur=None
        if var in ['pts','clks','pps']: cur = globals().get(var)
        elif hasattr(g, var): cur = getattr(g, var)
        else: raise NameError(f"Variable '{var}' not found")
        if cur is None: raise ValueError(f"Variable '{var}' has value None.")
        typ=type(cur); cmp=None
        try:
            if typ is bool: cmp=val_s.lower() in ['true','1','t','y','yes']
            elif typ is int: cmp=int(float(val_s))
            elif typ is float: cmp=float(val_s)
            elif typ is str: cmp=val_s
            elif cur is None and val_s.lower() == 'none': cmp=None
            else: raise TypeError(f"Unsupported type {typ}")
        except ValueError: raise TypeError(f"Cannot convert '{val_s}' to {typ}")
        if op=='==' or op == 'is': return cur==cmp;
        elif op=='!=' or op == 'is not': return cur!=cmp
        if isinstance(cur,(int,float)) and isinstance(cmp,(int,float)):
            if op=='>': return cur>cmp
            elif op=='<': return cur<cmp
            elif op=='>=': return cur>=cmp
            elif op=='<=': return cur<=cmp
        raise ValueError(f"Unsupported op '{op}' for type {typ}")
    except Exception as e: log_admin_ts(f"Condition Error: {e}"); return False
def cmd_setvalue(args):
    global pts, clks, g
    if len(args)!=2: return "Usage: set <var> <val>"
    var,val_s=args[0].lower(),args[1]; tgt=None; is_global=False; current_val=None; old_val=None
    if var in ['pts','clks','pps','is_running']: tgt=globals(); is_global=True; current_val=tgt.get(var)
    elif hasattr(g, var): tgt=g; current_val=getattr(g, var)
    else: return f"Error: Variable '{var}' not found."
    old_val = current_val; target_type = type(current_val) if current_val is not None else None; new_value = None
    try:
        if target_type is bool or var in ['asc_first','p20_lim_brk','upg5_comp','upg6_comp','cryst_unl','asc_unl', 'celest_unl', 'r2_unl','r3_unl','r6_unl','cr1_u4_unl','cr3_unl','cr4_unl','cr5_comp','p12_auto_u4']: new_value = val_s.lower() in ['true','1','t','y','yes']; target_type = bool
        elif target_type is int or var in ['asc_lvl','asc_cnt','pur_cnt','cryst_cnt', 'celest_cnt', 'upg1_lvl','upg2_lvl','upg3_lvl','upg4_lvl','upg7_lvl','upg8_lvl']: f_val = float(val_s); new_value = int(f_val); target_type = int
        elif target_type is float or var in ['upg1_max','upg2_max','upg3_max','upg4_max','upg7_max','upg8_max', 'asc_xp','sd','pps_exp','clk_pow','mult','mult_str','r1_bst','r3_cst_m','r4_u2_bst','r5_u3_bst','r6_bst','cr1_bst','cr2_bst','cryst_comp_bst','p11_pps_bst','p14_u2_bst','p16_cst_reduc','p17_u1_bst','p18_pass_clk','p19_bst','p24_pur_cst_div','chal_sd_bst','chal_perm_clk_bst','chal_upg_cst_scale_mult', 'pts','clks','pps','upg1_cst','upg2_cst','upg3_cst','upg4_cst','upg7_cst','upg8_cst','pur_cst','cryst_cst','asc_cst', 'celest_cst', 'nebula_fragments', 'auto_cps','clk_pt_scale','pps_pt_scale_exp','chal_eff_pps_exp_mod','chal_eff_cst_exp_mod','clk_crit_c','clk_crit_m']: new_value = float(val_s); target_type = float
        elif var=='active_chal': new_value = None if val_s.lower() in ['none','null','false','0',''] else val_s; target_type = type(new_value)
        elif var in ['relic_lvls','chal_comps']: parsed = ast.literal_eval(val_s); new_value = {str(k): v for k, v in parsed.items()}; target_type = dict
        elif target_type is str: new_value = val_s
        elif target_type is None and var in ['active_chal']: new_value = None if val_s.lower() in ['none','null','false','0',''] else val_s; target_type = type(new_value)
        else:
            if target_type: new_value = target_type(val_s)
            else:
                 try: new_value = ast.literal_eval(val_s); target_type = type(new_value)
                 except (ValueError, SyntaxError): new_value = val_s; target_type = str; log_admin_ts(f"Warning: Guessed str type for '{var}'.")
    except (ValueError, TypeError, SyntaxError) as e: return f"Error parsing value '{val_s}' for '{var}': {e}"
    if is_global: globals()[var] = new_value
    else: setattr(tgt, var, new_value)
    buff_msg = ""; recalc_needed = True
    if not is_global and var in ['pur_cnt', 'cryst_cnt', 'celest_cnt'] and isinstance(old_val, (int, float)) and isinstance(new_value, int) and new_value > old_val:
        try:
            old_int, new_int = int(old_val), int(new_value); log_admin_ts(f"ADMIN: Retro buffs {var} {old_int+1}..{new_int}")
            if var == 'pur_cnt': [apply_purification_effects(i) for i in range(old_int, new_int)]; buff_msg = " P buffs."
            elif var == 'cryst_cnt': [apply_crystalline_effects(i + 1) for i in range(old_int, new_int)]; buff_msg = " C buffs."
            # No direct buff application for celest_cnt, effects derived from NF
        except Exception as e: log_admin_ts(f"Buff Err: {e}")
    elif not is_global and var == 'cr4_unl' and new_value is True and old_val is False: apply_crystalline_effects(4); buff_msg = " C4 effects."
    no_recalc_globals = ['is_running']; no_recalc_gamestate = ['last_save_time', 'admin_panel_active', 'playtime', 'needs_recalc_from_click_xp']
    if (is_global and var in no_recalc_globals) or (not is_global and var in no_recalc_gamestate): recalc_needed = False
    if not is_global and var in ['asc_lvl', 'asc_xp']: recalc_needed = False; g.check_ascension_level_up()
    if var == 'asc_lvl' and isinstance(new_value, (int,float)) and new_value > old_val: g.check_celestiality_unlock()
    result_msg = f"Set {var} to {new_value!r}."
    if recalc_needed: recalculate_derived_values(); result_msg += f" Recalc.{buff_msg}"
    elif buff_msg: recalculate_derived_values(); result_msg += f"{buff_msg} Recalc(buffs)."
    return result_msg
def cmd_varinfo(args):
    if len(args)!=1: return "Usage: get <var>"
    var=args[0].lower(); val=None; source="Not Found"
    if var in globals(): val=globals().get(var); source="Global"
    elif hasattr(g, var): val=getattr(g, var); source="GameState (g)"
    else:
        if hasattr(g, args[0]): val = getattr(g, args[0]); source = "GameState (g) [Case Sensitive]"; var = args[0]
        else: return f"Error: Variable '{args[0]}' not found."
    type_name = type(val).__name__; value_repr = repr(val)
    if isinstance(val, float): value_repr = format_number(val); value_repr += f" ({repr(val)})"
    return f"{var} ({type_name}) [{source}] = {value_repr}"
def cmd_list(args):
    filter_term = args[0].lower() if args else None; lines = []
    lines.append("--- Game State (g) ---")
    for key, value in sorted(vars(g).items()):
         if key.startswith('_'): continue
         if filter_term and filter_term not in key.lower(): continue
         type_name = type(value).__name__; value_repr = repr(value)
         if isinstance(value, float) or key == 'nebula_fragments': value_repr = format_number(value)
         lines.append(f"  {key} ({type_name}) = {value_repr}")
    lines.append("\n--- Globals ---"); global_vars = {'pts': pts, 'clks': clks, 'pps': pps, 'is_running': is_running}
    for key, value in sorted(global_vars.items()):
        if filter_term and filter_term not in key.lower(): continue
        type_name = type(value).__name__; value_repr = repr(value)
        if isinstance(value, float): value_repr = format_number(value)
        lines.append(f"  {key} ({type_name}) = {value_repr}")
    if not args and len(lines) <= 3: return "No variables found matching filter."
    elif len(lines) <= 3: return "No variables found."
    return "\n".join(lines)
def cmd_type(args):
    if len(args)!=1: return "Usage: type <var>"
    var=args[0].lower(); type_name=None
    if var in globals(): type_name=type(globals().get(var)).__name__
    elif hasattr(g, var): type_name=type(getattr(g, var)).__name__
    else: return f"Error: Variable '{var}' not found."
    return f"Type of '{var}' is {type_name}"
def cmd_limbrk(args):
    global g; count=0; log_func=log_admin_ts; targets_to_break=[]
    target_vars = [k for k in g.__dict__ if k.endswith('_max')];
    if not args or args[0].lower()=='all': targets_to_break = target_vars
    else:
        var_name = args[0].lower(); target = None
        if f"{var_name}_max" in target_vars: target = f"{var_name}_max"
        elif var_name in target_vars: target = var_name
        elif var_name.startswith("upg") and var_name[3:].isdigit() and f"upg{var_name[3:]}_max" in target_vars: target = f"upg{var_name[3:]}_max"
        if target: targets_to_break.append(target)
        else: return f"Error: No matching '_max' variable found for '{args[0]}'."
    if not targets_to_break: return "No target variables specified or found."
    for target_var in targets_to_break:
        if hasattr(g, target_var):
            try:
                current_value = getattr(g, target_var)
                if isinstance(current_value, (int, float)): setattr(g, target_var, float('inf')); count += 1; log_func(f"Set {target_var} limit to Infinity.")
                else: log_func(f"Warning: {target_var} not numeric, skipped.")
            except Exception as e: log_func(f"Error setting {target_var} to Inf: {e}")
    if count > 0: recalculate_derived_values(); return f"Set {count} variable limits to Infinity. Recalculated."
    else: return "No variable limits were changed."
def cmd_settype(args):
    if len(args)!=2: return "Usage: settype <var> <type>"
    var, type_str = args[0].lower(), args[1].lower(); target=None; is_global=False; current_val=None
    if var in globals(): target=globals(); is_global=True; current_val=target.get(var)
    elif hasattr(g, var): target=g; current_val=getattr(g, var)
    else: return f"Error: Variable '{var}' not found."
    new_value = None
    try:
        current_val_str = str(current_val); target_type = None
        if type_str == 'int': target_type = int; new_value = int(float(current_val_str))
        elif type_str == 'float': target_type = float; new_value = float(current_val_str)
        elif type_str == 'str': target_type = str; new_value = current_val_str
        elif type_str == 'bool': target_type = bool; new_value = current_val_str.lower() in ['true', '1', 't', 'y', 'yes']
        elif type_str == 'dict': target_type = dict; parsed = ast.literal_eval(current_val_str); new_value = parsed
        elif type_str == 'list': target_type = list; parsed = ast.literal_eval(current_val_str); new_value = parsed
        elif type_str in ['none', 'nonetype']: target_type = type(None); new_value = None
        else: return f"Error: Unsupported target type '{type_str}'."
        if is_global: globals()[var] = new_value
        else: setattr(target, var, new_value)
        recalc_needed = True; no_recalc_globals = ['is_running']; no_recalc_gamestate = ['last_save_time', 'admin_panel_active', 'playtime', 'needs_recalc_from_click_xp', 'active_chal']
        if (is_global and var in no_recalc_globals) or (not is_global and var in no_recalc_gamestate): recalc_needed = False
        result_msg = f"Attempted type change '{var}' to {type_str}. New: {new_value!r}."
        if recalc_needed: recalculate_derived_values(); result_msg += " Recalc."
        return result_msg
    except (ValueError, TypeError, SyntaxError) as e: return f"Error converting '{var}' ({current_val!r}) to {type_str}: {e}"
def cmd_buy(args):
    if len(args)<1 or len(args)>2: return "Usage: buy <id> [times=1]"
    item_id = args[0].lower(); times_to_buy = 1
    if len(args)==2:
        try: times_to_buy = int(args[1]); assert times_to_buy > 0
        except: return "Error: Invalid times."
    buy_functions = {'upg1': upgrade1, 'upg2': upgrade2, 'upg3': upgrade3, 'upg4': upgrade4, 'upg5': upgrade5, 'upg6': upgrade6, 'upg7': upgrade7, 'upg8': upgrade8, 'purify': purify, 'crystalline': crystalline, 'ascend': ascend, 'celestiality': celestiality }
    for relic_id in RELICS_DATA: buy_functions[relic_id] = lambda r=relic_id: buy_relic(r)
    purchase_func = buy_functions.get(item_id)
    if not purchase_func: return f"Error: Unknown Buy ID '{item_id}'."
    succeeded_count = 0; stop_reason = ""
    for i in range(times_to_buy):
        if not is_running: stop_reason = f"Game stopped at attempt {i+1}."; break
        state_before = {'pts': pts, 'clks': clks, 'sd': g.sd, 'lvl': getattr(g, f"{item_id}_lvl", None) if item_id.startswith('upg') and item_id[3].isdigit() else (g.relic_lvls.get(item_id) if item_id in RELICS_DATA else None), 'comp': getattr(g, f"{item_id}_comp", None) if item_id in ['upg5','upg6'] else None, 'count': getattr(g, f"{item_id}_cnt", None) if item_id in ['purify', 'crystalline', 'ascend', 'celestiality'] else None }
        try: purchase_func()
        except Exception as e: stop_reason = f"Error at attempt {i+1}: {e}"; logging.error(f"Admin Buy Err ({item_id}, att {i+1}): {e}", exc_info=True); break
        state_after = {'pts': pts, 'clks': clks, 'sd': g.sd, 'lvl': getattr(g, f"{item_id}_lvl", None) if item_id.startswith('upg') and item_id[3].isdigit() else (g.relic_lvls.get(item_id) if item_id in RELICS_DATA else None), 'comp': getattr(g, f"{item_id}_comp", None) if item_id in ['upg5','upg6'] else None, 'count': getattr(g, f"{item_id}_cnt", None) if item_id in ['purify', 'crystalline', 'ascend', 'celestiality'] else None }
        changed = False
        if state_after['pts'] != state_before['pts'] or state_after['clks'] != state_before['clks'] or state_after['sd'] != state_before['sd'] or state_after['lvl'] != state_before['lvl'] or state_after['comp'] != state_before['comp'] or state_after['count'] != state_before['count']: changed = True
        if changed: succeeded_count += 1
        else:
            is_maxed = False # Check if maxed
            if item_id.startswith('upg') and item_id[3].isdigit(): maxl = getattr(g, f"{item_id}_max", float('inf')); is_maxed = state_after['level'] is not None and int(state_after['level']) >= int(maxl)
            elif item_id in ['upg5', 'upg6']: is_maxed = state_after['comp'] is True
            elif item_id in RELICS_DATA: maxl = RELICS_DATA[item_id].get('max_level', RELIC_MAX_LEVEL); is_maxed = state_after['level'] is not None and maxl is not None and int(state_after['level']) >= int(maxl)
            if is_maxed: stop_reason = f"Stopped at attempt {i+1} (Maxed)."
            else: stop_reason = f"Stopped at attempt {i+1} (No change - unaffordable?)."
            break
    result = f"Attempted '{item_id}' x{times_to_buy}. Succeeded {succeeded_count} time(s)."
    if stop_reason: result += f" {stop_reason}"
    return result
def cmd_imprint(args):
    set_result = cmd_setvalue(args);
    if "Error" not in set_result: save_game(); return f"{set_result} Saved."
    else: return set_result
def cmd_stop(args):
    should_save = not (args and args[0].lower() in ['f','0','n','nosave','false'])
    msg=f"Shutdown initiated (Save: {should_save})..."; log_admin(msg); logging.info(msg)
    window.after(100, lambda save_flag=should_save: on_closing(save_flag))
    return "Shutdown scheduled."
def cmd_offline(args):
    if len(args)!=1: return "Usage: offline <seconds>"
    try:
        seconds = float(args[0]); assert seconds>=0; recalculate_derived_values()
        offline_pps = pps * 0.5 if ma.isfinite(pps) else 0.0; offline_pts = offline_pps * seconds
        offline_cps = g.auto_cps * 0.5 if ma.isfinite(g.auto_cps) else 0.0; offline_clks = offline_cps * seconds
        current_pts = pts if ma.isfinite(pts) else float('inf'); current_clks = clks if ma.isfinite(clks) else float('inf')
        try: pts = min(float('inf'), current_pts + offline_pts) if ma.isfinite(offline_pts) else float('inf')
        except OverflowError: pts = float('inf')
        try: clks = min(float('inf'), current_clks + offline_clks) if ma.isfinite(offline_clks) else float('inf')
        except OverflowError: clks = float('inf')
        recalculate_derived_values()
        return f"Simulated {seconds:.1f}s offline. Gained ~+{format_number(offline_pts)} P, +{format_number(offline_clks)} C."
    except (ValueError, AssertionError) as e: return f"Offline Err: Invalid input - {e}"
    except Exception as e: return f"Offline Error: {e}"
def cmd_recalc(args): recalculate_derived_values(); return "Derived values recalculated."
def cmd_reset(args):
    if not args: return "Usage: reset <purify | cryst | asc | celest | save>"
    reset_type = args[0].lower()
    if reset_type == "purify": reset_for_purify(); msg = "Purify progress reset."
    elif reset_type in ["cryst", "crystalline"]: reset_for_crystalline(); msg = "Crystalline & Purify progress reset."
    elif reset_type in ["asc", "ascension"]: reset_for_ascension(); msg = "Ascension, Crystalline & Purify progress reset."
    elif reset_type in ["celest", "celestiality"]: reset_for_celestiality(); msg = "Celestiality Reset Done (Full reset incl. SD/Asc/Relics/Chals). NF Kept."
    elif reset_type == "save":
        log_admin("Attempting full save file reset..."); msg = "Save file reset failed."
        try:
            if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE); log_admin_ts(f"Deleted save file: {SAVE_FILE}")
            else: log_admin_ts("Save file not found, skipping deletion.")
            g = GameState(); pts,clks=0.0,0.0; recalculate_derived_values(); save_game()
            log_admin_ts("Game state reset to default and saved."); msg = "Save file reset successfully."
        except OSError as e: log_admin_ts(f"Error deleting save file: {e}"); msg = f"Error deleting save file: {e}"
        except Exception as e: log_admin_ts(f"Error resetting game state: {e}"); msg = f"Error resetting game state: {e}"
    else: return f"Unknown reset type '{reset_type}'. Use purify, cryst, asc, celest, or save."
    if reset_type != "save": recalculate_derived_values() # Recalc after non-save resets
    return msg
def cmd_getchal(args):
    if len(args)!=1: return "Usage: getchal <id (e.g., c1)>"
    cid=args[0].lower();
    if cid not in CHALLENGES: return f"Error: Challenge '{cid}' not found."
    chal_data=CHALLENGES[cid]; comps=g.chal_comps.get(cid,0); maxc=chal_data.get('mc')
    is_maxed = (maxc is not None and comps >= maxc); status = "Not Started"
    if g.active_chal == cid: status = "ACTIVE"
    elif is_maxed: status = "MAXED"
    elif comps > 0: status = "In Progress"
    req_desc = "???"; reward_desc = "???"
    try: req_val = chal_data['rf'](g, comps); req_desc = chal_data['rd'](req_val)
    except Exception as e: req_desc = f"ReqError:{e}"
    try: reward_level = comps if is_maxed else comps + 1; reward_desc = chal_data['rwd'](g, reward_level)
    except Exception as e: reward_desc = f"RewardError:{e}"
    comp_str = f"({comps}/{maxc})" if maxc is not None else f"({comps})"
    restrictions = chal_data.get('restr','N/A'); reset_level = chal_data.get('rl','asc').capitalize()
    return (f"--- Chal {cid.upper()} [{status}] ---\nDesc: {chal_data['db']} {comp_str}\nReq: {req_desc}\n"
            f"Reward: {reward_desc}\nRestrict: {restrictions}\nReset: {reset_level}")
def cmd_setchal(args):
    logf = log_admin_ts;
    if len(args)!=2: return "Usage: setchal <id> <count>"
    try:
        cid=args[0].lower(); count=int(args[1]); assert count>=0
        if cid not in CHALLENGES: return f"Error: Challenge '{cid}' not found."
        maxc = CHALLENGES[cid].get('mc')
        if maxc is not None and count > maxc: logf(f"Warn: Clamping {count} > max {maxc}."); count = maxc
        g.chal_comps[cid] = count; logf(f"ADMIN NOTE: Set '{cid}' comps to {count}. No retro rewards. Use applychalrewards.");
        recalculate_derived_values() # Update derived values affected by completion count
        return f"Set chal '{cid}' completions to {count}."
    except (ValueError, AssertionError) as e: return f"SetChal Err: Invalid count - {e}"
    except Exception as e: return f"SetChal Error: {e}"
def cmd_applychalrewards(args):
    logf = log_admin_ts; cid_filter = args[0].lower() if args else None; applied_count = 0
    logf("Applying challenge rewards based on current completions...")
    g.chal_sd_bst = 1.0; g.chal_perm_clk_bst = 1.0; g.r3_cst_m = 1.0; g.chal_upg_cst_scale_mult = 1.0 # Reset reward vars
    for cid, chal_data in CHALLENGES.items():
        if cid_filter and cid != cid_filter: continue
        completions = g.chal_comps.get(cid, 0)
        if completions > 0:
             apply_func = chal_data.get('arf')
             if apply_func:
                 try: apply_func(g); logf(f"Applied '{cid}' rewards ({completions} comps)."); applied_count += 1
                 except Exception as e: logf(f"Err applying '{cid}' reward: {e}")
             else: logf(f"Warn: No reward func ('arf') for '{cid}'.")
    if applied_count > 0: recalculate_derived_values(); return f"Applied rewards for {applied_count} challenges. Recalculated."
    else: return "No challenge rewards applied."
def cmd_resetchal(args):
    logf = log_admin_ts;
    if len(args)!=1: return "Usage: resetchal <id | all>"
    target_id = args[0].lower()
    if target_id == 'all':
        if not g.chal_comps: return "No challenge completions to reset."
        g.chal_comps.clear(); cmd_applychalrewards([]); recalculate_derived_values()
        logf("Reset all chal comps and re-applied rewards."); return "Reset all challenge completions."
    elif target_id in CHALLENGES:
        if target_id in g.chal_comps:
            del g.chal_comps[target_id]; cmd_applychalrewards([]); recalculate_derived_values()
            logf(f"Reset chal '{target_id}' and re-applied all rewards."); return f"Reset completions for '{target_id}'."
        else: return f"Challenge '{target_id}' already 0."
    else: return f"Error: Unknown challenge ID '{target_id}'."
def cmd_forcechal(args):
    if len(args)<1: return "Usage: forcechal <enter|exit> [id]"
    action = args[0].lower()
    if action == 'enter':
        if len(args)!=2: return "Usage: forcechal enter <id>"; cid = args[1].lower()
        if cid not in CHALLENGES: return f"Err: Unknown chal '{cid}'"
        if g.active_chal: return f"Err: Already in chal '{g.active_chal}'. Exit first."
        reset_for_challenge(cid); updateui(); return f"Forced entry into chal '{cid}'."
    elif action == 'exit':
        if not g.active_chal: return "Err: Not in chal."; exiting_chal = g.active_chal; exit_challenge()
        return f"Forced exit from chal '{exiting_chal}'."
    else: return "Err: Unknown action. Use 'enter' or 'exit'."
def cmd_completechal(args):
    if len(args)!=0: return "Usage: completechal"
    if not g.active_chal: return "Err: Not in chal."; cid=g.active_chal; chal_data=CHALLENGES.get(cid)
    if not chal_data: exit_challenge(); return f"Err: Invalid active chal '{cid}'. Exited."
    comps=g.chal_comps.get(cid,0); maxc=chal_data.get('mc')
    if maxc is not None and comps >= maxc: return f"Chal '{cid}' maxed."
    complete_challenge(cid); return f"Force complete '{cid}' (Lvl {g.chal_comps.get(cid, '??')})."
def cmd_help(args):
    h = COMMAND_HANDLERS; help_text = "Admin Console Commands:\n";
    main_cmds = sorted([c for c, d in h.items() if 'alias' not in d])
    aliases = sorted([c for c, d in h.items() if 'alias' in d])
    max_len = 0;
    if main_cmds: max_len = max(len(c) for c in main_cmds)
    if aliases: max_len = max(max_len, max(len(c) for c in aliases))
    for c in main_cmds: help_text += f"  {c:<{max_len}}  {h[c]['help']}\n"
    if aliases:
        help_text += "\nAliases:\n";
        for c in aliases: target = next((k for k,v in h.items() if v['func']==h[c]['func'] and 'alias' not in v),'?'); help_text += f"  {c:<{max_len}}  Alias for '{target}'\n"
    return help_text.strip()
def _start_admin_thread(target_func, args_tuple, task_id_prefix, log_func):
    global active_admin_thds; task_id = f"{task_id_prefix}-{random.randint(100,999)}"
    thread = th.Thread(target=target_func, args=args_tuple + (task_id,), daemon=True)
    active_admin_thds.append(task_id); thread.start(); log_func(f"ADMIN: Started BG task {task_id}.")
    return task_id
def _admin_thread_wrapper(func, *args):
    task_id = args[-1]; log_func = log_admin_ts; func_args = args[:-1]
    log_func(f"[{task_id}] Starting...");
    try: func(*func_args); log_func(f"[{task_id}] Finished.")
    except Exception as e: log_func(f"[{task_id}] Error: {e}"); logging.error(f"Admin Task [{task_id}] Err: {e}", exc_info=True)
    finally:
        if task_id in active_admin_thds: active_admin_thds.remove(task_id); # log_func(f"[{task_id}] Removed.") # Less verbose
        # else: log_func(f"[{task_id}] Warn: Task ID not found on completion.")
def _wait_task(seconds_to_wait): time.sleep(seconds_to_wait)
def cmd_wait(args):
    if len(args)!=1: return "Usage: wait <seconds>"
    try: s = float(args[0]); assert s>=0; task_id = _start_admin_thread(_admin_thread_wrapper, (_wait_task, s), "wait", log_admin_ts); return f"wait: Started BG wait {task_id} for {s}s."
    except: return "Error: Invalid time."
def _repeat_task(times, command_str):
    logf = log_admin_ts; executed_count = 0
    for i in range(times):
        if not is_running: logf(f"repeat: Game stopped. Halting after {executed_count}/{times}."); break
        _exec_cmd(command_str, False); executed_count += 1; time.sleep(0.05)
def cmd_repeat(args):
    if len(args)<2: return "Usage: repeat <times> <command...>"
    try: t = int(args[0]); assert t>0; cmd = " ".join(args[1:]); task_id = _start_admin_thread(_admin_thread_wrapper, (_repeat_task, t, cmd), "repeat", log_admin_ts); return f"repeat: Started BG repeat {task_id} ('{cmd}' x{t})."
    except: return "Error: Invalid times."
def _while_task(condition_str, command_str):
    logf = log_admin_ts; iterations = 0; max_iterations = 10000
    while is_running and iterations < max_iterations:
        if _eval_cond(condition_str): _exec_cmd(command_str, False); iterations += 1; time.sleep(0.1)
        else: logf(f"while: Cond '{condition_str}' false. Stop."); break
    else:
        if iterations >= max_iterations: logf(f"while: Max iter ({max_iterations}). Stop.")
def cmd_while(args):
    if len(args)<4 or args[1].lower() not in ['==','!=','>','<','>=','<=','is','is not']: return "Usage: while <var> <op> <val> <command...>"
    try: condition = " ".join(args[0:3]); command = " ".join(args[3:]); initial_check = _eval_cond(condition); task_id = _start_admin_thread(_admin_thread_wrapper, (_while_task, condition, command), "while", log_admin_ts); return f"while: Started BG loop {task_id}. Cond ('{condition}') init {initial_check}."
    except Exception as e: return f"Error setup while: {e}"
def cmd_setrelic(args):
    if len(args)!=2: return "Usage: setrelic <id> <level>"; relic_id, level_str = args[0].lower(), args[1]
    if relic_id not in RELICS_DATA: return f"Error: Relic ID '{relic_id}' not found."
    try: level = int(level_str); assert level >= 0
    except: return "Error: Invalid level."
    max_level = RELICS_DATA[relic_id].get('max_level', RELIC_MAX_LEVEL)
    if max_level is not None and level > max_level: return f"Error: Level {level} exceeds max {max_level}."
    g.relic_lvls[relic_id] = level; recalculate_derived_values(); return f"Set relic '{relic_id}' to {level}. Recalc."
def cmd_listrelics(args):
    output = "--- Relics ---\n"; owned = g.relic_lvls
    if not RELICS_DATA: return "No relics defined."
    for rid in sorted(list(RELICS_DATA.keys())):
        d = RELICS_DATA[rid]; lvl = owned.get(rid, 0); owned_m = "(Owned)" if lvl > 0 else ""; ml = d.get('max_level', RELIC_MAX_LEVEL)
        ls = f"Lvl:{lvl}/{ml}" if ml is not None else f"Lvl:{lvl}"; eff = get_relic_effect(rid, '?'); eff_s = format_number(eff) if eff != '?' else '?'
        output += f"{rid} [{d.get('name','???')}]: {ls} {owned_m} (Eff: {eff_s})\n" # Show effect
    return output.strip()
def cmd_resetrelics(args):
    if not g.relic_lvls: return "No relics owned."
    g.relic_lvls.clear(); recalculate_derived_values(); return "Relics reset. Recalc."

COMMAND_HANDLERS = {
    'set': {'func': cmd_setvalue, 'help': '<v> <val> Set var'}, 'get': {'func': cmd_varinfo, 'help': '<v> Get var info'},
    'type': {'func': cmd_type, 'help': '<v> Get var type'}, 'list': {'func': cmd_list, 'help': '[f] List vars'},
    'limbrk': {'func': cmd_limbrk, 'help': '<n|all> Set _max inf'}, 'settype': {'func': cmd_settype, 'help': '<v> <t> Set type'},
    'buy': {'func': cmd_buy, 'help': '<id> [t] Buy item'}, 'imprint': {'func': cmd_imprint, 'help': '<v> <val> Set & save'},
    'stop': {'func': cmd_stop, 'help': "[nosave] Stop game"}, 'offline': {'func': cmd_offline, 'help': '<secs> Sim offline'},
    'recalc': {'func': cmd_recalc, 'help': '- Force recalc'}, 'reset': {'func': cmd_reset, 'help': '<type> Reset progress'},
    'help': {'func': cmd_help, 'help': '- Show help'}, 'getchal': {'func': cmd_getchal, 'help': '<id> Get chal details'},
    'setchal': {'func': cmd_setchal, 'help': '<id> <c> Set chal comps'}, 'applychalrewards': {'func': cmd_applychalrewards, 'help': '[id] Apply rewards'},
    'resetchal': {'func': cmd_resetchal, 'help': '<id|all> Reset chal comps'}, 'forcechal': {'func': cmd_forcechal, 'help': '<in|out> [id] Force chal state'},
    'completechal': {'func': cmd_completechal, 'help': '- Force complete active chal'}, 'wait': {'func': cmd_wait, 'help': '<s > Wait secs (BG)'},
    'repeat': {'func': cmd_repeat, 'help': '<t> <cmd> Repeat (BG)'}, 'while': {'func': cmd_while, 'help': '<cond> <cmd> Loop (BG)'},
    'setrelic': {'func': cmd_setrelic, 'help': '<id> <lvl> Set relic lvl'}, 'listrelics': {'func': cmd_listrelics, 'help': '- List relics'},
    'resetrelics': {'func': cmd_resetrelics, 'help': '- Reset relics'},
    'setvalue': {'func': cmd_setvalue, 'help': '-> set', 'alias': True}, 'varinfo': {'func': cmd_varinfo, 'help': '-> get', 'alias': True},
}
def admin_execute_command(event=None):
    if not DEVELOPER_MODE or not admin_wdgs.get('cmd_input'): return
    cmd_string=admin_wdgs['cmd_input'].get().strip();
    if not cmd_string: return
    admin_wdgs['cmd_input'].delete(0,tk.END); log_admin(f"> {cmd_string}"); _exec_cmd(cmd_string, True)
def log_admin(msg):
    if th.current_thread() is not th.main_thread(): log_admin_ts(msg); return
    output_widget=admin_wdgs.get('cmd_output')
    if output_widget and window and window.winfo_exists():
        try:
            text_widget = output_widget.text if hasattr(output_widget, 'text') else output_widget
            current_state = text_widget['state']
            text_widget.configure(state=tk.NORMAL)
            text_widget.insert(tk.END, str(msg) + "\n")
            text_widget.configure(state=tk.DISABLED)
            text_widget.see(tk.END)
        except tk.TclError: pass
        except Exception as e: logging.warning(f"log_admin UI update failed: {e}")
def open_admin_panel():
    global admin_window, admin_wdgs, g
    if not DEVELOPER_MODE: return
    if admin_window and admin_window.winfo_exists():
        try: admin_window.lift(); admin_window.focus_force(); return
        except: admin_window=None
    g.admin_panel_active=True; admin_window=ttk.Toplevel(window); admin_window.title("Admin Console"); admin_window.geometry("700x500"); admin_window.protocol("WM_DELETE_WINDOW", on_admin_close)
    main_frame=ttk.Frame(admin_window, padding=10); main_frame.pack(expand=True, fill=tk.BOTH); main_frame.grid_rowconfigure(0, weight=1); main_frame.grid_columnconfigure(0, weight=1)
    output_area = ttkScrolledText(main_frame, height=20, wrap=tk.WORD, state=tk.DISABLED, autohide=True, font=("Consolas", 10)); output_area.grid(row=0, column=0, sticky='nsew', padx=5, pady=5); admin_wdgs['cmd_output'] = output_area
    input_entry = ttk.Entry(main_frame, font=("Consolas", 10)); input_entry.grid(row=1, column=0, sticky='ew', padx=5, pady=(5,10)); input_entry.bind("<Return>", admin_execute_command); admin_wdgs['cmd_input'] = input_entry; input_entry.focus_set(); log_admin("Admin Console Ready. Type 'help'.")
def on_admin_close():
    global admin_window, admin_wdgs, g, active_admin_thds
    if not DEVELOPER_MODE: return
    g.admin_panel_active=False
    if active_admin_thds: log_admin(f"Closing admin panel. {len(active_admin_thds)} BG task(s) remain.")
    if admin_window:
        try: admin_window.destroy()
        except: pass
    admin_window=None; admin_wdgs.clear(); logging.info("Admin panel closed.")

# ==============================================================================
#                           UI SETUP
# ==============================================================================
def create_label(parent, text, row, col, **kwargs):
    grid_opts = {k: kwargs.pop(k) for k in list(kwargs.keys()) if k in ['sticky', 'padx', 'pady', 'columnspan', 'rowspan']}
    grid_opts.setdefault('sticky', 'w'); grid_opts.setdefault('padx', 5); grid_opts.setdefault('pady', 2)
    lbl = ttk.Label(parent, text=text, **kwargs)
    lbl.grid(row=row, column=col, **grid_opts)
    return lbl

def create_button(parent, text, command, row, col, **kwargs):
    grid_opts = {k: kwargs.pop(k) for k in list(kwargs.keys()) if k in ['sticky', 'padx', 'pady', 'columnspan', 'rowspan']}
    grid_opts.setdefault('sticky', 'ew'); grid_opts.setdefault('padx', 5); grid_opts.setdefault('pady', 5)
    style = kwargs.pop('bootstyle', 'primary-outline'); width = kwargs.pop('width', 10)
    btn = ttk.Button(parent, text=text, command=command, bootstyle=style, width=width, **kwargs)
    btn.grid(row=row, column=col, **grid_opts)
    return btn

# --- Main Window ---
window = ttk.Window(themename="darkly"); window.title("Ordinal Ascent II"); window.geometry("1000x700")
window.grid_rowconfigure(0, weight=1); window.grid_columnconfigure(0, weight=1)

# --- Notebook (Tabs) ---
notebook_ref = ttk.Notebook(window, bootstyle="primary"); notebook_ref.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
tab_frames = {} # Reset for population

# Define frames and unlock checks
pres_f = ttk.Frame(notebook_ref, padding=(20,10)); tab_frames[0] = (pres_f, lambda: True, " Prestige ")
upg_f = ttk.Frame(notebook_ref, padding=(20,10)); tab_frames[1] = (upg_f, lambda: True, " Upgrades ")
clk_f = ttk.Frame(notebook_ref, padding=(20,10)); tab_frames[2] = (clk_f, lambda: g.cr4_unl, " Clicking ")
asc_f = ttk.Frame(notebook_ref, padding=(20,10)); tab_frames[3] = (asc_f, lambda: g.asc_unl, " Ascension ")
relic_f = ttk.Frame(notebook_ref, padding=(20,10)); tab_frames[4] = (relic_f, lambda: g.asc_first, " Relics ")
chal_f = ttk.Frame(notebook_ref, padding=(20,10)); tab_frames[5] = (chal_f, lambda: g.asc_first, " Challenges ")
celest_f = ttk.Frame(notebook_ref, padding=(20,10)); tab_frames[6] = (celest_f, lambda: g.celest_unl, " Celestiality ")
stats_f = ttk.Frame(notebook_ref, padding=(10,10)); tab_frames[7] = (stats_f, lambda: True, " Statistics ")
help_f = ttk.Frame(notebook_ref, padding=(0,0)); tab_frames[8] = (help_f, lambda: True, " Help ")

# Add tabs using the defined frames and names
for i in range(len(tab_frames)):
    frame, _, base_name = tab_frames[i]
    notebook_ref.add(frame, text=base_name) # Add with base name initially

# Configure Frame Grids
pres_f.grid_columnconfigure((0,3),weight=1); pres_f.grid_rowconfigure(0, weight=0)
upg_f.grid_columnconfigure(1,weight=1); upg_f.grid_columnconfigure(3,weight=0);
clk_f.grid_columnconfigure(1,weight=1); clk_f.grid_rowconfigure(1,weight=1);
asc_f.grid_columnconfigure(0,weight=1); asc_f.grid_rowconfigure(4, weight=1) # Label row 4 expands now
relic_f.grid_columnconfigure(1,weight=1);
chal_f.grid_columnconfigure(0,weight=1); chal_f.grid_rowconfigure(2,weight=1)
celest_f.grid_columnconfigure(0,weight=1); celest_f.grid_rowconfigure(1, weight=1)
stats_f.grid_columnconfigure(0,weight=1); stats_f.grid_rowconfigure(0, weight=1)

# === Populate Prestige Tab ===
purlbl=create_label(pres_f,"...",0,0,columnspan=2,sticky='ew',wraplength=350); purbtn=create_button(pres_f,"Purify",purify,1,0,columnspan=2)
ttk.Separator(pres_f,orient=VERTICAL).grid(row=0,column=2,rowspan=2,sticky='ns',padx=20)
crylbl=create_label(pres_f,"...",0,3,columnspan=2,sticky='ew',wraplength=350); crybtn=create_button(pres_f,"Crystalline",crystalline,1,3,columnspan=2)

# === Populate Upgrades Tab ===
ptslbl=create_label(upg_f,"Pts: ...",0,0,columnspan=4); ppslbl=create_label(upg_f,"PPS: ...",1,0,columnspan=4)
ttk.Separator(upg_f,orient=HORIZONTAL).grid(row=2,column=0,columnspan=4,sticky='ew',pady=10)
create_label(upg_f,"Upg1:",3,0,sticky='e',font=('-weight','bold')); upg1cstlbl=create_label(upg_f,"C:...",3,1,sticky='w'); btn1=create_button(upg_f,"Buy",upgrade1,3,2,width=5); upg1explbl=create_label(upg_f,"E:...",4,1,columnspan=2, sticky='w')
create_label(upg_f,"Upg2:",5,0,sticky='e',font=('-weight','bold')); upg2cstlbl=create_label(upg_f,"C:...",5,1,sticky='w'); btn2=create_button(upg_f,"Buy",upgrade2,5,2,width=5); upg2explbl=create_label(upg_f,"E:...",6,1,columnspan=2, sticky='w')
create_label(upg_f,"Upg3:",7,0,sticky='e',font=('-weight','bold')); upg3cstlbl=create_label(upg_f,"C:...",7,1,sticky='w'); btn3=create_button(upg_f,"Buy",upgrade3,7,2,width=5); upg3explbl=create_label(upg_f,"E:...",8,1,columnspan=2, sticky='w')
create_label(upg_f,"Upg4:",9,0,sticky='e',font=('-weight','bold')); upg4cstlbl=create_label(upg_f,"C:...",9,1,sticky='w'); btn4=create_button(upg_f,"Buy",upgrade4,9,2,width=5); upg4explbl=create_label(upg_f,"E:...",10,1,columnspan=2, sticky='w')

# === Populate Clicking Tab ===
clkslbl=create_label(clk_f,"Clk:...",0,0,columnspan=2,sticky='ew',anchor=tk.CENTER); clkbtn=create_button(clk_f,"Click!",click_power_action,1,0,columnspan=2,rowspan=2,sticky='nsew',pady=20)
ttk.Separator(clk_f,orient=HORIZONTAL).grid(row=3,column=0,columnspan=2,sticky='ew',pady=15)
create_label(clk_f,"Upg5:",4,0,sticky='e',font=('-weight','bold')); upg5cstlbl=create_label(clk_f,"C:...",4,1); btn5=create_button(clk_f,"Buy",upgrade5,5,0, width=5); upg5explbl=create_label(clk_f,"E:...",5,1)
create_label(clk_f,"Upg6:",6,0,sticky='e',font=('-weight','bold')); upg6cstlbl=create_label(clk_f,"C:...",6,1); btn6=create_button(clk_f,"Buy",upgrade6,7,0, width=5); upg6explbl=create_label(clk_f,"E:...",7,1)
create_label(clk_f,"Upg7:",8,0,sticky='e',font=('-weight','bold')); upg7cstlbl=create_label(clk_f,"C:...",8,1); btn7=create_button(clk_f,"Buy",upgrade7,9,0, width=5); upg7explbl=create_label(clk_f,"E:...",9,1)
create_label(clk_f,"Upg8:",10,0,sticky='e',font=('-weight','bold')); upg8cstlbl=create_label(clk_f,"C:...",10,1); btn8=create_button(clk_f,"Buy",upgrade8,11,0, width=5); upg8explbl=create_label(clk_f,"E:...",11,1)

# === Populate Ascension Tab ===
sdlbl=create_label(asc_f,"SD: 0",0,0,columnspan=2,sticky='ew',font=('-weight','bold')); asclvllbl=create_label(asc_f,"AscLvl:0",1,0,columnspan=2,sticky='ew'); ascproglbl=create_label(asc_f,"XP:0/1K(0%)",2,0,columnspan=2,sticky='ew')
ttk.Separator(asc_f, orient=HORIZONTAL).grid(row=3, column=0, columnspan=2, sticky='ew', pady=10)
asclbl=create_label(asc_f,"Asc Locked",4,0,columnspan=2,sticky='nsew',wraplength=400); ascbtn=create_button(asc_f,"Ascend",ascend,5,0,columnspan=2)

# === Populate Relics Tab ===
relic_title_lbl=create_label(relic_f,"Relics",0,0,columnspan=3,sticky='ew',font=('-weight','bold'))
relic_row_counter=1
for rid,data in RELICS_DATA.items():
    nl=create_label(relic_f, data['name'], relic_row_counter, 0, sticky='e', font=('-weight','bold'))
    dl=create_label(relic_f, data['desc'], relic_row_counter, 1, sticky='w', wraplength=300)
    ll=create_label(relic_f, "L:0", relic_row_counter + 1, 1, sticky='w')
    cl=create_label(relic_f, "C:...", relic_row_counter + 2, 1, sticky='w')
    bb=create_button(relic_f, "Buy", lambda r=rid: buy_relic(r), relic_row_counter, 2, rowspan=3, sticky='ewns', width=5)
    relic_wdgs[rid]=(nl, dl, ll, cl, bb); relic_row_counter += 3
    # Widgets start hidden, shown by updateui if g.asc_first

# === Populate Challenges Tab ===
chal_frame = ttk.Frame(chal_f); chal_frame.grid(row=0, column=0, sticky='nsew'); chal_frame.grid_columnconfigure(0, weight=1); chal_frame.grid_rowconfigure(2, weight=1)
create_label(chal_frame,"Challenges",0,0,sticky='ew',font=('-weight','bold')); exitchalbtn=create_button(chal_frame,"Exit Challenge",exit_challenge,1,0,sticky='ew',bootstyle="danger-outline")
chal_scroll_outer_f=ttk.Frame(chal_frame); chal_scroll_outer_f.grid(row=2,column=0,sticky='nsew',pady=(10,0)); chal_scroll_outer_f.grid_rowconfigure(0,weight=1); chal_scroll_outer_f.grid_columnconfigure(0,weight=1)
chal_cvs=tk.Canvas(chal_scroll_outer_f, borderwidth=0, highlightthickness=0); chal_scr=ttk.Scrollbar(chal_scroll_outer_f, orient="vertical", command=chal_cvs.yview, bootstyle="round"); chal_cvs.configure(yscrollcommand=chal_scr.set)
chal_list_f=ttk.Frame(chal_cvs); chal_list_f.grid_columnconfigure(0, weight=1)
chal_cvs.grid(row=0,column=0,sticky='nsew'); chal_scr.grid(row=0,column=1,sticky='ns'); chal_cvs_win=chal_cvs.create_window((0,0), window=chal_list_f, anchor="nw")
chal_list_f.bind("<Configure>", lambda e: chal_cvs.configure(scrollregion=chal_cvs.bbox("all"))); chal_cvs.bind('<Configure>', lambda e: chal_cvs.itemconfig(chal_cvs_win, width=e.width))
current_chal_row=0
for cid,chal_data in CHALLENGES.items():
    cf=ttk.Frame(chal_list_f, padding=5, borderwidth=1, relief="solid"); cf.grid(row=current_chal_row, column=0, sticky='ew', pady=5); cf.grid_columnconfigure(0,weight=1); cf.grid_columnconfigure(1,weight=0)
    cl=create_label(cf,"...",0,0,sticky='nw',wraplength=550); cb=create_button(cf,f"Enter C{cid[1:]}",lambda c=cid:enter_challenge(c),0,1,sticky='ne'); chal_wdgs[cid]=(cl,cb); current_chal_row+=1
# Frame starts hidden, shown by updateui if g.asc_first

# === Populate Celestiality Tab ===
nf_lbl = create_label(celest_f, "Nebula Fragments: 0", 0, 0, columnspan=2, sticky='ew', font=('-weight','bold'))
celestlbl = create_label(celest_f, "Celestiality Locked", 1, 0, columnspan=2, sticky='nsew', wraplength=400)
celestbtn = create_button(celest_f, "Perform Celestiality", celestiality, 2, 0, columnspan=2)
# Widgets start hidden, shown by updateui if g.celest_unl

# === Populate Statistics Tab ===
stats_text = ttkScrolledText(stats_f, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 10), autohide=True)
stats_text.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

# === Populate Help Tab ===
help_pane = PanedWindow(help_f, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, showhandle=True, handlesize=10)
help_pane.pack(fill=tk.BOTH, expand=True)
help_nav_f = ttk.Frame(help_pane, padding=(10, 10)); help_pane.add(help_nav_f) # No weight
help_nav_f.grid_columnconfigure(0, weight=1)
help_text_f = ttk.Frame(help_pane, padding=(5, 5)); help_pane.add(help_text_f) # No weight
help_text_f.grid_rowconfigure(0, weight=1); help_text_f.grid_columnconfigure(0, weight=1)
help_text = ttkScrolledText(help_text_f, wrap=tk.WORD, state=tk.DISABLED, font=("TkDefaultFont", 10), autohide=True)
help_text.grid(row=0, column=0, sticky='nsew')
_active_help_topic = None
def show_help(topic):
    global _active_help_topic, help_text, help_buttons
    if not help_text or not help_buttons: return
    if _active_help_topic and _active_help_topic in help_buttons and help_buttons[_active_help_topic].winfo_exists():
         # Check if the previously active button is still unlocked before resetting style
         is_unlocked_prev = False
         try: # Add try-except for safety during update/state checks
             if help_buttons[_active_help_topic].cget('state') != tk.DISABLED:
                 is_unlocked_prev = True
         except tk.TclError: pass # Widget might not exist anymore
         update_button_style(help_buttons[_active_help_topic], "primary" if is_unlocked_prev else "locked")

    _active_help_topic = topic; content = "Help topic not found."; unlocked = False
    # Determine unlock status based on game state
    if topic == 'points': unlocked = True
    elif topic == 'purify': unlocked = g.pur_cnt > 0 or g.cryst_unl or g.asc_unl or g.celest_unl
    elif topic == 'crystalline': unlocked = g.cryst_cnt > 0 or g.asc_unl or g.celest_unl
    elif topic == 'clicking': unlocked = g.cr4_unl
    elif topic == 'ascension': unlocked = g.asc_first
    elif topic == 'relics': unlocked = g.asc_first
    elif topic == 'challenges': unlocked = g.asc_first
    elif topic == 'celestiality': unlocked = g.celest_unl

    if unlocked:
        content = HELP_CONTENT.get(topic, "Help content missing.")
        if topic in help_buttons and help_buttons[topic].winfo_exists(): update_button_style(help_buttons[topic], "info")
    else: content = "Unlock this feature to view help."
    try:
        help_text.state = tk.NORMAL
        help_text.delete('1.0', tk.END)
        help_text.insert('1.0', content)
        help_text.state = tk.DISABLED
        help_text.see('1.0') # Scroll to the top of the help text
    except tk.TclError: pass # Ignore errors if widget destroyed during update
help_row = 0; help_topics_order = ['points', 'purify', 'crystalline', 'clicking', 'ascension', 'relics', 'challenges', 'celestiality']
for topic in help_topics_order:
    if topic in HELP_CONTENT:
        btn_text = topic.replace('_', ' ').title(); btn = create_button(help_nav_f, btn_text, lambda t=topic: show_help(t), row=help_row, col=0, sticky='ew', width=15); help_buttons[topic] = btn; help_row += 1
# Initial help view deferred to after load_game()

# === Admin Button ===
if DEVELOPER_MODE:
    admin_btn=ttk.Button(window,text="A",command=open_admin_panel,bootstyle="info-outline", width=2)
    admin_btn.place(relx=0.0, rely=1.0, x=5, y=-5, anchor='sw') # Bottom Left

# ==============================================================================
#                             INITIALIZATION & MAIN LOOP
# ==============================================================================
load_game()
logging.info("Starting game threads...")
game_thd=th.Thread(target=game_loop_thread_func,daemon=True); game_thd.start()
save_thd=th.Thread(target=autosave_thread_func,daemon=True); save_thd.start()
start_autobuy_thread_if_needed()

# Ensure the initial help topic is displayed after loading the game state
if help_text and HELP_CONTENT: # Ensure widget and content exist
    # Default to 'points' topic, but check if it should be shown
    initial_topic_to_show = 'points'
    show_help(initial_topic_to_show)

updateui() # Initial UI update (will handle initial help view and tab names)

if stats_text and stats_text.winfo_exists():
    stats_content = "--- Game State ---\n"
    # ... (rest of stats_content generation) ...
    stats_content += f"Limit Break (p20_lim_brk): {g.p20_lim_brk}\n"
    stats_content += f"Active Challenge (active_chal): {g.active_chal}\n"

    try:
            current_state = stats_text.state
            stats_text.state = tk.NORMAL
            stats_text.delete('1.0', tk.END)
            stats_text.insert('1.0', stats_content)
            stats_text.state = tk.DISABLED
            stats_text.see('1.0') # Scroll to top for stats
    except tk.TclError: pass # Ignore errors if widget is destroyed


# --- Help Tab ---
# Help tab should always be visible, update button states/text
    if help_buttons and help_text:
        for topic, button in help_buttons.items():
            if not button or not button.winfo_exists(): continue # Added check for button existence
            unlocked = False
            if topic == 'points': unlocked = True
            elif topic == 'purify': unlocked = g.pur_cnt > 0 or g.cryst_unl or g.asc_unl or g.celest_unl
            elif topic == 'crystalline': unlocked = g.cryst_cnt > 0 or g.asc_unl or g.celest_unl
            elif topic == 'clicking': unlocked = g.cr4_unl
            elif topic == 'ascension': unlocked = g.asc_first
            elif topic == 'relics': unlocked = g.asc_first
            elif topic == 'challenges': unlocked = g.asc_first
            elif topic == 'celestiality': unlocked = g.celest_unl

            btn_text = topic.replace('_', ' ').title()
            # Use try-except for configure as well, just in case
            try:
                button.configure(text=btn_text if unlocked else obfuscate(btn_text))

                if _active_help_topic == topic:
                        # Keep active style if unlocked, otherwise force locked style
                        update_button_style(button, "info" if unlocked else "locked")
                else:
                        # Set normal or locked style
                        update_button_style(button, "primary" if unlocked else "locked")
            except tk.TclError: pass # Ignore if button destroyed

        # Schedule next update
        if is_running: window.after(UPDATE_INTERVAL_MS, updateui)


# === Admin Button ===
if DEVELOPER_MODE:
    admin_btn=ttk.Button(window,text="A",command=open_admin_panel,bootstyle="info-outline", width=2)
    admin_btn.place(relx=0.0, rely=1.0, x=5, y=-5, anchor='sw') # Bottom Left

# ==============================================================================
#                             INITIALIZATION & MAIN LOOP
# ==============================================================================
load_game()
logging.info("Starting game threads...")
game_thd=th.Thread(target=game_loop_thread_func,daemon=True); game_thd.start()
save_thd=th.Thread(target=autosave_thread_func,daemon=True); save_thd.start()
start_autobuy_thread_if_needed()
updateui() # Initial UI update (will handle initial help view and tab names)

def on_closing(save_on_exit=True):
    global is_running, admin_window, active_admin_thds;
    if not is_running: return
    logging.info("Shutdown sequence initiated..."); is_running=False
    if admin_window and admin_window.winfo_exists(): on_admin_close()
    shutdown_timeout=0.5
    threads_to_join = [t for t in [game_thd, save_thd, autobuy_thd] if t and t.is_alive()]
    if threads_to_join:
        logging.debug(f"Waiting up to {shutdown_timeout}s for {len(threads_to_join)} threads...")
        start_join = time.monotonic()
        for t in threads_to_join:
            remaining_time = shutdown_timeout - (time.monotonic() - start_join)
            if remaining_time > 0: t.join(timeout=remaining_time)
            else: break
    if active_admin_thds: logging.info(f"Note: {len(active_admin_thds)} admin BG task(s) may still be running.")
    if save_on_exit: save_game(); logging.info("Final save completed.")
    else: logging.info("Skipping final save.")
    try:
        if window and window.winfo_exists(): window.destroy()
    except Exception as e: logging.error(f"Error destroying main window: {e}")
    logging.info("Shutdown complete."); logging.shutdown()

window.protocol("WM_DELETE_WINDOW", lambda: on_closing(True))
try:
    window.mainloop()
except KeyboardInterrupt:
    logging.info("KeyboardInterrupt. Shutting down...")
    on_closing(True)
except Exception as e:
    logging.critical(f"Unhandled exception in main loop: {e}", exc_info=True)
    on_closing(False) # Don't save on crash

# --- END OF FILE ---
