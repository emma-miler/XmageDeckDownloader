import tkinter as tk
import tkinter.filedialog as fd
from tkinter import ttk

import requests
import re
from pprint import pprint as pp
import shutil
import os

import queue, time, urllib.request
import urllib3
from threading import Thread
import threading

import random

import io
import zipfile

# Setting up Tkinter window
root = tk.Tk()
root.title="XMage Deck Downloader"
root.attributes('-type', 'dialog')
root.configure(bg="#1c1e21")
width, height = (800,600)
root.geometry(f"{width}x{height}")

# Bunch of styling code i still really understand
style = ttk.Style()
style.map("C.TButton",
    foreground=[('!disabled', 'white'), ('active', 'white')],
    background=[('pressed', '#3c45a5'), ("!disabled", "!active", "#5875f2"), ('active', '#4752c4'), ("disabled", "#AA4444")],
	relief=[("!disabled","flat"), ("disabled","flat")]
)
style.map("C.TEntry",
    foreground=[('!disabled', 'white'), ('active', 'white')],
    fieldbackground=[('pressed', '#3c45a5'), ("!active", "#3b3b3b"), ('active', '#4752c4')],
	relief=[("!disabled","flat")],
	borderwidth=[("!disabled", "0")],
)
style.map("C.TLabel",
    foreground=[('!disabled', 'white')],
    background=[('!disabled', '#1c1e21')],
)
style.map("C.Treeview",
    foreground=[('!disabled', 'white'), ('active', 'white')],
    fieldbackground=[('pressed', '#3c45a5'), ("!active", "#202225"), ('active', '#4752c4')],
	relief=[("!disabled","flat")],
	borderwidth=[("!disabled", "0")],
)
style.map("C.TCombobox",
    foreground=[('!disabled', 'white')],
    background=[('!disabled', '#3b3b3b')],
    arrowcolor=[("!disabled", "white")],
    arrowsize=[("!disabled", "15")],
    selectbackground=[("!disabled", "#3b3b3b")],
    selectborderwidth=[("!disabled", "0")],
    fieldbackground=[('!disabled', '#3b3b3b')],
	relief=[("!disabled","flat")],
	bordercolor=[("!disabled", "#0000FF")],
	highlightbackground=[("!disabled", "#0000FF")],
	borderwidth=[("!disabled", "0")],
)
style.map("Horizontal.TProgressbar", 
	background=[("!disabled", "#5875f2")],
	troughcolor=[("!disabled", "#202225"), ("disabled", "#1c1e21")], 
	bordercolor=[("!disabled", "red")],
)
style.map("Vertical.TScrollbar", 
	background=[("!disabled", "#202225"), ("disabled", "#202225")],
	troughcolor=[("!disabled", "#1c1e21"), ("disabled", "#1c1e21")], 
)

# Small dict for translating between card status and GUI string
GUIName = {
	"notdone": "Will Download",
	"wontrun": "Already Exists",
	"done": "Downloaded"
}


style.configure("C.Treeview", highlightthickness=0, bd=0, font=('Calibri', 12)) # Modify the font of the body
style.configure("C.Treeview.Heading", highlightthickness=0, bd=0, background="#303235", foreground="white", borderwidth="0")
style.configure("C.TLabel", font=('Calibri', 14))
style.configure("C.TCombobox", font=('Calibri', 14))

pattern = re.compile("(?<=\[)(.{0,})(?=\])(?:\]\ )(.*)") # Compile regex pattern for scanning XMage decklist

filename_var = tk.StringVar()
folder_var = tk.StringVar()

globals()["cardList"] = []

# This function is the main workhorse in terms of actually downloading stuff
def perform_web_requests(urls, treeView):
	# Setting up the Worker class
	class Worker(Thread):
		def __init__(self, card, size):
			Thread.__init__(self)
			self.results = []
			self.handled = False
			self.card = card
			self.size = size

		def run(self):
			card = self.card
			if True:
				url = "https://api.scryfall.com/cards" # Scryfall api url
				cardObject = requests.get(url=f"{url}/{card['set']}/{card['number']}") # Make up api request
				if cardObject.status_code == 200:
					print(f"got card object for {card['name']}")
					if "image_uris" in cardObject.json():
						with urllib.request.urlopen(cardObject.json()["image_uris"][size]) as stream:
							f = io.BytesIO(stream.read())
							self.results.append([card, f])
					else:
						with urllib.request.urlopen(cardObject.json()["card_faces"][0]["image_uris"][size]) as stream:
							x = io.BytesIO(stream.read())
						with urllib.request.urlopen(cardObject.json()["card_faces"][1]["image_uris"][size]) as stream:
							y = io.BytesIO(stream.read())
						self.results.append([card, x, y, [cardObject.json()["card_faces"][0]["name"], cardObject.json()["card_faces"][1]["name"]]])

	# Create workers and set them going
	workers = []
	size = sizeCombobox.get()
	for x in range(len(urls)):
		worker = Worker(urls[x], size)
		worker.start()
		workers.append(worker)

	finished = []
	progressDelta = 80/len(urls)
	while len(finished) < len(urls): # Loop until all workers are done
		root.update() # Update the UI so it remains responsive
		for t in workers:
			if not t.is_alive() and not t.handled: # Check all dead workers that havent yet been handled
				t.handled = True
				progress["value"] += progressDelta
				try:
					card = t.results[0][0] # Read card data
					# Update the UI to indicate this card has been downloaded
					treeView.item(item=card["name"], values=(True, card["name"], card["set"], card["number"]), tags=("done"))
				except IndexError:
					print("Fucky Wucky", t.results, t, t.card)
		finished = [t for t in workers if t.handled] # Update the loop condition
	# This shouldn't be necessary but it's a nice security measure to make sure all threads have stopped
	for worker in workers:
		worker.join()
	# Combine results from all workers
	r = []
	for worker in workers:
		r.extend(worker.results)
	return r

def runDownload():
	toDownload = [card for card in cardList if cardView.item(item=card["name"])["tags"] == ["notdone"]]
	returned = perform_web_requests(toDownload, cardView) # Run the downloads
	downloadedSets = []
	for card in cardList:
		if card["set"] not in downloadedSets:
			downloadedSets.append(card["set"])
	fileWriteDelta = 10/len(returned) # Amount to increase progress bar by when writing to file
	zipfiles = {}
	print(downloadedSets)
	for setName in downloadedSets:
		print(setName)
		zipfiles[setName] = zipfile.ZipFile(folder_var.get() + "/" + setName.upper() + ".zip", "a")
	for returnObject in returned:
		if len(returnObject) == 2: # regular card
			card, imageObject = returnObject # object has structue [dict<string><string>, BinaryData]
			# Write the virtual file (io.BytesIO) to zip file
			zipfiles[card["set"]].writestr(card["set"].upper() + "/" + card["name"] + ".full.jpg", imageObject.read())
		else: # Split/transform card
			card, image1, image2, names = returnObject
			zipfiles[card["set"]].writestr(card["set"].upper() + "/" + names[0] + ".full.jpg", image1.read())
			zipfiles[card["set"]].writestr(card["set"].upper() + "/" + names[1] + ".full.jpg", image2.read())
		progress["value"] += fileWriteDelta
	zipDelta = 10/len(downloadedSets) # Amount to increase progress bar by when zipping folder
	print("Done!")

def fileCallback(name=None):
	progress["value"] = 0
	cardView.delete(*cardView.get_children())
	# Gets called when selecting file
	if name is None:
		name= fd.askopenfilename(filetypes=[("XMage Deck File", [".dck"])]) # Format should be correct?
	if name == "":
		return
	if type(name) == str: # Check if file was provided
		filename_var.set(name) # Update filename entry
		if os.path.exists(name): # Check if ile exists
			with open(name, "r") as f:
				readcards = [pattern.search(line).groups() for line in f.readlines()] # Parse decklist
			globals()["cardList"] = []
			for card in readcards:
				parsedCard = {}
				setInfo = card[0].lower().strip("*").split(":") # Split data into set and number
				parsedCard["set"] = setInfo[0]
				parsedCard["number"] = setInfo[1]
				parsedCard["name"] = card[1]
				globals()["cardList"].append(parsedCard)
			
			openedSets = []
				
			for card in globals()["cardList"]:
				if card["set"] not in openedSets:
					openedSets.append(card["set"])
	
			setZips = {}
			# TODO: should probably keep these around instead of reopening them later but whatever
			for setName in openedSets:
				if os.path.exists(folder_var.get() + "/" + setName.upper() + ".zip"):
					setZips[setName] = zipfile.ZipFile(folder_var.get() + "/" + setName.upper() + ".zip", "r").namelist()
				else:
					setZips[setName] = []
			cardView.delete(*cardView.get_children())
			for card in globals()["cardList"]:
				# Insert data into treeview
				tags = []
				if folder_var.get() != "" and f"{card['set'].upper()}/{card['name']}.full.jpg" in setZips[card["set"]]:
					tags.append("wontrun")
				else:
					tags.append("notdone")
				cardView.insert("",'end',iid=card["name"],values=(GUIName[tags[0]], card["name"], card["set"], card["number"]), tags=tags)
				
		else:
			raise FileNotFoundError(f"Could not read {name}!")

def updateRunButton(*args):
	if len(filename_var.get()) > 0 and len(folder_var.get()) > 0:
		runButton["state"] = tk.NORMAL
	else:
		runButton["state"] = tk.DISABLED 

def folderCallback(name=None):
	# Gets called when selecting folder
	if name is None:
		name= fd.askdirectory()
	if type(name) == str:
		folder_var.set(name)
	fileCallback(name=filename_var.get())
		
# TODO: should probably tidy this up into a class at some point

filenameEntry = ttk.Entry(root, textvariable=filename_var, style="C.TEntry")
filenameEntry.place(relx=0.02, rely=0.02, relwidth=0.77, relheight=0.05)

openfileButton = ttk.Button(text='Click to Open File', command=fileCallback, style="C.TButton")
openfileButton.place(relx=0.8, rely=0.02, relwidth=0.18, relheight=0.05)

directoryEntry = ttk.Entry(root, textvariable=folder_var,  style="C.TEntry")
directoryEntry.place(relx=0.02, rely=0.08, relwidth=0.77, relheight=0.05)

folderButton = ttk.Button(text='Select Output Folder', command=folderCallback,  style="C.TButton")
folderButton.place(relx=0.8, rely=0.08, relwidth=0.18, relheight=0.05)

imagesizeLabel = ttk.Label(text="Image Size:", style="C.TLabel")
imagesizeLabel.place(relx=0.02, rely=0.14, relwidth=0.2, relheight=0.05)

sizeCombobox = ttk.Combobox(style="C.TCombobox", values=["small", "normal", "large"], state="readonly")
sizeCombobox.set("normal")
sizeCombobox.place(relx=0.16, rely=0.14, relwidth=0.2, relheight=0.05)

cardView = ttk.Treeview(root, selectmode ='browse',  style="C.Treeview")
cardView.place(relx=0.02, rely=0.20, relwidth=.94, relheight=0.70)
cardView["columns"] = ("Done", "Cardname", "Set", "Number")
cardView["show"] = "headings"
# Set up treeview column names
cardView.column("Done", width = int(width/8), anchor ='center')
cardView.column("Cardname", width = int(width/4), anchor ='w')
cardView.column("Set", width = int(width/4), anchor ='center')
cardView.column("Number", width = int(width/4), anchor ='center')
# Set up treeview display names
cardView.heading("Done", text ="Done")
cardView.heading("Cardname", text ="Cardname")
cardView.heading("Set", text ="Set")
cardView.heading("Number", text ="Number")
cardView.tag_configure("done", background="#448844")
cardView.tag_configure("notdone", background="#884444")
cardView.tag_configure("wontrun", background="#BB6622")

# Create scrollbar for treeview
verscrlbar = ttk.Scrollbar(root, orient ="vertical", command = cardView.yview)
verscrlbar.set(0.1,0.1)
verscrlbar.place(relx=0.96, rely=0.20, relwidth=0.02, relheight=0.70)
cardView.configure(yscrollcommand = verscrlbar.set)

# Progress bar, default size = 100
progress = ttk.Progressbar(root, orient="horizontal")
progress.place(relx=0.02, rely=0.912, relwidth=0.96, relheight=0.02)

runButton = ttk.Button(text="Run", style="C.TButton", command=runDownload)
runButton["state"] = tk.DISABLED
runButton.place(relx=0.27, rely=0.94, relwidth=0.5, relheight=0.05)

filename_var.trace("w", updateRunButton)
folder_var.trace("w", updateRunButton)

# Debug stuff
folderCallback(name="/home/emma/Downloads/xmage/mage-client/plugins/images")
fileCallback(name="/home/emma/xmage_reaper.dck")

root.mainloop()


