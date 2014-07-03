#!/usr/bin/env python

###############################################################################
#                                                                             #
# Copyright (C) 2014 Troels E. Linnet                                         #
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

# Python module imports.
import cProfile
from os import getcwd, path
from numpy import array, int32, float64, ones, pi, zeros
import pstats
import sys

# Add to system path, according to 
if len(sys.argv) == 1:
    path_to_base = path.join(getcwd(), '..', '..', '..', '..')
else:
    path_to_base = path.abspath(sys.argv[1])

# Reverse sys path.
sys.path.reverse()
# Add to path.
sys.path.append(path_to_base)
# Reverse sys path.
sys.path.reverse()

# relax module imports.
from lib.physical_constants import g1H, g15N
from target_functions.relax_disp import Dispersion
from specific_analyses.relax_disp.variables import EXP_TYPE_CPMG_SQ, MODEL_B14_FULL, MODEL_CR72, MODEL_CR72_FULL, MODEL_NS_CPMG_2SITE_3D_FULL, MODEL_NS_CPMG_2SITE_STAR_FULL


# Alter setup.
def main():
    s_filename = 'single'
    # Profile for a single spin.
    cProfile.run('single(iter=100)', s_filename)

    c_filename = 'cluster'
    # Profile for a cluster of 100 spins.
    cProfile.run('cluster(iter=100)', c_filename)

    # Read all stats files into a single object
    s_stats = pstats.Stats(s_filename)
    c_stats = pstats.Stats(c_filename)
    #stats.add(c_filename)

    # Clean up filenames for the report
    s_stats.strip_dirs()
    c_stats.strip_dirs()

    # Sort the statistics by the cumulative time spent in the function. cumulative, time, calls
    s_stats.sort_stats('time')
    c_stats.sort_stats('time')

    s_stats.print_stats()
    c_stats.print_stats()


class Profile(Dispersion):
    """
    Class Profile inherits the Dispersion container class object.
    """

    def __init__(self, num_spins=1, num_points=10, model=None):
        """
        Special method __init__() is called first (acts as Constructor).
        It brings in data from outside the class like the variable num_spins.
        (in this case num_spins is also set to a default value of 1)
        The first parameter of any method/function in the class is always self,
        the name self is used by convention.  Assigning num_spins to self.num_spins allows it
        to be passed to all methods within the class.  Think of self as a carrier,
        or if you want impress folks call it target instance object.
        """

        # Define parameters
        self.model = model
        self.num_spins = num_spins
        #self.fields = [800. * 1E6]
        self.fields = [600. * 1E6, 800. * 1E6]
        #self.fields = [600. * 1E6, 800. * 1E6, 900. * 1E6]
        self.exp_type = [EXP_TYPE_CPMG_SQ]
        self.offset = [0]

        # Required data structures.
        self.num_points = num_points
        self.ncyc_list = list(range(2, 2*self.num_points + 1, 2))
        self.relax_time = 0.04
        self.points = array(self.ncyc_list) / self.relax_time
        self.value = array(list(range(1, len(self.ncyc_list)+1)), float64) * 1.00
        self.error = ones(len(self.ncyc_list), float64) * 0.01

        # Make nested list arrays of data. And return them.
        values, errors, cpmg_frqs, missing, frqs, exp_types, relax_times, offsets = self.return_r2eff_arrays()

        # Init the Dispersion Class.
        self.model = Dispersion(model=self.model, num_params=None, num_spins=self.num_spins, num_frq=len(self.fields), exp_types=exp_types, values=values, errors=errors, missing=missing, frqs=frqs, frqs_H=None, cpmg_frqs=cpmg_frqs, spin_lock_nu1=None, chemical_shifts=None, offset=offsets, tilt_angles=None, r1=None, relax_times=relax_times, scaling_matrix=None)


    def return_r2eff_arrays(self):
        """Return numpy arrays of the R2eff/R1rho values and errors.

        @return:    The numpy array structures of the R2eff/R1rho values, errors, missing data, and corresponding Larmor frequencies.  For each structure, the first dimension corresponds to the experiment types, the second the spins of a spin block, the third to the spectrometer field strength, and the fourth is the dispersion points.  For the Larmor frequency structure, the fourth dimension is omitted.  For R1rho-type data, an offset dimension is inserted between the spectrometer field strength and the dispersion points.
        @rtype:         lists of numpy float arrays, lists of numpy float arrays, lists of numpy float arrays, numpy rank-2 int array
        """

        # Initialise the data structures for the target function.
        exp_types = []
        values = []
        errors = []
        missing = []
        frqs = []
        frqs_H = []
        relax_times = []
        offsets = []
        for ei in range(len(self.exp_type)):
            values.append([])
            errors.append([])
            missing.append([])
            frqs.append([])
            frqs_H.append([])
            relax_times.append([])
            offsets.append([])
            for si in range(self.num_spins):
                values[ei].append([])
                errors[ei].append([])
                missing[ei].append([])
                frqs[ei].append([])
                frqs_H[ei].append([])
                offsets[ei].append([])
                for mi in range(len(self.fields)):
                    values[ei][si].append([])
                    errors[ei][si].append([])
                    missing[ei][si].append([])
                    frqs[ei][si].append(0.0)
                    frqs_H[ei][si].append(0.0)
                    offsets[ei][si].append([])
                    for oi in range(len(self.offset)):
                        values[ei][si][mi].append([])
                        errors[ei][si][mi].append([])
                        missing[ei][si][mi].append([])
                        offsets[ei][si][mi].append([])
            for mi in range(len(self.fields)):
                relax_times[ei].append(None)

        cpmg_frqs = []
        for ei in range(len(self.exp_type)):
            cpmg_frqs.append([])
            for mi in range(len(self.fields)):
                cpmg_frqs[ei].append([])
                for oi in range(len(self.offset)):
                    #cpmg_frqs[ei][mi].append(self.points)
                    cpmg_frqs[ei][mi].append([])


        # Pack the R2eff/R1rho data.
        si = 0
        for spin_index in range(self.num_spins):
            data_flag = True

            for ei in range(len(self.exp_type)):
                exp_type = self.exp_type[ei]
                # Add the experiment type.
                if exp_type not in exp_types:
                    exp_types.append(exp_type)

                for mi in range(len(self.fields)):
                    frq = self.fields[mi]
                    for oi in range(len(self.offset)):
                        for di in range(len(self.points)):
                            # The Larmor frequency for this spin (and that of an attached proton for the MMQ models) and field strength (in MHz*2pi to speed up the ppm to rad/s conversion).
                            frqs[ei][si][mi] = 2.0 * pi * frq / g1H * g15N * 1e-6

                            cpmg_frqs[ei][mi][oi] = self.points

                            missing[ei][si][mi][oi].append(0)

                            # Values
                            values[ei][si][mi][oi].append(self.value[di])
                            # The errors.
                            errors[ei][si][mi][oi].append(self.error[di])

                            # The relaxation times.
                            # Found.
                            relax_time = self.relax_time

                            # Store the time.
                            relax_times[ei][mi] = relax_time

            # Increment the spin index.
            si += 1

        # Convert to numpy arrays.
        relax_times = array(relax_times, float64)
        for ei in range(len(self.exp_type)):
            for si in range(self.num_spins):
                for mi in range(len(self.fields)):
                    for oi in range(len(self.offset)):
                        values[ei][si][mi][oi] = array(values[ei][si][mi][oi], float64)
                        errors[ei][si][mi][oi] = array(errors[ei][si][mi][oi], float64)
                        missing[ei][si][mi][oi] = array(missing[ei][si][mi][oi], int32)

        # Return the structures.
        return values, errors, cpmg_frqs, missing, frqs, exp_types, relax_times, offsets


    def assemble_param_vector(self, r2=None, r2a=None, r2b=None, dw=None, pA=None, kex=None, spins_params=None):
        """Assemble the dispersion relaxation dispersion curve fitting parameter vector.

        @keyword r2:            The transversal relaxation rate.
        @type r2:               float
        @keyword r2a:           The transversal relaxation rate for state A in the absence of exchange.
        @type r2a:              float
        @keyword r2b:           The transversal relaxation rate for state B in the absence of exchange.
        @type r2b:              float
        @keyword dw:            The chemical exchange difference between states A and B in ppm.
        @type dw:               float
        @keyword pA:            The population of state A.
        @type pA:               float
        @keyword kex:           The rate of exchange.
        @type kex:              float
        @keyword spins_params:  List of parameter strings used in dispersion model.
        @type spins_params:     array of strings
        @return:                An array of the parameter values of the dispersion relaxation model.
        @rtype:                 numpy float array
        """

        # Initialise.
        param_vector = []

        # Loop over the parameters of the cluster.
        for param_name, spin_index, mi in self.loop_parameters(spins_params=spins_params):
            if param_name == 'r2':
                value = r2
                value = value + mi + spin_index*0.1
            elif param_name == 'r2a':
                value = r2a
                value = value + mi+ spin_index*0.1
            elif param_name == 'r2b':
                value = r2b
                value = value + mi + spin_index*0.1
            elif param_name == 'dw':
                value = dw + spin_index
            elif param_name == 'pA':
                value = pA
            elif param_name == 'kex':
                value = kex

            # Add to the vector.
            param_vector.append(value)

        # Return a numpy array.
        return array(param_vector, float64)


    def loop_parameters(self, spins_params=None):
        """Generator function for looping of the parameters of the cluster.

        @keyword spins_params:  List of parameter strings used in dispersion model.
        @type spins_params:     array of strings
        @return:                The parameter name.
        @rtype:                 str
        """

        # Loop over the parameters of the cluster.
        # First the R2 parameters (one per spin per field strength).
        for spin_index in range(self.num_spins):

            # The R2 parameter.
            if 'r2' in spins_params:
                for ei in range(len(self.exp_type)):
                    for mi in range(len(self.fields)):
                        yield 'r2', spin_index, mi

            # The R2A parameter.
            if 'r2a' in spins_params:
                for ei in range(len(self.exp_type)):
                    for mi in range(len(self.fields)):
                        yield 'r2a', spin_index, mi


            # The R2B parameter.
            if 'r2b' in spins_params:
                for ei in range(len(self.exp_type)):
                    for mi in range(len(self.fields)):
                        yield 'r2b', spin_index, mi


        # Then the chemical shift difference parameters 'phi_ex', 'phi_ex_B', 'phi_ex_C', 'padw2', 'dw', 'dw_AB', 'dw_BC', 'dw_AB' (one per spin).
        for spin_index in range(self.num_spins):

            if 'dw' in spins_params:
                yield 'dw', spin_index, 0

        # All other parameters (one per spin cluster).
        for param in spins_params:
            if not param in ['r2', 'r2a', 'r2b', 'phi_ex', 'phi_ex_B', 'phi_ex_C', 'padw2', 'dw', 'dw_AB', 'dw_BC', 'dw_AB', 'dwH', 'dwH_AB', 'dwH_BC', 'dwH_AB']:
                if param == 'pA':
                    yield 'pA', 0, 0
                elif param == 'kex':
                    yield 'kex', 0, 0


    def calc(self, params):
        """Calculate chi2 values.

        @keyword params:  List of parameter strings used in dispersion model.
        @type params:     array of strings
        @return:          Chi2 value.
        @rtype:           float
        """

        # Return chi2 value.
        chi2 = self.model.func_CR72_full(params)
        return chi2


def single(num_spins=1, num_points=20, model=MODEL_CR72_FULL, iter=None):
    """Calculate for a single spin.

    @keyword num_spins:     Number of spins in the cluster.
    @type num_spins:        integer
    @keyword num_points:    The number of points the R2eff array should consists of.
    @type num_points:       integer
    @keyword model:         The dispersion model to instantiate the Dispersion class with.
    @type model:            string
    @keyword iter:          The number of iterations to perform the function call.
    @type iter:             int
    @return:                Chi2 value.
    @rtype:                 float
    """

    # Instantiate class
    C1 = Profile(num_spins=num_spins, num_points=num_points, model=model)

    # Assemble the parameter list.
    params = C1.assemble_param_vector(r2a=5.0, r2b=10.0, dw=3.0, pA=0.9, kex=1000.0, spins_params=['r2a', 'r2b', 'dw', 'pA', 'kex'])

    # Repeat the function call, to simulate minimisation.
    for i in range(iter):
        chi2 = C1.calc(params)


def cluster(num_spins=100, num_points=20, model=MODEL_CR72_FULL, iter=None):
    """Calculate for a number of clustered spins.

    @keyword num_spins:     Number of spins in the cluster.
    @type num_spins:        integer
    @keyword num_points:    The number of points the R2eff array should consists of.
    @type num_points:       integer
    @keyword model:         The dispersion model to instantiate the Dispersion class with.
    @type model:            string
    @keyword iter:          The number of iterations to perform the function call.
    @type iter:             int
    @return:                Chi2 value.
    @rtype:                 float
    """

    # Instantiate class
    C1 = Profile(num_spins=num_spins, num_points=num_points, model=model)

    # Assemble the parameter list.
    params = C1.assemble_param_vector(r2a=5.0, r2b=10.0, dw=3.0, pA=0.9, kex=1000.0, spins_params=['r2a', 'r2b', 'dw', 'pA', 'kex'])

    # Repeat the function call, to simulate minimisation.
    for i in range(iter):
        chi2 = C1.calc(params)


# Execute main function.
if __name__ == "__main__":
    main()

def test_reshape():
    C1 = Profile(num_spins=4, num_points=20, model=MODEL_CR72_FULL)
    end_index = C1.model.end_index
    print("end_index:", end_index)
    num_spins = C1.model.num_spins
    print("num_spins:", num_spins)
    num_frq = C1.model.num_frq
    print("num_frq:", num_frq)
    params = C1.assemble_param_vector(r2a=5.0, r2b=10.0, dw=3.0, pA=0.9, kex=1000.0, spins_params=['r2a', 'r2b', 'dw', 'pA', 'kex'])
    print("params", params)

    R20 = params[:end_index[1]].reshape(num_spins*2, num_frq)
    R20A = R20[::2].flatten()
    R20B = R20[1::2].flatten()
    dw = params[end_index[1]:end_index[2]]
    pA = params[end_index[2]]
    kex = params[end_index[2]+1]
    print("R20A", R20A, len(R20A))
    print("R20B", R20B, len(R20B))
    print("dw", dw, len(dw))
    print("dw", pA)
    print("kex", kex)

    for si in range(num_spins):
        for mi in range(num_frq):
            r20_index = mi + si*num_frq
            r20a=R20A[r20_index]
            r20b=R20B[r20_index]
            print "r20a", r20a, "r20b", r20b

    for mi in range(num_frq):
        mi_s = mi*num_spins
        mi_e = mi_s + num_spins
        r20a=R20A[mi_s:mi_e]
        r20b=R20B[mi_s:mi_e]
        print "r20a", r20a, "r20b", r20b

    values = array(C1.model.values)
    values = array(values)
    ex = values
    # (1, 4, 3, 1, 20): ex, spin, frq, off, disp
    #print type(ex), len(ex), ex.shape, ex
    ex2 = ex.reshape(num_frq*20*num_spins)
    #print type(ex2), len(ex2), ex2.shape, ex2
    #print "here"
    model = C1.calc(params)
    print model

#test_par()