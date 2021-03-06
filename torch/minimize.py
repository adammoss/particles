from __future__ import print_function, division

import argparse
import os

import torch
import numpy as np


def pairwise_forces(x, masses):
    mass_matrix = masses[:, None] * masses
    res = torch.norm(x[:, None] - x, dim=2, p=2) * mass_matrix
    return res


def optimise(masses, dim, lam, num_iters=5000, lr=0.1, log_dir='', output_iter=100, opt='Adam'):

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('Device: %s' % device)

    masses = torch.from_numpy(masses).double().to(device)
    num_particles = masses.size()[0]

    # Initialise random particle positions
    x = torch.randn(num_particles, dim, requires_grad=True, device=device, dtype=torch.float64)

    if opt == 'Adam':
        opt = torch.optim.Adam([x], lr=lr)
    elif opt == 'Adamax':
        opt = torch.optim.Adam([x], lr=lr)
    elif opt == 'RMSprop':
        opt = torch.optim.RMSprop([x], lr=lr)
    elif opt == 'SGD':
        opt = torch.optim.RMSprop([x], lr=lr)
    else:
        raise ValueError

    scheduler = torch.optim.lr_scheduler.StepLR(opt, step_size=1, gamma=0.9999)

    # Indices of upper triangular distance matrix
    idx = torch.triu(torch.ones(num_particles, num_particles), diagonal=1) == 1

    # Create log directory if it doesn't exist
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    if log_dir:
        f = open(os.path.join(log_dir, 'log.txt'), 'w')

    min_energy = np.inf
    positions = None

    for i in range(num_iters):
        scheduler.step()
        opt.zero_grad()
        dist = pairwise_forces(x, masses)[idx]
        V = torch.sum(1.0 / dist) + lam / 6.0 * torch.sum(masses * torch.norm(x, dim=1)**2)
        V.backward()
        opt.step()
        energy = V.detach().cpu().numpy()
        if energy < min_energy:
            min_energy = energy
            positions = x.detach().cpu().numpy()
        if i % output_iter == 0:
            print(i, min_energy, scheduler.get_lr())
            if log_dir and positions is not None:
                f.write('%i %5.4f \n' % (i, min_energy))
                f.flush()
                np.savetxt(os.path.join(log_dir, 'positions.txt'), positions, fmt='%1.6e')


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--dim', type=int, default=3, help="Dimensionality")
    parser.add_argument('--iters', type=int, default=20000, help="Number of iters")
    parser.add_argument("--particles", type=int, default=256, help="Number of particles")
    parser.add_argument('--lam', type=float, default=3, help="Lambda")
    parser.add_argument('--log_dir', type=str, default='output/test')
    parser.add_argument('--masses', type=str)
    parser.add_argument('--opt', type=str, default='Adam')
    parser.add_argument('--lr', type=float, default=0.1)
    args = parser.parse_args()

    if args.masses:
        masses = np.loadtxt(args.masses)
    else:
        masses = np.ones(args.particles)

    optimise(masses, args.dim, args.lam, num_iters=args.iters, log_dir=args.log_dir,
             lr=args.lr, opt=args.opt)
