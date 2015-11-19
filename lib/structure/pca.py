###############################################################################
#                                                                             #
# Copyright (C) 2015 Edward d'Auvergne                                        #
#                                                                             #
# This file is part of the program relax (http://www.nmr-relax.com).          #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU General Public License as published by        #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

# Module docstring.
"""Module for performing a principle component analysis (PCA)."""

# Python module imports.
from numpy import float64, outer, zeros
from numpy.linalg import eigh

# relax library module imports.
from lib.structure.statistics import calc_mean_structure


def calc_covariance_matrix(coord=None):
    """Calculate the covariance matrix for the structures.

    @keyword coord:         The list of coordinates of all models to superimpose.  The first index is the models, the second is the atomic positions, and the third is the xyz coordinates.
    @type coord:            list of numpy rank-2, Nx3 arrays
    @return:                The covariance matrix.
    @rtype:                 numpy rank-2, 3N array
    """

    # Init.
    M = len(coord)
    N = len(coord[0])
    covariance_matrix = zeros((N*3, N*3), float64)
    mean_struct = zeros((N, 3), float64)

    # Calculate the mean structure.
    calc_mean_structure(coord, mean_struct)

    # Loop over the models.
    for i in range(M):
        # The deviations from the mean.
        deviations = coord[i] - mean_struct

        # Sum the covariance element.
        covariance_matrix += outer(deviations, deviations)

    # Normalise.
    covariance_matrix /= M

    # Return the matrix.
    return covariance_matrix


def pca_analysis(coord=None, num_modes=4):
    """Perform the PCA analysis.

    @keyword coord:         The list of coordinates of all models to superimpose.  The first index is the models, the second is the atomic positions, and the third is the xyz coordinates.
    @type coord:            list of numpy rank-2, Nx3 arrays
    @keyword num_modes:     The number of PCA modes to calculate.
    @type num_modes:        int
    """

    # Calculate the covariance matrix for the structures.
    covariance_matrix = calc_covariance_matrix(coord)

    # Perform an eigenvalue decomposition on the covariance matrix.
    values, vectors = eigh(covariance_matrix)

    # Sort the values and vectors.
    indices = values.argsort()[::-1]
    values = values[indices]
    vectors = vectors[:, indices]

    # Truncation to the desired number of modes.
    values = values[:num_modes]
    vectors = vectors[:,:num_modes]

    # Printout.
    print("\nThe eigenvalues are:")
    for i in range(num_modes):
        print("Mode %i:  %10.5f" % (i+1, values[i]))
