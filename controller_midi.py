from asyncore import loop
from triad_openvr import triad_openvr
import time
import sys
import mido
from pythonosc import udp_client
import random
import argparse
import os
import signal
from curve_function_graphs import curve_quad
import numpy as np

MIDI_CC_MAX = 127

parser = argparse.ArgumentParser()
parser.add_argument("--hand", type=str, default='right', choices=['right','left'], 
    help="Which controller")
parser.add_argument("--send-osc", action="store_true",
    help="Don't send osc messages")
parser.add_argument("--no-haptic", action="store_false",
    help="Don't send osc messages")
parser.add_argument("--debug", action="store_true",
    help="Don't send osc messages")
parser.add_argument("--ip", default="127.0.0.1",
    help="The ip of the OSC server")
parser.add_argument("--port", type=int, default=10000,
    help="The port the OSC server is listening on")
args = parser.parse_args()

# from rtmidi.midiconstants import CONTROL_CHANGE, PITCH_BEND

interval = 1/250

print('wait interval is ' + str(interval))

v = triad_openvr.triad_openvr()
v.print_discovered_objects()


#Indicate what controller belongs to which hand...Must be a more elegant way...
present_controllers = [key for key in v.devices if 'controller' in key]

models = {controller: v.devices[controller].get_model() for controller in present_controllers}

present_controllers = {}
for controller in models.keys():
    if 'Left' in models[controller]:
        present_controllers['left'] = controller
    elif 'Right' in models[controller]:
        present_controllers['right'] = controller

print("Controller hand associations: ")
print(present_controllers)


#Argument 1: left or right, default to controller_1...
#Argument 2: midi port name

default_midi_ports = {
    'right' : 'Right Controller',
    'left' : 'Left Controller'
}

#TODO use better argument handling library


controller_name = present_controllers[args.hand]  
midiportname = default_midi_ports[args.hand]

print("connecting to " + controller_name)
contr = v.devices[controller_name]

#TODO: Figure out whether these dicts should be same or different (stress test 1 midi channel...)

if controller_name == "controller_1":
    cc_dict = {
    'x': 22,
    'y': 23,
    'z': 24,
    'tpy':25,
}


elif controller_name == "controller_2":
    cc_dict = {
    'x': 22,
    'y': 23,
    'z': 24,
    'tpy':25,
}


available_ports = mido.get_output_names()

def signal_handler(signal, frame):
    """Runs and exits when crtl-C is pressed"""
    print("\nprogram exiting gracefully")
    midiout.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# here we're printing the ports to check that we see the one that loopMidi created. 
# In the list we should see a port called "loopMIDI port".

midi_connected = False

for i, port in enumerate(available_ports):
    if midiportname in port:
        print('Connecting to midi port: ' + port)
        midiout = port = mido.open_output(port)
        midi_connected = True

if not midi_connected:
    print('Could not find port ' + midiportname + ' in following midi ports')
    print(available_ports)

if args.send_osc:
    print("Sending osc messages to IP: {} over port {}".format(args.ip, args.port))
    osc_client = udp_client.SimpleUDPClient(args.ip, args.port)
else:
    osc_client = None

import json
with open('ranges_dict_{}.json'.format(args.hand), 'r') as f:
    cube_ranges = json.load(f)

#This is for flipping the axes along an axis. currently done during pose retrival TODO: More elegant way?
direction_dict = {
    'x': -1.0,
    'y': 1.0,
    'z': 1.0
}


data_scaled = {
    'x': MIDI_CC_MAX/2,
    'y': MIDI_CC_MAX/2,
    'z': MIDI_CC_MAX/2
}

rangesetbutton = 'b'
senddatabutton = 'a'


def scale_data(data_raw, cube_ranges, dim, half):

    length = cube_ranges[dim]['max'] - cube_ranges[dim]['min']
    relative_dist = data_raw[dim] - cube_ranges[dim]['min']

    if half:
        halflength = length/2

        if relative_dist < halflength:
            relative_dist = relative_dist
        elif relative_dist > halflength:
            relative_dist = length - relative_dist

        scaled = (relative_dist/halflength)*MIDI_CC_MAX  
    else:  
        scaled = (relative_dist/length)*MIDI_CC_MAX

    if scaled < 0:
        scaled = 0
    elif scaled > MIDI_CC_MAX:
        scaled = MIDI_CC_MAX

    scaled = curve_quad(scaled, 1)

    #Added for conversion to mido, believe rtmidi was converting inside api
    scaled = int(scaled)


    return scaled


def range_set_mode(contr, debugstr=''):
    inputs, pose = get_inputs_and_pose(contr)

    cube_ranges = {
        'x': {'min': pose['x'], 'max': pose['x']},
        'y': {'min': pose['y'], 'max': pose['y']},
        'z': {'min': pose['z'], 'max': pose['z']}
    }      

    while(inputs['button'] == rangesetbutton):
        debugstr = ''

        inputs, pose = get_inputs_and_pose(contr)

        if debug: debugstr = 'Range Set Mode: '
        if debug: debugstr = debugstr + '\nPose: ' + str(pose)

        if pose is not None:
            for dim in pose:
                if pose[dim] < cube_ranges[dim]['min']:
                    cube_ranges[dim]['min'] = pose[dim]
                elif pose[dim] > cube_ranges[dim]['max']:
                    cube_ranges[dim]['max'] = pose[dim]

            if debug: debugstr = debugstr + '\nRange: ' + str(cube_ranges)

        sleep_time = interval-(time.time()-start)
        if sleep_time>0:
            time.sleep(sleep_time)
        
        if debug:
            #not working in anaconda prompt?
            os.system('cls')
            print(debugstr)

    return cube_ranges
    
def get_inputs_and_pose(contr):
    #Pose
    positionarray = contr.get_pose_euler()

    if positionarray == None:
        pose = None
    else:
        pose = {
            'x': positionarray[0],
            'y': positionarray[1],
            'z': positionarray[2]
            }

        pose = {dim: val*direction_dict[dim] for dim, val in pose.items()}
    #Inputs
    inputs = contr.get_controller_inputs()

    #Convert weird button number system into something simpler
    if inputs['ulButtonPressed']==2 or inputs['ulButtonPressed']==6:
        inputs['button'] = 'b'
    elif inputs['grip_button'] == True: # inputs['ulButtonPressed'] == 4 not true when trigger
        inputs['button'] = 'a'
    else:
        inputs['button'] = None

    return inputs, pose

debug = args.debug
running = True

save_range_dict = False #Save range dict when exiting range set mode
trackpad_reset = False #used to reset pitchbend after letting go of touchpad


#Going to reset this each time haptic feedback is sent...so do want to call it a general loop counter
haptic_loop_counter = 0
while(running):
    haptic_loop_counter += 1
    start = time.time()

    inputs, pose = get_inputs_and_pose(contr)

    if debug: 
        debugstr = 'Controller: ' + controller_name + '\nMidi Port Name: ' + midiportname# + '\nInputs ' + str(inputs)

    if inputs['button'] == rangesetbutton and pose != None:
        #enter range set mode
        cube_ranges = range_set_mode(contr)
        save_range_dict = True
    else:
        #normal mode
        if debug:
            debugstr = debugstr + '\nNormal Mode:'
        if save_range_dict:
            with open('ranges_dict_{}.json'.format(args.hand), 'w') as f:
                json.dump(cube_ranges, f)
            save_range_dict = False

        trigger = inputs['trigger']
        
        if pose is not None:   
            if debug:
                pose_debug = {key: "{:5.3f}".format(val) for key, val in pose.items()}
                debugstr = debugstr + '\nPose: ' + str(pose_debug)

            for dim in pose:
                if (dim == 'y') and (trigger == 1):
                    data_scaled[dim] = scale_data(pose, cube_ranges, dim, half=True)
                else: 
                    data_scaled[dim] = scale_data(pose, cube_ranges, dim, half=False)

            if debug: debugstr = debugstr + '\nScaled Pose: ' + str(data_scaled)

            if inputs['button'] == senddatabutton or inputs['trackpad_touched']:
                ccx = mido.Message('control_change',control=cc_dict['x'], value=data_scaled['x'])
                # ccx = [CONTROL_CHANGE, cc_dict['x'], data_scaled['x']]
                midiout.send(ccx)            
                ccy = mido.Message('control_change',control=cc_dict['y'], value=data_scaled['y'])
                midiout.send(ccy)                  
                ccz = mido.Message('control_change',control=cc_dict['z'], value=data_scaled['z'])
                midiout.send(ccz)  


                if osc_client != None:
                    osc_client.send_message("/{}/x".format(args.hand), data_scaled['x']/127)
                    osc_client.send_message("/{}/y".format(args.hand), data_scaled['y']/127)
                    osc_client.send_message("/{}/z".format(args.hand), data_scaled['z']/127)

                if debug: debugstr = debugstr + '\nCCx Message: ' + str(ccx)
                if debug: debugstr = debugstr + '\nCCy Message: ' + str(ccy)
                if debug: debugstr = debugstr + '\nCCz Message: ' + str(ccz)

                scaled_y = data_scaled['y']


                haptic_threshold = 40
                if args.no_haptic:
                    if haptic_loop_counter > 10:
                        if (scaled_y > haptic_threshold):
                            scaled_y_vib = int(scaled_y-haptic_threshold)*30
                            contr.trigger_haptic_pulse(duration_micros=scaled_y_vib)
                            haptic_loop_counter = 0




            ### Not sure exactly how pitchbend works in mido, use 'pitch wheel'?

            #     if inputs['trackpad_touched']:
            #         tpy = int(inputs['trackpad_y']*64+64)

            #         # cctpy = [CONTROL_CHANGE, cc_dict['tpy'], tpy]
            #         # midiout.send_message(cctpy)  


            #         pb = tpy
            #         # pb = [PITCH_BEND, 0 , pb]
            #         pb = mido.Message('pitchwheel', value=pb)
            #         midiout.send(pb)

            #         # if debug: debugstr = debugstr + '\npb Message: ' + str(pb)
            #         trackpad_reset = True
            # else:
            #     if trackpad_reset:
            #         # cctpy = [CONTROL_CHANGE, cc_dict['tpy'], 64]
            #         cctpy= mido.Message('control_change',control=cc_dict['tpy'], value=64)
            #         midiout.send(cctpy)
            #         trackpad_reset = False
                    


    sleep_time = interval-(time.time()-start)
    if sleep_time>0:
        time.sleep(sleep_time)
        
    if debug: 
        os.system('cls')
        print(debugstr)
        

