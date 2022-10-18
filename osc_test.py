
from pythonosc import udp_client
import argparse
import time

parser = argparse.ArgumentParser()

parser.add_argument("--ip", default="127.0.0.1",
    help="The ip of the OSC server")
parser.add_argument("--port", type=int, default=10000,
    help="The port the OSC server is listening on")
args = parser.parse_args()

osc_client = udp_client.SimpleUDPClient(args.ip, args.port)

for i in range(5):
    
    osc_client.send_message("/test_signal", i)
    time.sleep(0.1)