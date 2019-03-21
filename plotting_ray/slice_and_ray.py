import yt
import trident as tri
import numpy as np

home="/mnt/home/boydbre1/"
filename=home+"data/DD0076/DD0076"

#load in dataset
ds = yt.load(filename)

ray_start= np.array([0, 0, 0], dtype=float)
ray_end = np.array([0.5, 1, 1], dtype=float)

line_list = ['H', 'Si', 'Mg II', 'C II 1335']

#calc norm vec and center
center = (ray_end + ray_start)/2
center[2]=0.5

#find ray and normalize it
ray = ray_end - ray_start
ray = ray/np.linalg.norm(ray)

#find ray perpendicular with z=0
norm_vec = [-1 * ray[0], ray[1], 0]

y_slice = yt.SlicePlot(ds, 'y', 'density', north_vector = [0, 0, 1], center=center)
cut = yt.SlicePlot(ds, norm_vec, 'density', north_vector = [0, 0, 1], center=center)

ray_start =ds.arr(ray_start, "code_length")
ray_end = ds.arr(ray_end, "code_length")
tri_ray = tri.make_simple_ray(ds,
                              start_position = ray_start,
                              end_position = ray_end,
                              lines = line_list,
			      ftype = 'gas')

cut.annotate_ray(tri_ray)
cut.save("attempted_cut.png")
y_slice.annotate_ray(tri_ray)
y_slice.save("normal_orientation.png")
print(ray_start)
print(ray_end)
