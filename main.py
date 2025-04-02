#-Imports.
import tkinter as tk
import threading as th
import time as tm
import warnings as warn
import datetime as dt
#-Variables - > MAIN.
points = 0
pointpersecond = 1
multiplier = 1
multiplierstrength = 1
mulstrshow = 10
multraiser = 1
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
#-Variables - > PURIFICATION.
purifytimes = 0
purifycost = 1000
purifydescriptions = ["Doubles all point gain.","For every purification, add one max level to upgrades 1 and 2.","Reduce upgrades 1-3 cost by 5%","Increase upgrade 2 power by x3","Increase upgrade 3 power by +^0.01, making it ^0.06 per upgrade."]
rank1booster = 1
rank2unlocked = False
rank3costmultiplier = 1
rank4upg2booster = 1
rank5upg3booster = 0
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
adminwindow.geometry("900x900")
adminwindow.configure(bg="black")
#-Point calculation.

def pointcalc():
    while True:
        global points, multiplier, pointpersecond,multiplierstrength,mpower

        pointpersecond = mpower

        count = 0
        while count < 5:
            count+=1
            points += pointpersecond / 20 #-Divide by 20 -> 50ms sleep -> 1 point / s
            points = round(points, 3) 
            tm.sleep(0.05)

#-Update UI.

def updateui():
    global mpower,multiplierstrength, multiplier, points, pointpersecond, upgrade1cost, buyamount1, upgrade2cost, buyamount2, upgrade3cost, buyamount3, mulstrshow, multraiser, rank1booster
    while True:
        #-Variable calculation.
        mulstrshow = (multiplierstrength * 100) - 100
        mulstrshow = round(mulstrshow, 2)
        multiplier = round(multiplier, 2)
        multraiser = round(multraiser, 2)
        mpower = rank1booster * (multiplierstrength * multiplier)
        mpower = round(mpower, 2)
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
        # Update purification label with current description
        if purifytimes < len(purifydescriptions):
            purificationlabel.configure(text=f"Next: {purifydescriptions[purifytimes]} ({format_number(purifycost)} points)")
        else:
            purificationlabel.configure(text="All purifications complete!")
        tm.sleep(0.05)

#-Definitions.

def upgrade1():
    global points, multiplier, upgrade1cost, buyamount1
    if points >= upgrade1cost:
        points -= upgrade1cost
        buyamount1 += 1
        upgrade1cost = round((upgrade1cost * (1+(buyamount1/10))) * rank3costmultiplier, 2)
        multiplier += 1
        print(f"INFO: Upgraded! Current multiplier: {multiplier}")
    else:
        warn.warn("WARNING: Not enough points to upgrade.")

def recalculate_multiplier_strength():
    global multiplierstrength, buyamount2, multraiser
    base = (1 + (buyamount2 * 0.1)) * rank4upg2booster
    multiplierstrength = round(base ** multraiser, 3)

def upgrade2():
    global points, multiplierstrength, upgrade2cost, buyamount2
    if points >= upgrade2cost:
        points -= upgrade2cost
        buyamount2 += 1
        upgrade2cost = round((upgrade2cost * (1+(buyamount2/10))) * rank3costmultiplier, 2)
        recalculate_multiplier_strength()
        print(f"INFO: Upgraded! Current multiplier strength: {multiplierstrength}")
    else:
        warn.warn("WARNING: Not enough points to upgrade.")

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
        else:
            warn.warn("WARNING: Upgrade maxed out.")
    else:
        warn.warn("WARNING: Not enough points to upgrade.")

def purify():
    global points, purifytimes, purifycost, multiplier, multiplierstrength, upgrade1cost, upgrade2cost
    global upgrade3cost, buyamount1, buyamount2, buyamount3, multraiser, rank1booster, rank2unlocked
    global rank3costmultiplier, rank4upg2booster, rank5upg3booster, upgrade1max, upgrade2max, upgrade3max
    
    if points >= purifycost:
        if purifytimes < len(purifydescriptions):
            points -= purifycost
            
            # Apply purification effects based on rank
            if purifytimes >= 0:
                rank1booster = 2
            if purifytimes >= 1:
                rank2unlocked = True
            if purifytimes >= 2:
                rank3costmultiplier = 0.95  # 5% cost reduction
            if purifytimes >= 3:
                rank4upg2booster = 3  # Triple upgrade 2 power
            if purifytimes >= 4:
                rank5upg3booster = 0.01  # Add 0.01 to upgrade 3's power

            if rank2unlocked:
                upgrade1max += 1
                upgrade2max += 1
                upgrade3max += 1

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

#-Currency labels.

pointlabel = tk.Label(window, text=f"Current points: {points}")
pointlabel.grid(row=0, column=0, padx=5, pady=5)
pointlabel.configure(width=30, height=2)

pointpersecondlabel = tk.Label(window, text=f"Points per second: {pointpersecond}")
pointpersecondlabel.grid(row=1, column=0, padx=5, pady=5)
pointpersecondlabel.configure(width=30, height=1)

#-Purification labels.

purificationlabel = tk.Label(window, text=f"null", wraplength=200)  # Add wraplength
purificationlabel.grid(row=0, column=1, padx=5, pady=5)
purificationlabel.configure(width=30, height=5)

purificationbutton = tk.Button(window, text="Purify", command=purify)
purificationbutton.grid(row=0, column=2, padx=5, pady=5)
purificationbutton.configure(bg="grey", fg="white", border=5,borderwidth=5)
#-Upgrade1 tkinter things.

upgrade1label = tk.Label(window, text=f"{upgrade1cost} points")
upgrade1label.grid(row=1, column=1, padx=5, pady=5)
upgrade1label.configure(width=15, height=1)

button1 = tk.Button(window, text="Upgrade", command=upgrade1)
button1.grid(row=1, column=2, padx=5, pady=5)
button1.configure(bg="grey", fg="white", border=5,borderwidth=5)

upgrade1explain = tk.Label(window, text=f"+{multiplierstrength} multipliers. [{buyamount1}]")
upgrade1explain.grid(row=1, column=3, padx=5, pady=5)
upgrade1explain.configure(width=15, height=1)

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

#-Save and load functions.
def savewaiter():
    global currenttime
    while True:
        tm.sleep(30)
        currenttime = dt.datetime.now().strftime("%H:%M:%S")  # Fix datetime format
        print(f"INFO: Attempted save at {currenttime}.")
        save()


def save():
    with open("save.txt", "w") as f:
        f.write(f"{points}:{pointpersecond}:{multiplier}:{multiplierstrength}:{mpower}:{upgrade1cost}:{buyamount1}:{upgrade2cost}:{buyamount2}:{upgrade3cost}:{buyamount3}:{multraiser}:{purifytimes}:{purifycost}")
    print(f"INFO: Saved at {currenttime}.")

def load():
    try:
        with open("save.txt", "r") as f:
            data = f.read().split(":")
            global points, pointpersecond, multiplier, multiplierstrength, mpower, upgrade1cost, buyamount1, upgrade2cost, buyamount2, upgrade3cost, buyamount3, multraiser, purifytimes, purifycost
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
    except:
        print("No save file found or corrupted save.")
#-Load save data
load()

#-Threads.

uiupdatethread = th.Thread(target=updateui)
uiupdatethread.start()

pointcalcthread = th.Thread(target=pointcalc)
pointcalcthread.start()

savethread = th.Thread(target=savewaiter)
savethread.start()

#-Loops the window.
window.mainloop()
