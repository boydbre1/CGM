import yt
import numpy as np
from sys import argv, path
path.insert(0,"/mnt/home/boydbre1/Repo/foggie")
from foggie.utils.foggie_load import foggie_load

#
#Find the center and orientation of galaxy
#return center coordinates and normal vector
#

def find_center(ds_fname, tracking_dir='/mnt/home/boydbre1/data/track_files', use_foggie=True, save_data=True, max_field=None):
    """
    Use to retrieve the center of galaxy

    Parameters:
        ds_fname : string: path to dataset containing galaxy
        tracking_dir : string: path to directory contianing tracking files
        save_data : bool : write data to file? defaults to True
        max_field : string : field name. finds maximum of that field and sets
                    that to be the center. If None, will try to retrieve the center
                    from files in track_files directory

    Returns:
        center : yt array : the center of galaxy in units of code_length
        normal_vector : yt array : vector pointing along the axis of rotation
                        of the galaxy. (units are dimensionless)
        bulk_vel : yt array : bulk velocity of the galaxy in units km/s
    """
    ds = yt.load(ds_fname)
    rshift = ds.current_redshift

    if max_field is not None:
        print(f"using max of field {max_field} as centere")

        #let max field be center of gal
        v, center = ds.find_max(max_field)
        n_vec, bulk_vel = find_normal_vector(ds, center)
    else:
        #get directory where tracker files are kept
        sfname = ds_fname.split('/')
        refinement = sfname[-3]
        ds_name = sfname[-1]

        try:
            #check if kept center and normal_vector in center_normal_track.dat
            center_norm_file = tracking_dir + '/main_track.dat'

            center, n_vec, bulk_vel = search_center_norm(center_norm_file, ds_name, refinement)

            #check if center was found
            if center is None:
                raise RuntimeError("could not find {} in {}" \
                                        .format(ds_name, center_norm_file))
            else:
                print(f"using info found in {center_norm_file}")
                center = ds.arr(center, 'code_length')
                n_vec = ds.arr(n_vec, 'dimensionless')
                bulk_vel = ds.arr(bulk_vel, 'km/s')
        #catch if file or entry not found
        except (FileNotFoundError, RuntimeError):
            #use foggie load to find info
            if use_foggie:
                box_trackfile = tracking_dir + '/halo_track_200kpc_nref10' #might want to make more flexible

                # uses "young stars" to calculate normal vector of disk
                ds_foggie, reg_foggie = foggie_load(ds_fname, box_trackfile, disk_relative=True)

                center = ds.arr(ds_foggie.halo_center_code, 'code_length')
                bulk_vel = ds_foggie.halo_velocity_kms
                n_vec = ds_foggie.z_unit_disk

            else:
                #check for center in center_track file
                try:
                    #return center of track with nearest redshift to dataset's
                    center_file = tracking_dir + '/center_track.dat'
                    f = np.loadtxt(center_file, skiprows=2, usecols=(0, 1, 2, 3))
                    indx = np.abs(f[:, 0] - rshift).argmin()
                    center = ds.arr(f[indx, 1:], 'code_length')

                    #compute normal vec from center
                    n_vec, bulk_vel = find_normal_vector(ds, center)
                    print(f"Found center in {center_file}. Calculated n_vec/bluk velocity")

                except OSError:
                    raise RuntimeError("Need {} to exist, otherwise set max_field to define center or use foggie "\
                                            .format(tracking_dir + '/center_track.dat'))

            # save data so don't have to calculate again
            if save_data:
                print(f"Saving that data to {center_norm_file}")
                #write center and norm to file
                w = open(center_norm_file, 'a')
                write_str = "{:s} {:s} {:f} ".format(refinement, ds_name, rshift)

                #write out all the array values
                write_str += ' '.join(str(x) for x in center.value) + ' '
                write_str += ' '.join(str(x) for x in n_vec.value) + ' '
                write_str += ' '.join(str(x) for x in bulk_vel.value)

                w.write(write_str + '\n')
                w.close()

    return center, n_vec, rshift, bulk_vel

def search_center_norm(file, ds_name, refinement):
    """
    Tries to find the center and normal vector from the file

    Parameters:
        file : string: path to file with center and normal information
                formatted as ds_name redshift center(x, y, z) n_vec(x, y, z)
        ds_name : string: name of the dataset i.e. RD0036, DD0075

    Returns:
        center : list/array floats: coordinates to center of galaxy
        n_vec : list/array floats: vector pointing along axis of rotation

        NOTE: Both return NoneType if entry not found in file
    """
    center = None
    n_vec = None
    bulk_vel = None
    #read through file
    f = open(file, 'r')
    for line in f:
        sline = line.split()
        #check dataset name. return center and n_vector
        #check line is not empty
        if len(sline) ==0:
            pass
        elif line[0] == '#':
            pass
        elif refinement == sline[0] and ds_name == sline[1]:
            #convert to floats then stop reading file
            center = [ float(val) for val in sline[3:6] ]
            n_vec = [ float(val) for val in sline[6:9] ]
            bulk_vel = [ float(val) for val in sline[9:12]]
            break

    f.close()
    return center, n_vec, bulk_vel

def find_normal_vector(ds, center):
    """
    Finds normal vector given dataset and center of galaxy

    Parameters:
        ds : yt loaded dataset
        center : array: coordinates to center of galaxy in cod_lenght units
    Returns:
        normal_vector : yt array: dimensionless normal vector pointing in the
                        direction of the axis of rotation of given center
        bulk_vel : yt array : bulk velocity of the galaxy in units km/s
    """

    #create sphere inside disk of galaxy
    sph_gal = ds.sphere(center, (10, 'kpc'))

    #compute the bulk velocity
    bulk_velocity = sph_gal.quantities.bulk_velocity(use_particles=False).in_units('km/s')
    sph_gal.set_field_parameter(("bulk_velocity"), bulk_velocity)

    #compute angular momentum vector normalize it
    axis_rot = sph_gal.quantities.angular_momentum_vector()
    normal_vector = axis_rot/(np.linalg.norm(axis_rot) * axis_rot.unit_array)

    return normal_vector, bulk_velocity
if __name__ == '__main__':
    ds_filename = argv[1]
    c, n, r, bv = find_center(ds_filename)

    print("x, y, z")
    print(f"{c[0]}, {c[1]}, {c[2]}")
    print(f"{n[0]}, {n[1]}, {n[2]}")
    print(f"{r}")
    print(f"{bv[0]}, {bv[1]}, {bv[2]}")
