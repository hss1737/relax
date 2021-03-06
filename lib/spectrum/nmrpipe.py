###############################################################################
#                                                                             #
# Copyright (C) 2013-2014 Troels E. Linnet                                    #
# Copyright (C) 2014 Edward d'Auvergne                                        #
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
"""Module containing functions for handling NMRPipe SeriesTab files."""


# Python module imports.
import re
from glob import glob
from os import sep
from os.path import abspath
subprocess_module = False
try:
    import subprocess
    subprocess_module = True
except ImportError:
    pass
from warnings import warn

# relax module imports.
from lib.errors import RelaxError
from lib.io import file_root, get_file_path, open_write_file, sort_filenames, write_data
from lib.warnings import RelaxWarning


def read_seriestab(peak_list=None, file_data=None, int_col=None):
    """Extract the intensity information from the NMRPipe SeriesTab peak intensity file.

    @keyword peak_list: The peak list object to place all data into.
    @type peak_list:    lib.spectrum.objects.Peak_list instance
    @keyword file_data: The data extracted from the file converted into a list of lists.
    @type file_data:    list of lists of str
    @keyword int_col:  The column which to multiply the peak intensity data (used by the SeriesTab intensity file format).
    @type int_col:     int
    @raises RelaxError: When the expected peak intensity is not a float.
    """

    # Set start variables.
    modeline = False
    mode = False
    varsline = False
    header = False

    # Loop over lines, to extract variables and find header size.
    line_nr = 0
    for line in file_data:
        if len(line) > 0:
            if line[0] == 'REMARK' and line[1] == 'Mode:':
                modeline = line[2:]
                mode = modeline[0]
            elif line[0] == 'VARS':
                varsline = line[1:]
            elif line[0] == '1':
                header = line_nr
                break
        line_nr += 1

    # Raise RelaxError, if the MODE is not found.
    if not (modeline and mode):
        raise RelaxError("MODE not detected. Expecting line 2:\nREMARK Mode: Summation")

    # Raise RelaxError, if the VARS line is not found.
    if not (varsline):
        raise RelaxError("VARS not detected. Expecting line 8:\nVARS INDEX X_AXIS Y_AXIS X_PPM Y_PPM VOL ASS Z_A0")

    # Raise RelaxError, if the header size is not found.
    if not header:
        raise RelaxError("'1' not detected in start of line. Cannot determine header size.")

    # Find index of assignment ASS.
    ass_i = varsline.index('ASS')

    # Chemical shifts preparation.
    w1_col = None
    w2_col = None

    # Find index of chemical shift Y_PPM which in sparky is w1.
    w1_col = varsline.index('Y_PPM')

    # Find index of chemical shift X_PPM which in sparky is w2.
    w2_col = varsline.index('X_PPM')

    # Make a regular search for Z_A entries.
    Z_A = re.compile("Z_A*")
    spectra = list(filter(Z_A.search, varsline))

    # Find index of Z_A entries.
    spectra_i = []
    for y in spectra:
        spectra_i.append(varsline.index(y))

    # Remove the header.
    file_data = file_data[header:]

    # Loop over the file data.
    for line in file_data:
        # Skip non-assigned peaks.
        if line[ass_i] == '?-?':
            continue

        # First split by the 2D separator.
        assign1, assign2 = re.split('-', line[ass_i])

        # The assignment of the first dimension.
        row1 = re.split('([a-zA-Z]+)', assign1)
        name1 = row1[-2] + row1[-1]

        # The assignment of the second dimension.
        row2 = re.split('([a-zA-Z]+)', assign2)
        name2 = row2[-2] + row2[-1]

        # Get the residue number for dimension 1.
        got_res_num1 = True
        try:
            res_num1 = int(row1[-3])
        except:
            got_res_num1 = False
            raise RelaxError("Improperly formatted NMRPipe SeriesTab file, cannot process the residue number for dimension 1 in assignment: %s." % line[0])

        # Get the residue number for dimension 2.
        try:
            res_num2 = int(row2[-3])
        except:
            # We cannot always expect dimension 2 to have residue number.
            if got_res_num1:
                res_num2 = res_num1
            else:
                res_num2 = None
                warn(RelaxWarning("Improperly formatted NMRPipe SeriesTab file, cannot process the residue number for dimension 2 in assignment: %s. Setting residue number to %s." % (line[0], res_num2)))

        # The residue name for dimension 1.
        got_res_name1 = True
        try:
            res_name1 = row1[-4]
        except:
            got_res_name1 = False
            res_name1 = None
            warn(RelaxWarning("Improperly formatted NMRPipe SeriesTab file, cannot process the residue name for dimension 1 in assignment: %s. Setting residue name to %s." % (line[0], res_name1)))

        # The residue name for dimension 2.
        try:
            res_name2 = row2[-4]
        except:
            # We cannot always expect dimension 2 to have residue name.
            if got_res_name1:
                res_name2 = res_name1
            else:
                res_name2 = None
                warn(RelaxWarning("Improperly formatted NMRPipe SeriesTab file, cannot process the residue name for dimension 2 in assignment: %s. Setting residue name to %s." % (line[0], res_name2)))

        # Get the intensities.
        try:
            # Loop over the spectra.
            intensities = []
            for i in range(len(spectra)):
                # The intensity is given by column multiplication.
                intensities.append(float(line[spectra_i[i]])*float(line[5]))

        # Bad data.
        except ValueError:
            raise RelaxError("The peak intensity value %s from the line %s is invalid." % (intensity, line))

        # Chemical shifts.
        w1 = None
        w2 = None
        if w1_col != None:
            try:
                w1 = float(line[w1_col])
            except ValueError:
                raise RelaxError("The chemical shift from the line %s is invalid." % line)
        if w2_col != None:
            try:
                w2 = float(line[w2_col])
            except ValueError:
                raise RelaxError("The chemical shift from the line %s is invalid." % line)

        # Add the assignment to the peak list object.
        peak_list.add(res_nums=[res_num1, res_num2], res_names=[res_name1, res_name2], spin_names=[name1, name2], shifts=[w1, w2], intensity=intensities, intensity_name=spectra)


def show_apod_extract(file_name=None, dir=None, path_to_command='showApod'):
    """Extract showApod information for spectrum fourier transformed with NMRPipe.

    @keyword file:              The filename of the NMRPipe fourier transformed file.
    @type file:                 str
    @keyword dir:               The directory where the file is located.
    @type dir:                  str
    @keyword path_to_command:   If showApod not in PATH, then specify absolute path as: /path/to/showApod
    @type path_to_command:      str
    @return:                    The output from showApod as list of lines.
    @rtype:                     list of lines
    """

    # Get the file path.
    file_path = get_file_path(file_name=file_name, dir=dir)

    if not subprocess_module:
        raise RelaxError("Python module 'subprocess' not found, cannot call showApod.")

    # Call function.
    Temp = subprocess.Popen([path_to_command, file_path], stdout=subprocess.PIPE)

    # Communicate with program, and get outout and exitcode.
    (output, errput) = Temp.communicate()

    # Wait for finish and get return code.
    return_value = Temp.wait()

    # Python 3 support - convert byte arrays to text.
    if hasattr(output, 'decode'):
        output = output.decode()

    return output.splitlines()


def show_apod_rmsd(file_name=None, dir=None, path_to_command='showApod'):
    """Extract showApod 'Noise Std Dev' for spectrum fourier transformed with NMRPipe.

    @keyword file:              The filename of the NMRPipe fourier transformed file.
    @type file:                 str
    @keyword dir:               The directory where the file is located.
    @type dir:                  str
    @keyword path_to_command:   If showApod not in PATH, then specify absolute path as: /path/to/showApod
    @type path_to_command:      str
    @return:                    The Noise Std Dev from line: 'REMARK Automated Noise Std Dev in Processed Data'
    @rtype:                     float
    """

    # Call extract function.
    show_apod_lines = show_apod_extract(file_name=file_name, dir=dir, path_to_command=path_to_command)

    # Loop over the lines
    found = False
    for line in show_apod_lines:
        # Look for line with this remark.
        if line[:49] == 'REMARK Automated Noise Std Dev in Processed Data:':
            # The rest of the line is the rmsd.
            rmsd = float(line[49:].split()[0])
            return rmsd

    if not found:
        print(show_apod_lines)
        raise RelaxError("Could not find the line: 'REMARK Automated Noise Std Dev in Processed Data:', from the output of showApod.")


def show_apod_rmsd_to_file(file_name=None, dir=None, path_to_command='showApod', outdir=None, force=False):
    """Extract showApod 'Noise Std Dev' from showApod, and write to file with same filename and ending '.rmsd'

    @keyword file:              The filename of the NMRPipe fourier transformed file.
    @type file:                 str
    @keyword dir:               The directory where the file is located.
    @type dir:                  str
    @keyword path_to_command:   If showApod not in PATH, then specify absolute path as: /path/to/showApod
    @type path_to_command:      str
    @keyword outdir:            The directory where to write the file.  If 'None', then write in same directory.
    @type outdir:               str
    @param force:               Boolean argument which if True causes the file to be overwritten if it already exists.
    @type force:                bool
    @return:                    Write the 'Noise Std Dev' from showApod to a file with same file filename, with ending '.rmsd'.  This will be a file path.
    @rtype:                     str
    """

    # Call extract function.
    apod_rmsd = show_apod_rmsd(file_name=file_name, dir=dir, path_to_command=path_to_command)

    # Get the filename striped of extension details.
    file_name_root = file_root(file_name)

    # Define extension.
    extension = ".rmsd"

    # Define file name for writing.
    file_name_out = file_name_root + extension

    # Define folder to write to.
    if outdir == None:
        write_outdir = dir
    else:
        write_outdir = outdir

    # Open file for writing,
    wfile, wfile_path = open_write_file(file_name=file_name_out, dir=write_outdir, force=force, verbosity=1, return_path=True)

    # Write to file.
    out_write_data = [['%s'%apod_rmsd]]

    # Write data
    write_data(out=wfile, headings=None, data=out_write_data, sep=None)

    # Close file.
    wfile.close()

    # Return path to file.
    return wfile_path


def show_apod_rmsd_dir_to_files(file_ext='.ft2', dir=None, path_to_command='showApod', outdir=None, force=False):
    """Searches 'dir' for files with extension 'file_ext'.  Extract showApod 'Noise Std Dev' from showApod, and write to file with same filename and ending '.rmsd'.

    @keyword file_ext:          The extension for files which is NMRPipe fourier transformed file.
    @type file_ext:             str
    @keyword dir:               The directory where the files is located.
    @type dir:                  str
    @keyword path_to_command:   If showApod not in PATH, then specify absolute path as: /path/to/showApod
    @type path_to_command:      str
    @keyword outdir:            The directory where to write the files.  If 'None', then write in same directory.
    @type outdir:               str
    @param force:               Boolean argument which if True causes the file to be overwritten if it already exists.
    @type force:                bool
    @return:                    Write the 'Noise Std Dev' from showApod to a file with same file filename, with ending '.rmsd'.  This will be a list of file paths.
    @rtype:                     list of str
    """

    # First get correct dir, no matter if dir is specified with or without system folder separator.
    dir_files = abspath(dir)

    # Define glop pattern.
    glob_pat = '*%s' % file_ext

    # Get a list of files which math the file extension.
    file_list = glob(dir_files + sep + glob_pat)

    # Now sort into Alphanumeric order.
    file_list_sorted = sort_filenames(filenames=file_list, rev=False)

    # Loop over the files.
    rmsd_files = []
    for ft_file in file_list_sorted:
        # Write rmsd to file, and get file path to file.
        rmsd_file = show_apod_rmsd_to_file(file_name=ft_file, path_to_command=path_to_command, outdir=outdir, force=force)

        # Collect file path.
        rmsd_files.append(rmsd_file)

    return rmsd_files
