from datetime import datetime
from typing import List, Tuple

import sys
import getopt
import numpy as np
import math as m
import skyfield.api as skf
from scipy import linalg


def quaternion_from_axisangle(axis, angle):
    '''
    axis must be normalized
    angle must be in radians
    '''
    q_0 = m.cos(angle / 2)
    q_1 = m.sin(angle / 2) * axis[0]
    q_2 = m.sin(angle / 2) * axis[1]
    q_3 = m.sin(angle / 2) * axis[2]
    q = np.array([q_0, q_1, q_2, q_3])
    return q

def rot2q(R):
    '''
    Convert a rotation matrix to a quaternion
    input is a 3x3 numpy array
    output is a 4 element numpy array
    '''
    theta = m.acos((np.trace(R) - 1) / 2)
    r_off_diag_diff = np.array([[(R[1][2] - R[2][1])], [(R[2][0] - R[0][2])], [(R[0][1] - R[1][0])]])
    
    
    e_hat = 1 / (2 * m.sin(theta)) * r_off_diag_diff
    q_0 = m.cos(theta / 2)
    q_1 = m.sin(theta / 2) * e_hat[0][0]
    q_2 = m.sin(theta / 2) * e_hat[1][0]
    q_3 = m.sin(theta / 2) * e_hat[2][0]
    q = np.array([q_0, q_1, q_2, q_3])
    q_normalized = q / np.linalg.norm(q)

    if abs(r_off_diag_diff).sum() < 0.0001:
        print("warning: rotation matrix is close to symmetric!", R, r_off_diag_diff, q)

    return q_normalized

def qxq(q1,q2):
    '''
    q1 and q2 must be four element lists of numbers or 4 element nump array
    returns a numpy array containing the quaternion product q1 x q2
    rotate around current  axes qxq(q_current, q_rotate)
    rotate around original axes qxq(q_rotate, q_current)
    '''
    mag = m.sqrt(q1[0]**2 + q1[1]**2 + q1[2]**2 + q1[3]**2)
    q1[0] /= mag
    q1[1] /= mag
    q1[2] /= mag
    q1[3] /= mag
    #
    mag = m.sqrt(q2[0]**2 + q2[1]**2 + q2[2]**2 + q2[3]**2)
    q2[0] /= mag
    q2[1] /= mag
    q2[2] /= mag
    q2[3] /= mag
    #
    w = q1[0]*q2[0] - q1[1]*q2[1] - q1[2]*q2[2] - q1[3]*q2[3]
    x = q1[0]*q2[1] + q1[1]*q2[0] + q1[2]*q2[3] - q1[3]*q2[2]
    y = q1[0]*q2[2] - q1[1]*q2[3] + q1[2]*q2[0] + q1[3]*q2[1]
    z = q1[0]*q2[3] + q1[1]*q2[2] - q1[2]*q2[1] + q1[3]*q2[0]
    #
    qp = np.array([w, x, y, z])
    return qp

def get_pointing_quat_np(relative_position_np, satpos_np, satvel_np, scandir):

    # Compue LVLH axes unit vectors in ECI
    lvlh_x = satvel_np / m.sqrt((satvel_np**2).sum())
    lvlh_z = - satpos_np / m.sqrt((satpos_np**2).sum())
    lvlh_y = np.cross(lvlh_z, lvlh_x)
    
    if type(scandir) == str:
        if scandir == 'velocity':
            scandir_np = lvlh_x
    else:
        scandir_np = scandir # [0.0, 0.0, 1.0]
    
    # Compute desired Body axes in ECI frame
    new_body_z = relative_position_np / m.sqrt((relative_position_np**2).sum())

    # The following three should all be equivalent,
    # but generate scanning directions not along velocity
    #new_body_x = np.cross(np.cross(new_lvlh_z, scandir_np), new_lvlh_z)
    #new_body_x = np.cross(new_lvlh_z, np.cross(scandir_np, new_lvlh_z))
    #new_body_x = scandir_np * ((new_body_z*new_body_z).sum()) - new_body_z * (scandir_np*new_body_z).sum()

    # this method forces scan dir to be in orbital plane

    a = 1/(m.sqrt(1 + ( (scandir_np*new_body_z).sum() / (lvlh_z*new_body_z).sum() )**2 ))
    # a positive -> scan dir in velocity direction
    b = m.sqrt(1 - a*a)
    # b positive -> looking back
    new_body_x = a*scandir_np + b*lvlh_z
    if (new_body_x*new_body_z).sum() > 1e-6:
        new_body_x = a*scandir_np - b*lvlh_z

    new_body_y = np.cross(new_body_z, new_body_x)
    
    # compute desired Body axes in LVLH frame
    new_body_x_ = np.array([np.dot(lvlh_x, new_body_x), np.dot(lvlh_y, new_body_x), np.dot(lvlh_z, new_body_x)])
    new_body_y_ = np.array([np.dot(lvlh_x, new_body_y), np.dot(lvlh_y, new_body_y), np.dot(lvlh_z, new_body_y)])
    new_body_z_ = np.array([np.dot(lvlh_x, new_body_z), np.dot(lvlh_y, new_body_z), np.dot(lvlh_z, new_body_z)])
    
    #print(new_body_x)
    #print(new_body_y)
    #print(new_body_z)
    
    # make a rotation matrix out of it
    R = np.array([new_body_x_, new_body_y_, new_body_z_])
    
    #print(R)

    quat = rot2q(R)
    
    return quat

def get_pointing_quat(location_skf, sat_skf, scandir, timestamp_skf):
    '''
    compute a quaternion in LVLH frame such that a given satellite
    points to the given location with the slit paralell to the scanning
    direction at the given timestamp
    '''
    ground_position_skf = location_skf.at(timestamp_skf)
    satellite_position_skf = sat_skf.at(timestamp_skf)

    ground_position_np = ground_position_skf.position.km
    satellite_position_np = satellite_position_skf.position.km
    satellite_velocity_np = satellite_position_skf.velocity.km_per_s

    relative_position_np = ground_position_np - satellite_position_np

    return get_pointing_quat_np(relative_position_np, satellite_position_np, satellite_velocity_np, scandir)


def generate_quaternions(skf_satellite: skf.EarthSatellite, timestamp: datetime, lat: float, lon: float, ele: float, forward_tilt=False, backwards_tilt=False):
    tc = skf.load.timescale().from_datetime(timestamp)
    loc_skf = skf.wgs84.latlon(lat * skf.N, lon * skf.E, ele)

    #satpos_skf = skf_satellite.at(tc)
    #sat_pos_np = satpos_skf.position.km
    #sat_vel_np = satpos_skf.velocity.km_per_s
    q_direct_pointing = get_pointing_quat(loc_skf, skf_satellite, 'velocity', tc) # location_skf, sat_skf, scandir, timestamp_skf


    if forward_tilt:
        #print("forward tilt")
        q = qxq(q_direct_pointing, quaternion_from_axisangle([0.0, 1.0, 0.0], 10.0*m.pi/180.0))
        #print(satpass[2], sat_pos_np, sat_vel_np, '  |  ', q2, ' forward tilt')

    # If the sun is in front, we need a 180° yaw-rotation and then a pitch-rotation the other way around
    # Backwards tilt capture is starting later. Northern hemisphere
    elif backwards_tilt:
        #print("backwards tilt")
        q_ = qxq(q_direct_pointing, quaternion_from_axisangle([0.0, 1.0, 0.0], -10.0*m.pi/180.0))
        q = qxq(q_, quaternion_from_axisangle([0.0, 0.0, 1.0], m.pi))

    # We need this for the actual pure rotation and use it to figure out the position of the sun before recalculating the quaternions since the timestamp
    # of the actual capture and rotation changes based on the pitch. If the sun is behind, we need to point forwards => starting earlier
    # If the sun is in front, we need to point backwards => starting capture later
    else:
        q = q_direct_pointing

    if q[0] < 0.0:
        q = - q

    return q


def get_param_filepath(argv):
    """Gets filepath of parameter list"""
    # inputfile = 'quaternion_calculations_io.yaml'
    inputfile = 'temp.yaml'
    try:
        opts, args = getopt.getopt(argv, "hi:", ["ifile="])
    except getopt.GetoptError:
        print("quaternion_calculations.py -i <inputfile>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("quaternion_calculations.py -i <inputfile>")
            sys.exit()
        elif opt in ("-i", "--ifile"):
            print(arg)
            inputfile = arg
    return inputfile


def perifocal(a, e, nu, mu):
    """Calculate orbit position [m] and orbit velocity [m/s] in perfocal frame"""
    p = a * (1 - e ** 2)  # Semi-latus rectum, m
    r_P = p / (1 + e * m.cos(nu)) * np.array([[m.cos(nu)], [m.sin(nu)], [0]])
    v_P = m.sqrt(mu / p) * np.array([[-m.sin(nu)], [e + m.cos(nu)], [0]])
    return r_P, v_P


def oe2eci(a, e, RAAN, i, arg_of_peri, nu, mu):
    """Transformation from perifocal to inertial (geocentric) frame"""
    r_P, v_P = perifocal(a, e, nu, mu)
    R_pi_1 = np.array([[m.cos(RAAN), -m.sin(RAAN), 0], [m.sin(RAAN), m.cos(RAAN), 0], [0, 0, 1]])
    R_pi_2 = np.array([[1, 0, 0], [0, m.cos(i), -m.sin(i)], [0, m.sin(i), m.cos(i)]])
    R_pi_3 = np.array(
        [[m.cos(arg_of_peri), -m.sin(arg_of_peri), 0], [m.sin(arg_of_peri), m.cos(arg_of_peri), 0], [0, 0, 1]])
    R_pi = R_pi_1.dot(R_pi_2).dot(R_pi_3)

    # Inertial frame
    r_i = R_pi.dot(r_P)  # position in inertial frame [m]
    v_i = R_pi.dot(v_P)  # velocity in inertial frame [m/s]
    return r_i, v_i


def eci2LVLH(r_i, v_i):
    """ Transformation from inertial (geocentric) frame to orbit frame """
    z_o = (-r_i / np.linalg.norm(r_i))
    y_o = (-np.cross(r_i, v_i, axis=0) / np.linalg.norm(np.cross(r_i, v_i, axis=0)))
    x_o = np.cross(y_o, z_o, axis=0)
    R_i_o = np.array([x_o.T[0], y_o.T[0], z_o.T[0]])  # Transformation from ECI to orbit frame

    r_o = R_i_o.dot(r_i)  # position in orbit frame [m]
    # v_o = np.dot(R_i_o, v_i)      # velocity in orbit frame [m/s]
    return r_o, R_i_o


def lla2ecef(lat, lon, ele):
    """ Transformation from lla  to eccef  """
    lat_rad = lat * np.pi / 180
    lon_rad = lon * np.pi / 180
    a = 6.3781370e+6
    b = 6.3567523142e+6
    e_sq = 1 - ((b ** 2) / (a ** 2))
    N_lat = a / (m.sqrt(1 - e_sq * (m.sin(lat_rad)) ** 2))
    x = (N_lat + ele) * m.cos(lat_rad) * m.cos(lon_rad)
    y = (N_lat + ele) * m.cos(lat_rad) * m.sin(lon_rad)
    z = (((b ** 2) / (a ** 2)) * N_lat + ele) * m.sin(lat_rad)
    return x, y, z


def skew_sym(x):
    return np.array([[0, -x[2][0], x[1][0]],
                     [x[2][0], 0, -x[0][0]],
                     [-x[1][0], x[0][0], 0]])


def rot_rodrigues(a, b):
    a_hat = a / np.linalg.norm(a)
    b_hat = b / np.linalg.norm(b)
    theta = np.arccos(a_hat.T.dot(b_hat))
    lam = np.cross(a_hat, b_hat, axis=0)
    lambda_hat = lam / np.linalg.norm(lam)
    return linalg.expm(skew_sym(theta * lambda_hat))



def rot2q(R):
    # -1.000000048
    trace = np.trace(R)

    # TODO make sure this works for ALL possible rotation matrices

    #print(R)
    #print(trace)
    if trace <= -1.0:
        trace = -1.0
    #if trace >= 1.0:
    #    trace = 1.0
    theta = m.acos((trace - 1) / 2)
    e_hat = 1 / (2 * m.sin(theta)) * np.array([[R[1][2] - R[2][1]], [R[2][0] - R[0][2]], [R[0][1] - R[1][0]]])
    q_0 = m.cos(theta / 2)
    q_1 = m.sin(theta / 2) * e_hat[0][0]
    q_2 = m.sin(theta / 2) * e_hat[1][0]
    q_3 = m.sin(theta / 2) * e_hat[2][0]
    q = np.array([q_0, q_1, q_2, q_3])
    return q / np.linalg.norm(q)


def euler2rot_zyx(phi, theta, psi):
    return np.array([[m.cos(psi) * m.cos(theta), m.sin(psi) * m.cos(theta), -m.sin(theta)],
                     [-m.sin(psi) * m.cos(phi) + m.cos(psi) * m.sin(theta) * m.sin(phi),
                      m.cos(psi) * m.cos(phi) + m.sin(psi) * m.sin(theta) * m.sin(phi), m.cos(theta) * m.sin(phi)],
                     [m.sin(psi) * m.sin(phi) + m.cos(psi) * m.sin(theta) * m.cos(phi),
                      -m.cos(psi) * m.sin(phi) + m.sin(psi) * m.sin(theta) * m.cos(phi), m.cos(theta) * m.cos(phi)]])




# def generate_quaternions_old(sat_pos: List[float], sat_vel: List[float],
#                          time: datetime, lat: float, lon: float, ele: float, forward_tilt=False, backwards_tilt=False) -> Tuple[List[float], List[float]]:
#     """Generates quaternions from satellite position and velocity, returns a tuple (a, b), where a is the
#     normal and b the pure x-axis quaternion.

#     :param sat_pos: satellite position in [km]
#     :param sat_vel: satellite velocity in [km/s]
#     :param time: time of observation, as UTC datetime object
#     :param lat: latitude of target, in degrees
#     :param lon: longitude of target, in degrees
#     :param ele: elevation of target, in [km] """

#     mu = 3.986004418e14
#     Re = 6371e3

#     # Satellite position[km] & velocity[km/s] passed in from sat_pos and sat_vel
#     # Converting pyorbital (or any [km] and [km/s]) vectors to m/s and m,
#     # while changing to nested numpy arrays in order for eci2lvlh to work.
#     sat_pos_eci = np.array([[np.array(i) * 1e3] for i in sat_pos])
#     sat_vel_eci = np.array([[np.array(i) * 1e3] for i in sat_vel])

#     # Satellite position & velocity in orbit Frame
#     r_io_o, R_io = eci2LVLH(sat_pos_eci, sat_vel_eci)

#     # Target position [m] in ECEF
#     target_x, target_y, target_z = lla2ecef(lat, lon, ele)

#     # Target position [m] in ECI
#     target_pos_eci = trf2crf(target_x, target_y, target_z, time)

#     relative_pos_eci = target_pos_eci - sat_pos_eci
#     relative_pos_orbit = R_io.dot(relative_pos_eci)

#     z_o_hat_o = np.array([[0], [0], [1]])
#     z_b_hat_o = relative_pos_orbit / np.linalg.norm(relative_pos_orbit)

#     # Computing pointing quaternion
#     R_bo = rot_rodrigues(z_o_hat_o, z_b_hat_o)  # Rotate a to b. Args: (a,b) This should result in pi/2-epsilon
#     R_ob = R_bo.transpose()
#     q_ob = rot2q(R_ob)

#     ## Computing pure x-axis rotation quaternion
#     kappa = m.acos(np.divide((np.dot(sat_pos_eci.transpose(), target_pos_eci)),
#                              (np.dot(np.linalg.norm(sat_pos_eci), np.linalg.norm(target_pos_eci)))))
#     H = -(r_io_o[2][0] + Re)
#     rho = m.asin(Re / (Re + H))
#     D = m.sqrt(Re ** 2 + (Re + H) ** 2 - 2 * Re * (Re + H) * m.cos(kappa))
#     r_rel_b = np.array([[0], [0], [D]])
#     r_rel_o        = R_ob.transpose().dot(r_rel_b)
#     eta = m.atan2(m.sin(rho) * m.sin(kappa), 1 - m.sin(rho) * m.cos(kappa))

    
#     theta_ob_pure = 10*m.pi/180
#     psi_ob_pure = m.pi
#     phi_ob_pure = eta



#     if q_ob[1] < 0:
#         phi_ob_pure = -phi_ob_pure
#     roll_rot = euler2rot_zyx(phi_ob_pure, 0, 0)

#     # We need the forwards tilt in order to get the star tracker more than 90° off-nadir
#     # Forward tilt is capture earlier. Southern hemisphere
#     if forward_tilt:
#         #print("forward tilt")
#         pitch_rot = euler2rot_zyx(0, theta_ob_pure, 0)
#         R_ob = np.dot(pitch_rot, roll_rot)
#         q_ob_pure = rot2q(R_ob) # Not actually pure anymore


#     # If the sun is in front, we need a 180° yaw-rotation and then a pitch-rotation the other way around
#     # Backwards tilt capture is starting later. Northern hemisphere
#     elif backwards_tilt:
#         #print("backwards tilt")
#         yaw_rot = euler2rot_zyx(0, 0, psi_ob_pure)
#         pitch_rot = euler2rot_zyx(0, theta_ob_pure, 0)
#         R_ob = np.dot(pitch_rot, (np.dot(yaw_rot, roll_rot)))
#         q_ob_pure = rot2q(R_ob) #Not actually pure anymore
#         #if q_ob[1] < 0:
#         #   q_ob_pure[1] = -q_ob_pure[1]
#         #print(R_ob)
#         #print(q_ob_pure)
#     # q_ib_pure      = rot2q(R_ob_pure.dot(R_io))

#     # We need this for the actual pure rotation and use it to figure out the position of the sun before recalculating the quaternions since the timestamp
#     # of the actual capture and rotation changes based on the pitch. If the sun is behind, we need to point forwards => starting earlier
#     # If the sun is in front, we need to point backwards => starting capture later
#     else:
#         q_ob_pure = rot2q(roll_rot)
    

#     return q_ob, q_ob_pure


# def yaml_loader(filepath):
#     """Loads yaml file"""
#     with open(filepath, "r") as file_descriptor:
#         param = yaml.full_load(file_descriptor)
#     return param


# def trf2crf(x, y, z, t):
#     """Transformation from trf to crf frame"""
#     trf = SkyCoord(x, y, z,
#                    frame='itrs',
#                    differential_type='cartesian',
#                    obstime=t)
#     crf = trf.transform_to('gcrs')
#     crf.representation_type = 'cartesian'
#     # print(trf, "\n",crf, "\n crf z", crf.z)
#     return np.array([[crf.x], [crf.y], [crf.z]])


# def main():
#     filepath = get_param_filepath(sys.argv[1:])
#     param = yaml_loader(filepath)

#     # Initialize satellite parameters
#     if param['title_line'] and (not param['line_1'] or not param['line_2']):
#         print('Line 1 or line 2 is not defined, fetching from Celestrak ...')
#         satellite = Orbital(param['title_line'])
#     elif param['line_1'] and param['line_2']:
#         print('Using line 1 and line 2 from input file ...')
#         satellite = Orbital(satellite="", line1=param['line_1'], line2=param['line_2'])
#     else:
#         print('No valid input, please supply either title line or line 1 and line 2')
#         return

#     time = param['timestamp']
#     pos_vel = satellite.get_position(time, normalize=False)

#     target_lat = param['latitude']
#     target_lon = param['longitude']
#     target_ele = param['elevation']

#     q_ob, q_ob_pure = generate_quaternions_old(
#         pos_vel[0],
#         pos_vel[1],
#         time,
#         target_lat,
#         target_lon,
#         target_ele,
#     )

#     sat_pos_eci = pos_vel[0]

#     # Target position [m] in ECEF
#     target_x, target_y, target_z = lla2ecef(target_lat, target_lon, target_ele)

#     # Target position [m] in ECI
#     target_pos_eci = trf2crf(target_x, target_y, target_z, time)

#     ## Displaying positions
#     print(time)
#     print("Target   ECEF position [km]: ", target_x / 1000, target_y / 1000, target_z / 1000)
#     print("Target    ECI position [km]: ", target_pos_eci[0] / 1000, target_pos_eci[1] / 1000, target_pos_eci[2] / 1000)
#     print("Satellite ECI position [km]: ", sat_pos_eci[0], sat_pos_eci[1], sat_pos_eci[2])

#     ## Displaying quaternions
#     print("Quaternion:", q_ob[0], q_ob[1], q_ob[2], q_ob[3])
#     print("  --> Nadir Angle:", m.degrees(2.0 * m.acos(q_ob[0])))
#     print("Quaternion pure x-axis rotation:", q_ob_pure[0], q_ob_pure[1], q_ob_pure[2], q_ob_pure[3])


# if __name__ == "__main__":
#     main()

