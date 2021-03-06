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

# Module docstring.
"""Module for all of the reduced spectral density mapping specific user functions."""

# relax module imports.
from lib.errors import RelaxError, RelaxFuncSetupError
from pipe_control.pipes import check_pipe
import specific_analyses


def set_frq(frq=None):
    """Function for selecting which relaxation data to use in the J(w) mapping."""

    # Test if the current pipe exists.
    check_pipe()

    # Test if the pipe type is set to 'jw'.
    function_type = cdp.pipe_type
    if function_type != 'jw':
        raise RelaxFuncSetupError(specific_analyses.setup.get_string(function_type))

    # Test if the frequency has been set.
    if hasattr(cdp, 'jw_frq'):
        raise RelaxError("The frequency has already been set.")

    # Create the data structure if it doesn't exist.
    if not hasattr(cdp, 'jw_frq'):
        cdp.jw_frq = {}

    # Set the frequency.
    cdp.jw_frq = frq
