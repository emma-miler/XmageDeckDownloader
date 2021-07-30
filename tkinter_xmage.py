import tkinter as tk
import tkinter.filedialog as fd
from tkinter import ttk

import requests
import re
from pprint import pprint as pp
import shutil
import os

import queue, time, urllib.request
from threading import Thread
import threading

import random

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
)
style.map("C.Treeview",
    foreground=[('!disabled', 'white'), ('active', 'white')],
    fieldbackground=[('pressed', '#3c45a5'), ("!active", "#202225"), ('active', '#4752c4')],
	relief=[("!disabled","flat")],
)
style.map("Vertical.TScrollbar", 
	background=[("!disabled", "#202225"), ("disabled", "#202225")],
	darkcolor="DarkGreen",
	lightcolor="LightGreen",
	troughcolor=[("!disabled", "#1c1e21"), ("disabled", "#1c1e21")], 
	bordercolor="blue", 
	arrowcolor="white"
)


style.configure("C.Treeview", highlightthickness=0, bd=0, font=('Calibri', 12)) # Modify the font of the body
style.configure("C.Treeview.Heading", highlightthickness=0, bd=0, background="#303235", foreground="white")
#style.layout("C.TEntry", [('C.TEntry.treearea', {'sticky': 'nswe'})]) # Remove the borders


pattern = re.compile("(?<=\[)(.{0,})(?=\])(?:\]\ )(.*)") # Compile regex pattern for scanning XMage decklist

filename_var = tk.StringVar()
folder_var = tk.StringVar()

globals()["cardList"] = []

def perform_web_requests(urls, treeView):
	class Worker(Thread):
		def __init__(self, request_queue, treeView):
			Thread.__init__(self)
			self.queue = request_queue
			self.results = []
			self.treeview = treeView
			self.handled = False

		def run(self):
			card = self.queue.get()
			if card == None:
				raise KeyError(f"what the fuck {card}")
			#time.sleep(random.randint(2, 5))
			url = "https://api.scryfall.com/cards" # Scryfall api url
			cardObject = requests.get(url=f"{url}/{card['set']}/{card['number']}") # Make up api request
			if cardObject.status_code == 200:
				print(f"got card object for {card['name']}")
				imageObject = requests.get(url=cardObject.json()["image_uris"]["normal"], stream=True) # Get image from server
				print(f"Correct status for {card['name']}")
				if imageObject.status_code == 200:
					self.results.append([card, imageObject])
				
				else:
					raise KeyError(f"Could not download '{card['name']}' with parsed set {card['set']}:{card['number']}")
			self.queue.task_done()
			
	# Create queue and add addresses
	q = queue.Queue()
	for url in urls:
		q.put(url)

	# Create workers and add tot the queue
	workers = []
	for _ in range(len(urls)):
		worker = Worker(q, treeView)
		worker.start()
		workers.append(worker)
	# Join workers to wait till they finished
	for worker in workers:
		pass
		#worker.join()
	finished = []
	while len(finished) < len(urls):
		for t in workers:
			if not t.is_alive() and not t.handled:
				t.handled = True
				card = t.results[0][0] # Read card data
				treeView.item(item=card["name"], values=(True, card["name"], card["set"], card["number"]), tags=("done"))
				root.update()
		finished = [t for t in workers if t.handled]
	for worker in workers:
		worker.join()
	# Combine results from all workers
	r = []
	for worker in workers:
		r.extend(worker.results)
	return r

def runDownload():
	print("running")
	print(globals()["cardList"])
	if not os.path.exists(folder_var.get()):
		os.mkdir(folder_var.get())
	returned = perform_web_requests(cardList, cardView)
	for returnObject in returned:
		card, imageObject = returnObject
		with open(f"{folder_var.get()}/{card['name']}.jpg", 'wb') as f: # Open
			print(f"Opened file {card['name']}")
			imageObject.raw.decode_content = True # Dunno tbh
			print(f"Started write to file file {card['name']}")
			shutil.copyfileobj(imageObject.raw, f) # Write image to file
	print("RETURNED")

def fileCallback(name=None):
	# Gets called when selecting file
	if name is None:
		name= fd.askopenfilename(filetypes=[("XMage Deck File", [".dck"])]) # Format should be correct?
	if type(name) == str: # Check if file was provided
		filename_var.set(name) # Update filename entry
		if os.path.exists(name): # Check if ile exists
			with open(name, "r") as f:
				readcards = [pattern.search(line).groups() for line in f.readlines()] # Parse decklist
			globals()["cardList"]
			for card in readcards:
				parsedCard = {}
				setInfo = card[0].lower().split(":") # Split data into set and number
				parsedCard["set"] = setInfo[0]
				parsedCard["number"] = setInfo[1]
				parsedCard["name"] = card[1]
				globals()["cardList"].append(parsedCard)
				# Insert data into treeview
				cardView.insert("",'end',iid=parsedCard["name"],values=(False, parsedCard["name"], parsedCard["set"], parsedCard["number"]), tags=("notdone"))

		else:
			raise FileNotFoundError(f"Could not read {name}!")

def updateRunButton(*args):
	if len(filename_var.get()) > 0 and len(folder_var.get()) > 0:
		runButton["state"] = tk.NORMAL
	else:
		runButton["state"] = tk.DISABLED 

def folderCallback():
	# Gets called when selecting folder
	name= fd.askdirectory()
	if type(name) == str:
		folder_var.set(name)

filenameEntry = ttk.Entry(root, textvariable=filename_var, style="C.TEntry")
filenameEntry.place(relx=0.02, rely=0.02, relwidth=0.77, relheight=0.05)

openfileButton = ttk.Button(text='Click to Open File', command=fileCallback, style="C.TButton")
openfileButton.place(relx=0.8, rely=0.02, relwidth=0.18, relheight=0.05)

directoryEntry = ttk.Entry(root, textvariable=folder_var,  style="C.TEntry")
directoryEntry.place(relx=0.02, rely=0.08, relwidth=0.77, relheight=0.05)

folderButton = ttk.Button(text='Select Output Folder', command=folderCallback,  style="C.TButton")
folderButton.place(relx=0.8, rely=0.08, relwidth=0.18, relheight=0.05)

cardView = ttk.Treeview(root, selectmode ='browse',  style="C.Treeview")
cardView.place(relx=0.02, rely=0.14, relwidth=.94, relheight=0.76)
cardView["columns"] = ("Done", "Cardname", "Set", "Number")
cardView["show"] = "headings"
# Set up treeview column names
cardView.column("Done", width = int(width/16), anchor ='center')
cardView.column("Cardname", width = int(width/8*3), anchor ='w')
cardView.column("Set", width = int(width/8*2), anchor ='center')
cardView.column("Number", width = int(width/8*2), anchor ='center')
# Set up treeview display names
cardView.heading("Done", text ="Done")
cardView.heading("Cardname", text ="Cardname")
cardView.heading("Set", text ="Set")
cardView.heading("Number", text ="Number")
cardView.tag_configure("done", background="#448844")
cardView.tag_configure("notdone", background="#884444")

# Create scrollbar for treeview
verscrlbar = ttk.Scrollbar(root, orient ="vertical", command = cardView.yview)
verscrlbar.set(0.1,0.1)
verscrlbar.place(relx=0.96, rely=0.14, relwidth=0.02, relheight=0.76)
cardView.configure(yscrollcommand = verscrlbar.set)

runButton = ttk.Button(text="Run", style="C.TButton", command=runDownload)
runButton["state"] = tk.DISABLED
runButton.place(relx=0.27, rely=0.92, relwidth=0.5, relheight=0.05)

filename_var.trace("w", updateRunButton)
folder_var.trace("w", updateRunButton)

fileCallback("/home/emma/xmage_small.dck")
folder_var.set("/home/emma/downloaded_cards")

root.mainloop()


