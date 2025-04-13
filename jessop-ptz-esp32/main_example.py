#
# Copyright (c) 2006-2019, RT-Thread Development Team
#
# SPDX-License-Identifier: MIT License
#
# Change Logs:
# Date           Author       Notes
# 2019-09-27     SummerGift   first version
#

# import time
# from machine import Pin
# led = Pin(2, Pin.OUT)  # create LED object from pin2,Set Pin2 to output

# while True:
#     led.value(1)  # Set led turn on
#     time.sleep(0.5)
#     led.value(0)  # Set led turn off
#     time.sleep(0.5)


# Connect to WiFi
import network
ssid = "awong6test"  # Replace with your WiFi SSID
password = "password312"  # Replace with your WiFi password

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(ssid, password)

# Wait for connection
while not wifi.isconnected():
    pass

print("Connected to WiFi")
print("Network config:", wifi.ifconfig())

PAYLOAD_TYPES = {
    "VISCA COMMAND": [0x01, 0x00],
    "VISCA INQUIRY": [0x01, 0x10],
    "VISCA REPLY": [0x01, 0x11],
    "VISCA DEVICE SETTING COMMAND": [0x01, 0x20],
    "CONTROL COMMAND": [0x02, 0x00],
    "CONTROL REPLY": [0x02, 0x01],
}

PANTILT_DIRECTIONS = {
    "Up": [0x03, 0x01],
    "Down": [0x03, 0x02],
    "Left": [0x01, 0x03],
    "Right": [0x02, 0x03],
    "UpLeft": [0x01, 0x01],
    "UpRight": [0x02, 0x01],
    "DownLeft": [0x01, 0x02],
    "DownRight": [0x02, 0x02],
    "Stop": [0x03, 0x03],
}


import asyncio
# class PayloadHeader:
#     def __init__(self):
#         self._buffer = [0x00] * 8

#     @property
#     def seq_no(self):
#         return self._headerBuffer[0]


# class Payload:
#     _header: PayloadHeader
#     def __init__(self, data):
#       self._payloadBuffer = [0x00] * 16
#       self._payloadBufferLen = 1

#     @property
#     def header(self):
#         return self._header

#     @header.setter
#     def set_header(self, value):
#         if len(value) != 8:
#             raise ValueError("Header must be 8 bytes long")
#         self._headerBuffer = value
    
#     @property
#     def payload(self):
#         return self._payloadBuffer

#     @payload.setter
#     def set_payload(self, value):
#         if len(value) < 1 or len(value) > 16:
#             raise ValueError("Payload must be between 1 and 16 bytes long")
#         self._payloadBuffer = value
#         self._payloadBufferLen = len(value)
COMMAND_BUFFER = [None, None]
PTZ_COMMAND = [

    # Payload type
    0x01, 0x00, 

    # Payload length
    0x00,      0x09,

    # seqno, u32 MSB / LSB?
    0x00, 0x00, 0x00, 0x00,

    ##### PAYLOAD
    0x81, 0x01, 0x06, 0x01, 
    0x01, 0x01, # Pan Speed, Tilt Speed
    0x01, 0x03, # Direction
    0xFF
]


import struct



PTZ_INQUIRY = [
    # Payload type
    0x01, 0x10, 

    # Payload length
    0x00,      0x05,

    # seqno, u32 MSB / LSB?
    0x00, 0x00, 0x00, 0x00,

    # 8x 09 06 12 FF     # position     X
    # 8x 09 06 31 FF     # ramp curve   X
    # 8x 09 06 45 FF     # speed step   X
    # 8x 09 06 44 FF     # speed mode   X
    # 8x 09 06 07 0q FF  # limit        X
    0x80, 0x09, 0x06, 0x10, 0xFF     # status       --> y0 50 pp pp FF
                                        # 0b0010 (01/10) 0100010000 
    # 8x 09 06 11 FF     # capability   ?
]

def handleBuffer(buffer, callbackFn=None):
    payloadType = None
    for key, value in PAYLOAD_TYPES.items():
        if buffer[0:2] == value:
            print(f"Payload type: {key}")
            payloadType = key
            break
    if payloadType is None:
        raise ValueError("Invalid Payload Type")

    payloadLength = buffer[3] # 1-16

    payload = buffer[8:8+payloadLength]
    if payloadLength < 1 or payloadLength > 16:
        raise ValueError("Payload should be between 1 and 16 bytes long")
    if payloadLength != len(payload):
        raise ValueError(f"Payload length mismatch: expected {payloadLength}, got {len(payload)}")

    # Irrelevant for control command
    TARGET_CAMERA_ID = payload[0] ^ 0x80
    print("TARGET_CAMERA_ID", TARGET_CAMERA_ID)
    # ignore this id though, assume it's 1
    # also assume the controller is 0

    if payloadType == "VISCA COMMAND":
        SOCKET_NUMBER = 0
        if payload[1:1+3] == [0x01, 0x06, 0x01]:
            print("Pan-Tilt Command")

            direction = None
            for key, value in PANTILT_DIRECTIONS.items():
                if payload[6:6+2] == value:
                    direction = key
                    print(f"Pan-Tilt Direction: {key}")
                    break
            if direction is None:
                print("Invalid Pan-Tilt Direction")
                return PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x60, 0x02, 0xff]
            else:
                panSpeed = payload[4]
                tiltSpeed = payload[5]

                print("Direction", direction)
                print("Pan Speed", panSpeed)
                print("Tilt Speed", tiltSpeed)

                if COMMAND_BUFFER[0] is not None and COMMAND_BUFFER[1] is not None:
                    # Command Buffer Full
                    return PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x60, 0x03, 0xFF]
                else:
                    if COMMAND_BUFFER[0] is None:
                        COMMAND_BUFFER[0] = buffer
                        SOCKET_NUMBER = 0
                    elif COMMAND_BUFFER[1] is None:
                        COMMAND_BUFFER[1] = buffer
                        SOCKET_NUMBER = 1
                    
                    async def a():
                        await asyncio.sleep(1)
                        COMMAND_BUFFER[SOCKET_NUMBER] = None
                        print("callback")
                        callbackFn(PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x5 << 4 | SOCKET_NUMBER, 0xFF])

                    a()
                    return PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x4 << 4 | SOCKET_NUMBER, 0xFF]
                
                    # TODO: Schedule
                    # Completion
                    print(PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x5 << 4 | SOCKET_NUMBER, 0xFF])

        elif payload[2] & 0xF0 == 0x20:
            # cancel
            SOCKET_NUMBER = payload[2] & 0x0F
            print("CANCEL SOCKET", SOCKET_NUMBER)
            if SOCKET_NUMBER not in [0, 1] or COMMAND_BUFFER[SOCKET_NUMBER] is None:
                return PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x6 << 4 | SOCKET_NUMBER, 0x05, 0xFF]
            else:
                return PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x6 << 4 | SOCKET_NUMBER, 0x04, 0xFF]
        else:
            print("REJECT")
            # Syntax Error
            return PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x60, 0x02, 0xFF]

            # # Command Not Executable
            # print([0x90, 0x6 << 4 | SOCKET_NUMBER, 0x41, 0xFF])

    elif payloadType == "VISCA INQUIRY":
        print("VISCA INQUIRY")
        # Handle VISCA INQUIRY
        # Example: print the inquiry payload
        print("Inquiry Payload:", payload)
        if payload[1:1+3] != [0x09, 0x06, 0x10]:
            print("REJECT")
            # Syntax Error
            return PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x60, 0x02, 0xFF]
        else:
            sending  = True
            if sending:
                return PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x50, 0b00100101, 0b00010000, 0xFF]
            else:
                # Fin
                return PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x50, 0b00101001, 0b00010000, 0xFF]
    elif payloadType == "VISCA DEVICE SETTING COMMAND":
        print("VISCA DEVICE SETTING COMMAND")

        if payload[1:1+3] != [0x01, 0x00, 0x01]:
            print("IF_CLEAR")
            return PAYLOAD_TYPES["VISCA REPLY"], [0x90, 0x50, 0xFF]
    elif payloadType == "CONTROL COMMAND":
        if payload[0] == 0x01:
            return PAYLOAD_TYPES["CONTROL REPLY"], [0x01]
            pass
        elif payload[0] == 0x0F:
            payload[1]
            raise ValueError("Meant to handle incoming error message")
            # pp=01: Abnormality in the sequence
            # pp=02: Abnormality in the message (message type)
    else:
        raise ValueError("Unknown Payload Type")
        # Handle unknown payload type




def craftPayload(type, payload, seqNo: int):
    output = []
    output += type # 2
    output += [0x00, len(payload)] # 2
    output += struct.pack("<I", seqNo) # 4
    output += payload # 1-16
    return output

latestSeqNo = -1
def doThing(buffer):
    global latestSeqNo
    seqNo = struct.unpack("<I", bytes(buffer[4:8]))[0]

    def sendResult(
            type,
            payload
    ):
        # global seqNo
        print(type, payload, seqNo)
        result = craftPayload(type, payload, seqNo)
        print("Sending result", result)


    if seqNo <= latestSeqNo:
        # responseType, response = 
        sendResult(PAYLOAD_TYPES["CONTROL REPLY"], [0x0F, 0x01])

    else:
        sendResult(*handleBuffer(buffer, sendResult))
        # responseType, response = handleBuffer(buffer)
        latestSeqNo = seqNo

# doThing(PTZ_COMMAND)


import socket

port = 52381

# Create a UDP socket
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind(("0.0.0.0", port))  # Bind to all interfaces on port 12345

print(f"UDP listener started on port {port}")

while True:
    data, addr = udp_socket.recvfrom(1024)  # Receive up to 1024 bytes
    print("Received message:", data.decode("utf-8"), "from", addr)
    doThing(data)