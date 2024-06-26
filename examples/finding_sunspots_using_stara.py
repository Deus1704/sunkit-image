"""
============================
Finding sunspots using STARA
============================

This example demonstrates the use of Sunspot Tracking And Recognition
Algorithm (STARA) in detecting and plotting sunspots. More information
on the algorithm can be found in `this <https://doi.org/10.1017/S1743921311014992>`__ paper.
If you wish to perform analysis over a large period of time we suggest to refer
`this <https://gitlab.com/wtbarnes/aia-on-pleiades/-/blob/master/notebooks/tidy/finding_sunspots.ipynb>`__
notebook implementation of the same algorithm using dask arrays.
"""
# sphinx_gallery_thumbnail_number = 4 # NOQA: ERA001

import astropy.units as u
import matplotlib.pyplot as plt
import sunpy.io._fits
import sunpy.map
from astropy.table import QTable
from astropy.time import Time
from skimage.measure import label, regionprops_table
from sunpy.net import Fido
from sunpy.net import attrs as a

from sunkit_image.stara import stara

###############################################################################
# Firstly, let's download HMI continuum data from the Virtual Solar Observatory.

query = Fido.search(a.Time("2023-01-01 00:00", "2023-01-01 00:01"), a.Instrument("HMI"), a.Physobs("intensity"))
file = Fido.fetch(query)

###############################################################################
# Once the data is downloaded, we read the FITS file using`sunpy.map.Map`.

hmi_map = sunpy.map.Map(file)

###############################################################################
# HMI maps are inverted, meaning that the solar north pole appears at the
# bottom of the image. To correct this, we rotate each map in the MapSequence
# using the ``rotate`` method with an order of 3. For detailed reason as to why, please refer this
# `example <https://docs.sunpy.org/en/stable/generated/gallery/map_transformations/upside_down_hmi.html#sphx-glr-generated-gallery-map-transformations-upside-down-hmi-py>`__.

cont_rotated = hmi_map.rotate(order=3)

###############################################################################
# Plot the rotated map.

fig = plt.figure()
ax = plt.subplot(projection=cont_rotated)
im = cont_rotated.plot(axes=ax)

###############################################################################
# To reduce computational expense, we resample the continuum image to a lower
# resolution. For computational perspective, the ``hmi_map`` has a dimension of ``4102*4102`` pixels.
# The next step downsamples this continuum image to a dimension of ``1024*1024`` pixels,
# reducing the data size by nearly 16 times. This step ensures that running the algorithm on the full-resolution
# image is not overly computationally expensive.

cont_rotated_resample = cont_rotated.resample((1024, 1024) * u.pixel)

###############################################################################
# Next, we use the STARA function to detect sunspots in the resampled map.

segs = stara(cont_rotated_resample, limb_filter=10 * u.percent)

###############################################################################
# Finally, we plot the resampled map along with the detected sunspots. We create
# a new Matplotlib figure and subplot with the projection defined by the resampled
# map, plot the resampled map, and overlay contours of the detected sunspots using
# the ``contour`` method.

fig = plt.figure()
ax = plt.subplot(projection=cont_rotated_resample)
im = cont_rotated_resample.plot(axes=ax, autoalign=True)
ax.contour(segs, levels=0)

###############################################################################
# To focus on specific regions containing sunspots, we can create a submap,
# which is a smaller section of the original map. This allows us to zoom in
# on areas of interest. We define the coordinates of the rectangle to crop
# in pixel coordinates.

bottom_left = cont_rotated_resample.pixel_to_world(240 * u.pix, 350 * u.pix)
top_right = cont_rotated_resample.pixel_to_world(310 * u.pix, 410 * u.pix)

# Create the submap using the world coordinates of the bottom left and top right corners.
hmi_submap = cont_rotated_resample.submap(bottom_left, top_right=top_right)
segs = stara(hmi_submap, limb_filter=10 * u.percent)

# Plot the submap along with the contours.
fig = plt.figure()
ax = plt.subplot(projection=hmi_submap)
im = hmi_submap.plot(axes=ax, autoalign=True)
ax.contour(segs, levels=0)

###############################################################################
# We can further enhance our analysis by extracting key properties from the
# segmented image and organizing them into a structured table.
# First, a labeled image is created where each connected component (sunspot)
# is assigned a unique label.

labelled = label(segs)

# Extract properties of the labeled regions (sunspots)
regions = regionprops_table(
    labelled,
    hmi_submap.data,
    properties=[
        "label",  # Unique for each sunspot
        "centroid",  # Centroid coordinates (center of mass)
        "area",  # Total area (number of pixels)
        "min_intensity",
    ],
)
# A new column named "obstime" is added to the table, which contains
# the observation date for each sunspot.
regions["obstime"] = Time([hmi_submap.date] * regions["label"].size)
# The pixel coordinates of sunspot centroids are converted to world coordinates
# (solar longitude and latitude) in the heliographic Stonyhurst projection.
regions["center_coord"] = hmi_submap.pixel_to_world(
    regions["centroid-0"] * u.pix,
    regions["centroid-1"] * u.pix,
).heliographic_stonyhurst
# Finally, the QTable containing the extracted sunspot properties is printed.
print(QTable(regions))

###############################################################################
# Further we could also plot a map with the corresponding center coordinates
# marked and their number.

# Extract centroid coordinates.
centroids_x = regions["centroid-1"]
centroids_y = regions["centroid-0"]

# Plot the submap with centroids.
fig = plt.figure()
ax = plt.subplot(projection=hmi_submap)
im = hmi_submap.plot(axes=ax, autoalign=True)
ax.contour(segs, levels=0)

# Plot the centroids on the image.
ax.scatter(centroids_x, centroids_y, color="red", marker="o", s=30, label="Centroids")

# Label each centroid with its corresponding sunspot label for better identification.
for i, labels in enumerate(regions["label"]):
    ax.text(centroids_x[i], centroids_y[i], f"{labels}", color="yellow", fontsize=16)

plt.legend()

plt.show()