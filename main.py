#-Imports.
import tkinter as tk
import threading as th
import time as tm
import warnings as warn
import datetime as dt
import math as ma
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
purifydescriptions = ["Triples all point gain. For every purification afterwards, double all point gain.","For every purification, add one max level to upgrades 1 and 2.","For every purification, Reduce upgrades 1-3 cost by 5%","Increase upgrade 2 power by x3","Increase upgrade 3 power by +^0.01, making it ^0.06 per upgrade.","Gain (1+x)^2 x points, where x is the purification number.","No boost.","No boost. Maybe try again?","No boost. Next will be a new unlock, I promise.","Unlock Crystalline."]
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
crystallinedescriptions = ["Triple point gain. Unlocks the 4th point upgrade.", "Point gain is raised to the ^1.5 power.","Autobuy point upgrades 1-3.","Unlocks clicking power."]
cry1booster = 1
cry1upg4unlocked = False
cry2booster = 1
cry3unlocked = False
cry4unlocked = False
#-Variables - > Excess.
mpower = 1
currenttime = None
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

#-Creates a window.
window = tk.Tk()
window.title("test")
window.geometry("900x900")
window.configure(bg="black")
#-Admin window.
adminwindow = tk.Tk()
adminwindow.title("Admin")
adminwindow.geometry("150x150")
adminwindow.configure(bg="black")
#-Point calculation.

def pointcalc():
    while True:
        global points, multiplier, pointpersecond, multiplierstrength, mpower
        pointpersecond = mpower 

        count = 0
        while count < 5:
            count+=1
            points += pointpersecond / 20 #-Divide by 20 -> 50ms sleep -> 1 point / s
            points = round(points, 3) 
            tm.sleep(0.05)

#-Update UI.

def updateui():
    global mpower,multiplierstrength, multiplier, points, pointpersecond, upgrade1cost, buyamount1, upgrade2cost, buyamount2, upgrade3cost, buyamount3, mulstrshow, multraiser, rank1booster, rank6booster, cry1booster, cry4unlocked, clickpower, clicks, maxpurify
    while True:
        #-Variable calculation.
        mulstrshow = (multiplierstrength * 100) - 100
        mulstrshow = round(mulstrshow, 2)
        multiplier = round(multiplier, 2)
        multraiser = round(multraiser, 2)
        mpower = ((rank1booster * rank6booster) * (multiplierstrength * multiplier) * cry1booster) ** cry2booster 
        mpower = round(mpower, 2)
        clickpower = round(((ma.log2(points / 1e15) / (2+ma.log10(clickpower)))),2)
        #UPGRADE 1
        upgrade1label.configure(text=f"{format_number(upgrade1cost)} points")
        pointlabel.configure(text=f"Current points: {format_number(points)}")
        pointpersecondlabel.configure(text=f"Points per second: {format_number(pointpersecond)}")
        upgrade1explain.configure(text=f"+{format_number(multiplierstrength)} multipliers. [{format_number(buyamount1)}]")
        #UPGRADE 2
        upgrade2label.configure(text=f"{format_number(upgrade2cost)} points")
        upgrade2explain.configure(text=f"+{format_number(mulstrshow)}% multiplier strength. [{format_number(buyamount2)}] (^{multraiser})")
        #UPGRADE 3
        upgrade3label.configure(text=f"{format_number(upgrade3cost)} points")
        upgrade3explain.configure(text=f"Increase exponent by 0.05. [{format_number(buyamount3)}]")
        #UPGRADE 4
        upgrade4label.configure(text=f"{format_number(upgrade4cost)} points [P]")
        upgrade4explain.configure(text=f"Increases maximum upgrade 3's by 1 [{format_number(buyamount4)}]")
        # Update purification label with current description
        if purifytimes < len(purifydescriptions) and purifytimes < maxpurify:
            purificationlabel.configure(text=f"Next: {purifydescriptions[purifytimes]} ({format_number(purifycost)} points)")
        elif purifytimes == len(purifydescriptions) and purifytimes <= maxpurify:
            purificationlabel.configure(text="All purifications complete!")
        elif purifytimes == maxpurify:
            purificationlabel.configure(text="Maximum purifications completed!")
        # Update crystalline label with current description
        if crystallinetimes < len(crystallinedescriptions):
            crystalinelabel.configure(text=f"Next: {crystallinedescriptions[crystallinetimes]} ({format_number(crystallinecost)} points)")
        else:
            crystalinelabel.configure(text="All crystallines complete!")
        # Update click button text
        if cry4unlocked:
            clickbutton.configure(text=f"Gain {clickpower} click power [C]")
            clicklabel.configure(text=f"Clicks: {format_number(clicks)}")
            upgrade5label.configure(text="1K P")
            button5.configure(text="Unlock")
            upgrade5explain.configure(text="Unlock purify 11-15 [C]")
        tm.sleep(0.05)

#-Definitions.

def upgrade1():
    global points, multiplier, upgrade1cost, buyamount1, upgrade1max
    print(f"{buyamount1} / {upgrade1max} upgrades!")
    if points >= upgrade1cost:
        if buyamount1 <= upgrade1max:
            points -= upgrade1cost
            buyamount1 += 1
            upgrade1cost = round((upgrade1cost * (1+(buyamount1/10))) * rank3costmultiplier, 2)
            multiplier += 1
            print(f"INFO: Upgraded! Current multiplier: {multiplier}")
        else:
            warn.warn("WARNING: Upgrade maxed out.")
    else:
        warn.warn("WARNING: Not enough points to upgrade.")

def recalculate_multiplier_strength():
    global multiplierstrength, buyamount2, multraiser
    base = (1 + (buyamount2 * 0.1)) * rank4upg2booster
    multiplierstrength = round(base ** multraiser, 3)

def upgrade2():
    global points, multiplierstrength, upgrade2cost, buyamount2, upgrade2max
    print(f"{buyamount2} / {upgrade2max} upgrades!")
    if points >= upgrade2cost:
        if buyamount2 < upgrade2max:
            points -= upgrade2cost
            buyamount2 += 1
            upgrade2cost = round((upgrade2cost * (1+(buyamount2/10))) * rank3costmultiplier, 2)
            recalculate_multiplier_strength()
            print(f"INFO: Upgraded! Current multiplier strength: {multiplierstrength}")
        else:
            warn.warn("WARNING: Upgrade maxed out.")
    else:
        warn.warn("WARNING: Not enough points to upgrade.")

def upgrade3():
    global points, multraiser, upgrade3cost, buyamount3, multiplierstrength
    print(f"{buyamount3} / {upgrade3max} upgrades!")
    if points >= upgrade3cost:
        if buyamount3 < upgrade3max:
            points -= upgrade3cost
            buyamount3 += 1
            upgrade3cost = round((upgrade3cost * (1+(buyamount3/10))) * rank3costmultiplier, 2)
            multraiser += (0.05 + rank5upg3booster)
            recalculate_multiplier_strength()
            print(f"INFO: Upgraded! Current multiplier raiser: {multraiser}")
        else:
            warn.warn("WARNING: Upgrade maxed out.")
    else:
        warn.warn("WARNING: Not enough points to upgrade.")

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
            else:
                warn.warn("WARNING: Not enough points to upgrade.")
        else:
            warn.warn("WARNING: Upgrade maxed out.")
    else:
        warn.warn("WARNING: This upgrade is not unlocked.")

#Purification

def purify():
    global points, purifytimes, purifycost, multiplier, multiplierstrength, upgrade1cost, upgrade2cost
    global upgrade3cost, buyamount1, buyamount2, buyamount3, multraiser, rank1booster, rank2unlocked
    global rank3costmultiplier, rank4upg2booster, rank5upg3booster, upgrade1max, upgrade2max, upgrade3max, rank3unlocked, rank6unlocked,rank6booster, crystallineunlocked

    if points >= purifycost:
        if purifytimes < len(purifydescriptions):
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
    global cry2booster, cry3unlocked, crystallinecost,upgrade4cost, buyamount4,upgrade4max, cry4unlocked
    if crystallineunlocked:
        if points >= crystallinecost:
            if crystallinetimes < len(crystallinedescriptions):
                points -= crystallinecost
                crystallinetimes += 1
                if crystallinetimes == 1:
                    cry1booster = 3  
                    cry1upg4unlocked = True                 
                if crystallinetimes == 2:
                    cry2booster = 1.5
                if crystallinetimes == 3:
                    cry3unlocked = True
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
            maxpurify = 15
            upgrade5complete = True
            print("INFO: Upgrade 5 complete!")
        else:
            warn.warn("WARNING: Upgrade 5 already complete!")
    else: 
        warn.warn("WARNING: Not enough click power to upgrade.")
    
#-Currency labels.

pointlabel = tk.Label(window, text=f"Current points: {points}")
pointlabel.grid(row=0, column=0, padx=5, pady=5)
pointlabel.configure(width=30, height=2)

pointpersecondlabel = tk.Label(window, text=f"Points per second: {pointpersecond}")
pointpersecondlabel.grid(row=1, column=0, padx=5, pady=5)
pointpersecondlabel.configure(width=30, height=1)

clicklabel = tk.Label(window, text="null")
clicklabel.grid(row=2, column=0, padx=5, pady=5)
clicklabel.configure(width=30, height=1)

#-Purification labels.

purificationlabel = tk.Label(window, text="null", wraplength=200) 
purificationlabel.grid(row=0, column=1, padx=5, pady=5)
purificationlabel.configure(width=30, height=5)

purificationbutton = tk.Button(window, text="Purify", command=purify)
purificationbutton.grid(row=0, column=2, padx=5, pady=5)
purificationbutton.configure(bg="grey", fg="white", border=5,borderwidth=5)

#Crystalline labels.

crystalinelabel = tk.Label(window, text="null", wraplength=200)
crystalinelabel.grid(row=0,column=3, padx=5, pady=5)
crystalinelabel.configure(width=30,height=5)

crystalinebutton = tk.Button(window, text="Crystalline", command=crystalline)
crystalinebutton.grid(row=0,column=4, padx=5, pady=5)
crystalinebutton.configure(bg="grey", fg="white", border=5,borderwidth=5)
#-Upgrade1 tkinter things.

upgrade1label = tk.Label(window, text=f"{upgrade1cost} points")
upgrade1label.grid(row=1, column=1, padx=5, pady=5)
upgrade1label.configure(width=15, height=1)

button1 = tk.Button(window, text="Upgrade", command=upgrade1)
button1.grid(row=1, column=2, padx=5, pady=5)
button1.configure(bg="grey", fg="white", border=5,borderwidth=5)

upgrade1explain = tk.Label(window, text=f"+{multiplierstrength} multipliers. [{buyamount1}]")
upgrade1explain.grid(row=1, column=3, padx=5, pady=5)
upgrade1explain.configure(width=25, height=1)

#-Upgrade2 tkinter things.

upgrade2label = tk.Label(window, text=f"{upgrade2cost} points")
upgrade2label.grid(row=2, column=1, padx=5, pady=5)
upgrade2label.configure(width=15, height=1)

button2 = tk.Button(window, text="Upgrade", command=upgrade2)
button2.grid(row=2, column=2, padx=5, pady=5)
button2.configure(bg="grey", fg="white", border=5,borderwidth=5)

upgrade2explain = tk.Label(window, text=f"+{mulstrshow}% multiplier strength. [{buyamount2}] (^{multraiser})")
upgrade2explain.grid(row=2, column=3, padx=5, pady=5)
upgrade2explain.configure(width=35, height=1)

#-Upgrade3 tkinter things.

upgrade3label = tk.Label(window, text=f"{upgrade3cost} points")
upgrade3label.grid(row=3, column=1, padx=5, pady=5)
upgrade3label.configure(width=15, height=1)

button3 = tk.Button(window, text="Upgrade", command=upgrade3)
button3.grid(row=3, column=2, padx=5, pady=5)
button3.configure(bg="grey", fg="white", border=5, borderwidth=5)

upgrade3explain = tk.Label(window, text=f"Increase exponent by 0.05. [{buyamount3}]")
upgrade3explain.grid(row=3, column=3, padx=5, pady=5)
upgrade3explain.configure(width=35, height=1)

#-Upgrade4 tkinter things.

upgrade4label = tk.Label(window, text=f"{upgrade4cost}")
upgrade4label.grid(row=4, column=1, padx=5, pady=5)
upgrade4label.configure(width=15, height=1)

button4 = tk.Button(window, text="Upgrade", command=upgrade4)
button4.grid(row=4, column=2, padx=5, pady=5)
button4.configure(bg="grey", fg="white", border=5,borderwidth=5)

upgrade4explain = tk.Label(window, text=f"Increases max level of upgrade 3 by {format_number(buyamount4)}.")
upgrade4explain.grid(row=4, column=3, padx=5, pady=5)
upgrade4explain.configure(width=35, height=1)

#-Upgrade5 tkinter things.

upgrade5label = tk.Label(window, text="???")
upgrade5label.grid(row=6, column=1, padx=5, pady=5)
upgrade5label.configure(width=15, height=1)

button5 = tk.Button(window, text="???", command=upgrade5)
button5.grid(row=6, column=2, padx=5, pady=5)
button5.configure(bg="grey", fg="white", border=5,borderwidth=5)

upgrade5explain = tk.Label(window, text="???")
upgrade5explain.grid(row=6, column=3, padx=5, pady=5)
upgrade5explain.configure(width=35, height=1)

#Clicking powers.
def click_power():
    global cry4unlocked, clickpower, clicks
    if cry4unlocked:
        clicks += clickpower

clickbutton = tk.Button(window, text="???", command=click_power)
clickbutton.grid(row=5, column=2, padx=5, pady=5)
clickbutton.configure(bg="grey", fg="white", border=5, borderwidth=5)

#-Admin window.

#sets a currency to a value

def setcurrency():
    global points
    try:
        points = float(setcurrencyentry.get())
        print(f"INFO: Set currency to {points}")
    except ValueError:
        warn.warn("WARNING: Invalid value.")

setcurrencyentry = tk.Entry(adminwindow, width=10)
setcurrencyentry.grid(row=0, column=0, padx=5, pady=5)
setcurrencyentry.configure(bg="grey", fg="white", border=5,borderwidth=5)

setcurrencybutton = tk.Button(adminwindow, text="Set Points", command=setcurrency)
setcurrencybutton.grid(row=0, column=1, padx=5, pady=5)
setcurrencybutton.configure(bg="grey", fg="white", border=5, borderwidth=5)

def setpurification():
    global purifytimes
    try:
        purifytimes = int(setpurificationentry.get())
        print(f"INFO: Set purification times to {purifytimes}")
    except ValueError:
        warn.warn("WARNING: Invalid value.")

setpurificationentry = tk.Entry(adminwindow, width=10)
setpurificationentry.grid(row=1, column=0, padx=5, pady=5)
setpurificationentry.configure(bg="grey", fg="white", border=5,borderwidth=5)

setpurificationbutton = tk.Button(adminwindow, text="Set Purification", command=setpurification)
setpurificationbutton.grid(row=1, column=1, padx=5, pady=5)
setpurificationbutton.configure(bg="grey", fg="white", border=5, borderwidth=5)

#-Autobuyers

def autobuy():
    global crystallinetimes, points, upgrade1cost, upgrade2cost, upgrade3cost, buyamount1, buyamount2, buyamount3, upgrade1max, upgrade2max, upgrade3max
    while True:
        if crystallinetimes >= 3:
            if points >= upgrade1cost and buyamount1 < upgrade1max:
                upgrade1()
            if points >= upgrade2cost and buyamount2 < upgrade2max:
                upgrade2()
            if points >= upgrade3cost and buyamount3 < upgrade3max:
                upgrade3()
        tm.sleep(0.05)

#-Save and load functions.
def load2():
    global points, pointpersecond, multiplier, multiplierstrength, mpower, upgrade1cost, buyamount1
    global upgrade2cost, buyamount2, upgrade3cost, buyamount3, multraiser, purifytimes, purifycost
    global rank1booster, rank2unlocked, rank3costmultiplier, rank3unlocked, rank4upg2booster
    global rank5upg3booster, rank6unlocked, rank6booster, upgrade1max, upgrade2max, upgrade3max, crystallineunlocked, crystallinetimes, crystallinecost
    global cry1upg4unlocked, cry1booster, cry2booster, cry3unlocked, cry4unlocked

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
        autobuythread.start()
def savewaiter():
    global currenttime
    while True:
        tm.sleep(30)
        currenttime = dt.datetime.now().strftime("%H:%M:%S")
        print(f"INFO: Attempted save at {currenttime}.")
        save()


def save():
    with open("save.txt", "w") as f:
        f.write(f"{points}:{pointpersecond}:{multiplier}:{multiplierstrength}:{mpower}:{upgrade1cost}:{buyamount1}:{upgrade2cost}:{buyamount2}:{upgrade3cost}:{buyamount3}:{multraiser}:{purifytimes}:{purifycost}:{rank1booster}:{rank2unlocked}:{rank3costmultiplier}:{rank3unlocked}:{rank4upg2booster}:{rank5upg3booster}:{rank6unlocked}:{rank6booster}:{upgrade1max}:{upgrade2max}:{upgrade3max}:{crystallineunlocked}:{crystallinetimes}:{crystallinecost}:{cry1booster}:{cry1upg4unlocked}:{cry2booster}:{cry3unlocked}:{clickpower}:{clicks}:{buyamount4}:{upgrade4cost}:{cry4unlocked}")
    print(f"INFO: Saved at {currenttime}.")

def load():
    try:
        with open("save.txt", "r") as f:
            data = f.read().split(":")
            global points, pointpersecond, multiplier, multiplierstrength, mpower, upgrade1cost, buyamount1
            global upgrade2cost, buyamount2, upgrade3cost, buyamount3, multraiser, purifytimes, purifycost
            global rank1booster, rank2unlocked, rank3costmultiplier, rank3unlocked, rank4upg2booster
            global rank5upg3booster, rank6unlocked, rank6booster, upgrade1max, upgrade2max, upgrade3max, crystallineunlocked, crystallinetimes, crystallinecost, cry1upg4unlocked, cry1booster, buyamount4, upgrade4cost, cry4unlocked
            global cry2booster, cry3unlocked, clickpower,clicks
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
            print("INFO: Loaded save data.")
    except:
        print("No save file found or corrupted save.")

    load2()
#-Load save data
load()

#-Threads.

uiupdatethread = th.Thread(target=updateui)
uiupdatethread.start()

pointcalcthread = th.Thread(target=pointcalc)
pointcalcthread.start()

savethread = th.Thread(target=savewaiter)
savethread.start()

autobuythread = th.Thread(target=autobuy)
#-Loops the window.
window.mainloop()
