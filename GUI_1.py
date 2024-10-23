# -*- coding: utf-8 -*-
"""
Created on Wed Mar  6 09:14:09 2024

@author: 20020308
"""

import h5py
import time
import numpy as np
import os
import math
import csv
import matplotlib.pyplot as plt
import re
import natsort
from datetime import datetime
#import sys
import subprocess
import pandas as pd
import tkinter as tk
from tkinter import filedialog, ttk
from tkinter import simpledialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import mpld3

def berechne_ausfuehrungszeit_poly3(dateigroesse):
    # Polynomiale Koeffizienten
    poly3_func = np.poly1d([0.002837344127959294, -0.01756857059665256, -0.009283272964127013, 1.4001872034363547])
    
    # Logarithmus der Dateigröße berechnen
    log_dateigroesse = np.log(dateigroesse)
    
    # Polynomiale Funktion anwenden
    poly_wert = poly3_func(log_dateigroesse)
    
    # Exponentiation des Ergebnisses
    ausfuehrungszeit = np.exp(poly_wert)
    
    # Ausführungszeit in Minuten umrechnen
    ausfuehrungszeit_minuten = ausfuehrungszeit / 60
    
    # Auf halbe Minuten runden
    ausfuehrungszeit_gerundet = 0.5 * round(ausfuehrungszeit_minuten / 0.5)
    
    return ausfuehrungszeit_gerundet

    
    return ausfuehrungszeit_gerundet
def human_readable_size(size, decimal_places=2):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.{decimal_places}f} {unit}"
        size /= 1024.0
class ScrollableDialog(simpledialog.Dialog):
    def __init__(self, parent, title, testRunList):
        self.testRunList = testRunList
        super().__init__(parent, title)

    def body(self, master):
        frame = tk.Frame(master)
        frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set, selectmode=tk.SINGLE)
        for testRun in self.testRunList:
            listbox.insert(tk.END, testRun)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=listbox.yview)
        
        entry_label = tk.Label(master, text="Geben Sie die TestRun-Nummer ein oder lassen Sie sie leer für den letzten TestRun:")
        entry_label.pack(fill=tk.X, padx=10, pady=5)
        
        self.entry = tk.Entry(master)
        self.entry.pack(fill=tk.X, padx=10, pady=5)

        return self.entry

    def apply(self):
        user_choice = self.entry.get().strip()
        self.result = f"TSR{user_choice}.TestRun" if user_choice else None

# Funktion, um die letzte Bearbeitungszeit zu ermitteln
def get_last_modified_time(file_path):
    return os.path.getmtime(file_path)
class HDF5AnalyzerGUI:
    def __init__(self, master):
        #hier wird der GUI Aufbau initialisiert weitere Felder und Variablen können einfach hinzugefügt werden
        self.master = master
        self.master.title("H5 Files Auswertung")
        self.master.state('zoomed')
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        #print(screen_width)
        #print(screen_height)
        # Setze das Fenster auf volle Bildschirmgröße
        self.master.geometry(f"{screen_width}x{screen_height}")

        # Setze die maximale Größe des Fensters auf die Bildschirmgröße
        #self.master.maxsize(screen_width, screen_height)
        
        # Setze die minimale Größe des Fensters, damit es nur kleiner gemacht werden kann
        self.master.minsize(1050, 580)
        self.master.grid_rowconfigure(0, weight=1)  # Macht die Zeile 0 dynamisch
        self.master.grid_columnconfigure(0, weight=1)  # Macht die Spalte 0 dynamisch

        # Setze die Größe des Fensters auf 600x400 Pixel
        self.notebook = ttk.Notebook(master)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # Erste Registerkarte: Hauptsteuerung
        self.main_frame = tk.Frame(self.notebook)
        self.notebook.add(self.main_frame, text="Auswertung")

        # Zweite Registerkarte: Plot-Anzeige
        self.plot_frame = tk.Frame(self.notebook)
        self.notebook.add(self.plot_frame, text="Plots")
        
        # Dritte Registerkarte: Filtern
        #self.filter_frame = tk.Frame(self.notebook)
        #self.notebook.add(self.filter_frame, text="Filtern (noch nicht implementiert)")
        
        
        
        # Erstellen Sie ein Tooltip-Widget
        self.tooltip = tk.Label(master, text="", justify="left", wraplength=300, relief="solid", bg="white")
        self.tooltip.place_forget()  # Verstecke den Tooltip zunächst
        self.master.bind("<Motion>", self.update_tooltip_position)  # Aktualisiere die Tooltip-Position bei Mausbewegungen

        # Beschreibung für Pfad
        self.path_label = tk.Label(self.main_frame, text="Pfad zum Test:")
        self.path_label.grid(row=0, column=0, sticky="w")
        self.path_entry = tk.Entry(self.main_frame, textvariable=tk.StringVar(), width=30)
        self.path_entry.grid(row=0, column=1)
        self.path_entry.config(width=60)
        self.path_button = tk.Button(self.main_frame, text="Pfad auswählen", command=self.choose_path)
        self.path_button.grid(row=0, column=2)
        # Tooltip für Pfad
        self.create_tooltip(self.path_label, "Hier den Dateipfad eingeben oder auswählen (Meist TRXXXX/Tests/TESTNAME  Endung /TestRuns ist auch zulässig oder direkt ein TestRun Ordner mit Endung /TRXX.TestRun auswählen (keine Überprüfung ob TestRun läuft), ansonsten wird nach dem TestRun gefragt).")

        # Beschreibung für Datei
        #self.file_label = tk.Label(self.main_frame, text="Datei wird nach dem Starten des Skripts ausgewählt")
        #self.file_label.grid(row=2, column=0, sticky="w")

        self.filex_var = tk.StringVar(value="n")
        self.daqminmax_checkbox = tk.Checkbutton(self.main_frame, text="daqMinMaxActivity1.h5 und cyclicDaqActivity überlagern ", variable=self.filex_var, onvalue="daqMinMaxActivity1.h5", offvalue="n")
        self.daqminmax_checkbox.grid(row=0, column=3)
        ueberlagert_tooltip=("cyclicDaqActivity1-Daq(1).h5 und daqMinMaxActivity1.h5 können überlagert werden."
                            " Allerdings momentan nur in einem sehr kleinen Bereich, da es sonst zu lange dauert (ca. 15min für 30MB) und nur wenn beide Dateien vorhanden sind,"
                            " sonst wird nach Starten nach einer anderen Datei gefragt (Plot wird nicht gespeichert)")
        self.create_tooltip(self.daqminmax_checkbox, ueberlagert_tooltip)

        # Wertebereich einschränken
        self.wertebereich_label = tk.Label(self.main_frame, text="Wertebereich einschränken:")
        self.wertebereich_label.grid(row=4, column=0, columnspan=3, sticky="w")

        # Prozent min
        self.wertebereich_prozent_min_label = tk.Label(self.main_frame, text="Prozent Min:")
        self.wertebereich_prozent_min_label.grid(row=5, column=0, sticky="w")
        self.wertebereich_prozent_min_entry = tk.Entry(self.main_frame)
        self.wertebereich_prozent_min_entry.insert(0, "0")
        self.wertebereich_prozent_min_entry.grid(row=5, column=1)

        # Prozent max
        self.wertebereich_prozent_max_label = tk.Label(self.main_frame, text="Prozent Max:")
        self.wertebereich_prozent_max_label.grid(row=5, column=2, sticky="w")
        self.wertebereich_prozent_max_entry = tk.Entry(self.main_frame)
        self.wertebereich_prozent_max_entry.insert(0, "100")
        self.wertebereich_prozent_max_entry.grid(row=5, column=3)
        wertetext=( "Bezieht sich auf die Sessions. Wenn zB 10 Sessions vorhanden sind und man eingibt: von 99 bis 100, dann zeigt es alle Daten in der letzten Session (also 10%)."
                   "Das heißt, dass das Programm erst bei einer gewissen Anzahl von Sessions wirklich kleinere Prozentangaben wahrnimmt")
        self.create_tooltip(self.wertebereich_prozent_min_label, wertetext)
        
        #PLot-darstellungseinstellungen
        self.plotting_label = tk.Label(self.main_frame, text="Plotten:")
        self.plotting_label.grid(row=7, column=0, sticky="w")
        self.plotting_var = tk.StringVar(value="einzelne Datenpunkte")  
        self.plotting_combobox = ttk.Combobox(self.main_frame, textvariable=self.plotting_var, values=[ "einzelne Datenpunkte", "verbundene Datenpunkte","kein Plotten"], state="readonly")
        self.plotting_combobox.grid(row=7, column=1, columnspan=7, sticky="w")
        plottext = ("Hier können Sie auswählen, wie die Daten geplottet werden sollen. "
            "Sie haben die Möglichkeit, die einzelnen Datenpunkte entweder zu "
            "verbinden oder einzeln darzustellen.")
        self.create_tooltip(self.plotting_label,plottext)
        
        #x-Achse auswählen
        self.x_label = tk.Label(self.main_frame, text="x-Achse:")
        xText= ("Hier kann man auswählen ob die Daten über der Zeit, den Segmenten, den Zyklen(Segmente/2) oder den Datenpunkten geplottet werden, soweit die Kanäle vorhanden sind."
                " Die Default-Einstellung wählt die passende Skalierung für den ausgewählten Dateityp.")
        self.create_tooltip(self.x_label,xText)
        self.x_label.grid(row=7, column=2, sticky="w")
        self.plottime_var = tk.StringVar(value="default")
        self.combobox_time = ttk.Combobox(self.main_frame, textvariable=self.plottime_var,values=["default","Zeit","Segmente","Data Points","Zyklen"], state="readonly")
        self.combobox_time.grid(row=7, column=3, columnspan=3, sticky="w")

        #Andere Variablen?
        self.var_label = tk.Label(self.main_frame, text="Mehrere Variablen:")
        self.var_label.grid(row=8, column=0, sticky="w")
        self.create_tooltip(self.var_label,'Wenn es Variablen außerhalb von Kraft und Weg gibt, werden diese angezeigt, und Sie können auswählen, welche Sie plotten möchten')
        
        self.var_var = tk.StringVar(value="keine anderen Kanäle")  # Standardwert auf "y" setzen
        self.var_Combobox = ttk.Combobox(self.main_frame, textvariable=self.var_var,values=["keine anderen Kanäle", "auswählen", "alle anderen Kanäle"], state="readonly")
        self.var_Combobox.grid(row=8, column=1, columnspan=3, sticky="w")
        
        #Alle Dateien eines TestRuns auswerten
        self.tst_label=tk.Label(self.main_frame, text="Alle Dateien des TestRuns:")
        self.tst_label.grid(row=8, column=2, sticky="w")
        self.tst_var=tk.StringVar(value="")
        self.tst_checkbutton = tk.Checkbutton(self.main_frame,  variable=self.tst_var, onvalue="y", offvalue="")
        self.tst_checkbutton.grid(row=8, column=3, columnspan=3, sticky="w")
        tsttext="Wenn dieser Button aktiviert ist muss nur noch ein TestRun ausgewählt werden und alle dort befindlichen Dateien werden ausgewertet. Eine txt-Datei kann auch generiert werden zu jeder H5 Date."
        self.create_tooltip(self.tst_label,tsttext)
        
        #Alle TestRuns aneinanderhängen
        self.alltst_label=tk.Label(self.main_frame,text="Alle TestRuns auswerten")
        self.alltst_label.grid(row=8, column=3,sticky= "e", padx=(6, 0))
        self.alltst_var=tk.StringVar(value="")
        self.alltst_checkbutton = tk.Checkbutton(self.main_frame,  variable=self.alltst_var, onvalue="y", offvalue="")
        self.alltst_checkbutton.grid(row=8, column=4, columnspan=3, sticky="w")
        alltext="Es werden alle TestRuns ausgewertet. Dabei kann man sich noch für einen Dateitypen entscheiden, der in jedem TestRun vorhanden ist und diese zusammengefügten Dateien mit dem Txt-File Button in einer Txt Datei speichern. Falls es viele TestRuns gibt oder die Dateien sehr groß sind kann das Ausführen der Funktion sehr lange dauern. "
        self.create_tooltip(self.alltst_label,alltext)
        
        #modify variablen
        self.modify_var = tk.StringVar(value="n")  # Standardwert auf "y" setzen
        self.modify_checkbutton = tk.Checkbutton(self.main_frame, text="Kanäle modifizieren", variable=self.modify_var, onvalue="y", offvalue="n")
        self.modify_checkbutton.grid(row=9, column=0, columnspan=4, sticky="w")
        modify_tooltip_text = (
            "Wenn 'Kanäle modifizieren' aktiviert ist:\n"
            "Es werden 2 txt-Dateien der Kanäle des ausgewählten Files erstellt:\n"
            "1. 'Alle Kanäle.txt' wird immer erstellt (wird immer überschrieben).\n"
            "2. 'Kanäle modified.txt':\n"
            "   wird erstellt oder kann modifiziert werden falls schon vorhanden, dafür Kanäle löschen und Datei speichern und schließen."
        )
        
        
        
        self.create_tooltip(self.modify_checkbutton, modify_tooltip_text)
        #Zykluenmitzähler
        self.zykl_var = tk.StringVar(value="n")  
        self.zykl_checkbutton = tk.Checkbutton(self.main_frame, text="Zyklen mitzählen", variable=self.zykl_var, onvalue="y", offvalue="n")
        self.zykl_checkbutton.grid(row=10, column=0, columnspan=4, sticky="w")
        #Statistikoptionen
        self.statistik_option_label = tk.Label(self.main_frame, text="Statistikauswertung:")
        self.statistik_option_label.grid(row=11, column=0, sticky="w")
        
        self.statistik_option_var = tk.StringVar(value="keine")
        self.statistik_option_combobox = ttk.Combobox(self.main_frame, textvariable=self.statistik_option_var, values=["keine", "Kompaktzangenversuch", "anderer Versuch"], state="readonly")
        self.statistik_option_combobox.grid(row=11, column=1)
        self.create_tooltip(self.statistik_option_label, " Struktur: der Sollwert (egal ob min/max oder valley min/max) wird automatisch als Maximum und Minimum aufgefasst Bsp: sollwert_Fcirc = 12.64 bedeutet: sollwert_Fcirc Maximum= 12.64 kN // sollwert_Fcirc Minimum = -12.64 kN Statistik: Angelehnt an Norm DIN 50100 - 95% der Werte sollten sich in einem Toleranzband von ±3% der Lastamplitude befinden.(Deswegen muss man auch die Valleys angeben, da man sonst nicht die Lastamplitude bestimmen kann.")
        
        self.set_variables_button = tk.Button(self.main_frame, text="Variablen setzen zur Auswertung aller Kanäle", command=self.set_multiple_variables)
        self.set_variables_button.grid(row=12, column=2, columnspan=2)
        
        #Plots Speichern
        self.save_plots_var = tk.StringVar(value="n")  
        self.save_plots_checkbox = tk.Checkbutton(self.main_frame, text="Plots speichern", variable=self.save_plots_var, onvalue="y", offvalue="n")
        self.save_plots_checkbox.grid(row=12, column=0, columnspan=4, sticky="w")
        self.create_tooltip(self.save_plots_checkbox,"Die angezeigten Plots werden in dem Dateipfad gespeichert falls sie noch nicht existieren. Der Dateiname setzt sich aus dem TestRun + dem Dateityp + dem ChannelNamen (+ dem Wertebereich falls dieser nicht von 0 bis 100 ist) zusammen")
        
        #interaktive Plots speichern
        self.int_plots_var= tk.StringVar(value="n")
        self.int_checkbox=tk.Checkbutton(self.main_frame,text ="Interkative Plots speichern", variable=self.int_plots_var, onvalue="y", offvalue="n")
        self.int_checkbox.grid(row=12,column=1,sticky="w")
        self.create_tooltip(self.int_checkbox, text="Der erstelle Plot kann im interaktiven html-Format gespeichert werden. Weil diese Dateien aber sehr groß werden und lange zum öffnen brauchen , geht diese Funktion nur bis zu einer Ursprungsdateigröße von 10MB")
        #Session Anzahl anzeigen lassen
        self.session_var= tk.StringVar(value="")
        self.checkbox_session= tk.Checkbutton(self.main_frame,text="Anzahl der Sessions ausgeben",variable=self.session_var,onvalue="y",offvalue="")
        self.checkbox_session.grid(row=13,column=0,columnspan=1,sticky="w")
        #Button für csv-File erstellen
        self.csv_var=tk.StringVar(value="")
        self.checkbox_csv=tk.Checkbutton(self.main_frame,text="Txt-File der Daten erstellen", variable=self.csv_var,onvalue="y",offvalue="")
        self.checkbox_csv.grid(row=14,column=0,columnspan=1,sticky="w")
        tooltext=("Die daten der HDF5 dateien werden in einem mit Leerzeichen separiertem Txt.-File ausgegeben und können dadurch in Excel dargestellt werden. Zudem kann man eine Anzahl an gültigen Ziffern eingeben auf die gerundet werden kann, damit die Dateigröße reduziert wird."
                  " z.B verursachen 6 stat 9-17 gültigen Ziffern eine 40% kleinere Datei. "
                  "Diese Funktion verlängert die Ausführungszeit des Programms deutlich")
        self.create_tooltip(self.checkbox_csv, tooltext)
        #Button zum Starten des Skripts
        self.start_button = tk.Button(self.main_frame, text="Skript starten", command=self.run_script)
        self.start_button.grid(row=14, column=0, columnspan=4)
    

        # Textausgabe hier wird das Design der Ausgabe festgelegt
        self.output_frame = tk.Frame(self.main_frame, padx=10, pady=10)
        self.output_frame.grid(row=15, column=0, columnspan=8, sticky="nsew")

        self.output_text = tk.Text(self.output_frame, wrap=tk.WORD, height=10, width=80, bg="#f0f0f0", fg="#333333", font=("Helvetica", 12), padx=10, pady=10)
        self.output_text.grid(row=0, column=0, sticky="nsew")

        # Scrollbar hinzufügen
        self.scrollbar = tk.Scrollbar(self.output_frame, command=self.output_text.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.output_text.config(yscrollcommand=self.scrollbar.set)

        self.output_text.insert(tk.END, "Hier werden Ausgaben angezeigt.\nInfos zu den Eingaben erscheinen als Tooltip, wenn Sie die Maus über den linken Rand bewegen.\nFür eine allgemeine, schnelle Auswertung Pfad auswählen und danach Skript starten.")

        # Grid-Konfiguration für das Output-Frame
        self.output_frame.grid_rowconfigure(0, weight=1)
        self.output_frame.grid_columnconfigure(0, weight=1)
#################################################################################################
###2. Registerkarte
        
        self.create_plot_frame()
        self.plot_frame.grid_rowconfigure(0, weight=1)  
        self.plot_frame.grid_columnconfigure(0, weight=1) 
#####################################################################################################
###3.Registerkarte
        #self.path_label2 = tk.Label(self.filter_frame, text="Dateipfad:")
        #self.path_label2.grid(row=0, column=0, sticky="w")
        #self.path_entry2 = tk.Entry(self.filter_frame, textvariable=tk.StringVar(), width=30)
        #self.path_entry2.grid(row=0, column=1)
        #self.path_entry2.config(width=60)
        #self.path_button2 = tk.Button(self.filter_frame, text="Pfad auswählen", command=self.choose_path)
        #self.path_button2.grid(row=0, column=2)
        
        
    def create_plot_frame(self):
        # Erstelle einen scrollbaren Canvas für die Plots
        self.plot_canvas = tk.Canvas(self.plot_frame)
        self.plot_canvas.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = tk.Scrollbar(self.plot_frame, orient="vertical", command=self.plot_canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.plot_canvas.configure(yscrollcommand=self.scrollbar.set)
        self.plot_canvas.bind('<Configure>', lambda e: self.plot_canvas.configure(scrollregion=self.plot_canvas.bbox("all")))

        self.plot_container = tk.Frame(self.plot_canvas)
        self.plot_canvas.create_window((0, 0), window=self.plot_container, anchor="nw")

        # Konfiguration des Plot-Containers, um den gesamten Platz auszufüllen
        self.plot_container.grid_rowconfigure(0, weight=1)
        self.plot_container.grid_columnconfigure(0, weight=1)
###########################################################################################       
    def set_multiple_variables(self):
        #Voreinstellungen für schnelle Allgemeinauswertung
        
        self.wertebereich_prozent_min_entry.delete(0, tk.END)
        self.wertebereich_prozent_min_entry.insert(0, "0")
        
        self.wertebereich_prozent_max_entry.delete(0, tk.END)
        self.wertebereich_prozent_max_entry.insert(0, "100") 
        
        self.plotting_var.set("einzelne Datenpunkte")
        self.var_var.set("alle anderen Kanäle") 
        self.modify_var.set("n")  
        self.zykl_var.set("y")  
        self.statistik_option_var.set("keine")
        self.filex_var.set("n")
        self.save_plots_var.set("n")
        self.plottime_var.set("default")
        self.session_var.set("")
        self.csv_var.set("")
        self.tst_var.set("")
        self.alltst_var.set("")
        self.int_plots_var.set("n")
        

    def choose_file(self):
        path = self.path_entry.get()
        chosen_file = self.select_h5_file(path)
        if chosen_file:
            self.selected_file_type.set(chosen_file)    
    def create_tooltip(self, widget, text):
        def enter(event):
            
            self.tooltip.config(text=text)
            self.tooltip.place(x=event.x_root,  y=event.y_root )
            self.tooltip.lift()# Aktualisiere die Position des Tooltips basierend auf der Mausposition
        def leave(event):
            self.tooltip.config(text="")
            self.tooltip.place_forget()  # Verstecke den Tooltip, wenn die Maus das Widget verlässt
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)
        
    def update_tooltip_position(self, event):
        if self.tooltip.winfo_ismapped():
            self.tooltip.place(x=event.x_root , y=event.y_root)
                             
    def insert_output(self, message):
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.yview(tk.END)    
  

    def choose_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
    
    
    def select_h5_file(self, directory):
        h5_files_with_sizes_and_times = [
            f"{file} ({human_readable_size(os.path.getsize(os.path.join(directory, file)), 1)}, ungefähr {berechne_ausfuehrungszeit_poly3(os.path.getsize(os.path.join(directory, file))/1024):.2f} Minuten)"
            for file in os.listdir(directory) if file.endswith(".h5")
        ]
        
        root = tk.Tk()
        root.title("H5-Datei auswählen")
        root.lift()
        
        selected_file = None  # Initialisieren Sie die Variable für die ausgewählte Datei
        file_size = None      # Variable für die Dateigröße
    
        if h5_files_with_sizes_and_times:
            label_text = (
                "Hier die zu analysierende Datei auswählen:\n"
                "Für periodisch getriggerte Dateien: cyclicDaqActivity1-Daq.h5\n"
                "Für Haltedruck-getriggerte Dateien: daqMinMaxActivity.h5\n"
                "Für zeitgetriggerte Dateien: daqTaskActivity.h5\n"
                "(Es wird nicht garantiert, dass Dateien außerhalb dieses Namensschemas verarbeitet werden können)"
            )
            label = tk.Label(root, text=label_text)
            label.pack()
        
            # Combobox für die Auswahl der H5-Datei
            combo = ttk.Combobox(root, values=h5_files_with_sizes_and_times, state="readonly", width=100)
            combo.pack()
        
            def ok():
                nonlocal selected_file, file_size
                selected_file = combo.get().split(' (')[0]  # Setze die ausgewählte Datei
                file_size = os.path.getsize(os.path.join(directory, selected_file))  # Berechne Dateigröße
                print(f"Ausgewählte Datei: {selected_file}")
                print(f"Dateigröße: {file_size}")
                root.quit()  # Beende die mainloop(), um das Fenster zu schließen
        
            button = tk.Button(root, text="OK", command=ok)
            button.pack()
            root.mainloop()  # Starte die Tkinter-Hauptschleife
        else:
            print("Keine H5-Dateien im angegebenen Verzeichnis gefunden.")
        
        root.destroy()  # Schließe das Fenster
    
        return selected_file, file_size
    
    def ask_user_input(self):
        #Funktion für die weitren Variablen
        root.lift()
        
        try:
            user_choice = simpledialog.askstring("Eingabe erforderlich", "Eingabe der Zeilennummer die Sie plotten möchten (Leer lassen oder Abbruch mit Cancel):")
            if user_choice is None or user_choice == "":
                return None
            user_choice = int(user_choice)
            return user_choice
        except ValueError:
            return None      
            
    def select_files_from_list(self,file_list):
        root = tk.Tk()
        root.title("Select Files")
        root.lift()
    
        selected_files = []
    
        if file_list:
            label_text = "Wähle den Daateityp aus, der aus allen TestRuns ausgewertet werden soll. Ein 'ok' ohne auswählen wertet alle Dateien aus:"
            label = tk.Label(root, text=label_text)
            label.pack()
    
            listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, width=100, height=20)
            for file in file_list:
                listbox.insert(tk.END, file)
            listbox.pack()
    
            def ok():
                nonlocal selected_files
                selected_files = [listbox.get(idx) for idx in listbox.curselection()]
                root.quit()
    
            button = tk.Button(root, text="OK", command=ok)
            button.pack()
            root.mainloop()
        else:
            messagebox.showinfo("Info", "No files available for selection.")
    
        root.destroy()
        return selected_files

        

    def run_script(self):
        #Variablen werden hier in die Hauptfunktion übernommen
        statistik_anderer_versuch="n"
        statistik_kompakt="n"
        path0 = self.path_entry.get()  
        chosenFile_extra = self.filex_var.get() 
        ab_wieviel_prozent = float(self.wertebereich_prozent_min_entry.get())
        bis_wieviel_prozent = float(self.wertebereich_prozent_max_entry.get())
        plotting = self.plotting_var.get()
        extra = self.var_var.get()
        modify = self.modify_var.get()
        zykluszähler= self.zykl_var.get()
        statistik_option = self.statistik_option_var.get()
        plots_save=self.save_plots_var.get()
        plot_time=self.plottime_var.get()
        session_var=self.session_var.get()
        write_to_csv=self.csv_var.get()
        tst=self.tst_var.get()
        altst=self.alltst_var.get()
        chosen=None
        decimal_places=2
        intplot=self.int_plots_var.get()
        
        if extra == "keine anderen Kanäle":
            extra="n"
            
        elif extra== "auswählen":
            extra="y"
        else:
            extra="x"
        print(f"extra Kanäle:{extra}")
        #print(f"nachtime:{plot_time}")
        if write_to_csv:
            decimal_places= simpledialog.askstring("Eingabe erforderlich", "Geben Sie ein auf wie viele Nachommastellen Sie die Daten für das Txt-File Runden möchten. Falls Sie die Daten belassen möchten lassen sie das Feld leer oder brechen mit Cancel ab:")
            if decimal_places!= None and decimal_places!= "":
                decimal_places=int(decimal_places)
            else:
                decimal_places=None
        if statistik_option == "Kompaktzangenversuch":
            
            statistik_kompakt="y"

        elif statistik_option == "anderer Versuch":
            
            statistik_anderer_versuch="y"

        elif statistik_option == "keine":
            pass
        
        #if/else Bedingungen um zur richtigen Datei zu kommen
        if path0.endswith('TestRun') or path0.endswith('TestRun/'):
            path = path0 + '/Data/'
        elif path0.endswith('Data'):
            path = path0
        else:
            if path0.endswith('TestFiles') or path0.endswith('TestRuns'):
                path1 = path0
            else:
                path1 = path0 + '/TestRuns/'

            if not path1.endswith('/'):
                path1 += '/'

            os.chdir(path1)
            
            
                
            testRunList = [f for f in os.listdir(path1) if f.startswith("TSR") and f.endswith(".TestRun")]
            testRunList = natsort.natsorted(testRunList)
            
                # Sortiere die TestRuns nach ihrer letzten Bearbeitungszeit
            testRunList_sorted_by_time = sorted(testRunList, key=lambda x: get_last_modified_time(os.path.join(path1, x)))
            if altst == "":
                root = tk.Tk()
                root.withdraw()
                dialog = ScrollableDialog(root, "Verfügbare TestRuns", testRunList)
                chosen = dialog.result
            
                # bei keiner eingabe wird der letzte oder vorletzte testrun ausgewählt, je nach dem wann der letzte testRun 
                #zuletzt bearbeitet wurde (um das abbrechen eines laufenden testruns zu verhindern)
                last_run_time = get_last_modified_time(os.path.join(path1, testRunList_sorted_by_time[-1]))
                time_difference = datetime.now().timestamp() - last_run_time
                if not chosen:
                    
                    if len(testRunList_sorted_by_time) > 1:
                        
                        
                        if time_difference < 60:  # wenn der letzte TestRun vor weniger als 60 Sekunden bearbeitet wurde wird der vorletzte ausgewählt
                            chosen = testRunList_sorted_by_time[-2]
                        else:
                            chosen = testRunList_sorted_by_time[-1]
                if len(testRunList_sorted_by_time)==1:
                        if time_difference > 60:
                            chosen = testRunList_sorted_by_time[-1]
                        else:
                            outm="\n Es existiert nur ein TestRun und dieser läuft gerade oder die Datei wurde vor Kurzem bearbeitet"
                            self.insert_output(outm)
                            chosen=None
                            return
                root.destroy()
                path2 = chosen
                path3 = "/Data/"
                path = path1 + path2 + path3
            else:
                path=path1
        #Handling fürs Plotten da Code angepasst wurde
        if plotting == "einzelne Datenpunkte":
            plot_style="s"
            plotting="y"
        elif plotting =="verbundene Datenpunkte":
            plot_style="l"
            plotting="y"
        else:
            plotting="n"
        
        #print(plotting)
        #print(plot_style)
        start_time = time.time() 
        path=os.path.normpath(path)
        os.chdir(path) # "conditional" statements: ein leerer String ist "False" --> defaultTestRun / ein befüllter String ("11") ist True
        #print(tst)
        if chosenFile_extra != "n":
            chosenFile = "cyclicDaqActivity1-Daq(1).h5"
            print(chosenFile_extra)
            try:
                peak1 = h5py.File(chosenFile, "r")
                print("extra aktiviert")
                peak1_extra = h5py.File(chosenFile_extra,"r")
            except FileNotFoundError:
                #print("xx")
                output_message = "\n cyclicDaqActivity und/oder DaqMinMaxActivity sind nicht vorhanden.\n Bitte eine neue Datei wählen."
                self.insert_output(output_message)
                try:
                    chosenFile1, file_size = self.select_h5_file(path)
                    peak1 = h5py.File(chosenFile1, "r")
                    chosenFile = chosenFile1
                    chosenFile_extra="n"
                    #print(chosenFile)
                    #print(chosenFile_extra)
                except FileNotFoundError:
                    output_message = "\n Alternative Datei auch nicht gefunden."
                    self.insert_output(output_message)
                except NameError:
                    output_message = "\n Ausgewähltes File überprüfen"
                    self.insert_output(output_message)
        
        #Alle Dateien oder ein Dateintyp aus allen TestRuns
        elif altst:
            all_files = []
            unique_files = set()
        
            for test_run in testRunList:
                test_run_path = os.path.join(path1, test_run, "Data")
                if os.path.exists(test_run_path):
                    files = [os.path.join(test_run_path, f) for f in os.listdir(test_run_path) if f.endswith(".h5")]
                    all_files.extend(files)
                    unique_files.update([os.path.basename(f) for f in files])
        
            # Let the user select files from the list
            if  tst== "":
                selected_files, file_size = self.select_files_from_list(list(unique_files))
                print(file_size)
            else:
                selected_files=None
            if not selected_files :
                # If no files are selected, process all files
                files = all_files
            else:
                # Filter all_files to include only the selected files
                files = [f for f in all_files if os.path.basename(f) in selected_files]

            print(f"alle daten{files}")
            
        #wenn alle Dateien aus einem TestRun ausgewertet werden sollen
        elif tst != "":
            files = [os.path.join(path, f) for f in os.listdir(path) if f.endswith(".h5")]
        #Standardauswertung einer Datei   
        else:
            try:
                chosenFile1, file_size = self.select_h5_file(path)
                files = [chosenFile1]
                #peak1 = h5py.File(chosenFile1, "r")
                #print("Inhalt der HDF5-Datei:")
                #peak1.visit(print)
                #chosenFile = chosenFile1
            except FileNotFoundError:
                output_message = "\n Keine Datei gefunden."
                self.insert_output(output_message)
            except NameError:
                output_message = "\n Ausgewähltes File überprüfen"
                self.insert_output(output_message)
                
        # Schleife für Auswertung mehrerer Dateien im TestRun
        for chosenFile in files:
            print(f"die ausgewählte Datei: {chosenFile}")
            dateiname = os.path.basename(chosenFile)
            print(dateiname)
            peak1 = h5py.File(chosenFile, "r")
            file_size = os.path.getsize(chosenFile)/ (1024 * 1024) 
            """ Spaltennamen der "Signals"...Ziel: ['Name', 'Identifier', 'Dimension', 'Unit'] """
            #Einlesen der Kanäle aus der ersten Session
            sign = peak1.get("Session0000000000000000/Signals")  # .get() wird verwendet, um auf Datensätze oder Gruppen in HDF5-Dateien zuzugreifen. Hier wird der Datensatz namens 'Signals' abgerufen, welcher sich im Pfad Session0000000000000000/ befindet. Um die Struktur zu sehen --> sign.value in Konsole eingeben. Hier wird nur die erste Session gewählt, da die 'Signals' (Kanalnamen) bei jeder Session die gleichen sind
            #print(sign[:])  # sign[:] in Konsole --> Struktur des arrays der Kanalnamen sichtbar
            head = str (sign.dtype)  # ergibt: {'names': ['Name', 'Identifier', 'Dimension', 'Unit'], 'formats': ['O', 'O', 'O', 'O'], 'offsets': [0, 16, 32, 48], 'itemsize': 64}  // .dtype zeigt den Struktur des arrays auf (hier jeweils auf die 4 Spalten bezogen). "name" ≙ Name // "formats" ≙ Datentyp; 'O' bedeutet Datentyp "Python Objekt" // "offsets"  ≙ Speicherort innerhalb des Speicherblocks des arrays // "itemsize" ≙ Größe der Elemente in Bytes
            head = [item for item in re.findall(r'\b[A-Z][a-z]*\b', head) if item not in ["names", "formats", "offsets", "itemsize", "O"]]  # hier wird aus dem unübersichtlichen Ausdruck vorheriger Zeile folgender erstellt: ['Name', 'Identifier', 'Dimension', 'Unit']
            
            """ Spaltennamen der "Signals" mit Daten der "Signals" zusammenfügen """
            sign0 = [tuple(elem.decode() if isinstance(elem, bytes) else elem for elem in tpl) for tpl in sign]  # um zu verstehen --> sign[:] in Konsole // vereinfacht wird hier wird der array sign in eine Liste umgewandelt
            sign = np.array(head)
            
            
            for item in sign0:
                row = list(item)  # Konvertieren Sie das Tupel in eine Liste
                if len(row) == 4:  # Nur Zeilen mit genau 4 Elementen hinzufügen
                    sign = np.vstack((sign, row))
                else:
                    print(f"Skipping row with unexpected length: {row}")
            
            print("Final array:", sign)
    
            NEWsign = sign
            
            """ Textfile input/output """
            
            if modify == "y":
                
                os.chdir(path1)
                with open(f"{chosenFile} - Alle Kanäle.txt", "w") as f:
                    f.write(chosen)
                    f.write("\n")
                    for i, row in enumerate(NEWsign):
                        formated_row=[f"{value:^30}" for value in row] 
                        formated_row_string = "|".join(formated_row)
                        f.write(str(formated_row_string) + "\n")  # hier werden die Kanalnamen in das Textfile eingelesen
                        if i == 0:  # nach den Spaltenbezeichnungen eine Zeile frei lassen (übersichtlich)
                            f.write("\n")
                
    
                if os.path.exists(f"{chosenFile} - Kanäle modified.txt"):
                    choice = messagebox.askokcancel("Datei existiert", f"Die Datei {chosenFile} - Kanäle modified.txt existiert bereits. Wollen Sie sie ansehen bzw. modifizieren?")
        
                    if choice:  # Benutzer hat "OK" gewählt
                        subprocess.call(["notepad.exe", f"{chosenFile} - Kanäle modified.txt"], shell=True)
                        sign_dataframe = pd.read_csv(f"{chosenFile} - Kanäle modified.txt", delimiter="|", skipinitialspace=True, header=None)
                        NEWsign = np.array(sign_dataframe)
                        NEWsign = NEWsign.astype(str)
                        NEWsign = np.char.strip(NEWsign)
                        output_message = "\nSie können die Kanäle nun modifizieren.\n"
                        self.output_text.insert(tk.END, output_message)
                    else:  # Benutzer hat "Cancel" gewählt
                        sign_dataframe = pd.read_csv(f"{chosenFile} - Kanäle modified.txt", delimiter="|", skipinitialspace=True, header=None)
                        NEWsign = np.array(sign_dataframe)
                        NEWsign = NEWsign.astype(str)
                        NEWsign = np.char.strip(NEWsign)
                        output_message = f"Datei {chosenFile} - Kanäle modified.txt wird ohne Modifikation wieder eingelesen.\n"
                        self.output_text.insert(tk.END, output_message)
                        
                else:
                    with open(f"{chosenFile} - Kanäle modified.txt", "w") as f:  # Create a new file if it doesn't exist
                        for i, row in enumerate(NEWsign):
                            formated_row = [f"{value:^30}" for value in row]
                            formated_row_string = "|".join(formated_row)
                            f.write(str(formated_row_string) + "\n")
                            if i == 0:
                                f.write("\n")
                    output_message="Datei " f"\n{chosenFile} - Kanäle modified.txt" " noch nicht vorhanden. Kanäle werden ausgelesen und in txt File dargestellt, wo Sie modifiziert werden können.\n"
                    self.output_text.insert(tk.END, output_message)
                    subprocess.call(["notepad.exe", f"{chosenFile} - Kanäle modified.txt"], shell=True)
            
                    sign_dataframe = pd.read_csv(f"{chosenFile} - Kanäle modified.txt", delimiter="|", skipinitialspace=True, header=None)
                    NEWsign = np.array(sign_dataframe)
                    NEWsign = NEWsign.astype(str)
                    NEWsign = np.char.strip(NEWsign)
                
            """ Force/Displacement/Segment/Time Indizes """
            
            fidx=np.where(NEWsign=="force")  # np.where(), um die Indizes der Elemente im 'sign' array zu erhalten, welche dem string 'force' entsprechen. where() ergibt immer einen "tuple of arrays"; jeder array ist dabei den Indizes der "True" Übereinstimmungen zugeordnet. In diesem Fall ergibt fidx: (array([1, 2, 3, 4, 5], dtype=int64), array([2, 2, 2, 2, 2], dtype=int64)). Vertikal Zeile 1-5, Horizontal nur Spalte 2 (Nachvollziehbar im HDF5 Viewer oder wenn sign in der Konsole ausgegeben wird) 
            fidx=fidx[0]-1
            #print(f"kraftidx:{fidx}")# Nur der erste array wird weiterverarbeitet ([0]) ; bei diesem wird jeder Eintrag um 1 verringert --> array([0, 1, 2, 3, 4], dtype=int64)
            didx=np.where(NEWsign=="length") 
            didx=didx[0]-1      
            cidx=np.where(NEWsign=="segment_count") 
            cidx=cidx[0]-1
            #print(f"segmentidx:{cidx}")
            tidx=np.where(NEWsign=="time")
            tidx=tidx[0]-1
            #print(f"timeidx:{tidx}")
            
            grps1 = list(peak1.keys())
            #print(f"grps1:{grps1}")# Liste mit allen Sessions
            maxSessions = grps1.__len__()
            if session_var:
             outputmessage=f"\n\nAnzahl der Sessions:{maxSessions}\n" # Länge der Liste entspricht Anzahl der Sessions
             self.output_text.insert(tk.END, outputmessage)
            marker1 = int((ab_wieviel_prozent / 100) * maxSessions)  
            marker2 = int((bis_wieviel_prozent / 100) * maxSessions)
            
            """ Daten der einzelnen Sessions werden zusammengefügt """
            
            gp1 = peak1.get(grps1[marker1])  # ruft das Objekt (Gruppe oder Datensatz...Aufbau HDF5!) auf Position 'marker1' in der Liste grps1 ab. (Das Objekt ist in diesem Fall eine Gruppe...zu sehen mit type (gp1))         gp1.keys() in Konsole
            scan = np.array(gp1.get("Scans"))  # .get('Scans') ruft den Datensatz Scans in der Gruppe gp1 auf. Das erste Element muss seperat ausgegeben werden, damit die while-Schleife funktioniert (warum?)
            i=marker1+1 
            scan_list = [scan]
            #debugging für Werte der Kanäle
            #print(f"scan shape: {scan.shape}")
            #print(f"scan sample: {scan[:5]}")
    
            
            while marker1 < i < marker2:  # oben definierte Grenzen bestimmen Bereich der Iteration
                gp2 = peak1.get(grps1[i])  # gleiche Schritte wie oben
                scan2 = np.array(gp2.get("Scans"))
                scan_list.append(scan2)
                i+=1
            scan = np.vstack(scan_list)  # vstack nur einmal ganz am Ende, da dies viel Rechenkapa benötigt (mitunter Grund für die lange Ladezeit, da es ursprünglich bei jeder while-Iteration verwendet wurde). (Listenoperationen sind schneller)
            #print(f"scan shape aller sessions: {scan.shape}")
            #print(f"Alle daten: {scan}")
            
            if modify == "y":
                deleted_row_indices = np.where(~np.isin(sign, NEWsign))[0]-1  # Vorher/Nachher Vergleich (welche Kanalzeilen rausgelöscht wurden)
                deleted_row_indices = np.unique(deleted_row_indices)[::-1]  # array reverse: sonst stimmen die Indizes nicht, da Array modifiziert wird und die Indizes sonst auf dem modifizierten Array basieren...--> von hinten
                
                for deleted_row_index in deleted_row_indices:
                    scan = np.delete(scan, deleted_row_index, axis=1)
            
            
            #Ab hier wird das txtFile mit den Daten der Sessions erstellt und die Daten werden wenn gewünscht gerundet
            
            def extract_test_run_from_path(chosenFile):
                # Normalize the path to handle different separators
                normalized_path = os.path.normpath(chosenFile)
                
                # Split the path to get the directory containing the TestRun
                parts = normalized_path.split(os.sep)
                
                # Find the index where 'Data' is located
                if 'Data' in parts:
                    data_index = parts.index('Data')
                    
                    # The TestRun directory is immediately before 'Data'
                    test_run_directory = parts[data_index - 1]
                    
                    # Extract the part containing TestRun
                    return test_run_directory
                
                return None
            
            # Example usage
            if altst:
                chosen = extract_test_run_from_path(chosenFile)
            def round_to_significant_figures(number, sig_figs):
                if number == 0:
                    return 0
                else:
                    return round(number, sig_figs - int(math.floor(math.log10(abs(number)))) - 1)
            
            def replace_dots_with_commas(row, sig_figs=None):
                rounded_row = []
                for item in row:
                    # Check if the item can be converted to a float
                    try:
                        number = float(item)
                        if sig_figs is not None:
                            number = round_to_significant_figures(number, sig_figs)
                        item = str(number)
                    except ValueError:
                        pass
                    rounded_row.append(item.replace('.', ','))
                return rounded_row
            if write_to_csv:
                originalpath = path
                if chosen is not None:
                    csvFile = f"{chosenFile}_{chosen}.txt"
                else:
                    folder = os.path.normpath(path).split(os.sep)
                    lfolder = folder[-1]
                    print(lfolder)
                    csvFile = f"{chosenFile}_{lfolder}.txt"
            
                # Set the path to path0 for saving the CSV file
                path = os.path.normpath(path0)
                os.chdir(path)
            
                if altst and selected_files:
                    csvFile = f"{selected_files[0]}_All_Data.txt"
                    with open(csvFile, 'w', newline='') as file:
                        writer = csv.writer(file, delimiter=' ')
                        first_line_written = False
                        for file_path in files:
                                if not first_line_written:
                                    first_line = [row[0] for row in NEWsign]
                                    first_line.pop(0)
                                    writer.writerow(first_line)
                                    first_line_written = True
            
                                for row in scan:
                                    writer.writerow(replace_dots_with_commas(row, decimal_places))
                                writer.writerow("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx") #xxxx trennen zwei eingelesene Dateien im tst-file
                else:
                    with open(csvFile, 'w', newline='') as file:
                        writer = csv.writer(file, delimiter=' ')
                        first_line = [row[0] for row in NEWsign]
                        first_line.pop(0)
                        writer.writerow(first_line)
                        for row in scan:
                            writer.writerow(replace_dots_with_commas(row, decimal_places))
            
                #print("ready")
                path = originalpath
                os.chdir(path)
                #print("Aktuelles Arbeitsverzeichnis:", os.getcwd())
            
            
            
            """Für den Fall, dass ""cyclicDaqActivity1-Daq(1).h5"" und ""daqMinMaxActivity1.h5"" zusammen geplottet werden sollen"""
            if chosenFile_extra == "daqMinMaxActivity1.h5" :
                try:
                    #print("yx")
                    sign_extra = peak1_extra.get("Session0000000000000000/Signals")
                    head_extra = str (sign_extra.dtype)
                    head_extra = [item for item in re.findall(r'\b[A-Z][a-z]*\b', head_extra) if item not in ["names", "formats", "offsets", "itemsize", "O"]]
                    sign0_extra = [tuple(elem.decode() if isinstance(elem, bytes) else elem for elem in tpl) for tpl in sign_extra]
                    sign_extra = np.array(head_extra)
                    
                    for item in sign0_extra:
                        row = re.split("[()',]+", str(item))
                        row = row[1:(len(row)):2]
                        sign_extra = np.vstack((sign_extra,row))
                    
                    NEWsign_extra = sign_extra
                    
                    fidx_extra=np.where(NEWsign_extra=="force")
                    fidx_extra=fidx_extra[0]-1
                    didx_extra=np.where(NEWsign_extra=="length") 
                    didx_extra=didx_extra[0]-1      
                    cidx_extra=np.where(NEWsign_extra=="segment_count") 
                    cidx_extra=cidx_extra[0]-1
                    tidx_extra=np.where(NEWsign_extra=="time")
                    tidx_extra=tidx_extra[0]-1
                    
                    grps1_extra = list(peak1_extra.keys())
                    maxSessions_extra = grps1_extra.__len__()
                    
                    marker1_extra = int(((ab_wieviel_prozent) / 100) * maxSessions_extra)  
                    marker2_extra = int(((bis_wieviel_prozent) / 100) * maxSessions_extra)
                    
                    gp1_extra = peak1_extra.get(grps1_extra[marker1_extra])
                    scan_extra = np.array(gp1_extra.get("Scans"))
                    i=marker1_extra+1
                    scan_list_extra = [scan_extra]
                    
                    while marker1_extra < i < marker2_extra:
                        gp2_extra = peak1_extra.get(grps1_extra[i])
                        scan2_extra = np.array(gp2_extra.get("Scans"))
                        scan_list_extra.append(scan2_extra)
                        i+=1
                        
                    scan_extra = np.vstack(scan_list_extra)
                    
                    peak1_extra.close()
                
                except NameError:
                        pass
                    
            peak1.close() 
            if tst == "":# wichtig für Datensicherung, Entsperrung, und Freigabe dem Objekt zugewiesener Ressourcen
                plt.close("all")  # schließt alle offenen Matplotlib Diagrammfenster. Nicht gespeicherte, offene Diagramme gehen verloren.
            
            ####################################################################################################################################################################################################################################################################################################################################################################
            """ PLOTTING - graphische Darstellung """
            
            if plotting == "y":
                try:
                    xvals = np.arange(len(scan) + len(scan_extra))+1  # für den Fall, dass cyclic und minmax file beide "aktiviert" werden
                except NameError:
                    xvals = np.arange(len(scan))+1  # Falls keine zB Segments im Kanal-Array sind, wird einfach über die Datenpunkte selber geplottet
              
                def create_plot(fig_num, plottype, ylabel_multiplier, ylabel_zusatz, plot_style,plot_time):
                    plt.close(fig_num) 
                    fig, pl = plt.subplots(len(plottype), sharex=True, figsize=(14, 8), facecolor="white", num=fig_num)
                    # Convert to list if only one axis is present
                    if len(plottype) == 1:
                        pl = [pl]
                    print(f"plottype:{plottype}")
                    for idx, i in enumerate(plottype):
                        ax = pl[idx]
                        title = NEWsign[i + 1][0]
                        additional_info = NEWsign[i + 1][1]
                        ax.set_title(f"Name: {title}\nIdentifier: {additional_info}", fontsize=10)
                        values = scan[:, plottype[idx]] * ylabel_multiplier
                        #print(values)
                        y_label=ylabel_zusatz + NEWsign[i + 1][3]
                        ax.set_ylabel(y_label, fontsize=10)
                        ax.grid(True)
                        #print(f"plottype is {plottype} with length {len(plottype)}")
                        
                        running_time_idx = np.where((NEWsign[:, 1] == "Running Time"))[0]
                        if dateiname.startswith("cyclicDaqActivity") or chosenFile.startswith('customDaqActivity'):
                            if plot_time=="Zeit" and len(tidx!=0):
                                if running_time_idx.size>0:
                                    x=running_time_idx[0]-1
                                else:
                                    x=tidx[0]
                                x_axis=scan[:,x]
                                x_Label=NEWsign[x + 1][3]
                                #outmessage=f"genutzter Zeitkanal {NEWsign[x+1]}"
                                #self.insert_output(outmessage)
                            elif plot_time=="Data Points":
                                x_axis=xvals
                                x_Label="Data Points"
                            elif plot_time=="Zyklen" and len(cidx!=0):
                                x=cidx[0]
                                x_axis=scan[:,x]
                                x_axis = x_axis / 2
                                x_Label="Zyklen"
                            else:
                                x=cidx[0]
                                x_axis=scan[:,x]
                                x_Label=NEWsign[x + 1][3]
                            if plot_style == 's':
                                ax.scatter(x_axis, values, c="blue")
                            elif plot_style == 'l':
                                ax.plot(x_axis,values, c="blue")
                            ax.set_xlabel(x_Label, fontsize=10) if len(plottype) == 1 else pl[-1].set_xlabel(x_Label, fontsize=10)
                    
                        elif dateiname.startswith("daqMinMaxActivity"):
                            values_to_plot = values[(values <= 1e7) & (values >= -1e7)]
                            xvals_to_plot = xvals[(values <= 1e7) & (values >= -1e7)]
                            if plot_time=="Zeit" and len(tidx!=0):
                                if running_time_idx.size>0:
                                    x=running_time_idx[0]-1
                                else:
                                    x=tidx[0]
                                #outmessage=f"genutzter Zeitkanal {NEWsign[x+1]}"
                                #self.insert_output(outmessage)
                                x_axis=scan[:,x]
                                x_Label=NEWsign[x + 1][3]
                            elif plot_time=="Segmente" and len(cidx!=0):
                                x=cidx[0]
                                x_axis=scan[:,x]
                                x_Label=NEWsign[x + 1][3]
                            elif plot_time=="Zyklen" and len (cidx!=0):
                                x=cidx[0]
                                x_axis=scan[:,x]
                                x_axis = x_axis / 2
                                x_Label="Zyklen"
                                
                            else:
                                x_axis=xvals_to_plot
                                x_Label="Data Points"
                            if plot_style == 's':
                                ax.scatter(x_axis, values_to_plot, c="blue")
                            elif plot_style == 'l':
                                ax.plot(x_axis, values_to_plot, c="blue")
                            ax.set_xlabel(x_Label, fontsize=10) if len(plottype) == 1 else pl[-1].set_xlabel(x_Label, fontsize=10)
                    
                        elif dateiname.startswith("daqTaskActivity"):
                            
                            #print(f"Running time index: {running_time_idx}")
                            #print(len(tidx))
                            
                            if  plot_time=="Zeit" or plot_time=="default" and len(tidx!=0):
                                if len(running_time_idx) > 0 :
                                    x = running_time_idx[0]-1 
                                else:
                                    x=tidx[0]
                                x_axis=scan[:, x]
                                #outmessage=f"genutzter Zeitkanal {NEWsign[x+1]}"
                                #self.insert_output(outmessage)
                                x_Label=NEWsign[x + 1][3]
                            elif plot_time=="Segmente" and len(cidx!=0) :
                                x=cidx[0]
                                x_axis=scan[:,x]
                                x_Label=NEWsign[x + 1][3]
                            elif plot_time=="Zyklen" and len (cidx!=0):
                                x = cidx[0]  
                                x_axis = scan[:, x]
                                x_axis = x_axis / 2  
                                x_Label="Zyklen"
                                
                            else: 
                                x_axis=xvals
                                x_Label="Data Points"
                            if plot_style == 's':
                                ax.scatter(x_axis, values, c="blue")
                            elif plot_style == 'l':
                                ax.plot(x_axis, values, c="blue") 
                            
                            ax.set_xlabel(x_Label, fontsize=10) if len(plottype) == 1  else pl[-1].set_xlabel(x_Label, fontsize=10)
                            #print(x_Label)
                    fig.tight_layout(pad=2)
                    plot_canvas = FigureCanvasTkAgg(fig, master=self.plot_container)
                    
                    plot_canvas.draw()
                    plot_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.Y, expand=False, padx=1, pady=1)
                    plot_canvas.get_tk_widget().config(width=1100, height=590)

                    # Toolbar hinzufügen
                    toolbar_frame = tk.Frame(self.plot_container)
                    toolbar_frame.pack(side=tk.TOP, fill=tk.X)  # Toolbar oberhalb des Plots positionieren
                    toolbar = NavigationToolbar2Tk(plot_canvas, toolbar_frame)
                    toolbar.update()
                    
                    self.plot_canvas.configure(scrollregion=self.plot_canvas.bbox("all"))  
                    #print(f"chosen ist{chosen}")            
                    if plots_save == 'y':
                        save_folder = path0
                       
                        #for idx, channel_idx in enumerate(plottype):
                        channel_name = NEWsign[i + 1][2]
                        if ab_wieviel_prozent == 0 and bis_wieviel_prozent == 100 and chosen!= None:
                            file_name = f"TestRun{chosen.split('.')[0]}.{dateiname}.{channel_name}.png"
                            #print(file_name)
                        elif chosen==None :
                            file_name = f"{dateiname}.{channel_name}.png"
                        else:
                            file_name = f"TestRun{chosen.split('.')[0]}.{dateiname}.{channel_name}.{ab_wieviel_prozent}.{bis_wieviel_prozent}.png"
                            #save_folder=r"C:/temp/"
                        save_path = os.path.join(save_folder, file_name)
                        #print(save_path)
                            
                        if os.path.exists(save_path):
                                output_message = f"\nDie Datei '{file_name}' existiert bereits in '{save_folder}'. Überspringe das Speichern."
                                self.insert_output(output_message)
                                
                        else:
                                fig.savefig(save_path, dpi=300)
                                output_message = f"\nPlot '{channel_name}' als PNG unter '{save_path}' gespeichert."
                                self.insert_output(output_message)
                    print(f"filesize{file_size}")
                    if intplot=="y" and file_size < 10:
                        save_folder = path0
                        print(chosen)
                        channel_name = NEWsign[i + 1][2]
                        if ab_wieviel_prozent == 0 and bis_wieviel_prozent == 100 and chosen!= None:
                            file_name = f"TestRun{chosen.split('.')[0]}.{dateiname}.{channel_name}.html"
                            #print(file_name)
                        else :
                            file_name = f"{dateiname}.{channel_name}.html"
                        save_int=os.path.join(save_folder, file_name)
                        mpld3.save_html(fig, save_int)
                    
    
                
                def create_plot_combined(fig_num, plottype, plottype_extra, ylabel_multiplier, ylabel_zusatz,plot_style):
                    fig, pl = plt.subplots(len(plottype), sharex=True, figsize=(16, 12), facecolor="white", num=fig_num)
                    for idx, i in enumerate(plottype):
                        ax = pl if len(plottype) == 1 else pl[idx]
                        ax.set_title(NEWsign[i + 1][1], fontsize=10)
                        y_label=ylabel_zusatz + NEWsign[i + 1][3]
                        ax.set_ylabel(y_label, fontsize=10)
                        ax.grid(True)
                        scan_idx = 0
                        scan_extra_idx = 0
                    
                        for i in range(len(xvals)):
                            if i % 40 < 38 and scan_idx < len(scan):  # cyclic file..alle 19 cyclic Werte kommt ein minmax Wert
                              if plot_style=="s":
                                ax.scatter(xvals[i], scan[scan_idx, plottype[idx]] * ylabel_multiplier, c="blue")
                                scan_idx += 1
                              elif plot_style=="l" :
                                  ax.plot(xvals[i], scan[scan_idx, plottype[idx]] * ylabel_multiplier, c="blue")
                                  scan_idx += 1
                            elif scan_extra_idx < len(scan_extra):  # minmax file
                              if plot_style=="s":
                                values = scan_extra[scan_extra_idx, plottype_extra[idx]] * ylabel_multiplier
                                values_to_plot = values[(values <= 1e7) & (values >= -1e7)]
                                xvals_to_plot = xvals[i][(values <= 1e7) & (values >= -1e7)]
                                ax.scatter(xvals_to_plot, values_to_plot, c="red")
                                scan_extra_idx += 1
                              elif plot_style=="l" :
                                  ax.plot(xvals[i], scan[scan_idx, plottype[idx]] * ylabel_multiplier, c="blue")
                                  scan_idx += 1  
                            ax.set_xlabel("data_points", fontsize=10) if len(plottype) == 1 else pl[-1].set_xlabel("data_points", fontsize=10)
                    fig.tight_layout(pad=2)
                        
                
                if chosenFile_extra!= "n":
                  try:
                    if len(fidx) > 0:
                        create_plot_combined("Forces", fidx, fidx_extra, 0.001, "k",plot_style)
                    if len(didx) > 0:
                        create_plot_combined("Strokes", didx, didx_extra, 1000, "m",plot_style)
                  except NameError:
                    print("Problem")
                else:
                    if len(fidx) > 0:  # Force Funktion wird ausgeführt
                        create_plot("Forces", fidx, 0.001, "k",plot_style,plot_time)
                    if len(didx) > 0:  # Strokes Funktion wird ausgeführt
                        create_plot("Strokes", didx, 1000, "m",plot_style,plot_time)
            
            
            
            # PLOT 3 (OTHER)
            
                if extra != "n":
                    plotting_options = list(set(option for option in NEWsign[:, 2] if option not in ["Dimension", "force", "length", "segment_count", "time"]))
                    mid_time=time.time()
                    ex_time1=mid_time-start_time
                    if not plotting_options:
                        output_message = "\nKeine weiteren zu plottenden Variablen gefunden."
                        self.insert_output(output_message)
                    else:
                        indices = []
                        list_of_choices = []
                        output_message = '\n\nWählen Sie eine oder mehrere Zeilennummern aus. Alle Kanäle dieser Dimension werden dargestellt.\n'
                        self.insert_output(output_message)
                        output_message = "\n".join([f"{index}. {row[0]}   (Dimension: {row[2]})" for index, row in enumerate(NEWsign) if row[2] in plotting_options])
                        self.output_text.insert(tk.END, output_message)
                       
                        for index, row in enumerate(NEWsign):
                            if row[2] in plotting_options:
                                indices.append(index)
                        
                        if extra=="x":
                            indices = [index - 1 for index in indices]
                            allidx = np.array(indices, dtype=np.int64)
                            #print(f"alleanderen{allidx}")
                            for ix, idxx in enumerate(allidx):
                                create_plot("Other", [int(idxx)], 1, "", plot_style, plot_time)
                                
                        else:
                            user_choices = []
                            all_options_selected = False  # Variable zur Verfolgung, ob alle verfügbaren Optionen ausgewählt wurden
                            while not all_options_selected:  # Solange nicht alle Optionen ausgewählt wurden
                                try:
                                    user_choice = self.ask_user_input()
                                    if user_choice is None or user_choice == "":
                                        break
                                    user_choice = int(user_choice)
                                    if user_choice in indices:
                                        user_choices.append(user_choice-1) #channel array fängt bei 0 an Benutzereingabe aber bei eins
                                        list_of_choices.append(NEWsign[user_choice][0])
                                        #print(f"User selected channel {user_choice}: {NEWsign[user_choice]}")  # Debug-Ausgabe
                                    else:
                                        output_message = "\nUngültige Eingabe. Bitte geben Sie eine der angezeigten Zeilennummern ein."
                                        self.insert_output(output_message)
                                    # Überprüfen, ob alle verfügbaren Optionen ausgewählt wurden
                                    if len(user_choices) == len(indices):
                                        all_options_selected = True
                                except ValueError:
                                    output_message = "\nUngültige Eingabe. Bitte geben Sie eine ganze Zahl ein."
                                    self.insert_output(output_message)
                                    continue
                            
                            if user_choices:
                                oidx = np.array(user_choices, dtype=np.int64)
                                for ix, idxx in enumerate(oidx):
                                    create_plot("Other", [int(idxx)], 1, "", plot_style, plot_time)
                                    
                
                   
                time2=time.time()
                
   
            ###########################################################################################################################################################################
            """ STATISTIK """
            
            if statistik_kompakt == "y" or statistik_anderer_versuch == "y":  # kompakt =Kompaktzangenversuch am MeP
                
                if statistik_kompakt == "y":
                    sollwert_Fcirc = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Fcirc:")
                    sollwert_Fcirc_valley = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Fcirc_valley:")
                    sollwert_Fjerk = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Fjerk:")
                    sollwert_Fjerk_valley = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Fjerk_valley:")
                    sollwert_Fpad_min = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Fpadmax:")
                    sollwert_Fpad_max = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Fpadmin:")
                    forces_target_values = [(-sollwert_Fcirc, sollwert_Fcirc, -sollwert_Fcirc_valley, sollwert_Fcirc_valley), 
                                            (-sollwert_Fcirc, sollwert_Fcirc, -sollwert_Fcirc_valley, sollwert_Fcirc_valley), 
                                            (-sollwert_Fjerk, sollwert_Fjerk, -sollwert_Fjerk_valley, sollwert_Fjerk_valley), 
                                            (-sollwert_Fjerk, sollwert_Fjerk, -sollwert_Fjerk_valley, sollwert_Fjerk_valley), 
                                            (sollwert_Fpad_min, sollwert_Fpad_max, 0, 0)]  # jeweils: (unterer Sollwert, oberer Sollwert, unteres "load valley", oberes "load valley")
                            
                if statistik_anderer_versuch == "y":
                    kraft1 = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft1:")
                    kraft1_valley = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft1_valley:")
                    kraft2 = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft2:")
                    kraft2_valley = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft2_valley:")
                    kraft3 = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft3:")
                    kraft3_valley = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft3_valley:")
                    kraft4 = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft4:")
                    kraft4_valley = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft4_valley:")
                    kraft5 = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft5:")
                    kraft5_valley = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft5_valley:")
                    kraft6 = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft6:")
                    kraft6_valley = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft6_valley:")
                    kraft7 = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft7:")
                    kraft7_valley = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft7_valley:")
                    kraft8 = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft8:")
                    kraft8_valley = simpledialog.askfloat("Eingabe erforderlich", "Eingabe von Kraft8_valley:")
                    forces_target_values = []
    
                    if kraft1 is not None and kraft1_valley is not None:
                        forces_target_values.append((-kraft1, kraft1, -kraft1_valley, kraft1_valley))
                    if kraft2 is not None and kraft2_valley is not None:
                        forces_target_values.append((-kraft2, kraft2, -kraft2_valley, kraft2_valley))
                    if kraft3 is not None and kraft3_valley is not None:
                        forces_target_values.append((-kraft3, kraft3, -kraft3_valley, kraft3_valley))
                    if kraft4 is not None and kraft4_valley is not None:
                        forces_target_values.append((-kraft4, kraft4, -kraft4_valley, kraft4_valley))
                    if kraft5 is not None and kraft5_valley is not None:
                        forces_target_values.append((-kraft5, kraft5, -kraft5_valley, kraft5_valley))
                    if kraft6 is not None and kraft6_valley is not None:
                        forces_target_values.append((-kraft6, kraft6, -kraft6_valley, kraft6_valley))
                    if kraft7 is not None and kraft7_valley is not None:
                        forces_target_values.append((-kraft7, kraft7, -kraft7_valley, kraft7_valley))
                    if kraft8 is not None and kraft8_valley is not None:
                        forces_target_values.append((-kraft8, kraft8, -kraft8_valley, kraft8_valley))
    
                        
                
                
                def analyze_data(plottype, y_label_multiplier, target_values):
                    
                    if forces_target_values == [(),(),(),()]:
                        
                        output_message = "Vermutlich keine Sollwerte deklariert, keine Statistik verfügbar.\n"
                        self.output_text.insert(tk.END, output_message)
                        return
                    
                    for idx, i in enumerate(plottype):
                        
                        subplot_data = scan[:, i] * y_label_multiplier
                        
                        try: 
                            min_target_value_range, max_target_value_range, valley_value_lower, valley_value_upper = target_values[idx]
                        except IndexError:
                            return
                        
                        min_target_value_lower_threshold = min_target_value_range - 0.03 * abs(((abs(min_target_value_range) - abs(valley_value_lower)) / 2))
                        min_target_value_upper_threshold = min_target_value_range + 0.03 * abs(((abs(min_target_value_range) - abs(valley_value_lower)) / 2))
                        max_target_value_lower_threshold = max_target_value_range - 0.03 * abs(((abs(max_target_value_range) - abs(valley_value_upper)) / 2))
                        max_target_value_upper_threshold = max_target_value_range + 0.03 * abs(((abs(max_target_value_range) - abs(valley_value_upper)) / 2))
                        
                        min_target_value_lower_threshold_valley = valley_value_lower - 0.03 * abs(((abs(min_target_value_range) - abs(valley_value_lower)) / 2))
                        min_target_value_upper_threshold_valley = valley_value_lower + 0.03 * abs(((abs(min_target_value_range) - abs(valley_value_lower)) / 2))
                        max_target_value_lower_threshold_valley = valley_value_upper - 0.03 * abs(((abs(max_target_value_range) - abs(valley_value_upper)) / 2))
                        max_target_value_upper_threshold_valley = valley_value_upper + 0.03 * abs(((abs(max_target_value_range) - abs(valley_value_upper)) / 2))
                        
                        count_min_target = 0
                        count_max_target = 0
                        count_min_target_valley = 0
                        count_max_target_valley = 0
                        
                        for value in subplot_data:
            
                            if min_target_value_lower_threshold <= value <= min_target_value_upper_threshold:
                                count_min_target += 1
                            if max_target_value_lower_threshold <= value <= max_target_value_upper_threshold:
                                count_max_target += 1
                            if min_target_value_lower_threshold_valley <= value <= min_target_value_upper_threshold_valley:
                                count_min_target_valley += 1
                            if max_target_value_lower_threshold_valley <= value <= max_target_value_upper_threshold_valley:
                                count_max_target_valley += 1
                        
                        total_values = len(subplot_data)
                        
            
                        percentage_min_target = (count_min_target / (total_values/4)) * 100  # es wurden KEINE Einzel-Arrays erstellt; deswegen wird die Gesamt-Datenmenge durch 4 geteilt, (min, max, min_valley und max_valley) um zu sehen, wie viele Werte im definierten Band sein SOLLTEN
                        percentage_max_target = (count_max_target / (total_values/4)) * 100
                        percentage_min_target_valley = (count_min_target_valley / (total_values/4)) * 100
                        percentage_max_target_valley = (count_max_target_valley / (total_values/4)) * 100
                        
                        Kanalname = NEWsign[i + 1][1]
                        output_message=f"\n Subplot {idx + 1} ({Kanalname}) Statistik: \n Prozentsatz der Werte innerhalb Sollwert (Minimum): {percentage_min_target:.1f}% \n Prozentsatz der Werte innerhalb Sollwert (Maximum): {percentage_max_target:.1f}% \n Prozentsatz der Werte innerhalb Sollwert (Minimum valley): {percentage_min_target_valley:.1f}% \n Prozentsatz der Werte innerhalb Sollwert (Maximum valley): {percentage_max_target_valley:.1f}%"
                        self.output_text.insert(tk.END, output_message)
                analyze_data(fidx, 0.001, forces_target_values)  # die Funktion kann auch für die Strokes aufgerufen werden - jedoch ist die Auswertung so wie sie ist aufgrund der Datenstruktur nur bedingt für die Strokes geeignet
            
                
                
                
                
            #############################################################################################
            """ZYKLUSZÄHLER"""
            #print(chosenFile)
            #funktioniert besser (nicht sicher, ob 100% genau...)
            if zykluszähler == "y" and tst== "" and altst=="" :
            
               
                if chosenFile.startswith("cyclicDaqActivity") or chosenFile1.startswith("customDaq"):
                    if len(scan) != 0:  # Überprüfen, ob die Länge von scan nicht Null ist
                        output_message = f"\n Auf Datenpunkte bezogen: Anzahl Zyklen: {int((len(scan)/(2*19))*20)}"
                        self.output_text.insert(tk.END, output_message)
                        output_message = f"\nAuf Kompaktzange (20+1) bezogen: Anzahl Zyklen: {int(len(scan)/2)}"
                        self.output_text.insert(tk.END, output_message)
                    else:
                        output_message = "\n Fehler: Division durch Null"
                        self.output_text.insert(tk.END, output_message)
                elif chosenFile.startswith("daqMinMaxActivity"):
                    if len(scan) != 0:  # Überprüfen, ob die Länge von scan nicht Null ist
                        output_message = f"\n Auf Datenpunkte bezogen: Anzahl Zyklen:{int(len(scan)/2)}"
                        self.output_text.insert(tk.END, output_message)
                        output_message = f"\nAuf Kompaktzange (20+1) bezogen: Anzahl Zyklen: {int((len(scan)/2)*20)}"
                        self.output_text.insert(tk.END, output_message)
                    else:
                        output_message = "\n Fehler: Division durch Null"
                        self.output_text.insert(tk.END, output_message)
                elif chosenFile.startswith("daqTaskActivity"):
                    try:  # Überprüfen, ob die Länge von scan nicht Null ist und nicht 1830 ist
                        #kurz = int(len(scan)/1830)
                        output_message = f"\nAnzahl Zyklen (Halteruck): {int((len(scan)/1830))}"
                        self.output_text.insert(tk.END, output_message)
                        output_message = f"\nErklärung: {int((len(scan)/1830)*20)} + {int((len(scan)/1830))} = {int((len(scan)/1830)) + int((len(scan)/1830)*20)}  ...  {int((len(scan)/1830)) + int((len(scan)/1830)*20)} / {int(len(scan)/1830)} = {int((int((len(scan)/1830)) + int((len(scan)/1830)*20)) / int(len(scan)/1830))} (weil 20 mal zyklisch + 1 mal Halteruck ergibt 21)"
                        self.output_text.insert(tk.END, output_message)
                    except:
                        output_message = "\n Fehler: Division durch Null oder Scan-Länge ist 1830"
                        self.output_text.insert(tk.END, output_message)
            output_message="\nPlots werden dargestellt. Auswertung ist abgeschlossen"
            self.output_text.insert(tk.END, output_message)
            if bis_wieviel_prozent==100 and ab_wieviel_prozent==0:
                if extra == "y":
                    end_time2=time.time()
                    execution_time=ex_time1+end_time2-time2
                else:
                    end_time = time.time()  # Endzeit messen
                    execution_time = end_time - start_time  # Ausführungszeit berechnen
                outputmessage=f"\n\nAusführungszeit: {execution_time:.2f} Sekunden bei einer Dateigröße von {file_size:.1f} Mb"
                #log_path = r"Z:\Team_Members\Adam_Finn\h5files\h5allgemein\execution_log.txt"  # Ersetzen Sie dies durch den tatsächlichen Pfad
                
                # Daten in die Textdatei schreiben
                #with open(log_path, 'a') as log_file:
                    #log_file.write(f"{execution_time:.2f} \t {file_size * 1024:.1f} \n ")
                self.output_text.insert(tk.END, outputmessage)    
            
            
    
        
    

    
if __name__ == "__main__":
    root = tk.Tk()
    app = HDF5AnalyzerGUI(root)
    root.mainloop()