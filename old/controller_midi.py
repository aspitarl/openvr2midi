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
from openvr2midi.utils import curve_quad
import numpy as np

from openvr2midi.utils import get_inputs_and_pose, scale_data
from openvr2midi.utils import MIDI_CC_MAX, SEND_DATA_BUTTON, RANGE_SET_BUTTON, WAIT_INTERVAL

#TODO: Figure out whether there should be different cc dicts for each controller (stress test 1 midi channel...)

# Define CC channels to send, comment out to not send
cc_dict = {
    'x': 22,
    'y': 23,
    'z': 24,
    'yaw': 25,
    'pitch': 26,
    'roll': 27,
    'trigger':28,
    # 'tpy':26,
}


default_enabled_dict = {
    'x': True,
    'y': True,
    'z': True,
    'yaw': True,
    'pitch': False,
    'roll': False,
    'trigger':True,
    # 'tpy':26,
}

def signal_handler(signal, frame):
    """Runs and exits when crtl-C is pressed"""
    print("\nprogram exiting gracefully")
    midiout.close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


#This is for flipping the axes along an axis. currently done during pose retrival TODO: More elegant way?
direction_dict = {
    'x': 1.0,
    'y': 1.0,
    'z': 1.0,
    'yaw': 1.0,
    'pitch': 1.0,
    'roll': 1.0,
}




def range_set_mode(contr, debugstr=''):
    inputs, pose = get_inputs_and_pose(contr)

    cube_ranges = {
        'x': {'min': pose['x'], 'max': pose['x']},
        'y': {'min': pose['y'], 'max': pose['y']},
        'z': {'min': pose['z'], 'max': pose['z']},
        'yaw': {'min': pose['yaw'], 'max': pose['yaw']},
        'pitch': {'min': pose['pitch'], 'max': pose['pitch']},
        'roll': {'min': pose['roll'], 'max': pose['roll']}
    }      

    while(inputs['button'] == RANGE_SET_BUTTON):
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

        sleep_time = WAIT_INTERVAL-(time.time()-start)
        if sleep_time>0:
            time.sleep(sleep_time)
        
        if debug:
            #not working in anaconda prompt?
            os.system('cls')
            print(debugstr)

    return cube_ranges


if __name__ == '__main__':


    parser = argparse.ArgumentParser()
    parser.add_argument("--hand", type=str, default='right', choices=['right','left'], 
        help="Which controller")
    parser.add_argument("--send-osc", action="store_true",
        help="Don't send osc messages")
    parser.add_argument("--trigger-half", action="store_true",
        help="Enables trigger to go into half mode")
    parser.add_argument("--no-haptic", action="store_false",
        help="disable haptic feedback")
    parser.add_argument("--debug", action="store_true",
        help="enable debug mode")
    parser.add_argument("--ip", default="127.0.0.1",
        help="The ip of the OSC server")
    parser.add_argument("--port", type=int, default=10000,
        help="The port the OSC server is listening on")
    args = parser.parse_args()

    # from rtmidi.midiconstants import CONTROL_CHANGE, PITCH_BEND


    print('wait WAIT_INTERVAL is ' + str(WAIT_INTERVAL))

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

    controller_name = present_controllers[args.hand]  
    midiportname = default_midi_ports[args.hand]

    print("connecting to " + controller_name)
    contr = v.devices[controller_name]


    # here we're printing the ports to check that we see the one that loopMidi created. 
    # In the list we should see a port called "loopMIDI port".

    midi_connected = False

    available_ports = mido.get_output_names()
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

        if inputs['button'] == RANGE_SET_BUTTON and pose != None:
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
                if inputs['button'] == SEND_DATA_BUTTON or inputs['trackpad_touched']:
                    if debug:
                        pose_debug = {key: "{:5.3f}".format(val) for key, val in pose.items()}
                        debugstr = debugstr + '\nPose: ' + str(pose_debug)

                    for dim in cc_dict:

                        if dim == 'trigger':
                            data_scaled = int(trigger)*MIDI_CC_MAX
                        else:
                            half_mode = True if (dim == 'y') and (trigger == 1) and (args.trigger_half) else False
                            data_scaled = scale_data(pose, cube_ranges, dim, half=half_mode)

                        cc = mido.Message('control_change',control=cc_dict[dim], value=data_scaled)
                        midiout.send(cc)            
                        if debug: debugstr = debugstr + '\n{} CC Message: {}'.format(dim, cc)

                        if osc_client != None:
                            osc_client.send_message("/{}/{}".format(args.hand, dim), data_scaled/127)

                        if dim == 'y':
                            haptic_threshold = 40
                            if args.no_haptic:
                                if haptic_loop_counter > 10:
                                    if (data_scaled > haptic_threshold):
                                        scaled_y_vib = int(data_scaled-haptic_threshold)*30
                                        contr.trigger_haptic_pulse(duration_micros=scaled_y_vib)
                                        haptic_loop_counter = 0



        sleep_time = WAIT_INTERVAL-(time.time()-start)
        if sleep_time>0:
            time.sleep(sleep_time)
            
        if debug: 
            os.system('cls')
            print(debugstr)


