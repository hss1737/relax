###############################################################################
#                                                                             #
# Copyright (C) 2004-2014 Edward d'Auvergne                                   #
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

# Package docstring.
"""The R1 and R2 exponential relaxation curve fitting parameter functions."""

# Python module imports.
from numpy import array, float64, identity, zeros
from re import search

# relax module imports.
from lib.mathematics import round_to_next_order


def assemble_param_vector(spin=None, sim_index=None):
    """Assemble the exponential curve parameter vector (as a numpy array).

    @keyword spin:          The spin data container.
    @type spin:             SpinContainer instance
    @keyword sim_index:     The optional MC simulation index.
    @type sim_index:        int
    @return:                An array of the parameter values of the exponential model.
    @rtype:                 numpy array
    """

    # Initialise.
    param_vector = []

    # Loop over the model parameters.
    for i in range(len(spin.params)):
        # Relaxation rate.
        if spin.params[i] == 'rx':
            if sim_index != None:
                param_vector.append(spin.rx_sim[sim_index])
            elif spin.rx == None:
                param_vector.append(0.0)
            else:
                param_vector.append(spin.rx)

        # Initial intensity.
        elif spin.params[i] == 'i0':
            if sim_index != None:
                param_vector.append(spin.i0_sim[sim_index])
            elif spin.i0 == None:
                param_vector.append(0.0)
            else:
                param_vector.append(spin.i0)

        # Intensity at infinity.
        elif spin.params[i] == 'iinf':
            if sim_index != None:
                param_vector.append(spin.iinf_sim[sim_index])
            elif spin.iinf == None:
                param_vector.append(0.0)
            else:
                param_vector.append(spin.iinf)

    # Return a numpy array.
    return array(param_vector, float64)


def assemble_scaling_matrix(spin=None, scaling=True):
    """Create and return the scaling matrix.

    @keyword spin:          The spin data container.
    @type spin:             SpinContainer instance
    @keyword scaling:       A flag which if false will cause the identity matrix to be returned.
    @type scaling:          bool
    @return:                The diagonal and square scaling matrix.
    @rtype:                 numpy diagonal matrix
    """

    # Initialise.
    scaling_matrix = identity(len(spin.params), float64)
    i = 0

    # No diagonal scaling.
    if not scaling:
        return scaling_matrix

    # Loop over the parameters.
    for i in range(len(spin.params)):
        # Relaxation rate.
        if spin.params[i] == 'rx':
            pass

        # Intensity scaling.
        elif search('^i', spin.params[i]):
            scaling_matrix[i, i] = round_to_next_order(max(spin.peak_intensity.values()))

    # Return the scaling matrix.
    return scaling_matrix


def disassemble_param_vector(param_vector=None, spin=None, sim_index=None):
    """Disassemble the parameter vector.

    @keyword param_vector:  The parameter vector.
    @type param_vector:     numpy array
    @keyword spin:          The spin data container.
    @type spin:             SpinContainer instance
    @keyword sim_index:     The optional MC simulation index.
    @type sim_index:        int
    """

    # Monte Carlo simulations.
    if sim_index != None:
        # The relaxation rate.
        spin.rx_sim[sim_index] = param_vector[0]

        # Initial intensity.
        spin.i0_sim[sim_index] = param_vector[1]

        # Intensity at infinity.
        if cdp.curve_type == 'inv':
            spin.iinf_sim[sim_index] = param_vector[2]

    # Parameter values.
    else:
        # The relaxation rate.
        spin.rx = param_vector[0]

        # Initial intensity.
        spin.i0 = param_vector[1]

        # Intensity at infinity.
        if cdp.curve_type == 'inv':
            spin.iinf = param_vector[2]


def linear_constraints(spin=None, scaling_matrix=None):
    """Set up the relaxation curve fitting linear constraint matrices A and b.

    Standard notation
    =================

    The relaxation rate constraints are::

        Rx >= 0

    The intensity constraints are::

        I0 >= 0
        Iinf >= 0


    Matrix notation
    ===============

    In the notation A.x >= b, where A is an matrix of coefficients, x is an array of parameter
    values, and b is a vector of scalars, these inequality constraints are::

        | 1  0  0 |     |  Rx  |      |    0    |
        |         |     |      |      |         |
        | 1  0  0 |  .  |  I0  |  >=  |    0    |
        |         |     |      |      |         |
        | 1  0  0 |     | Iinf |      |    0    |


    @keyword spin:              The spin data container.
    @type spin:                 SpinContainer instance
    @keyword scaling_matrix:    The diagonal, square scaling matrix.
    @type scaling_matrix:       numpy diagonal matrix
    """

    # Initialisation (0..j..m).
    A = []
    b = []
    n = len(spin.params)
    zero_array = zeros(n, float64)
    i = 0
    j = 0

    # Loop over the parameters.
    for k in range(len(spin.params)):
        # Relaxation rate.
        if spin.params[k] == 'rx':
            # Rx >= 0.
            A.append(zero_array * 0.0)
            A[j][i] = 1.0
            b.append(0.0)
            j = j + 1

        # Intensity parameter.
        elif search('^i', spin.params[k]):
            # I0, Iinf >= 0.
            A.append(zero_array * 0.0)
            A[j][i] = 1.0
            b.append(0.0)
            j = j + 1

        # Increment i.
        i = i + 1

    # Convert to numpy data structures.
    A = array(A, float64)
    b = array(b, float64)

    return A, b
