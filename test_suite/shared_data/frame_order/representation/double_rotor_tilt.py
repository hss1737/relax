from numpy import float64, zeros

from lib.geometry.rotations import euler_to_R_zyz


# Create the data pipe.
pipe.create(pipe_name='frame order', pipe_type='frame order')

# Select the model.
frame_order.select_model('double rotor')

# The eigenframe.
eigen_alpha = 0.0
eigen_beta = -pi/4.0
eigen_gamma = 0.0
R = zeros((3, 3), float64)
euler_to_R_zyz(eigen_alpha, eigen_beta, eigen_gamma, R)
print("Motional eigenframe:\n%s" % R)

# Set the average domain position translation parameters.
value.set(param='ave_pos_x', val=0.0)
value.set(param='ave_pos_y', val=0.0)
value.set(param='ave_pos_z', val=0.0)
value.set(param='ave_pos_alpha', val=0.0)
value.set(param='ave_pos_beta', val=0.0)
value.set(param='ave_pos_gamma', val=0.0)
value.set(param='pivot_disp', val=100)
value.set(param='eigen_alpha', val=eigen_alpha)
value.set(param='eigen_beta', val=eigen_beta)
value.set(param='eigen_gamma', val=eigen_gamma)
value.set(param='cone_sigma_max', val=0.0)
value.set(param='cone_sigma_max_2', val=0.0)

# Set the pivot.
frame_order.pivot(pivot=[1, 0, 0], fix=True)

# Create the PDB.
frame_order.pdb_model(inc=10, size=45, rep='double_rotor_tilt', force=True)
