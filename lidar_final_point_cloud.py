#!/usr/bin/env python

# Copyright (c) 2019 Computer Vision Center (CVC) at the Universitat Autonoma de
# Barcelona (UAB).
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

import glob
import os
import sys
import carla
import random
import time
import numpy as np
import cv2

from plyfile import PlyData, PlyElement

INTERVAL = 0.3  # Arbitrary

IM_HEIGHT = 480
IM_WIDTH  = 640 


# Vecteur pour le nuage final
finalCloud = np.empty((0,4),dtype=np.float32)

npy_f = 'data'
#Commenter si dossier existant
os.mkdir(npy_f)

npy_name = os.path.join(npy_f,'outfile.ply')


def print_pnts(point_cloud):
    
    global finalCloud
        
    #Obtention de la matrice de transformation
    trns_mat = point_cloud.transform.get_matrix()
    #Reshape en 4x4
    trns_mat = np.array(trns_mat).reshape((4,4))
    #Obtention des points
    r_p = np.frombuffer(point_cloud.raw_data,dtype=np.dtype('f4'))
    #reshape en XYZ, intensité
    pnts = r_p.reshape(int(r_p.shape[0]/4),4)
    pnts, label = pnts[:,:3], pnts[:,3:]
    pnts, label = pnts[:,:3], pnts[:,3:]
    pnts = np.hstack((pnts,np.ones(pnts.shape[0])[:,None]))
    
    #Produit vectoriel entre la matrice de passage et la transposée des points
    #Pour obtenir les coordonnées dans le repère global
    
    new_pnts = np.dot(trns_mat,pnts.T)
    
    new_pnts = new_pnts.T
    new_pnts = np.hstack((new_pnts[:,:3],label))
    
    #Rajout au nuage global
    finalCloud = np.vstack((finalCloud,new_pnts))

def displayImage(cam_image):
    im_array = np.array(cam_image.raw_data)
    im_array2D = im_array.reshape((IM_HEIGHT, IM_WIDTH, 4))
    im_rgb = im_array2D[:, :, :3]
    cv2.imshow("", im_rgb)
    cv2.waitKey(1)
    return im_rgb/255.0
    
def main():
    actor_list = []

    # In this tutorial script, we are going to add a vehicle to the simulation
    # and let it drive in autopilot. We will also create a camera attached to
    # that vehicle, and save all the images generated by the camera to disk.

    try:
        print("Try connect to the simulator")
#        client = carla.Client('172.29.0.180', 2000)
        client = carla.Client('localhost', 2000)
        client.set_timeout(3.0)

        # Once we have a client we can retrieve the world that is currently
        # running.
        world = client.get_world()

        # The world contains the list blueprints that we can use for adding new
        # actors into the simulation.
        blueprint_library = world.get_blueprint_library()

        # Now let's filter all the blueprints of type 'vehicle' and choose one
        # at random.
        # bp = random.choice(blueprint_library.filter('vehicle.tesla.*'))
        bp = blueprint_library.filter('vehicle.tesla.model3')[0]

        # A blueprint contains the list of attributes that define a vehicle's
        # instance, we can read them and modify some of them. For instance,
        # let's randomize its color.
        if bp.has_attribute('color'):
            color = random.choice(bp.get_attribute('color').recommended_values)
            bp.set_attribute('color', color)

        # Now we need to give an initial transform to the vehicle. We choose a
        # random transform from the list of recommended spawn points of the map.
        # transform = random.choice(world.get_map().get_spawn_points())
        # print(transform)
        # ./config.py --xodr-path opendrive/Town07.xodr
        location = carla.Location(10., 0.,0.5)
        rotation = carla.Rotation(0., 0., 0.)
        transform = carla.Transform(location, rotation) 
        # print(transform)

        # So let's tell the world to spawn the vehicle.
        vehicle = world.spawn_actor(bp, transform)

        vehicle.apply_control(carla.VehicleControl(throttle=0.3, steer=0.0))

        
        # It is important to note that the actors we create won't be destroyed
        # unless we call their "destroy" function. If we fail to call "destroy"
        # they will stay in the simulation even after we quit the Python script.
        # For that reason, we are storing all the actors we create so we can
        # destroy them afterwards.
        actor_list.append(vehicle)
        print('created %s' % vehicle.type_id)

	# https://carla.readthedocs.io/en/latest/cameras_and_sensors
        # Let's add now a RGB camera attached to the vehicle. Note that the
        # transform we give here is now relative to the vehicle.
        camera_bp = blueprint_library.find('sensor.camera.rgb')

        camera_bp.set_attribute('image_size_x', f"{IM_WIDTH}")
        camera_bp.set_attribute('image_size_y', f"{IM_HEIGHT}")
        camera_bp.set_attribute('fov', '110')
        camera_bp.set_attribute('sensor_tick', str(INTERVAL))

        # Adjust sensor relative to vehicle # (x=2.5, z=0.7)
        camera_transform = carla.Transform(carla.Location(x=1.5, z=2.4))
        # spawn the sensor and attach to vehicle.
        camera = world.spawn_actor(camera_bp, camera_transform, attach_to=vehicle)
        actor_list.append(camera)
        print('created %s' % camera.type_id)

        # do something with this sensor
        # camera.listen(lambda image: image.save_to_disk('_out/%06d.png' % image.frame))
        camera.listen(lambda image: displayImage(image))

        lidar_cam = None
        lidar_bp = world.get_blueprint_library().find('sensor.lidar.ray_cast')
        lidar_bp.set_attribute('channels',str(64))
        lidar_bp.set_attribute('points_per_second',str(1000000))
        lidar_bp.set_attribute('rotation_frequency',str(1000))
        lidar_bp.set_attribute('range',str(15))
        lidar_location = carla.Location(0,0,2)
        lidar_rotation = carla.Rotation(0,0,0)
        lidar_transform = carla.Transform(lidar_location,lidar_rotation)
        lidar_sen = world.spawn_actor(lidar_bp,lidar_transform,attach_to=vehicle)
        #lidar_sen.listen(lambda point_cloud: point_cloud.save_to_disk('tutorial/new_lidar_output/%.6d.ply' % point_cloud.frame))

        lidar_sen.listen(lambda point_cloud: print_pnts(point_cloud))

        time.sleep(40)
    finally:


        print('Saving point cloud....')
        # np.savetxt(os.path.join(f_name, 'test.txt'),finalCloud,delimiter=',',comments='')
        print('Number of points: %d ' % finalCloud.shape[0])
        print('Saving points to the file: {}'.format(npy_name))
        s = time.time()
        vertex = np.array(list(map(tuple,finalCloud)),dtype=[('x', 'f4'), ('y', 'f4'),('z', 'f4'),('Intensity','f4')])
        el = PlyElement.describe(vertex, 'output')
        PlyData([el]).write(npy_name)
        e = time.time()
        print('Total time to create plyfile: %.4f seconds' % (e - s))

        print('destroying actors')
        camera.destroy()
        lidar_sen.destroy()
        client.apply_batch([carla.command.DestroyActor(x) for x in actor_list])
        print('done.')


if __name__ == '__main__':

    main()
