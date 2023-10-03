import numpy as np 

MIDI_CC_MAX = 127
RANGE_SET_BUTTON = 'b'
SEND_DATA_BUTTON = 'a'
WAIT_INTERVAL = 1/250


def curve_quad(cc_val, curve_amt):
    cc_val = cc_val/127
    cc_out = 127*( cc_val + curve_amt*(cc_val - cc_val**2) )
    return cc_out


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
    
def get_inputs_and_pose(contr):
    #Pose
    positionarray = contr.get_pose_euler()

    if positionarray == None:
        pose = None
    else:
        pose = { #TODO: Integrate with triad data representation better?
            'x': positionarray[0],
            'y': positionarray[1],
            'z': positionarray[2],
            'yaw': positionarray[3] + 180,
            'pitch': positionarray[4] + 180,
            'roll': positionarray[5] + 180
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
  