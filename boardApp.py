import bluetooth
from struct import *
import binascii
import time
from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Progressbar
from tkinter.ttk import *
from tkinter import ttk
from tkinter import filedialog
import threading
from datetime import datetime
import re
import json
import os

class OutputHandler():
	def __init__(self):
		if not os.path.exists("results\\json"):
			os.makedirs("results\\json")
		if not os.path.exists("results\\csv"):
			os.makedirs("results\\csv")
		if not os.path.exists("results\\txt"):
			os.makedirs("results\\txt")

	def setPackets(self, opening_packet, record_packets, closing_packet):
		self.opening_packet = opening_packet
		self.record_packets = record_packets
		self.closing_packet = closing_packet

	def getJsonOutput(self, dt_string):
		self.opening_packet["records_number"] = self.closing_packet["records_number"]
		acquisition_data = {
			"general_infos" : self.opening_packet,
			"acquisitions" : self.record_packets
		}
		with open("results/json/"+ dt_string + "-result.json", "w+") as fp:
			json.dump(acquisition_data, fp)

	def getCsvOutput(self, dt_string):
		file = open("results/csv/"+ dt_string + "-result.csv","w+")
		header = ["TIME_STAMP, \t", "SENSOR_1, \t", "SENSOR_2, \t", "SENSOR_3, \t", "SENSOR_4, \n"]
		file.writelines(header)

		for line in self.record_packets:
			line_values = [];
			line_values.append(str(line["time_stamp"])+ ", \t")
			for pressure_val in line["pressure"]:
				line_values.append(str(pressure_val)+ ", \t")
			line_values.append("\n")
			file.writelines(line_values)

		file.close()

	def getTxtOutput(self, dt_string):
		file = open("results/txt/"+ dt_string + "-result.txt","w+")
		header = ["TIME_STAMP \t", "SENSOR_1 \t", "SENSOR_2 \t", "SENSOR_3 \t", "SENSOR_4 \n"]
		file.writelines(header)

		for line in self.record_packets:
			line_values = [];
			line_values.append(str(line["time_stamp"])+ " \t")
			for pressure_val in line["pressure"]:
				line_values.append(str(pressure_val)+ " \t")
			line_values.append("\n")
			file.writelines(line_values)

		file.close()


class DataHandler():
	def __init__(self, scaleModes):
		self.record_packets = []
		self.packetsProcessed = False
		self.scaleModes = scaleModes

	def setRawData(self, rawData):
		self.rawData = rawData

	def getPackets(self):
		if self.packetsProcessed == False:
			self.processPackets()
		return (self.opening_packet, self.record_packets, self.closing_packet)

	def processPackets(self):
		self.processOpeningPacket()
		self.processRecordPackets()
		self.processClosingPacket()
		self.packetsProcessed = True

	def getIntValFromHex(self, hexVal):
		return int('0x'+hexVal, 0)

	def processOpeningPacket(self):
		raw_opening_packet = re.findall(r'5049.+?4950', self.rawData)[0]
		self.opening_packet = {
			"serial_number": self.getIntValFromHex(raw_opening_packet[4:12]),
			"sampling_frequency": self.getIntValFromHex(raw_opening_packet[12:14]),
			"frequency_unit": "Hz",
			"scale_mode": self.scaleModes[raw_opening_packet[14:16]],
			"version_number": self.getIntValFromHex(raw_opening_packet[16:18]),
			"battery_level": self.getIntValFromHex(raw_opening_packet[18:20]),
			"distance_between_X": self.getIntValFromHex(raw_opening_packet[20:24]),
			"distance_between_Y": self.getIntValFromHex(raw_opening_packet[24:28]),
			"distance_unit": "millisecond",
			"pressure_order": "[sensor 1, sensor 2, sensor 3, sensor 4]",
			"pressure_unit": "Newton"
		}

	def processRecordPackets(self):
		raw_record_packets = re.findall(r'504d.+?4d50', self.rawData)
		
		for packet in raw_record_packets:
			record_number = self.getIntValFromHex(packet[4:12])
			self.record_packets.append(
				{
					"record_number": record_number,
					"time_stamp": record_number / self.opening_packet["sampling_frequency"],
					"pressure": [	self.getIntValFromHex(packet[12:16]), 
									self.getIntValFromHex(packet[16:20]), 
									self.getIntValFromHex(packet[20:24]), 
									self.getIntValFromHex(packet[24:28])
								]
				}
			)

	def processClosingPacket(self):
		raw_closing_packet = re.findall(r'5052.+?5250', self.rawData)[0]
		self.closing_packet = {
			"records_number": self.getIntValFromHex(raw_closing_packet[4:12])
		}


class GuiHandler:
	def __init__(self, board_handler, data_handler, output_handler):
		self.board_handler = board_handler
		self.data_handler = data_handler
		self.output_handler = output_handler

	def initWindow(self):
		# create a window
		self.window = Tk() 
		self.window.title("UTT board App")

		# set grid columns config
		self.window.grid_columnconfigure(index=0, weight=10, minsize=150)
		self.window.grid_columnconfigure(index=1, weight=10, minsize=150)
		self.window.grid_columnconfigure(index=2, weight=10, minsize=150)
		# self.window.grid_columnconfigure(index=3, weight=10, minsize=150)

		# set grid rows config
		self.window.grid_rowconfigure(index=0, weight=10, minsize=30)
		self.window.grid_rowconfigure(index=1, weight=10, minsize=30)
		self.window.grid_rowconfigure(index=2, weight=10, minsize=30)
		self.window.grid_rowconfigure(index=3, weight=10, minsize=30)
		self.window.grid_rowconfigure(index=4, weight=10, minsize=50)

		# step label
		self.step = StringVar()
		self.step.set("Board disconnected")
		step_label = Label(self.window, textvariable=self.step, font=("Arial", 10)) 
		step_label.grid(column=0, row=4, columnspan=3)

		# acquisition type selection
		# label
		acquisition_type_label = Label(self.window, text="Acquisition type", font=("Arial", 10)) 
		acquisition_type_label.grid(column=0, row=0, sticky=W) 

		# set possible values (Timed acquisition, Manual acquisition)		
		self.acquisition_type_value = StringVar()
		acquisition_type_combo = Combobox(self.window, textvariable = self.acquisition_type_value, state = 'readonly') 
		acquisition_type_combo['values']= ("Timed acquisition", "Manual acquisition")
		acquisition_type_combo.current(0) 
		acquisition_type_combo.grid(column=1, row=0, sticky=W)

		# acquisition length setting
		# label
		acquisition_length_label = Label(self.window, text="Acquisition length (s)", font=("Arial", 10)) 
		acquisition_length_label.grid(column=0, row=1, sticky=W) 

		# define entry to set value
		self.acquisition_length_value = Entry(self.window) 
		self.acquisition_length_value.grid(column=1, row=1, sticky=W)
		self.acquisition_length_value.focus()

		# output format selection
		self.output_format_value = StringVar()
		json_radio_button = Radiobutton(self.window,text = 'JSON', value = 'JSON', variable = self.output_format_value) 
		csv_radio_button = Radiobutton(self.window,text = 'CSV', value = 'CSV', variable = self.output_format_value) 
		txt_radio_button = Radiobutton(self.window,text = 'txt', value = 'TXT', variable = self.output_format_value)
		 
		json_radio_button.grid(column=0, row=2) 
		csv_radio_button.grid(column=1, row=2) 
		txt_radio_button.grid(column=2, row=2)

		# command buttons
		connect_btn = Button(self.window, text="Connect board", command = self.connect_btn_clicked)
		connect_btn.grid(column=0, row=3)

		# disconnect_btn = Button(self.window, text="Disconnect board", command = self.disconnect_btn_clicked)
		# disconnect_btn.grid(column=1, row=3)

		start_btn = Button(self.window, text="Start acquisition", command = self.start_btn_clicked)
		start_btn.grid(column=1, row=3)

		stop_btn = Button(self.window, text="Stop acquisition", command = self.stop_btn_clicked)
		stop_btn.grid(column=2, row=3, ipadx=10)

		self.window.mainloop()

	def connect_btn_clicked(self):
		self.board_handler.connect()
		self.step.set("Board connected")

	# def disconnect_btn_clicked(self):
	# 	self.board_handler.disconnect()

	def start_btn_clicked(self):
		if self.acquisition_type_value.get() == "Timed acquisition":
			self.processTimedAcquisition(float(self.acquisition_length_value.get()))
		else:
			t = threading.Thread(target=self.processNonTimedAcquisition)
			t.start()

	def processTimedAcquisition(self, timeout_val):
		self.board_handler.processTimedAcquisition(timeout_val)
		self.processRawData()
		self.step.set("Acquisition finished!")
		
	def processNonTimedAcquisition(self):
		self.step.set("Acquisition in progress... click on the stop button to finish it")
		self.board_handler.processNonTimedAcquisition()
		self.processRawData()
		self.step.set("Acquisition finished!")

	def stop_btn_clicked(self):
		self.board_handler.stopAcquisition()

	def processRawData(self):
		raw_data = self.board_handler.getRawData()
		self.data_handler.setRawData(raw_data)
		opening_packet, record_packets, closing_packet = self.data_handler.getPackets()
		self.output_handler.setPackets(opening_packet, record_packets, closing_packet)
		self.processOutput()
		self.board_handler.reset()

	def processOutput(self):
		now = datetime.now()
		dt_string = now.strftime("%Y-%m-%d-%Hh%M")

		if self.output_format_value.get() == "JSON":
			self.output_handler.getJsonOutput(dt_string)
		elif self.output_format_value.get() == "CSV":
			self.output_handler.getCsvOutput(dt_string)
		else:
			self.output_handler.getTxtOutput(dt_string)

class BoardHandler:
	def __init__(self):
		self.socket = bluetooth.BluetoothSocket( bluetooth.RFCOMM )
		self.suffix = "5250".encode('utf-8')
		self.buffer = ""
		self.acquisitionStopped = False

	def connect(self):
		try : 
		    print ("connecting to the board...")
		    self.socket.connect(("94:21:97:60:14:D6", 1))
		    print ("connected!")
		except bluetooth.BluetoothError : raise
		return True

	def disconnect(self):
		self.socket.close()
		print ("disconnected")

	def startAcquisition(self):
		print ("Start acquisition...")
		self.socket.send(bytes.fromhex('52 53'))

	def stopAcquisition(self):
		print ("Stop acquisition...")
		self.socket.send(bytes.fromhex('53 50'))

	def getData(self):
		data = self.socket.recv(1024)
		hexlifyedData = binascii.hexlify(bytes(bytearray(data)))
		self.buffer += hexlifyedData.decode('utf-8')
		if hexlifyedData.endswith(self.suffix):
			self.acquisitionStopped = True

	def processTimedAcquisition(self, timeout_val):
		# self.connect()
		try:
		    self.startAcquisition()
		    timeout = time.time() + timeout_val
		    while True:
		        self.getData()
		        if self.acquisitionStopped:
		            break
		        if time.time() > timeout:
		            self.stopAcquisition()
		except IOError:
		    pass

	def processNonTimedAcquisition(self):
		try:
			self.startAcquisition()
			while True:
				self.getData()
				if self.acquisitionStopped:
					break
		except IOError:
			pass

	def getRawData(self):
		return self.buffer

	def reset(self):
		self.buffer = ""
		self.acquisitionStopped = False

def main():
	scaleModes =	{
					  "50": "Normal mode",
					  "46": "Real-time mode"
					}

	board_handler = BoardHandler()
	data_handler = DataHandler(scaleModes)
	output_handler = OutputHandler()
	gui = GuiHandler(board_handler, data_handler, output_handler)
	gui.initWindow()

if __name__ == "__main__":
	main()