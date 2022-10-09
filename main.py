from multiprocessing.connection import Client
from tkinter import scrolledtext
import whisper
import pyaudio
import wave
import time
from tkinter import *
from tkinter import ttk
from pythonosc.udp_client import SimpleUDPClient
from array import array


max_value = 0
recording = False
running = False
timestamp = time.time() -1
talking = False
frames = []
stream = ""
PYstream = ""
model = whisper.load_model("base") # model = whisper.load_model("base")
translateSpeach = False
chosenLanguage =  None
languages = {"Autodetect": None, "English": "en", "Dutch": "nl", "German": "de", "Japanese": "ja", "Chinese": "zh", "Spanish": "es", "Italian": "it", "Russian": "ru", "Swedish": "sv", "Norwegian": "no", "Icelandic": "is"}
languagesDropDown = ["Autodetect", "English", "Dutch", "German", "Japanese", "Chinese", "Spanish" , "Italian", "Russian" , "Swedish" , "Norwegian", "Icelandic"]


p = pyaudio.PyAudio()

info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')

devices = []
dictionary = {}


defaultDevice = p.get_default_input_device_info()
deviceId = defaultDevice['index']

for i in range(0, numdevices):
    if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
        devices.append(p.get_device_info_by_host_api_device_index(0, i).get('name'))
        dictionary[p.get_device_info_by_host_api_device_index(0, i).get('name')] = i
p.terminate()


class LogBox:
    def __init__(self, textbox: Text) -> None:
        self._textbox = textbox
        self._textbox.configure(state='disabled')

    def insert(self, text: str) -> None:
        self._textbox.configure(state='normal')
        self._textbox.insert(END, text)
        self._textbox.configure(state='disabled')
        self._textbox.see(END)


def setOSCClient():
    global ip
    global port
    global client
    client = SimpleUDPClient(ip.get(), port.get()) 

def toggleTranslate():
    global translateVar
    global translateSpeach
    if (translateVar.get() == 0):
        translateSpeach = False
    else:
        translateSpeach = True 


def getLanguage(selection):
    global languages
    global chosenLanguage
    chosenLanguage = languages[selection]
    # print(chosenLanguage)

def getInput(selection):
    global dictionary
    global deviceId
    deviceId = dictionary[selection]

def startToggle():
    global startStopButton
    global running

    if (running == False):
        running = True
        startStopButton['text'] = "Stop"

    else:
        running = False
        startStopButton['text'] = "Start"

def STT():
    try:
        global running
        global recording
        global deviceId
        global max_value
        global timestamp
        global talking
        global frames
        global stream
        global PYstream
        global gate
        global thresHold
        global translateSpeach
        global chosenLanguage
        global model
        global statusLabel


        if (running == True):
            statusLabel['text'] = f"running: {running}"
            statusLabel['foreground'] = "Green" 
            thresHold = int(gate.get())
            if (recording == False):
                PYstream = pyaudio.PyAudio()

                stream = PYstream.open(format=pyaudio.paInt16, channels=1, input_device_index=deviceId, rate=44100, input=True, frames_per_buffer=1024)
                recording = True
                # print("ran")

            else:
                data = stream.read(1024)
                as_ints = array('h', data)
                max_value = max(as_ints)

                # print(timestamp - time.time())

                if (timestamp < time.time()):
                    # print(talking)
                    if (talking == True):
                        talking = False
                        client.send_message("/chatbox/typing", False)  
                        voiceActivityLabel['text'] = f"Voice activity: {talking}"
                        voiceActivityLabel['foreground'] = "Red" 
                        if (recording == True):
                            recording = False
                            stream.stop_stream()
                            stream.close()
                            PYstream.terminate()

                            soundFile = wave.open("rec.wav", "wb")
                            soundFile.setnchannels(1)
                            soundFile.setsampwidth(PYstream.get_sample_size(pyaudio.paInt16))
                            soundFile.setframerate(44100)
                            soundFile.writeframes(b''.join(frames))
                            soundFile.close()

                            # load audio and pad/trim it to fit 30 seconds
                            audio = whisper.load_audio("rec.wav")
                            audio = whisper.pad_or_trim(audio)

                            # make log-Mel spectrogram and move to the same device as the model
                            mel = whisper.log_mel_spectrogram(audio).to(model.device)

                            # decode the audio
                            if (translateSpeach == True):
                                options = whisper.DecodingOptions(task="translate", language=chosenLanguage)
                            else:
                                options = whisper.DecodingOptions(language=chosenLanguage)



                            result = whisper.decode(model, mel, options)

                            # print the recognized text
                            if(chosenLanguage == None):
                                # detect the spoken language
                                _, probs = model.detect_language(mel)
                                # print(f"Detected language: {max(probs, key=probs.get)}")
                                textbox.insert("\n-" + f"{max(probs, key=probs.get)}" + " " + result.text)
                            else:
                                textbox.insert("\n-" + result.text)

                            # print(result.text)
                            client.send_message("/chatbox/input", (result.text, True))  
                            frames = []
                            
                        else:
                            PYstream = pyaudio.PyAudio()
                            stream = PYstream.open(format=pyaudio.paInt16, channels=1, input_device_index=6, rate=44100, input=True, frames_per_buffer=1024)
                            recording = True

                
                if (talking == True):
                    frames.append(data)
                
                if (thresHold != ""):
                    if (max_value > thresHold):

                        # print(max_value)
                        timestamp = time.time() + 1 

                        if (talking == False):
                            talking = True
                            client.send_message("/chatbox/typing", True)  
                            voiceActivityLabel['text'] = f"Voice activity: {talking}"
                            voiceActivityLabel['foreground'] = "Green" 
        else:
            statusLabel['text'] = f"running: {running}"
            statusLabel['foreground'] = "Red" 
    except KeyboardInterrupt:
        pass
    root.after(10, STT)


root = Tk()
root.title("OpenSTT-OSC")

mainframe = ttk.Frame(root, padding="3 3 12 12")
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))

root.grid_columnconfigure(0, weight=1)
root.grid_rowconfigure(0, weight=1)
root.resizable(width = False, height = False)

textboxItem = scrolledtext.ScrolledText(mainframe, width=70, height=20, state="disabled")
textbox = LogBox(textboxItem)
optionMenu = ttk.OptionMenu(mainframe, StringVar(root, defaultDevice['name']), defaultDevice['name'],  *devices, command=getInput)
optionMenuLanguage = ttk.OptionMenu(mainframe, StringVar(root, languagesDropDown[0]), languagesDropDown[0],  *languagesDropDown, command=getLanguage)
statusLabel = ttk.Label(mainframe, foreground="Red",text=f"Running: {running}")
voiceActivityLabel = ttk.Label(mainframe, foreground="Red",text=f"Voice activity: {talking}")
startStopButton = ttk.Button(mainframe, text="Start", command=startToggle)

ip = StringVar(mainframe, "127.0.0.1")
port = IntVar(mainframe, 9000)
client = SimpleUDPClient("127.0.0.1", 9000) 
gate = StringVar(mainframe, 1500)
style = ttk.Style()

translateVar = IntVar()
checkBox = ttk.Checkbutton(mainframe, variable=translateVar, command=toggleTranslate)

textbox.insert("- First transcription might be slow.\n- This program uses Cuda.\n  and might impact performance.\n- Translation is not very accurate.")



style.configure("startButton", foreground="white", background="Green")

startStopButton.grid(column=1, row=14, sticky="W")

ttk.Label(mainframe, text="Input:").grid(column=1, row=1, sticky="SW")
optionMenu.grid(column=1, row=2, sticky="NW")
ttk.Label(mainframe, text="Translate speech (EN ONLY):").grid(column=1, row=3, sticky="SW")
checkBox.grid(column=1, row=4, sticky="SW")
ttk.Label(mainframe, text="Spoken language:").grid(column=1, row=5, sticky="SW")
optionMenuLanguage.grid(column=1, row=6, sticky="NW")
ttk.Label(mainframe, text="Ip:").grid(column=1, row=7, sticky="SW")
ttk.Entry(mainframe, text=ip).grid(column=1, row=8, sticky="NWE")
ttk.Label(mainframe, text="Port:").grid(column=1, row=9, sticky="SW")
ttk.Entry(mainframe, text=port).grid(column=1, row=10, sticky="NWE")
ttk.Button(mainframe, text="Set OSC Parameters", command=setOSCClient).grid(column=1, row=11, sticky="SW")
ttk.Label(mainframe, text="Input sensitivity (gate):").grid(column=1, row=12, sticky="SW")
ttk.Entry(mainframe, text=gate).grid(column=1, row=13, sticky="NWE")
ttk.Label(mainframe, text="Output:").grid(column=2, row=1, sticky="NWSE")
statusLabel.grid(column=3, row=14, sticky="W")
voiceActivityLabel.grid(column=2, row=14, sticky="W")
textboxItem.grid(column=2, row=2, columnspan=2, rowspan=11, sticky="NWSE")


for child in mainframe.winfo_children(): 
    child.grid_configure(padx=5, pady=5)

# root.bind("<Return>", start)

root.after(100, STT)
root.mainloop()