import configparser
import glob
import os
import pygame
import RPi.GPIO as GPIO
import socket
import threading
import time


#################################################################################
# I/O is active low.                                                            #
#################################################################################
ON = 0
OFF = 1


#################################################################################
# I/O Terminal Definitions                                                      #
#################################################################################
IN1 = 29
IN2 = 31
IN3 = 33
IN4 = 35
IN5 = 37
IN6 = 32
IN7 = 36
IN8 = 38
START = 40
STOP = 22
UNMOUNT = 16

ledDriveMounted = 15
ledReady = 13
ledPlaying = 11


#################################################################################
# Initialize I/O                                                                #
#################################################################################
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

GPIO.setup(IN1,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(IN2,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(IN3,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(IN4,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(IN5,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(IN6,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(IN7,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(IN8,GPIO.IN,pull_up_down=GPIO.PUD_UP)
        
GPIO.setup(START,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(STOP,GPIO.IN,pull_up_down=GPIO.PUD_UP)
GPIO.setup(UNMOUNT,GPIO.IN,pull_up_down=GPIO.PUD_UP)

GPIO.setup(ledDriveMounted,GPIO.OUT)
GPIO.setup(ledReady,GPIO.OUT)
GPIO.setup(ledPlaying,GPIO.OUT)

GPIO.output(ledDriveMounted,OFF)
GPIO.output(ledReady,OFF)
GPIO.output(ledPlaying,OFF)


#################################################################################
# Initialize Variables                                                          #
#################################################################################
IO_Configured = False
FILE = 0
LAST_FILE = 0
NEXT_FILE = 1
PLAYING = False
READY = False
USB_Mounted = False


#################################################################################
# Initialize pygame                                                             #
#################################################################################
pygame.mixer.init()


#################################################################################
# Folders and files                                                             #
#################################################################################
folderUSB = "/media/pi/MEDIA"
folderMedia = folderUSB + "/snd"
fileConfiguration = folderUSB + "/Config.txt"


#################################################################################
# Check if a configuration file exists and retrieve configuration.              #
# Create one if it doesn't.                                                     #
#################################################################################
def CheckConfig(USB_Mounted, READY):
    if (USB_Mounted == True):
        if (READY == False):
            if (os.path.isfile(fileConfiguration)):
                print("Checking config")
                READY = True

                config = configparser.ConfigParser()
                config.read(fileConfiguration)

                global MODE
                MODE = config['Configuration']['MODE']

                global LAST_FILE
                LAST_FILE = config['Configuration']['LAST_FILE']
                LAST_FILE = int(LAST_FILE)
                
                global INTERRUPT
                INTERRUPT = config['Configuration']['INTERRUPT']
                INTERRUPT = INTERRUPT.lower() in ("true")


                if (MODE != "Binary") and (MODE != "Direct") and (MODE != "Sequential") and (MODE != "UDP"):
                    print ("Mode not set.")
                    READY = False

                if (INTERRUPT != False) and (INTERRUPT != True):
                    print ("Interrupt not set.")
                    READY = False

                if (READY == True):
                    toggle(ledReady, "ledReady", ON)

                print ("MODE:", MODE)
                print ("INTERRUPT:", INTERRUPT)

            else:
                toggle(ledReady, "ledReady", OFF)
        
                print("Creating default configuration file...")
        
                file = open(fileConfiguration, "w")
                file.write("[Configuration]\n\n")
                file.write("#################################################################################\n")
                file.write("# MODE = Binary, Direct, Sequential or UDP                                      #\n")
                file.write("# The audio player will always accept UDP triggers.                             #\n")
                file.write("# Setting the mode to UDP only disables the physical inputs.                    #\n")
                file.write("#################################################################################\n")
                file.write("MODE = Direct\n\n")
                file.write("#################################################################################\n")
                file.write("# LAST_FILE (Optional) specifies the last file to be played before starting     #\n")
                file.write("# at 1. There may be situations where additional files are loaded but only      #\n")
                file.write("# needed at special times. Those files would be numbered higher than LAST_FILE. #\n")
                file.write("#################################################################################\n")
                file.write("LAST_FILE = 0\n\n")
                file.write("#################################################################################\n")
                file.write("# INTERRUPT - Allow active files to be interrupted.                             #\n")
                file.write("#################################################################################\n")
                file.write("INTERRUPT = True\n\n")
                file.close()
    else:
        if (READY == True):
            READY = False
            toggle(ledReady, "ledReady", OFF)

    return READY


#################################################################################
# Check if USB drive is mounted.                                                #
#################################################################################
def CheckUSB(USB_Mounted):
    if (os.path.exists(folderUSB)):
        if (USB_Mounted == False):
            print ("USB drive detected.")
            USB_Mounted = True
            toggle(ledDriveMounted, "ledDriveMounted", ON)
    else:
        if (USB_Mounted == True):
            print ("USB drive has been removed.")
            USB_Mounted = False
            toggle(ledDriveMounted, "ledDriveMounted", OFF)

    return USB_Mounted


#################################################################################
# Get player status.                                                            #
#################################################################################
def GetPlayerStatus(PLAYING):
    if (pygame.mixer.music.get_busy() == True):
        if (PLAYING == False):
            toggle(ledPlaying, "ledPlaying", ON)
            PLAYING = True
    else:
        if (PLAYING == True):
            PLAYING = False
            print ("File has finished playing.")
            toggle(ledPlaying, "ledPlaying", OFF)

    return PLAYING

#################################################################################
# Play file.                                                                    #
#################################################################################
def Play(FILE):
    strFILE = str(FILE)

    if (PLAYING == False) or ((PLAYING == True) and (INTERRUPT == True)):
        for file in os.listdir(folderMedia):        
            if file.endswith(strFILE):
                strFile = folderMedia + "/" + file
                print ("Loading and playing " + strFile)

                if (PLAYING == True) and (INTERRUPT == True):
                    pygame.mixer.music.stop()

                pygame.mixer.music.load(strFile)
                pygame.mixer.music.play()
                GetPlayerStatus(PLAYING)

#################################################################################
# Read inputs.                                                                  #
#################################################################################
def ReadInputs(MODE, NEXT_FILE):
    FILE = 0

    if (MODE == "Binary"):
        if (GPIO.input(IN1) == ON):
            FILE = FILE + 1

        if (GPIO.input(IN2) == ON):
            FILE = FILE + 2

        if (GPIO.input(IN3) == ON):
            FILE = FILE + 4

        if (GPIO.input(IN4) == ON):
            FILE = FILE + 8

        if (GPIO.input(IN5) == ON):
            FILE = FILE + 16

        if (GPIO.input(IN6) == ON):
            FILE = FILE + 32

        if (GPIO.input(IN7) == ON):
            FILE = FILE + 64

        if (GPIO.input(IN8) == ON):
            FILE = FILE + 128


    if (MODE == "Direct"):
        if (GPIO.input(IN1) == ON):
            FILE = 1

        if (GPIO.input(IN2) == ON):
            FILE = 2

        if (GPIO.input(IN3) == ON):
            FILE = 3

        if (GPIO.input(IN4) == ON):
            FILE = 4

        if (GPIO.input(IN5) == ON):
            FILE = 5

        if (GPIO.input(IN6) == ON):
            FILE = 6

        if (GPIO.input(IN7) == ON):
            FILE = 7

        if (GPIO.input(IN8) == ON):
            FILE = 8

    if (MODE == "Sequential"):
        if (GPIO.input(START) == ON):
            FILE = NEXT_FILE

    return FILE


#################################################################################
# Receive UDP                                                                    #
#################################################################################
def recv_udp():
    while True:
        UDP_FILE, addr = sock.recvfrom(1024)
        UDP_FILE = str(UDP_FILE)
        UDP_FILE = UDP_FILE.replace("b'", "")
        UDP_FILE = UDP_FILE.replace("'", "")
        UDP_FILE = int(UDP_FILE)
        Play(UDP_FILE)


#################################################################################
# Stop file.                                                                    #
#################################################################################
def Stop():
    
    pygame.mixer.music.stop()


#################################################################################
# Turn an I/O point on or off.                                                  #
#################################################################################
def toggle(IO, Tag, State):
    if (State == OFF) and (GPIO.input(IO) == ON):
        GPIO.output(IO, State)
        print ("Turned", Tag, "OFF.")

    if (State == ON) and (GPIO.input(IO) == OFF):
        GPIO.output(IO, State)
        print ("Turned", Tag, "ON.")        


#################################################################################
# Main Loop                                                                     #
#################################################################################
try:
    # Initialize and start UDP.
    UDP_PORT = 1111
    UDP_IP = ""
    UDP_FILE = 0

    sock = socket.socket(socket.AF_INET,
                         socket.SOCK_DGRAM)

    sock.bind((UDP_IP, UDP_PORT))

    thread_udp = threading.Thread(name='UDP', target=recv_udp)
    thread_udp.start()

    while True:
        USB_Mounted=CheckUSB(USB_Mounted)
        READY = CheckConfig(USB_Mounted, READY)
        PLAYING = GetPlayerStatus(PLAYING)
        
        if (READY == True):
            if (PLAYING == False) or ((PLAYING == True) and (INTERRUPT == True)):
                FILE = ReadInputs(MODE, NEXT_FILE)

            if ((PLAYING == True) and ((GPIO.input(STOP) == ON) or (GPIO.input(UNMOUNT) == ON))):
                Stop()

        if (FILE != 0):
            Play(FILE)

            while (GPIO.input(START) == ON):
                time.sleep(0.1)

            if (MODE == "Sequential"):
                NEXT_FILE = NEXT_FILE + 1

                if (NEXT_FILE > LAST_FILE):
                    NEXT_FILE = 1

            while (FILE != 0):
                FILE = ReadInputs(MODE, NEXT_FILE)
                time.sleep(0.375)

        time.sleep(0.025)

finally:
    GPIO.cleanup()
