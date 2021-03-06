###############################################################################
#                                                                             #
# Copyright (C) 2014 Edward d'Auvergne                                        #
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
from numpy import array, cos, float64, pi, sin, zeros
from unittest import TestCase

# relax module imports.
from lib.dispersion.dpl94 import r1rho_DPL94


class Test_dpl94(TestCase):
    """Unit tests for the lib.dispersion.dpl94 relax module."""

    def setUp(self):
        """Set up for all unit tests."""

        # Default parameter values.


        # The R1rho_prime parameter value (R1rho with no exchange).
        self.r1rho_prime = 2.5
        # Population of ground state.
        self.pA = 0.95
        # The chemical exchange difference between states A and B in ppm.
        self.dw = 0.5
        self.kex = 1000.0
        # The R1 relaxation rates.
        self.r1 = 1.0
        # The spin-lock field strengths in Hertz.
        self.spin_lock_nu1 = array([ 1000., 1500., 2000., 2500., 3000., 3500., 4000., 4500., 5000., 5500., 6000.])
        # The rotating frame tilt angles for each dispersion point.
        self.theta = array([1.5707963267948966, 1.5707963267948966, 1.5707963267948966, 1.5707963267948966, 1.5707963267948966, 1.5707963267948966, 1.5707963267948966, 1.5707963267948966, 1.5707963267948966, 1.5707963267948966, 1.5707963267948966])

        # The spin Larmor frequencies.
        self.sfrq = 599.8908617*1E6

        # Required data structures.
        self.num_points = 11
        self.R1rho = zeros(self.num_points, float64)


    def calc_r1rho(self):
        """Calculate and check the R1rho values."""

        # Parameter conversions.
        phi_ex_scaled, spin_lock_omega1_squared = self.param_conversion(pA=self.pA, dw=self.dw, sfrq=self.sfrq, spin_lock_nu1=self.spin_lock_nu1)

        # Calculate the R1rho values.
        r1rho_DPL94(r1rho_prime=self.r1rho_prime, phi_ex=phi_ex_scaled, kex=self.kex, theta=self.theta, R1=self.r1, spin_lock_fields2=spin_lock_omega1_squared, back_calc=self.R1rho)

        # Compare to function value.
        r1rho_no_rex = self.r1 * cos(self.theta)**2 + self.r1rho_prime * sin(self.theta)**2

        # Check all R1rho values.
        if self.kex > 1.e5:
            for i in range(self.num_points):
                self.assertAlmostEqual(self.R1rho[i], r1rho_no_rex[i], 2)
        else:
            for i in range(self.num_points):
                self.assertAlmostEqual(self.R1rho[i], r1rho_no_rex[i])


    def param_conversion(self, pA=None, dw=None, sfrq=None, spin_lock_nu1=None):
        """Convert the parameters.

        @keyword pA:            The population of state A.
        @type pA:               float
        @keyword dw:            The chemical exchange difference between states A and B in ppm.
        @type dw:               float
        @keyword sfrq:          The spin Larmor frequencies in Hz.
        @type sfrq:             float
        @keyword spin_lock_nu1: The spin-lock field strengths in Hertz.
        @type spin_lock_nu1:    float
        @return:                The parameters {phi_ex_scaled, k_BA}.
        @rtype:                 tuple of float
        """

        # Calculate pB.
        pB = 1.0 - pA

        # Calculate spin Larmor frequencies in 2pi.
        frqs = sfrq * 2 * pi

        # The phi_ex parameter value (pA * pB * delta_omega^2).
        phi_ex = pA * pB * (dw / 1.e6)**2

        # Convert phi_ex from ppm^2 to (rad/s)^2.
        phi_ex_scaled = phi_ex * frqs**2

        # The R1rho spin-lock field strengths squared (in rad^2.s^-2).
        spin_lock_omega1_squared = (2. * pi * spin_lock_nu1)**2

        # Return all values.
        return phi_ex_scaled, spin_lock_omega1_squared


    def test_dpl94_no_rex1(self):
        """Test the r1rho_dpl94() function for no exchange when dw = 0.0."""

        # Parameter reset.
        self.dw = 0.0

        # Calculate and check the R1rho values.
        self.calc_r1rho()


    def test_dpl94_no_rex2(self):
        """Test the r1rho_dpl94() function for no exchange when pA = 1.0."""

        # Parameter reset.
        self.pA = 1.0

        # Calculate and check the R1rho values.
        self.calc_r1rho()


    def test_dpl94_no_rex3(self):
        """Test the r1rho_dpl94() function for no exchange when kex = 0.0."""

        # Parameter reset.
        self.kex = 0.0

        # Calculate and check the R1rho values.
        self.calc_r1rho()


    def test_dpl94_no_rex4(self):
        """Test the r1rho_dpl94() function for no exchange when dw = 0.0 and pA = 1.0."""

        # Parameter reset.
        self.pA = 1.0
        self.dw = 0.0

        # Calculate and check the R1rho values.
        self.calc_r1rho()


    def test_dpl94_no_rex5(self):
        """Test the r1rho_dpl94() function for no exchange when dw = 0.0 and kex = 0.0."""

        # Parameter reset.
        self.dw = 0.0
        self.kex = 0.0

        # Calculate and check the R1rho values.
        self.calc_r1rho()


    def test_dpl94_no_rex6(self):
        """Test the r1rho_dpl94() function for no exchange when pA = 1.0 and kex = 0.0."""

        # Parameter reset.
        self.pA = 1.0
        self.kex = 0.0

        # Calculate and check the R1rho values.
        self.calc_r1rho()


    def test_dpl94_no_rex7(self):
        """Test the r1rho_dpl94() function for no exchange when dw = 0.0, pA = 1.0, and kex = 0.0."""

        # Parameter reset.
        self.dw = 0.0
        self.kex = 0.0

        # Calculate and check the R1rho values.
        self.calc_r1rho()


    def test_dpl94_no_rex8(self):
        """Test the r1rho_dpl94() function for no exchange when kex = 1e20."""

        # Parameter reset.
        self.kex = 1e20

        # Calculate and check the R2eff values.
        self.calc_r1rho()
