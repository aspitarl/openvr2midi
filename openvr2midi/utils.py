import numpy as np 

from triad_openvr.triad_openvr import convert_to_euler, get_pose

MIDI_CC_MAX = 127
RANGE_SET_BUTTON = 'b'
SEND_DATA_BUTTON = 'a'
WAIT_INTERVAL = 1/250


#This is for flipping the axes along an axis. currently done during pose retrival TODO: More elegant way?
direction_dict = {
    'x': 1.0,
    'y': 1.0,
    'z': 1.0,
    'yaw': 1.0,
    'pitch': 1.0,
    'roll': 1.0,
    'velocity': 1.0
}


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


    
def get_inputs_and_pose_dict(contr, yaw_x_factor=1.0, yaw_y_factor=1.0):
    #Pose
    pose = get_pose(contr.vr)

    if not pose[contr.index].bPoseIsValid:
        pose_dict = None
    else:
        positionarray = convert_to_euler(pose[contr.index].mDeviceToAbsoluteTracking, yaw_x_factor=yaw_x_factor, yaw_y_factor=yaw_y_factor) 

        velocity = pose[contr.index].vVelocity
        
        pose_dict = { 
            'x': positionarray[0],
            'y': positionarray[1],
            'z': positionarray[2],
            'yaw': positionarray[3] + 180,
            'pitch': positionarray[4] + 180,
            'roll': positionarray[5] + 180,
            'velocity': np.linalg.norm([velocity.v[0], velocity.v[1], velocity.v[2]]),
            }

        pose_dict = {dim: val*direction_dict[dim] for dim, val in pose_dict.items()}
    #Inputs
    inputs = contr.get_controller_inputs()

    #Convert weird button number system into something simpler
    if inputs['ulButtonPressed']==2 or inputs['ulButtonPressed']==6:
        inputs['button'] = 'b'
    elif inputs['grip_button'] == True: # inputs['ulButtonPressed'] == 4 not true when trigger
        inputs['button'] = 'a'
    else:
        inputs['button'] = None

    return inputs, pose_dict
  