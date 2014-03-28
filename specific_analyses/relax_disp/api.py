###############################################################################
#                                                                             #
# Copyright (C) 2004-2014 Edward d'Auvergne                                   #
# Copyright (C) 2009 Sebastien Morin                                          #
# Copyright (C) 2013-2014 Troels E. Linnet                                    #
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
"""The relaxation dispersion API object."""

# Python module imports.
from copy import deepcopy
from re import search
from types import MethodType

# relax module imports.
from lib.errors import RelaxError, RelaxImplementError
from multi import Processor_box
from pipe_control import pipes, sequence
from pipe_control.mol_res_spin import check_mol_res_spin_data, return_spin, spin_loop
from pipe_control.sequence import return_attached_protons
from specific_analyses.api_base import API_base
from specific_analyses.api_common import API_common
from specific_analyses.relax_disp.checks import check_model_type
from specific_analyses.relax_disp.disp_data import average_intensity, calc_rotating_frame_params, find_intensity_keys, has_exponential_exp_type, has_proton_mmq_cpmg, loop_cluster, loop_exp_frq_offset_point, loop_time, pack_back_calc_r2eff, return_param_key_from_data, spin_ids_to_containers
from specific_analyses.relax_disp.optimisation import Disp_memo, Disp_minimise_command, back_calc_peak_intensities, back_calc_r2eff, calculate_r2eff, minimise_r2eff
from specific_analyses.relax_disp.parameters import assemble_scaling_matrix, get_param_names, get_value, loop_parameters, param_index_to_param_info, param_num
from specific_analyses.relax_disp.variables import EXP_TYPE_CPMG_PROTON_MQ, EXP_TYPE_CPMG_PROTON_SQ, MODEL_LIST_MMQ


class Relax_disp(API_base, API_common):
    """Class containing functions for relaxation dispersion curve fitting."""

    def __init__(self):
        """Initialise the class by placing API_common methods into the API."""

        # Execute the base class __init__ method.
        super(Relax_disp, self).__init__()

        # Place methods into the API.
        self.data_init = self._data_init_spin
        self.model_type = self._model_type_local
        self.return_conversion_factor = self._return_no_conversion_factor
        self.return_value = self.return_value
        self.set_param_values = self._set_param_values_spin

        # Set up the spin parameters.
        self.PARAMS.add('peak_intensity', scope='spin', desc='The peak intensities', py_type=dict, grace_string='\\qPeak intensities\\Q')
        self.PARAMS.add('relax_times', scope='spin', py_type=dict, grace_string='\\qRelaxation time period (s)\\Q')
        self.PARAMS.add('cpmg_frqs', scope='spin', py_type=dict, grace_string='\\qCPMG pulse train frequency (Hz)\\Q')
        self.PARAMS.add('spin_lock_nu1', scope='spin', py_type=dict, grace_string='\\qSpin-lock field strength (Hz)\\Q')
        self.PARAMS.add('r2eff', scope='spin', default=15.0, desc='The effective transversal relaxation rate', set='params', py_type=dict, grace_string='\\qR\\s2,eff\\N\\Q (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('i0', scope='spin', default=10000.0, desc='The initial intensity', py_type=dict, set='params', grace_string='\\qI\\s0\\Q', err=True, sim=True)
        self.PARAMS.add('r2', scope='spin', default=15.0, desc='The transversal relaxation rate', set='params', py_type=dict, grace_string='\\qR\\s2\\N\\Q (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('r2a', scope='spin', default=15.0, desc='The transversal relaxation rate for state A in the absence of exchange', set='params', py_type=dict, grace_string='\\qR\\s2,A\\N\\Q (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('r2b', scope='spin', default=15.0, desc='The transversal relaxation rate for state B in the absence of exchange', set='params', py_type=dict, grace_string='\\qR\\s2,B\\N\\Q (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('pA', scope='spin', default=0.5, desc='The population for state A', set='params', py_type=float, grace_string='\\qp\\sA\\N\\Q', err=True, sim=True)
        self.PARAMS.add('pB', scope='spin', default=0.5, desc='The population for state B', set='params', py_type=float, grace_string='\\qp\\sB\\N\\Q', err=True, sim=True)
        self.PARAMS.add('pC', scope='spin', default=0.5, desc='The population for state C', set='params', py_type=float, grace_string='\\qp\\sC\\N\\Q', err=True, sim=True)
        self.PARAMS.add('phi_ex', scope='spin', default=5.0, desc='The phi_ex = pA.pB.dw**2 value (ppm^2)', set='params', py_type=float, grace_string='\\xF\\B\\sex\\N = \\q p\\sA\\N.p\\sB\\N.\\xDw\\B\\S2\\N\\Q  (ppm\\S2\\N)', err=True, sim=True)
        self.PARAMS.add('phi_ex_B', scope='spin', default=5.0, desc='The fast exchange factor between sites A and B (ppm^2)', set='params', py_type=float, grace_string='\\xF\\B\\sex,B\\N (ppm\\S2\\N)', err=True, sim=True)
        self.PARAMS.add('phi_ex_C', scope='spin', default=5.0, desc='The fast exchange factor between sites A and C (ppm^2)', set='params', py_type=float, grace_string='\\xF\\B\\sex,C\\N (ppm\\S2\\N)', err=True, sim=True)
        self.PARAMS.add('padw2', scope='spin', default=1.0, desc='The pA.dw**2 value (ppm^2)', set='params', py_type=float, grace_string='\\qp\\sA\\N.\\xDw\\B\\S2\\N\\Q  (ppm\\S2\\N)', err=True, sim=True)
        self.PARAMS.add('dw', scope='spin', default=0.0, desc='The chemical shift difference between states A and B (in ppm)', set='params', py_type=float, grace_string='\\q\\xDw\\B\\Q (ppm)', err=True, sim=True)
        self.PARAMS.add('dw_AB', scope='spin', default=0.0, desc='The chemical shift difference between states A and B for 3-site exchange (in ppm)', set='params', py_type=float, grace_string='\\q\\xDw\\B\\Q\\SAB\\N (ppm)', err=True, sim=True)
        self.PARAMS.add('dw_AC', scope='spin', default=0.0, desc='The chemical shift difference between states A and C for 3-site exchange (in ppm)', set='params', py_type=float, grace_string='\\q\\xDw\\B\\Q\\SAC\\N (ppm)', err=True, sim=True)
        self.PARAMS.add('dw_BC', scope='spin', default=0.0, desc='The chemical shift difference between states B and C for 3-site exchange (in ppm)', set='params', py_type=float, grace_string='\\q\\xDw\\B\\Q\\SBC\\N (ppm)', err=True, sim=True)
        self.PARAMS.add('dwH', scope='spin', default=0.0, desc='The proton chemical shift difference between states A and B (in ppm)', set='params', py_type=float, grace_string='\\q\\xDw\\B\\sH\\N\\Q (ppm)', err=True, sim=True)
        self.PARAMS.add('dwH_AB', scope='spin', default=0.0, desc='The proton chemical shift difference between states A and B for 3-site exchange (in ppm)', set='params', py_type=float, grace_string='\\q\\xDw\\B\\sH\\N\\Q\\SAB\\N (ppm)', err=True, sim=True)
        self.PARAMS.add('dwH_AC', scope='spin', default=0.0, desc='The proton chemical shift difference between states A and C for 3-site exchange (in ppm)', set='params', py_type=float, grace_string='\\q\\xDw\\B\\sH\\N\\Q\\SAC\\N (ppm)', err=True, sim=True)
        self.PARAMS.add('dwH_BC', scope='spin', default=0.0, desc='The proton chemical shift difference between states B and C for 3-site exchange (in ppm)', set='params', py_type=float, grace_string='\\q\\xDw\\B\\sH\\N\\Q\\SBC\\N (ppm)', err=True, sim=True)
        self.PARAMS.add('kex', scope='spin', default=10000.0, desc='The exchange rate', set='params', py_type=float, grace_string='\\qk\\sex\\N\\Q (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('kex_AB', scope='spin', default=10000.0, desc='The exchange rate between sites A and B for 3-site exchange with kex_AB = k_AB + k_BA (rad.s^-1)', set='params', py_type=float, grace_string='\\qk\\sex\\N\\Q\\SAB\\N (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('kex_AC', scope='spin', default=10000.0, desc='The exchange rate between sites A and C for 3-site exchange with kex_AC = k_AC + k_CA (rad.s^-1)', set='params', py_type=float, grace_string='\\qk\\sex\\N\\Q\\SAC\\N (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('kex_BC', scope='spin', default=10000.0, desc='The exchange rate between sites B and C for 3-site exchange with kex_BC = k_BC + k_CB (rad.s^-1)', set='params', py_type=float, grace_string='\\qk\\sex\\N\\Q\\SBC\\N (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('kB', scope='spin', default=10000.0, desc='Approximate chemical exchange rate constant between sites A and B (rad.s^-1)', set='params', py_type=float, grace_string='\\qk\\sB\\N\\Q (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('kC', scope='spin', default=10000.0, desc='Approximate chemical exchange rate constant between sites A and C (rad.s^-1)', set='params', py_type=float, grace_string='\\qk\\sC\\N\\Q (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('tex', scope='spin', default=1.0/10000.0, desc='The time of exchange (tex = 1/kex)', set='params', py_type=float, grace_string='\\q\\xt\\B\\sex\\N\\Q (s.rad\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('theta', scope='spin', desc='Rotating frame tilt angle : ( theta = arctan(w_1 / Omega) ) (rad)', set='params', grace_string='Rotating frame tilt angle (rad)', py_type=dict, err=False, sim=False)
        self.PARAMS.add('w_eff', scope='spin', desc='Effective field in rotating frame : ( w_eff = sqrt(Omega^2 + w_1^2) ) (rad.s^-1)', grace_string='Effective field in rotating frame (rad.s\\S-1\\N)', set='params', py_type=dict, err=False, sim=False)
        self.PARAMS.add('k_AB', scope='spin', default=10000.0, desc='The exchange rate from state A to state B', set='params', py_type=float, grace_string='\\qk\\sAB\\N\\Q (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('k_BA', scope='spin', default=10000.0, desc='The exchange rate from state B to state A', set='params', py_type=float, grace_string='\\qk\\sBA\\N\\Q (rad.s\\S-1\\N)', err=True, sim=True)
        self.PARAMS.add('params', scope='spin', desc='The model parameters', py_type=list)
        self.PARAMS.add('model', scope='spin', desc='The dispersion model', py_type=str)

        # Add the minimisation data.
        self.PARAMS.add_min_data(min_stats_global=False, min_stats_spin=True)


    def base_data_loop(self):
        """Custom generator method for looping over the base data.

        For the R2eff model, the base data is the peak intensity data defining a single exponential curve.  For all other models, the base data is the R2eff/R1rho values for individual spins.


        @return:    For the R2eff model, a tuple of the spin container and the exponential curve identifying key (the CPMG frequency or R1rho spin-lock field strength).  For all other models, the spin container and ID from the spin loop.
        @rtype:     (tuple of SpinContainer instance and float) or (SpinContainer instance and str)
        """

        # The R2eff model data (the base data is peak intensities).
        if cdp.model_type == 'R2eff':
            # Loop over the sequence.
            for spin in spin_loop():
                # Skip deselected spins.
                if not spin.select:
                    continue

                # Skip spins with no peak intensity data.
                if not hasattr(spin, 'peak_intensity'):
                    continue

                # Loop over each spectrometer frequency and dispersion point.
                for exp_type, frq, offset, point in loop_exp_frq_offset_point():
                    yield spin, exp_type, frq, offset, point

        # All other models (the base data is the R2eff/R1rho values).
        else:
            # 1H MMQ flag.
            proton_mmq_flag = has_proton_mmq_cpmg()

            # Loop over the sequence.
            for spin, spin_id in spin_loop(return_id=True):
                # Skip deselected spins.
                if not spin.select:
                    continue

                # Skip protons for MMQ data.
                if spin.model in MODEL_LIST_MMQ and spin.isotope == '1H':
                    continue

                # Get the attached proton.
                proton = None
                if proton_mmq_flag:
                    proton = return_attached_protons(spin_id)[0]

                # Skip spins with no R2eff/R1rho values.
                if not hasattr(spin, 'r2eff') and not hasattr(proton, 'r2eff'):
                    continue

                # Yield the spin container and ID.
                yield spin, spin_id


    def calculate(self, spin_id=None, verbosity=1, sim_index=None):
        """Calculate the model chi-squared value or the R2eff values for fixed time period data.

        @keyword spin_id:   The spin identification string.
        @type spin_id:      None or str
        @keyword verbosity: The amount of information to print.  The higher the value, the greater the verbosity.
        @type verbosity:    int
        @keyword sim_index: The MC simulation index (unused).
        @type sim_index:    None
        """

        # Data checks.
        pipes.test()
        check_mol_res_spin_data()
        check_model_type()

        # Special exponential curve-fitting for the 'R2eff' model.
        if cdp.model_type == 'R2eff':
            calculate_r2eff()

        # Calculate the chi-squared value.
        else:
            # 1H MMQ flag.
            proton_mmq_flag = has_proton_mmq_cpmg()

            # Loop over all spins.
            for spin, spin_id in spin_loop(return_id=True, skip_desel=True):
                # Skip protons for MMQ data.
                if spin.model in MODEL_LIST_MMQ and spin.isotope == '1H':
                    continue

                # Get the attached proton.
                proton = None
                if proton_mmq_flag:
                    proton = return_attached_protons(spin_id)[0]

                # The back calculated values.
                back_calc = back_calc_r2eff(spin=spin, spin_id=spin_id, store_chi2=True)

                # Pack the data.
                pack_back_calc_r2eff(spin=spin, spin_id=spin_id, si=0, back_calc=back_calc, proton_mmq_flag=proton_mmq_flag)


    def constraint_algorithm(self):
        """Return the 'Log barrier' optimisation constraint algorithm.

        @return:    The 'Log barrier' constraint algorithm.
        @rtype:     str
        """

        # The log barrier algorithm, as required by minfx.
        return 'Log barrier'


    def create_mc_data(self, data_id):
        """Create the Monte Carlo peak intensity data.

        @param data_id: The tuple of the spin container and the exponential curve identifying key, as yielded by the base_data_loop() generator method.
        @type data_id:  SpinContainer instance and float
        @return:        The Monte Carlo simulation data.
        @rtype:         list of floats
        """

        # The R2eff model (with peak intensity base data).
        if cdp.model_type == 'R2eff':
            # Unpack the data.
            spin, exp_type, frq, offset, point = data_id

            # Back calculate the peak intensities.
            values = back_calc_peak_intensities(spin=spin, exp_type=exp_type, frq=frq, offset=offset, point=point)

        # All other models (with R2eff/R1rho base data).
        else:
            # 1H MMQ flag.
            proton_mmq_flag = has_proton_mmq_cpmg()

            # Unpack the data.
            spin, spin_id = data_id

            # Back calculate the R2eff/R1rho data.
            back_calc = back_calc_r2eff(spin=spin, spin_id=spin_id)

            # Get the attached proton data.
            if proton_mmq_flag:
                proton = return_attached_protons(spin_id)[0]
                proton_back_calc = back_calc_r2eff(spin=proton, spin_id=spin_id)

            # Convert to a dictionary matching the R2eff data structure.
            values = {}
            for exp_type, frq, offset, point, ei, mi, oi, di in loop_exp_frq_offset_point(return_indices=True):
                # Alias the correct data.
                current_bc = back_calc
                current_spin = spin
                if exp_type in [EXP_TYPE_CPMG_PROTON_SQ, EXP_TYPE_CPMG_PROTON_MQ]:
                    current_spin = proton
                    current_bc = proton_back_calc

                # The parameter key.
                param_key = return_param_key_from_data(exp_type=exp_type, frq=frq, offset=offset, point=point)

                # Skip missing data.
                if not hasattr(current_spin, 'r2eff') or param_key not in current_spin.r2eff.keys():
                    continue

                # Store the result.
                values[param_key] = back_calc[ei][0][mi][oi][di]

        # Return the MC data.
        return values


    def deselect(self, model_info, sim_index=None):
        """Deselect models or simulations.

        @param model_info:      The spin ID list from the model_loop() API method.
        @type model_info:       int
        @keyword sim_index:     The optional Monte Carlo simulation index.  If None, then models will be deselected, otherwise the given simulation will.
        @type sim_index:        None or int
        """

        # Loop over all the spins and deselect them.
        for spin_id in model_info:
            # Get the spin.
            spin = return_spin(spin_id)

            # Spin deselection.
            if sim_index == None:
                spin.select = False

            # Simulation deselection.
            else:
                spin.select_sim[sim_index] = False


    def duplicate_data(self, pipe_from=None, pipe_to=None, model_info=None, global_stats=False, verbose=True):
        """Duplicate the data specific to a single model.

        @keyword pipe_from:     The data pipe to copy the data from.
        @type pipe_from:        str
        @keyword pipe_to:       The data pipe to copy the data to.
        @type pipe_to:          str
        @keyword model_info:    The model index from model_info().
        @type model_info:       int
        @keyword global_stats:  The global statistics flag.
        @type global_stats:     bool
        @keyword verbose:       A flag which if True will cause info to be printed out.
        @type verbose:          bool
        """

        # First create the pipe_to data pipe, if it doesn't exist, but don't switch to it.
        if not pipes.has_pipe(pipe_to):
            pipes.create(pipe_to, pipe_type='relax_disp', switch=False)

        # Get the data pipes.
        dp_from = pipes.get_pipe(pipe_from)
        dp_to = pipes.get_pipe(pipe_to)

        # Duplicate all non-sequence specific data.
        for data_name in dir(dp_from):
            # Skip the container objects.
            if data_name in ['mol', 'interatomic', 'structure', 'exp_info', 'result_files']:
                continue

            # Skip dispersion specific parameters.
            if data_name in ['model']:
                continue

            # Skip special objects.
            if search('^_', data_name) or data_name in list(dp_from.__class__.__dict__.keys()):
                continue

            # Get the original object.
            data_from = getattr(dp_from, data_name)

            # The data already exists.
            if hasattr(dp_to, data_name):
                # Get the object in the target pipe.
                data_to = getattr(dp_to, data_name)

                # The data must match!
                if data_from != data_to:
                    raise RelaxError("The object " + repr(data_name) + " is not consistent between the pipes " + repr(pipe_from) + " and " + repr(pipe_to) + ".")

                # Skip the data.
                continue

            # Duplicate the data.
            setattr(dp_to, data_name, deepcopy(data_from))

        # No sequence data, so skip the rest.
        if dp_from.mol.is_empty():
            return

        # Duplicate the sequence data if it doesn't exist.
        if dp_to.mol.is_empty():
            sequence.copy(pipe_from=pipe_from, pipe_to=pipe_to, preserve_select=True, verbose=verbose)

        # Loop over the cluster.
        for id in model_info:
            # The original spin container.
            spin = return_spin(id, pipe=pipe_from)

            # Duplicate the spin specific data.
            for name in dir(spin):
                # Skip special objects.
                if search('^__', name):
                    continue

                # Get the object.
                obj = getattr(spin, name)

                # Skip methods.
                if isinstance(obj, MethodType):
                    continue

                # Duplicate the object.
                new_obj = deepcopy(getattr(spin, name))
                setattr(dp_to.mol[spin._mol_index].res[spin._res_index].spin[spin._spin_index], name, new_obj)


    def eliminate(self, name, value, model_info, args, sim=None):
        """Relaxation dispersion model elimination, parameter by parameter.

        @param name:        The parameter name.
        @type name:         str
        @param value:       The parameter value.
        @type value:        float
        @param model_info:  The list of spin IDs from the model_loop() API method.
        @type model_info:   int
        @param args:        The c1 and c2 elimination constant overrides.
        @type args:         None or tuple of float
        @keyword sim:       The Monte Carlo simulation index.
        @type sim:          int
        @return:            True if the model is to be eliminated, False otherwise.
        @rtype:             bool
        """

        # Skip the R2eff model parameters.
        if name in ['r2eff', 'i0']:
            return False

        # Default limits.
        c1 = 0.501
        c2 = 0.999
        c3 = 1.0

        # Depack the arguments.
        if args != None:
            c1, c2, c3 = args

        # Elimination text.
        elim_text = "Data pipe '%s':  The %s parameter of %.5f is %s, eliminating " % (pipes.cdp_name(), name, value, "%s")
        if sim == None:
            elim_text += "the spin cluster %s." % model_info
        else:
            elim_text += "simulation %i of the spin cluster %s." % (sim, model_info)

        # The pA parameter.
        if name == 'pA':
            if value < c1:
                print(elim_text % ("less than  %.5f" % c1))
                return True
            if value > c2:
                print(elim_text % ("greater than  %.5f" % c2))
                return True

        # The tex parameter.
        if name == 'tex':
            if value > c3:
                print(elim_text % ("greater than  %.5f" % c3))
                return True

        # Accept model.
        return False


    def get_param_names(self, model_info=None):
        """Return a vector of parameter names.

        @keyword model_info:    The list spin ID strings from the model_loop() API method.
        @type model_info:       list of str
        @return:                The vector of parameter names.
        @rtype:                 list of str
        """

        # Get the spin containers.
        spins = []
        for spin_id in model_info:
            # Get the spin.
            spin = return_spin(spin_id)

            # Skip deselected spins.
            if not spin.select:
                continue

            # Add the spin.
            spins.append(spin)

        # No spins.
        if not len(spins):
            return None

        # Call the get_param_names() function.
        return get_param_names(spins)


    def get_param_values(self, model_info=None, sim_index=None):
        """Return a vector of parameter values.

        @keyword model_info:    The model index from model_info().  This is zero for the global models or equal to the global spin index (which covers the molecule, residue, and spin indices).
        @type model_info:       int
        @keyword sim_index:     The Monte Carlo simulation index.
        @type sim_index:        int
        @return:                The vector of parameter values.
        @rtype:                 list of str
        """

        # Get the spin containers.
        spins = []
        for spin_id in model_info:
            # Get the spin.
            spin = return_spin(spin_id)

            # Skip deselected spins.
            if not spin.select:
                continue

            # Add the spin.
            spins.append(spin)

        # No spins.
        if not len(spins):
            return None

        # Loop over the parameters of the cluster, fetching their values.
        values = []
        for param_name, param_index, si, r20_key in loop_parameters(spins=spins):
            values.append(get_value(spins=spins, sim_index=sim_index, param_name=param_name, spin_index=si, r20_key=r20_key))

        # Return all values.
        return values


    def grid_search(self, lower=None, upper=None, inc=None, constraints=True, verbosity=1, sim_index=None):
        """The relaxation dispersion curve fitting grid search function.

        @keyword lower:         The lower bounds of the grid search which must be equal to the number of parameters in the model.
        @type lower:            array of numbers
        @keyword upper:         The upper bounds of the grid search which must be equal to the number of parameters in the model.
        @type upper:            array of numbers
        @keyword inc:           The increments for each dimension of the space for the grid search. The number of elements in the array must equal to the number of parameters in the model.
        @type inc:              array of int
        @keyword constraints:   If True, constraints are applied during the grid search (eliminating parts of the grid).  If False, no constraints are used.
        @type constraints:      bool
        @keyword verbosity:     A flag specifying the amount of information to print.  The higher the value, the greater the verbosity.
        @type verbosity:        int
        @keyword sim_index:     The index of the simulation to apply the grid search to.  If None, the normal model is optimised.
        @type sim_index:        int
        """

        # Minimisation.
        self.minimise(min_algor='grid', lower=lower, upper=upper, inc=inc, constraints=constraints, verbosity=verbosity, sim_index=sim_index)


    def minimise(self, min_algor=None, min_options=None, func_tol=None, grad_tol=None, max_iterations=None, constraints=False, scaling=True, verbosity=0, sim_index=None, lower=None, upper=None, inc=None):
        """Relaxation dispersion curve fitting function.

        @keyword min_algor:         The minimisation algorithm to use.
        @type min_algor:            str
        @keyword min_options:       An array of options to be used by the minimisation algorithm.
        @type min_options:          array of str
        @keyword func_tol:          The function tolerance which, when reached, terminates optimisation.  Setting this to None turns of the check.
        @type func_tol:             None or float
        @keyword grad_tol:          The gradient tolerance which, when reached, terminates optimisation.  Setting this to None turns of the check.
        @type grad_tol:             None or float
        @keyword max_iterations:    The maximum number of iterations for the algorithm.
        @type max_iterations:       int
        @keyword constraints:       If True, constraints are used during optimisation.
        @type constraints:          bool
        @keyword scaling:           If True, diagonal scaling is enabled during optimisation to allow the problem to be better conditioned.
        @type scaling:              bool
        @keyword verbosity:         The amount of information to print.  The higher the value, the greater the verbosity.
        @type verbosity:            int
        @keyword sim_index:         The index of the simulation to optimise.  This should be None if normal optimisation is desired.
        @type sim_index:            None or int
        @keyword lower:             The lower bounds of the grid search which must be equal to the number of parameters in the model.  This optional argument is only used when doing a grid search.
        @type lower:                array of numbers
        @keyword upper:             The upper bounds of the grid search which must be equal to the number of parameters in the model.  This optional argument is only used when doing a grid search.
        @type upper:                array of numbers
        @keyword inc:               The increments for each dimension of the space for the grid search. The number of elements in the array must equal to the number of parameters in the model.  This argument is only used when doing a grid search.
        @type inc:                  array of int
        """

        # Data checks.
        check_mol_res_spin_data()
        check_model_type()

        # Initialise some empty data pipe structures so that the target function set up does not fail.
        if not hasattr(cdp, 'cpmg_frqs_list'):
            cdp.cpmg_frqs_list = []
        if not hasattr(cdp, 'spin_lock_nu1_list'):
            cdp.spin_lock_nu1_list = []

        # Special exponential curve-fitting for the 'R2eff' model.
        if cdp.model_type == 'R2eff':
            # Sanity checks.
            if not has_exponential_exp_type():
                raise RelaxError("The R2eff model with the fixed time period dispersion experiments cannot be optimised.")

            # Optimisation.
            minimise_r2eff(min_algor=min_algor, min_options=min_options, func_tol=func_tol, grad_tol=grad_tol, max_iterations=max_iterations, constraints=constraints, scaling=scaling, verbosity=verbosity, sim_index=sim_index, lower=lower, upper=upper, inc=inc)

            # Exit the method.
            return

        # Get the Processor box singleton (it contains the Processor instance) and alias the Processor.
        processor_box = Processor_box() 
        processor = processor_box.processor

        # The number of time points for the exponential curves (if present).
        num_time_pts = 1
        if hasattr(cdp, 'num_time_pts'):
            num_time_pts = cdp.num_time_pts

        # Number of spectrometer fields.
        fields = [None]
        field_count = 1
        if hasattr(cdp, 'spectrometer_frq'):
            fields = cdp.spectrometer_frq_list
            field_count = cdp.spectrometer_frq_count

        # Loop over the spin blocks.
        for spin_ids in self.model_loop():
            # The spin containers.
            spins = spin_ids_to_containers(spin_ids)

            # Skip deselected clusters.
            skip = True
            for spin in spins:
                if spin.select:
                    skip = False
            if skip:
                continue

            # Diagonal scaling.
            scaling_matrix = assemble_scaling_matrix(spins=spins, scaling=scaling)

            # Set up the slave command object.
            command = Disp_minimise_command(spins=spins, spin_ids=spin_ids, sim_index=sim_index, scaling_matrix=scaling_matrix, min_algor=min_algor, min_options=min_options, func_tol=func_tol, grad_tol=grad_tol, max_iterations=max_iterations, constraints=constraints, verbosity=verbosity, lower=lower, upper=upper, inc=inc, fields=fields, param_names=get_param_names(spins))

            # Set up the memo.
            memo = Disp_memo(spins=spins, spin_ids=spin_ids, sim_index=sim_index, scaling_matrix=scaling_matrix, verbosity=verbosity)

            # Add the slave command and memo to the processor queue.
            processor.add_to_queue(command, memo)


    def model_desc(self, model_info):
        """Return a description of the model.

        @param model_info:  The model index from model_info().
        @type model_info:   int
        @return:            The model description.
        @rtype:             str
        """

        # The model loop is over the spin clusters, so return a description of the cluster.
        return "The spin cluster %s." % model_info


    def model_loop(self):
        """Loop over the spin groupings for one model applied to multiple spins.

        @return:    The list of spins per block will be yielded, as well as the list of spin IDs.
        @rtype:     tuple of list of SpinContainer instances and list of spin IDs
        """

        # The cluster loop.
        for spin_ids in loop_cluster(skip_desel=False):
            yield spin_ids


    def model_statistics(self, model_info=None, spin_id=None, global_stats=None):
        """Return the k, n, and chi2 model statistics.

        k - number of parameters.
        n - number of data points.
        chi2 - the chi-squared value.


        @keyword model_info:    The model index from model_info().
        @type model_info:       None or int
        @keyword spin_id:       The spin identification string.  This is ignored in the N-state model.
        @type spin_id:          None or str
        @keyword global_stats:  A parameter which determines if global or local statistics are returned.  For the N-state model, this argument is ignored.
        @type global_stats:     None or bool
        @return:                The optimisation statistics, in tuple format, of the number of parameters (k), the number of data points (n), and the chi-squared value (chi2).
        @rtype:                 tuple of (int, int, float)
        """

        # Unpack the data.
        spin_ids = model_info
        spins = spin_ids_to_containers(spin_ids)

        # The number of parameters for the cluster.
        k = param_num(spins=spins)

        # The number of points from all spins.
        n = 0
        for spin in spins:
            # Skip deselected spins.
            if not spin.select:
                continue

            n += len(spin.r2eff)

        # Take the chi-squared from the first spin of the cluster (which has a value).
        chi2 = None
        for spin in spins:
            # Skip deselected spins.
            if not spin.select:
                continue

            if hasattr(spin, 'chi2'):
                chi2 = spin.chi2
                break

        # Return the values.
        return k, n, chi2


    def overfit_deselect(self, data_check=True, verbose=True):
        """Deselect spins which have insufficient data to support minimisation.

        @keyword data_check:    A flag to signal if the presence of base data is to be checked for.
        @type data_check:       bool
        @keyword verbose:       A flag which if True will allow printouts.
        @type verbose:          bool
        """

        # Test the sequence data exists.
        check_mol_res_spin_data()

        # 1H MMQ flag.
        proton_mmq_flag = has_proton_mmq_cpmg()

        # Loop over spin data.
        for spin, spin_id in spin_loop(return_id=True, skip_desel=True):
            # Skip protons for MMQ data.
            if spin.model in MODEL_LIST_MMQ and spin.isotope == '1H':
                continue

            # Get the attached proton.
            proton = None
            if proton_mmq_flag:
                # Get all protons.
                proton_spins = return_attached_protons(spin_id)

                # Only one allowed.
                if len(proton_spins) > 1:
                    print("Multiple protons attached to the spin '%s', but one one attached proton is supported for the MMQ-type models." % spin_id)
                    spin.select = False
                    continue

                # Alias the single proton.
                if len(proton_spins):
                    proton = proton_spins[0]

            # Check if data exists.
            if not hasattr(spin, 'r2eff') and not hasattr(proton, 'r2eff'):
                print("No R2eff data could be found, deselecting the '%s' spin." % spin_id)
                spin.select = False
                continue


    def return_data(self, data_id=None):
        """Return the peak intensity data structure.

        @param data_id: The spin ID string, as yielded by the base_data_loop() generator method.
        @type data_id:  str
        @return:        The peak intensity data structure.
        @rtype:         list of float
        """

        # The R2eff model.
        if cdp.model_type == 'R2eff':
            # Unpack the data.
            spin, exp_type, frq, offset, point = data_id

            # Return the data.
            return spin.peak_intensity

        # All other models.
        else:
            raise RelaxImplementError


    def return_error(self, data_id=None):
        """Return the standard deviation data structure.

        @param data_id: The tuple of the spin container and the exponential curve identifying key, as yielded by the base_data_loop() generator method.
        @type data_id:  SpinContainer instance and float
        @return:        The standard deviation data structure.
        @rtype:         list of float
        """

        # The R2eff model.
        if cdp.model_type == 'R2eff':
            # Unpack the data.
            spin, exp_type, frq, offset, point = data_id

            # Generate the data structure to return.
            errors = []
            for time in loop_time(exp_type=exp_type, frq=frq, offset=offset, point=point):
                errors.append(average_intensity(spin=spin, exp_type=exp_type, frq=frq, offset=offset, point=point, time=time, error=True))

        # All other models.
        else:
            # Unpack the data.
            spin, spin_id = data_id

            # 1H MMQ flag.
            proton_mmq_flag = has_proton_mmq_cpmg()

            # Get the attached proton.
            proton = None
            if proton_mmq_flag:
                proton = return_attached_protons(spin_id)[0]

            # The errors.
            r2eff_err = {}
            if hasattr(spin, 'r2eff_err'):
                r2eff_err.update(spin.r2eff_err)
            if hasattr(proton, 'r2eff_err'):
                r2eff_err.update(proton.r2eff_err)
            return r2eff_err

        # Return the error list.
        return errors


    def return_value(self, spin, param, sim=None, bc=False):
        """Return the value and error corresponding to the parameter.

        If sim is set to an integer, return the value of the simulation and None.


        @param spin:    The SpinContainer object.
        @type spin:     SpinContainer
        @param param:   The name of the parameter to return values for.
        @type param:    str
        @keyword sim:   The Monte Carlo simulation index.
        @type sim:      None or int
        @keyword bc:    The back-calculated data flag.  If True, then the back-calculated data will be returned rather than the actual data.
        @type bc:       bool
        @return:        The value and error corresponding to
        @rtype:         tuple of length 2 of floats or None
        """

        # Define list of special parameters.
        special_parameters = ['theta', 'w_eff']

        # Use api_common function for paramets not defined in special_parameters.
        if param not in special_parameters:
            returnval = self._return_value_general(spin=spin, param=param, sim=sim, bc=bc)
            return returnval

        # If parameter in special_parameters, the do the following.

        # Initial values.
        value = None
        error = None

        # Return the data
        theta_spin_dic, Domega_spin_dic, w_eff_spin_dic, dic_key_list = calc_rotating_frame_params(spin=spin)

        # Return for parameter theta
        if param == "theta":
            value = theta_spin_dic

        # Return for parameter theta
        elif param == "w_eff":
            value = w_eff_spin_dic

        # Return the data.
        return value, error


    def set_error(self, model_info, index, error):
        """Set the parameter errors.

        @param model_info:  The spin container originating from model_loop().
        @type model_info:   unknown
        @param index:       The index of the parameter to set the errors for.
        @type index:        int
        @param error:       The error value.
        @type error:        float
        """

        # Unpack the data.
        spin_ids = model_info
        spins = spin_ids_to_containers(spin_ids)

        # The number of parameters.
        total_param_num = param_num(spins=spins)

        # No more model parameters.
        model_param = True
        if index >= total_param_num:
            model_param = False

        # The auxiliary cluster parameters.
        aux_params = []
        if 'pA' in spins[0].params:
            aux_params.append('pB')
        if 'pB' in spins[0].params:
            aux_params.append('pA')
        if 'kex' in spins[0].params:
            aux_params.append('tex')
        if 'tex' in spins[0].params:
            aux_params.append('kex')

        # Convert the parameter index.
        if model_param:
            param_name, si, mi = param_index_to_param_info(index=index, spins=spins)
        else:
            param_name = aux_params[index - total_param_num]
            si = 0
            mi = 0

        # The parameter error name.
        err_name = param_name + "_err"

        # The exponential curve parameters.
        if param_name in ['r2eff', 'i0']:
            # Initialise if needed.
            if not hasattr(spins[si], err_name):
                setattr(spins[si], err_name, {})

            # Set the value.
            setattr(spins[si], err_name, error)

        # Model and auxiliary parameters.
        else:
            for spin in spins:
                setattr(spin, err_name, error)


    def set_selected_sim(self, model_info, select_sim):
        """Set the simulation selection flag.

        @param model_info:  The list of spins and spin IDs per cluster originating from model_loop().
        @type model_info:   tuple of list of SpinContainer instances and list of spin IDs
        @param select_sim:  The selection flag for the simulations.
        @type select_sim:   bool
        """

        # Unpack the data.
        spin_ids = model_info
        spins = spin_ids_to_containers(spin_ids)

        # Loop over the spins, storing the structure for each spin.
        for spin in spins:
            spin.select_sim = deepcopy(select_sim)


    def sim_init_values(self):
        """Initialise the Monte Carlo parameter values."""

        # Get the parameter object names.
        param_names = self.data_names(set='params')

        # Add the names of kex-tex pair.
        pairs = {}
        pairs['kex'] = 'tex'
        pairs['tex'] = 'kex'

        # Add the names of pA-pB pair.
        pairs['pA'] = 'pB'
        pairs['pB'] = 'pA'

        # Add the names of kex-k_AB pair and kex-k_BA pair.
        pairs['k_AB'] = 'kex'
        pairs['k_BA'] = 'kex'

        # Get the minimisation statistic object names.
        min_names = self.data_names(set='min')


        # Test if Monte Carlo parameter values have already been set.
        #############################################################

        # Loop over the spins.
        for spin in spin_loop():
            # Skip deselected spins.
            if not spin.select:
                continue

            # Loop over all the parameter names.
            for object_name in param_names:
                # Name for the simulation object.
                sim_object_name = object_name + '_sim'


        # Set the Monte Carlo parameter values.
        #######################################

        # Loop over the spins.
        for spin in spin_loop():
            # Skip deselected spins.
            if not spin.select:
                continue

            # Skip protons for MMQ data.
            if spin.model in MODEL_LIST_MMQ and spin.isotope == '1H':
                continue

            # Loop over all the data names.
            for object_name in param_names:
                # Not a parameter of the model.
                if not (object_name in spin.params or (object_name in pairs and pairs[object_name] in spin.params)):
                    continue

                # Name for the simulation object.
                sim_object_name = object_name + '_sim'

                # Create the simulation object.
                setattr(spin, sim_object_name, [])

                # Get the simulation object.
                sim_object = getattr(spin, sim_object_name)

                # Loop over the simulations.
                for j in range(cdp.sim_number):
                    # The non-simulation value.
                    if object_name not in spin.params:
                        value = deepcopy(getattr(spin, pairs[object_name]))
                    else:
                        value = deepcopy(getattr(spin, object_name))

                    # Copy and append the data.
                    sim_object.append(value)

            # Loop over all the minimisation object names.
            for object_name in min_names:
                # Name for the simulation object.
                sim_object_name = object_name + '_sim'

                # Create the simulation object.
                setattr(spin, sim_object_name, [])

                # Get the simulation object.
                sim_object = getattr(spin, sim_object_name)

                # Loop over the simulations.
                for j in range(cdp.sim_number):
                    # Copy and append the data.
                    sim_object.append(deepcopy(getattr(spin, object_name)))


    def sim_pack_data(self, data_id, sim_data):
        """Pack the Monte Carlo simulation data.

        @param data_id:     The tuple of the spin container and the exponential curve identifying key, as yielded by the base_data_loop() generator method.
        @type data_id:      SpinContainer instance and float
        @param sim_data:    The Monte Carlo simulation data.
        @type sim_data:     list of float
        """

        # The R2eff model (with peak intensity base data).
        if cdp.model_type == 'R2eff':
            # Unpack the data.
            spin, exp_type, frq, offset, point = data_id

            # Initialise the data structure if needed.
            if not hasattr(spin, 'peak_intensity_sim'):
                spin.peak_intensity_sim = {}

            # Loop over each time point.
            ti = 0
            for time in loop_time(exp_type=exp_type, frq=frq, offset=offset, point=point):
                # Get the intensity keys.
                int_keys = find_intensity_keys(exp_type=exp_type, frq=frq, offset=offset, point=point, time=time)

                # Loop over the intensity keys.
                for int_key in int_keys:
                    # Test if the simulation data point already exists.
                    if int_key in spin.peak_intensity_sim:
                        raise RelaxError("Monte Carlo simulation data for the key '%s' already exists." % int_key)

                    # Initialise the list.
                    spin.peak_intensity_sim[int_key] = []

                    # Loop over the simulations, appending the corresponding data.
                    for i in range(cdp.sim_number):
                        spin.peak_intensity_sim[int_key].append(sim_data[i][ti])

                # Increment the time index.
                ti += 1

        # All other models (with R2eff/R1rho base data).
        else:
            # Unpack the data.
            spin, spin_id = data_id

            # 1H MMQ flag.
            proton_mmq_flag = has_proton_mmq_cpmg()

            # Get the attached proton.
            proton = None
            if proton_mmq_flag:
                proton = return_attached_protons(spin_id)[0]

            # Pack the data.
            spin.r2eff_sim = sim_data
            if proton != None:
                proton.r2eff_sim = sim_data


    def sim_return_param(self, model_info, index):
        """Return the array of simulation parameter values.

        @param model_info:  The model information originating from model_loop().
        @type model_info:   unknown
        @param index:       The index of the parameter to return the array of values for.
        @type index:        int
        @return:            The array of simulation parameter values.
        @rtype:             list of float
        """

        # Unpack the data.
        spin_ids = model_info
        spins = spin_ids_to_containers(spin_ids)

        # The number of parameters.
        total_param_num = param_num(spins=spins)

        # No more model parameters.
        model_param = True
        if index >= total_param_num:
            model_param = False

        # The auxiliary cluster parameters.
        aux_params = []
        for spin in spins:
            if not spin.select:
                continue
            if 'pA' in spin.params:
                aux_params.append('pB')
            if 'pB' in spin.params:
                aux_params.append('pA')
            if 'kex' in spin.params:
                aux_params.append('tex')
            if 'tex' in spin.params:
                aux_params.append('kex')
            break

        # No more auxiliary parameters.
        total_aux_num = total_param_num + len(aux_params)
        if index >= total_aux_num:
            return

        # Convert the parameter index.
        if model_param:
            param_name, si, mi = param_index_to_param_info(index=index, spins=spins)
            if not param_name in ['r2eff', 'i0']:
                si = 0
        else:
            param_name = aux_params[index - total_param_num]
            si = 0
            mi = 0

        # The exponential curve parameters.
        sim_data = []
        if param_name == 'r2eff':
            for i in range(cdp.sim_number):
                sim_data.append(spins[si].r2eff_sim[i])
        elif param_name == 'i0':
            for i in range(cdp.sim_number):
                sim_data.append(spins[si].i0_sim[i])

        # Model and auxiliary parameters.
        else:
            sim_data = getattr(spins[si], param_name + "_sim")

        # Set the sim data to None if empty.
        if sim_data == []:
            sim_data = None

        # Return the object.
        return sim_data


    def sim_return_selected(self, model_info):
        """Return the array of selected simulation flags.

        @param model_info:  The list of spins and spin IDs per cluster originating from model_loop().
        @type model_info:   tuple of list of SpinContainer instances and list of spin IDs
        @return:            The array of selected simulation flags.
        @rtype:             list of int
        """

        # Unpack the data.
        spin_ids = model_info
        spins = spin_ids_to_containers(spin_ids)

        # Return the array from the first spin, as this array will be identical for all spins in the cluster.
        return spins[0].select_sim
