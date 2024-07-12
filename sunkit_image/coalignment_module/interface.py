import warnings

import numpy as np
import sunpy.map
from sunpy.util.exceptions import SunpyUserWarning

from sunkit_image.coalignment_module.util.decorators import registered_methods

__all__ = ["coalignment"]


def update_metadata(target_map, affineParams):
    """
    Update the metadata of a sunpy Map object based on affine transformation
    parameters.

    Parameters
    ----------
    target_map : `sunpy.map.Map`
        The original map object whose metadata is to be updated.
    affineParams : object
        An object containing the affine transformation parameters. This object must
        have attributes for translation (dx, dy), scale, and rotation.

    Returns
    -------
    `sunpy.map.Map`
        A new sunpy map object with updated metadata reflecting the affine transformation.
    """
    ref_pix = target_map.reference_pixel
    pc_matrix = target_map.rotation_matrix

    # Extacting the affine parameters
    translation = affineParams.translation
    scale = affineParams.scale
    rotation = affineParams.rotation

    # Updating the reference pixel
    new_ref = ref_pix + translation
    # Updating the PC matrix
    cos_theta = np.cos(rotation)
    sin_theta = np.sin(rotation)
    rotation_matrix = np.array([[cos_theta, -sin_theta], [sin_theta, cos_theta]])
    new_pc_matrix = pc_matrix @ rotation_matrix @ scale

    # Create a new map with the updated metadata
    new_meta = target_map.meta.copy()
    new_meta["CRPIX1"] = new_ref[0].value
    new_meta["CRPIX2"] = new_ref[1].value
    new_meta["PC1_1"] = new_pc_matrix[0, 0]
    new_meta["PC1_2"] = new_pc_matrix[0, 1]
    new_meta["PC2_1"] = new_pc_matrix[1, 0]
    new_meta["PC2_2"] = new_pc_matrix[1, 1]

    return sunpy.map.Map(target_map.data, new_meta)


def warn_user_of_nan(array, name):
    """
    Issues a warning if there are NaN values in the input array.

    Parameters
    ----------
    array : `numpy.ndarray`
        The input array to be checked for NaN values.
    name : str
        The name of the array, used in the warning message.
    """
    if not np.all(np.isfinite(array)):
        warnings.warn(
            f"The {name} map has nonfinite entries. "
            "This could cause errors when calculating shift between two "
            "images. Please make sure there are no infinity or "
            "Not a Number values. For instance, replacing them with a "
            "local mean.",
            SunpyUserWarning,
            stacklevel=3,
        )


def coalignment(reference_map, target_map, method):
    """
    Performs image coalignment using a specified method. It updates the
    metadata of the target map so as to align it with the reference map.

    Parameters
    ----------
    reference_map : `sunpy.map.Map`
        The reference map to which the target map is to be coaligned.
    target_map : `sunpy.map.Map`
        The target map to be coaligned to the reference map.
    method : str
        The name of the registered coalignment method to use.

    Returns
    -------
    `sunpy.map.Map`
        The coaligned target map with the updated metadata.

    Raises
    ------
    ValueError
        If the specified method is not registered.
    """
    if method not in registered_methods:
        msg = f"Method {method} is not a registered method. Please register before using."
        raise ValueError(msg)
    target_array = target_map.data
    reference_array = reference_map.data

    # Warn user if any NANs, Infs, etc are present in the input or the template array
    warn_user_of_nan(target_array, "target")
    warn_user_of_nan(reference_array, "reference")

    affineParams = registered_methods[method](target_array, reference_array)
    return update_metadata(target_map, affineParams)
