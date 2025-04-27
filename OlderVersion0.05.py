#WARNING FOR FUTURE ME: TO USE THE CUSTOM STYLE DO pip install ttkbootstrap DO NOT COMPLAIN IF YOU ARE AN IDIOT!!!!

#-Imports.
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading as th
import time as tm
import warnings as warn
import datetime as dt
import math as ma
import sys

# Open the log file in append mode
log_file = open("gamelog.txt", "a")

# Define a custom write function
def log_and_print(message):
    sys.__stdout__.write(message)  # Write to the terminal
    log_file.write(message)  # Write to the log file

# Redirect sys.stdout to the custom function
class CustomStdout:
    def write(self, message):
        log_and_print(message)

    def flush(self):
        sys.__stdout__.flush()
        log_file.flush()

sys.stdout = CustomStdout()

# Colors
BACKGROUND_COLOR = "#061826"  # Dark blue
TEXT_COLOR = "#FFFADB"       # Light cream
BUTTON_COLOR = "#6F94D6"     # Slightly darker light blue for better contrast
HOVER_COLOR = "#E38CA8"      # Pink

# Create the main window
window = ttk.Window(themename="darkly")
window.title("Game")
window.geometry("900x900")
window.configure(bg=BACKGROUND_COLOR)
autobuythread = None

# Create custom styles for different button states
def create_custom_styles():
    style = ttk.Style()
    
    # Maxed out style (red)
    style.configure(
        "Maxed.TButton",
        foreground="red",
        background="#FFB3B3",
        bordercolor="red"
    )
    
    # Buyable style (green)
    style.configure(
        "Buyable.TButton",
        foreground="green",
        background="#B3FFB3",
        bordercolor="green"
    )
    
    # Default style (blue)
    style.configure(
        "Default.TButton",
        foreground="#6F94D6",
        background="#D9E6FF",
        bordercolor="#6F94D6"
    )
    
# Create custom styles
create_custom_styles()

# Create the admin window
adminwindow = ttk.Window(themename="darkly")
adminwindow.title("Admin")
adminwindow.geometry("150x150")
adminwindow.configure(bg=BACKGROUND_COLOR)

# Update all buttons to use the custom style
def create_button(parent, text, command, row, column, padx=5, pady=5, width=None):
    button = ttk.Button(
        parent,
        text=text,
        command=command,
        bootstyle="primary-outline",  # Default style
        width=width
    )
    button.grid(row=row, column=column, padx=padx, pady=pady)
    return button

# Update the button style function
def update_button_style(button, state):
    if state == "maxed":
        button.configure(bootstyle="danger-outline")
    elif state == "buyable":
        button.configure(bootstyle="success-outline")
    else:
        button.configure(bootstyle="primary-outline")

# Update all labels to use the new color scheme
def create_label(parent, text, row, column, width=None, wraplength=None):
    label = ttk.Label(
        parent,
        text=text,
        background=BACKGROUND_COLOR,  # Dark blue background
        foreground=TEXT_COLOR,  # Light cream text
        wraplength=wraplength
    )
    label.grid(row=row, column=column, padx=5, pady=5)
    return label

#-Variables - > MAIN.
points = 0
pointpersecond = 1
multiplier = 1
multiplierstrength = 1
mulstrshow = 10
multraiser = 1
clickpower = 1
clicks = 0
#-Variables - > UPGRADES.
upgrade1cost = 10.0
buyamount1 = 0
upgrade1max = 25
#-
upgrade2cost = 100.0
buyamount2 = 0
upgrade2max = 10
#-
upgrade3cost = 10000.0
buyamount3 = 0
upgrade3max = 10
#-
upgrade4cost = 10000000 
buyamount4 = 0
upgrade4max = 5
#-
upgrade5complete = False
#-Variables - > PURIFICATION.
purifytimes = 0
maxpurify = 10
purifycost = 1000
purifydescriptions = ["Triples all point gain. For every purification afterwards, double all point gain.","For every purification, add one max level to upgrades 1 and 2.","For every purification, Reduce upgrades 1-3 cost by 5%","Increase upgrade 2 power by x3","Increase upgrade 3 power by +^0.01, making it ^0.06 per upgrade.","Gain (1+x)^2 x points, where x is the purification number.","No boost.","No boost. Maybe try again?","No boost. Next will be a new unlock, I promise.","Unlock Crystalline.",
                      "For every purification from now on, gain 2x clicks.","None.","None. x2","None. x3","Oh hey, the creator could be bothered to make something. Unlock crystalline 5."]
rank1booster = 1
rank2unlocked = False
rank3unlocked = False
rank3costmultiplier = 1
rank4upg2booster = 1
rank5upg3booster = 0
rank6unlocked = False
rank6booster = 1
#-Crystalline
crystallineunlocked = False
crystallinecost = 250000000
crystallinetimes = 0
maxcrystalline = 4
crystallinedescriptions = ["Triple point gain. Unlocks the 4th point upgrade.", "Point gain is raised to the ^1.5 power.","Autobuy point upgrades 1-3.","Unlocks clicking power.","Unlocks more purifications. Boosts points by playtime."]
cry1booster = 1
cry1upg4unlocked = False
cry2booster = 1
cry3unlocked = False
cry4unlocked = False
upgrade6complete = False
#-Variables - > Excess.
mpower = 1
currenttime = None
adminpanel = True
#-Endings
endings = ["K","M","B","T","Qa","Qi","Sx","Sp","Oc","No","Dc","Ud","Dd","Td","Qad","Qid","Sxd","Spd","Ocd","Nod","Vg"]
#-Formatting
def format_number(num):
    if num < 1000:
        return str(round(num, 2))
    count = 0
    while num >= 1000 and count < len(endings):
        num /= 1000
        count += 1
    return f"{num:.2f}{endings[count-1]}"

#-Point calculation.

def pointcalc():
    while True:
        global points, multiplier, pointpersecond, multiplierstrength, mpower
        pointpersecond = mpower 

        # Accumulate points in larger chunks to reduce CPU usage
        points += (pointpersecond / 2)  # 0.5 seconds worth of points
        points = round(points, 3)
        tm.sleep(0.5)  # Sleep for 0.5 seconds

# Track total playtime in seconds
total_playtime = 0

def track_playtime():
    global total_playtime
    while True:
        total_playtime += 1  # Increment playtime by 1 second
        tm.sleep(1)  # Wait for 1 second

def calculate_playtime_multiplier():
    global total_playtime
    minutes_played = total_playtime // 60  # Convert seconds to minutes

    # Define thresholds for multiplier increases
    if minutes_played < 10:
        return 1  # 1x multiplier for less than 10 minutes
    elif minutes_played < 100:
        return 2  # 2x multiplier for 10 to 100 minutes
    elif minutes_played < 600:
        return 3  # 3x multiplier for 100 to 600 minutes (1 hour 40 minutes)
    else:
        return 4 + (minutes_played // 600)  # Increase multiplier every 10 hours

#-Update UI using after() to ensure it runs on the main thread

def updateui():
    global mpower, multiplierstrength, multiplier, points, pointpersecond, upgrade1cost, buyamount1, upgrade2cost, buyamount2, upgrade3cost
    global buyamount3, mulstrshow, multraiser, rank1booster, rank6booster, cry1booster, cry4unlocked, clickpower, clicks, maxpurify
    global crystallinetimes, maxcrystalline, upgrade4cost, buyamount4, upgrade4max

    # Update Upgrade 1
    upgrade1label.configure(text=f"{format_number(upgrade1cost)} points")
    upgrade1explain.configure(text=f"+{format_number(multiplierstrength)} multipliers. [{format_number(buyamount1)}]")
    if buyamount1 >= upgrade1max:
        update_button_style(button1, "maxed")
    elif points >= upgrade1cost:
        update_button_style(button1, "buyable")
    else:
        update_button_style(button1, "default")

    # Update Upgrade 2
    upgrade2label.configure(text=f"{format_number(upgrade2cost)} points")
    upgrade2explain.configure(text=f"+{format_number(mulstrshow)}% multiplier strength. [{format_number(buyamount2)}] (^{multraiser})")
    if buyamount2 >= upgrade2max:
        update_button_style(button2, "maxed")
    elif points >= upgrade2cost:
        update_button_style(button2, "buyable")
    else:
        update_button_style(button2, "default")

    # Update Upgrade 3
    upgrade3label.configure(text=f"{format_number(upgrade3cost)} points")
    upgrade3explain.configure(text=f"Increase exponent by 0.05. [{format_number(buyamount3)}]")
    if buyamount3 >= upgrade3max:
        update_button_style(button3, "maxed")
    elif points >= upgrade3cost:
        update_button_style(button3, "buyable")
    else:
        update_button_style(button3, "default")

    # Update Upgrade 4
    upgrade4label.configure(text=f"{format_number(upgrade4cost)} points")
    upgrade4explain.configure(text=f"Increases max level of upgrade 3 by {format_number(buyamount4)}.")
    if buyamount4 >= upgrade4max:
        update_button_style(button4, "maxed")
    elif points >= upgrade4cost:
        update_button_style(button4, "buyable")
    else:
        update_button_style(button4, "default")

    # Update Upgrade 5
    if cry4unlocked:  # Add this check
        upgrade5label.configure(text="1K Clicks")
        button5.configure(text="Unlock")
        upgrade5explain.configure(text="Unlock purify 11-15 [C]")
    else:
        upgrade5label.configure(text="???")
        button5.configure(text="???")
        upgrade5explain.configure(text="???")

    # Update Click Button
    if cry4unlocked:
        clickbutton.configure(state="normal", text=f"Click Power: {format_number(clickpower)}")
    else:
        clickbutton.configure(state="disabled", text="Click Locked")

    # Update other UI elements
    pointlabel.configure(text=f"Current points: {format_number(points)}")
    pointpersecondlabel.configure(text=f"Points per second: {format_number(pointpersecond)}")
    clicklabel.configure(text=f"Clicks: {format_number(clicks)}")

    # Update crystalline label
    if crystallinetimes < len(crystallinedescriptions):
        if upgrade5complete and crystallinetimes == 4:
            # Show crystalline 5 only if upgrade 5 is complete
            crystalinelabel.configure(text=f"Next: {crystallinedescriptions[4]} ({format_number(crystallinecost)} points)")
        elif crystallinetimes < 4:
            # Show crystallines 1-4 normally
            crystalinelabel.configure(text=f"Next: {crystallinedescriptions[crystallinetimes]} ({format_number(crystallinecost)} points)")
        else:
            crystalinelabel.configure(text="Maximum crystallines complete!")
    else:
        crystalinelabel.configure(text="All crystallines complete!")

    # Update purification label with proper description range
    if purifytimes < len(purifydescriptions):
        if upgrade5complete and purifytimes >= 10:
            # Show purifications 11-15 after upgrade 5 is complete
            purificationlabel.configure(text=f"Next: {purifydescriptions[purifytimes]} ({format_number(purifycost)} points)")
        elif purifytimes < 10:
            # Show normal purifications 1-10
            purificationlabel.configure(text=f"Next: {purifydescriptions[purifytimes]} ({format_number(purifycost)} points)")
        else:
            purificationlabel.configure(text="Maximum purifications completed!")
    else:
        purificationlabel.configure(text="All purifications complete!")

    # Schedule the next update less frequently
    window.after(200, updateui)  # Run updateui every 200ms

#-Definitions.

def upgrade1():
    global points, multiplier, upgrade1cost, buyamount1, upgrade1max
    if points >= upgrade1cost:
        if buyamount1 <= upgrade1max:
            points -= upgrade1cost
            buyamount1 += 1
            upgrade1cost = round((upgrade1cost * (1+(buyamount1/10))) * rank3costmultiplier, 2)
            multiplier += 1
            print(f"INFO: Upgraded! Current multiplier: {multiplier}")
            print(f"{buyamount1} / {upgrade1max} upgrades!")
        else:
            warn.warn("WARNING: Upgrade maxed out.")
            print(f"{buyamount1} / {upgrade1max} upgrades!")
    else:
        warn.warn("WARNING: Not enough points to upgrade.")
        print(f"{buyamount1} / {upgrade1max} upgrades!")

def recalculate_multiplier_strength():
    global multiplierstrength, buyamount2, multraiser
    base = (1 + (buyamount2 * 0.1)) * rank4upg2booster
    multiplierstrength = round(base ** multraiser, 3)

def upgrade2():
    global points, multiplierstrength, upgrade2cost, buyamount2, upgrade2max
    if points >= upgrade2cost:
        if buyamount2 < upgrade2max:
            points -= upgrade2cost
            buyamount2 += 1
            upgrade2cost = round((upgrade2cost * (1+(buyamount2/10))) * rank3costmultiplier, 2)
            recalculate_multiplier_strength()
            print(f"INFO: Upgraded! Current multiplier strength: {multiplierstrength}")
            print(f"{buyamount2} / {upgrade2max} upgrades!")
        else:
            warn.warn("WARNING: Upgrade maxed out.")
            print(f"{buyamount2} / {upgrade2max} upgrades!")
    else:
        warn.warn("WARNING: Not enough points to upgrade.")
        print(f"{buyamount2} / {upgrade2max} upgrades!")

def upgrade3():
    global points, multraiser, upgrade3cost, buyamount3, multiplierstrength
    if points >= upgrade3cost:
        if buyamount3 < upgrade3max:
            points -= upgrade3cost
            buyamount3 += 1
            upgrade3cost = round((upgrade3cost * (1+(buyamount3/10))) * rank3costmultiplier, 2)
            multraiser += (0.05 + rank5upg3booster)
            recalculate_multiplier_strength()
            print(f"INFO: Upgraded! Current multiplier raiser: {multraiser}")
            print(f"{buyamount3} / {upgrade3max} upgrades!")
        else:
            warn.warn("WARNING: Upgrade maxed out.")
            print(f"{buyamount3} / {upgrade3max} upgrades!")
    else:
        warn.warn("WARNING: Not enough points to upgrade.")
        print(f"{buyamount3} / {upgrade3max} upgrades!")

def upgrade4():
    global points, cry1upg4unlocked, upgrade4cost, upgrade4max, buyamount4, upgrade3max
    if cry1upg4unlocked:
        if upgrade4max >= buyamount4:
            if points >= upgrade4cost:
                points -= upgrade4cost
                buyamount4 += 1
                upgrade4cost = round((upgrade4cost * (1.25+(buyamount4/10))), 2)
                upgrade3max += 1
                print(f"INFO: Upgraded! Current upgrade 3 max: {upgrade3max}")
                print(f"{buyamount4} / {upgrade4max} upgrades!")
            else:
                warn.warn("WARNING: Not enough points to upgrade.")
                print(f"{buyamount4} / {upgrade4max} upgrades!")
        else:
            warn.warn("WARNING: Upgrade maxed out.")
            print(f"{buyamount4} / {upgrade4max} upgrades!")
    else:
        warn.warn("WARNING: This upgrade is not unlocked.")

#Purification

def purify():
    global points, purifytimes, purifycost, multiplier, multiplierstrength, upgrade1cost, upgrade2cost
    global upgrade3cost, buyamount1, buyamount2, buyamount3, multraiser, rank1booster, rank2unlocked
    global rank3costmultiplier, rank4upg2booster, rank5upg3booster, upgrade1max, upgrade2max, upgrade3max, rank3unlocked, rank6unlocked,rank6booster, crystallineunlocked
    global maxpurify

    if points >= purifycost:
        if purifytimes < len(purifydescriptions) or maxpurify == purifytimes:
            points -= purifycost

            # Apply purification effects based on rank
            if purifytimes >= 0:
                if rank1booster == 1:
                    rank1booster = 3
                else:
                    rank1booster *= 2

            if purifytimes >= 1:
                rank2unlocked = True
            if purifytimes >= 2 or rank3unlocked:
                rank3unlocked = True
                rank3costmultiplier -= 0.05
                if purifytimes == 10:
                    rank3unlocked = False
            if purifytimes >= 3:
                rank4upg2booster = 3  
            if purifytimes >= 4:
                rank5upg3booster = 0.01  
            if purifytimes >= 5:
                rank6unlocked = True

            if purifytimes >= 9:
                crystallineunlocked = True

            if rank2unlocked:
                upgrade1max += 1
                upgrade2max += 1

            if rank6unlocked:
                rank6booster = (1+purifytimes)**2
            # Reset mechanics
            points = 0
            multiplier = 1
            upgrade1cost = 10.0
            upgrade2cost = 100.0
            upgrade3cost = 10000.0
            buyamount1 = 0
            buyamount2 = 0
            buyamount3 = 0
            multiplierstrength = 1
            multraiser = 1

            purifycost = round(purifycost * (3+purifytimes), 2)
            if purifytimes == 9:
                purifycost == 1e15
            purifytimes += 1
            print(f"INFO: Purified! Current purification times: {purifytimes}")
        else:
            warn.warn("WARNING: All purifications completed!")
    else:
        warn.warn("WARNING: Not enough points to purify.")

def adminpurify():
    global points, purifytimes, purifycost, multiplier, multiplierstrength, upgrade1cost, upgrade2cost
    global upgrade3cost, buyamount1, buyamount2, buyamount3, multraiser, rank1booster, rank2unlocked
    global rank3costmultiplier, rank4upg2booster, rank5upg3booster, upgrade1max, upgrade2max, upgrade3max, rank3unlocked, rank6unlocked,rank6booster, crystallineunlocked
    points -= purifycost

    # Apply purification effects based on rank
    if purifytimes >= 0:
        if rank1booster == 1:
            rank1booster = 3
        else:
            rank1booster *= 2
        if purifytimes >= 1:
            rank2unlocked = True
        if purifytimes >= 2 or rank3unlocked:
            rank3unlocked = True
            rank3costmultiplier -= 0.05
        if purifytimes == 10:
            rank3unlocked = False
        if purifytimes >= 3:
            rank4upg2booster = 3  
        if purifytimes >= 4:
            rank5upg3booster = 0.01  
        if purifytimes >= 5:
            rank6unlocked = True

        if purifytimes >= 9:
            crystallineunlocked = True

        if rank2unlocked:
            upgrade1max += 1
            upgrade2max += 1

        if rank6unlocked:
            rank6booster = (1+purifytimes)**2
        # Reset mechanics
        points = 0
        multiplier = 1
        upgrade1cost = 10.0
        upgrade2cost = 100.0
        upgrade3cost = 10000.0
        buyamount1 = 0
        buyamount2 = 0
        buyamount3 = 0
        multiplierstrength = 1
        multraiser = 1

        purifycost = round(purifycost * (3+purifytimes), 2)
        print(f"INFO: Purified! Current purification times: {purifytimes}")

#Crystalline


def crystalline():
    global points, purifytimes, purifycost, multiplier, multiplierstrength, upgrade1cost, upgrade2cost
    global upgrade3cost, buyamount1, buyamount2, buyamount3, multraiser, rank1booster, rank2unlocked
    global rank3costmultiplier, rank4upg2booster, rank5upg3booster, upgrade1max, upgrade2max, upgrade3max
    global rank3unlocked, rank6unlocked, rank6booster, crystallineunlocked, crystallinetimes, cry1booster, cry1upg4unlocked
    global cry2booster, cry3unlocked, crystallinecost, upgrade4cost, buyamount4, upgrade4max, cry4unlocked, maxcrystalline, autobuythread
    
    if crystallineunlocked:
        if points >= crystallinecost:
            if crystallinetimes < len(crystallinedescriptions) or maxcrystalline == crystallinetimes:
                points -= crystallinecost
                crystallinetimes += 1
                if crystallinetimes == 1:
                    cry1booster = 3  
                    cry1upg4unlocked = True                 
                if crystallinetimes == 2:
                    cry2booster = 1.5
                if crystallinetimes == 3:
                    cry3unlocked = True
                    if autobuythread is None or not autobuythread.is_alive():
                        autobuythread = th.Thread(target=autobuy, daemon=True)
                        autobuythread.start()
                if crystallinetimes == 4:
                    cry4unlocked = True
                points = 0
                multiplier = 1
                upgrade1cost = 10.0
                upgrade2cost = 100.0
                upgrade3cost = 10000.0
                upgrade4cost = 10000000
                buyamount1 = 0
                buyamount2 = 0
                buyamount3 = 0
                buyamount4 = 0
                upgrade1max = 25
                upgrade2max = 10
                upgrade3max = 10
                upgrade4max = 5
                multiplierstrength = 1
                multraiser = 1
                purifytimes = 0
                purifycost = 1000
                rank1booster = 1
                rank2unlocked = False
                rank3unlocked = False
                rank3costmultiplier = 1
                rank4upg2booster = 1
                rank5upg3booster = 0
                rank6unlocked = False
                rank6booster = 1
                crystallineunlocked = False
                crystallinecost *= (10+((crystallinetimes+1)**2))
                if crystallinetimes == 4:
                    crystallinecost = 1e20

                print(f"INFO: Crystallized! Current crystalline times: {crystallinetimes}")
            else:
                warn.warn("WARNING: All crystallines completed!")
        else:
            warn.warn("WARNING: Not enough points to crystalline!")
    else:
        warn.warn("WARNING: Crystalline is locked!")


#-Upgrade 5

def upgrade5():
    global clicks, maxpurify, upgrade5complete
    if clicks >= 1000:
        if not upgrade5complete:
            clicks -= 1000
            maxpurify = 15
            upgrade5complete = True
            print("INFO: Upgrade 5 complete!")
        else:
            warn.warn("WARNING: Upgrade 5 already bought!")
    else: 
        warn.warn("WARNING: Not enough click power to upgrade.")

#-Upgrade 6

def upgrade6():
    global clicks, upgrade6complete, maxcrystalline
    if not upgrade6complete:
        if clicks >= 100000:
            maxcrystalline == 5
        else:
            warn.warn("WARNING: You cannot afford this!")
    else:
        warn.warn("WARNING: You have already bought this!")
#-Currency labels.

pointlabel = create_label(window, f"Current points: {points}", row=0, column=0, wraplength=200)
pointpersecondlabel = create_label(window, f"Points per second: {pointpersecond}", row=1, column=0, wraplength=200)
clicklabel = create_label(window, "null", row=2, column=0, wraplength=200)

#-Purification labels.

purificationlabel = create_label(window, "null", row=0, column=1, wraplength=200)
purificationbutton = create_button(window, "Purify", command=purify, row=0, column=2)

#Crystalline labels.

crystalinelabel = create_label(window, "null", row=0, column=3, wraplength=200)
crystalinebutton = create_button(window, "Crystalline", command=crystalline, row=0, column=4)

#-Upgrade1 tkinter things.

upgrade1label = create_label(window, f"{upgrade1cost} points", row=1, column=1, wraplength=200)
button1 = create_button(window, "Upgrade", command=upgrade1, row=1, column=2)
upgrade1explain = create_label(window, f"+{multiplierstrength} multipliers. [{buyamount1}]", row=1, column=3, wraplength=200)

#-Upgrade2 tkinter things.

upgrade2label = create_label(window, f"{upgrade2cost} points", row=2, column=1, wraplength=200)
button2 = create_button(window, "Upgrade", command=upgrade2, row=2, column=2)
upgrade2explain = create_label(window, f"+{mulstrshow}% multiplier strength. [{buyamount2}] (^{multraiser})", row=2, column=3, wraplength=200)

#-Upgrade3 tkinter things.

upgrade3label = create_label(window, f"{upgrade3cost} points", row=3, column=1, wraplength=200)
button3 = create_button(window, "Upgrade", command=upgrade3, row=3, column=2)
upgrade3explain = create_label(window, f"Increase exponent by 0.05. [{buyamount3}]", row=3, column=3, wraplength=200)

#-Upgrade4 tkinter things.

upgrade4label = create_label(window, f"{upgrade4cost}", row=4, column=1, wraplength=200)
button4 = create_button(window, "Upgrade", command=upgrade4, row=4, column=2)
upgrade4explain = create_label(window, f"Increases max level of upgrade 3 by {format_number(buyamount4)}.", row=4, column=3, wraplength=200)

#-Upgrade5 tkinter things.

upgrade5label = create_label(window, text="???", row=6, column=1, wraplength=200)
button5 = create_button(window, "???", command=upgrade5, row=6, column=2)
upgrade5explain = create_label(window, text="???", row=6, column=3, wraplength=200)

#Clicking powers.
def click_power():
    global cry4unlocked, clickpower, clicks
    if cry4unlocked:
        clicks += clickpower

# Set a fixed width for the click power button
clickbutton = create_button(window, "Click", command=click_power, row=5, column=2, width=20)

def restart_autobuy_thread():
    global autobuythread
    while True:
        if autobuythread is None or not autobuythread.is_alive():
            autobuythread = th.Thread(target=autobuy, daemon=True)
            autobuythread.start()
            print("INFO: Autobuy thread restarted.")
        tm.sleep(1)

#-Admin window.

#sets a currency to a value

def setcurrency():
    global points, adminpanel
    if adminpanel:
        try:
            points = float(setcurrencyentry.get())
            print(f"INFO: Set currency to {points}")
        except ValueError:
            warn.warn("WARNING: Invalid value.")

setcurrencyentry = tk.Entry(adminwindow, width=10, bg=BUTTON_COLOR, fg=TEXT_COLOR)
setcurrencyentry.grid(row=0, column=0, padx=5, pady=5)

setcurrencybutton = create_button(adminwindow, "Set Points", command=setcurrency, row=0, column=1)

def setpurification():
    global purifytimes, adminpanel
    if adminpanel:
        try:
            purifytimes = int(setpurificationentry.get())
            print(f"INFO: Set purification times to {purifytimes}")
        except ValueError:
            warn.warn("WARNING: Invalid value.")

setpurificationentry = tk.Entry(adminwindow, width=10, bg=BUTTON_COLOR, fg=TEXT_COLOR)
setpurificationentry.grid(row=1, column=0, padx=5, pady=5)

setpurificationbutton = create_button(adminwindow, "Set Purification", command=setpurification, row=1, column=1)

#-Autobuyers

# Update the autobuy function with exception handling
def autobuy():
    global points, upgrade1cost, upgrade2cost, upgrade3cost, upgrade4cost
    global buyamount1, buyamount2, buyamount3, buyamount4
    global upgrade1max, upgrade2max, upgrade3max, upgrade4max, cry3unlocked
    global multiplier, rank3costmultiplier, multraiser, rank5upg3booster, cry1upg4unlocked

    print("INFO: Autobuyer thread started")
    
    while True:
        try:
            if cry3unlocked:  # Only run if crystalline 3 is unlocked
                # Autobuy Upgrade 1
                if points >= upgrade1cost and buyamount1 < upgrade1max:
                    points -= upgrade1cost
                    buyamount1 += 1
                    upgrade1cost = round((upgrade1cost * (1 + (buyamount1 / 10))) * rank3costmultiplier, 2)
                    multiplier += 1

                # Autobuy Upgrade 2
                if points >= upgrade2cost and buyamount2 < upgrade2max:
                    points -= upgrade2cost
                    buyamount2 += 1
                    upgrade2cost = round((upgrade2cost * (1 + (buyamount2 / 10))) * rank3costmultiplier, 2)
                    recalculate_multiplier_strength()

                # Autobuy Upgrade 3
                if points >= upgrade3cost and buyamount3 < upgrade3max:
                    points -= upgrade3cost
                    buyamount3 += 1
                    upgrade3cost = round((upgrade3cost * (1 + (buyamount3 / 10))) * rank3costmultiplier, 2)
                    multraiser += (0.05 + rank5upg3booster)
                    recalculate_multiplier_strength()

                # Autobuy Upgrade 4
                if cry1upg4unlocked and points >= upgrade4cost and buyamount4 < upgrade4max:
                    points -= upgrade4cost
                    buyamount4 += 1
                    upgrade4cost = round((upgrade4cost * (1.25 + (buyamount4 / 10))), 2)
                    upgrade3max += 1

            tm.sleep(1)  # Sleep for 1 second to reduce CPU usage
        except Exception as e:
            print(f"ERROR: Exception in autobuy thread: {e}")
            break  # Exit the loop if an exception occurs

# Ensure all functions are defined before initializing threads
def save():
    global currenttime
    with open("save.txt", "w") as f:
        f.write(f"{points}:{pointpersecond}:{multiplier}:{multiplierstrength}:{mpower}:{upgrade1cost}:{buyamount1}:{upgrade2cost}:{buyamount2}:{upgrade3cost}:{buyamount3}:{multraiser}:{purifytimes}:{purifycost}:{rank1booster}:{rank2unlocked}:{rank3costmultiplier}:{rank3unlocked}:{rank4upg2booster}:{rank5upg3booster}:{rank6unlocked}:{rank6booster}:{upgrade1max}:{upgrade2max}:{upgrade3max}:{crystallineunlocked}:{crystallinetimes}:{crystallinecost}:{cry1booster}:{cry1upg4unlocked}:{cry2booster}:{cry3unlocked}:{clickpower}:{clicks}:{buyamount4}:{upgrade4cost}:{cry4unlocked}:{maxcrystalline}:{upgrade5complete}:{upgrade6complete}")
    print(f"INFO: Saved at {currenttime}.")

def savewaiter():
    global currenttime
    while True:
        tm.sleep(30)
        currenttime = dt.datetime.now().strftime("%H:%M:%S")
        print(f"INFO: Attempted save at {currenttime}.")
        save()

# Ensure all threads are properly started
try:
    pointcalcthread = th.Thread(target=pointcalc, daemon=True)
    pointcalcthread.start()

    savethread = th.Thread(target=savewaiter, daemon=True)
    savethread.start()

    testforautobuythread = th.Thread(target=restart_autobuy_thread, daemon=True)
    testforautobuythread.start()

    playtime_thread = th.Thread(target=track_playtime, daemon=True)
    playtime_thread.start()
except Exception as e:
    print(f"ERROR: Failed to start threads: {e}")

# Start the UI update loop using after()
window.after(50, updateui)

# Ensure window.mainloop() is at the end
window.mainloop()

#-Save and load functions.
def load2():
    global points, pointpersecond, multiplier, multiplierstrength, mpower, upgrade1cost, buyamount1
    global upgrade2cost, buyamount2, upgrade3cost, buyamount3, multraiser, purifytimes, purifycost
    global rank1booster, rank2unlocked, rank3costmultiplier, rank3unlocked, rank4upg2booster
    global rank5upg3booster, rank6unlocked, rank6booster, upgrade1max, upgrade2max, upgrade3max
    global crystallineunlocked, crystallinetimes, crystallinecost, cry1upg4unlocked, cry1booster
    global cry2booster, cry3unlocked, cry4unlocked, maxpurify, upgrade5complete, autobuythread

    if purifytimes >= 1:
        rank2unlocked = True
    if purifytimes >= 2 or rank3unlocked:
        rank3unlocked = True
        if purifytimes == 10:
            rank3unlocked = False 
    if purifytimes >= 5:
        rank6unlocked = True

    if purifytimes >= 9:
        crystallineunlocked = True
    if rank6unlocked:
        rank6booster = (1+purifytimes)**2
    if crystallinetimes == 1: 
        cry1upg4unlocked = True                 
    if crystallinetimes == 3:
        cry3unlocked = True
        if autobuythread is None or not autobuythread.is_alive():
            autobuythread = th.Thread(target=autobuy, daemon=True)
            autobuythread.start()
    if crystallinetimes == 4:
        cry4unlocked = True

    # Add this section to handle upgrade 5
    if upgrade5complete:
        maxpurify = 15  # Set max purify to 15 if upgrade was completed
    if crystallinetimes >= 3:
        cry3unlocked = True
        try:
            if autobuythread is None:
                autobuythread = th.Thread(target=autobuy, daemon=True)
                autobuythread.start()
            elif not autobuythread.is_alive():
                autobuythread = th.Thread(target=autobuy, daemon=True)
                autobuythread.start()
        except Exception as e:
            print(f"WARNING: Error starting autobuyer thread: {e}")

def savewaiter():
    global currenttime
    while True:
        tm.sleep(30)
        currenttime = dt.datetime.now().strftime("%H:%M:%S")
        print(f"INFO: Attempted save at {currenttime}.")
        save()


def save():
    with open("save.txt", "w") as f:
        f.write(f"{points}:{pointpersecond}:{multiplier}:{multiplierstrength}:{mpower}:{upgrade1cost}:{buyamount1}:{upgrade2cost}:{buyamount2}:{upgrade3cost}:{buyamount3}:{multraiser}:{purifytimes}:{purifycost}:{rank1booster}:{rank2unlocked}:{rank3costmultiplier}:{rank3unlocked}:{rank4upg2booster}:{rank5upg3booster}:{rank6unlocked}:{rank6booster}:{upgrade1max}:{upgrade2max}:{upgrade3max}:{crystallineunlocked}:{crystallinetimes}:{crystallinecost}:{cry1booster}:{cry1upg4unlocked}:{cry2booster}:{cry3unlocked}:{clickpower}:{clicks}:{buyamount4}:{upgrade4cost}:{cry4unlocked}:{maxcrystalline}:{upgrade5complete}:{upgrade6complete}")
    print(f"INFO: Saved at {currenttime}.")

def load():
    try:
        with open("save.txt", "r") as f:
            data = f.read().split(":")
            global points, pointpersecond, multiplier, multiplierstrength, mpower, upgrade1cost, buyamount1
            global upgrade2cost, buyamount2, upgrade3cost, buyamount3, multraiser, purifytimes, purifycost
            global rank1booster, rank2unlocked, rank3costmultiplier, rank3unlocked, rank4upg2booster
            global rank5upg3booster, rank6unlocked, rank6booster, upgrade1max, upgrade2max, upgrade3max, crystallineunlocked, crystallinetimes, crystallinecost, cry1upg4unlocked, cry1booster, buyamount4, upgrade4cost, cry4unlocked
            global cry2booster, cry3unlocked, clickpower, clicks, maxcrystalline, upgrade5complete, upgrade6complete

            # Load all variables from the save file
            points = float(data[0])
            pointpersecond = float(data[1])
            multiplier = float(data[2])
            multiplierstrength = float(data[3])
            mpower = float(data[4])
            upgrade1cost = float(data[5])
            buyamount1 = int(data[6])
            upgrade2cost = float(data[7])
            buyamount2 = int(data[8])
            upgrade3cost = float(data[9])
            buyamount3 = int(data[10])
            multraiser = float(data[11])
            purifytimes = int(data[12])
            purifycost = float(data[13])
            rank1booster = float(data[14])
            rank2unlocked = data[15].lower() == "true"
            rank3costmultiplier = float(data[16])
            rank3unlocked = data[17].lower() == "true"
            rank4upg2booster = float(data[18])
            rank5upg3booster = float(data[19])
            rank6unlocked = data[20].lower() == "true"
            rank6booster = float(data[21])
            upgrade1max = int(data[22])
            upgrade2max = int(data[23])
            upgrade3max = int(data[24])
            crystallineunlocked = data[25].lower() == "true"
            crystallinetimes = int(data[26])
            crystallinecost = float(data[27])
            cry1booster = float(data[28])
            cry1upg4unlocked = data[29].lower() == "true"
            cry2booster = float(data[30])
            cry3unlocked = data[31].lower() == "true"
            clickpower = float(data[32])
            clicks = float(data[33])
            buyamount4 = int(data[34])
            upgrade4cost = float(data[35])
            cry4unlocked = data[36].lower() == "true"
            maxcrystalline = int(data[37])
            upgrade5complete = data[38].lower() == "true"
            upgrade6complete = data[39].lower() == "true"

            print("INFO: Loaded save data.")

            # Ensure autobuy thread is started if cry3unlocked is true
            if cry3unlocked:
                restart_autobuy_thread()

            # Update the UI elements after loading
            update_ui_after_load()

    except Exception as e:
        print(f"WARNING: No save file found or corrupted save. Error: {e}")
        # Initialize variables with default values if save file is missing or corrupted
        load2()

def update_ui_after_load():
    # Update purification label
    if purifytimes < len(purifydescriptions) and purifytimes < maxpurify:
        purificationlabel.configure(text=f"Next: {purifydescriptions[purifytimes]} ({format_number(purifycost)} points)")
    elif purifytimes == len(purifydescriptions) and purifytimes <= maxpurify:
        purificationlabel.configure(text="All purifications complete!")
    elif purifytimes == maxpurify:
        purificationlabel.configure(text="Maximum purifications completed!")

    # Update crystalline label
    if crystallinetimes < len(crystallinedescriptions) and maxcrystalline >= crystallinetimes:
        crystalinelabel.configure(text=f"Next: {crystallinedescriptions[crystallinetimes]} ({format_number(crystallinecost)} points)")
    elif crystallinetimes < len(crystallinedescriptions) and maxcrystalline < crystallinetimes:
        crystalinelabel.configure(text="Maximum crystallines complete!")
    else:
        crystalinelabel.configure(text="All crystallines complete!")

    # Update click upgrade
    if cry4unlocked:
        clickbutton.configure(state="normal", text=f"Click Power: {format_number(clickpower)}")
        clicklabel.configure(text=f"Clicks: {format_number(clicks)}")
    else:
        clickbutton.configure(state="disabled", text="Click Locked")
        
    # Update other UI elements
    pointlabel.configure(text=f"Current points: {format_number(points)}")
    pointpersecondlabel.configure(text=f"Points per second: {format_number(pointpersecond)}")
    clicklabel.configure(text=f"Clicks: {format_number(clicks)}")

#-Load save data
load()

#-Threads.

pointcalcthread = th.Thread(target=pointcalc)
pointcalcthread.start()

savethread = th.Thread(target=savewaiter)
savethread.start()

testforautobuythread = th.Thread(target=restart_autobuy_thread())
testforautobuythread.start()

# Start the playtime tracker threade
playtime_thread = th.Thread(target=track_playtime)
playtime_thread.daemon = True  # Ensure the thread exits when the program ends
playtime_thread.start()

# Start the UI update loop using after()
window.after(50, updateui)

# Ensure window.mainloop() is at the end
window.mainloop()
