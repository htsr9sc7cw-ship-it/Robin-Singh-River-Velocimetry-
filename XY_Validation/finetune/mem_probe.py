"""mem_probe.py

Thesis section: see README.md
Inputs: see README.md
Outputs: see README.md


"""

import torch, sys, time

sys.path.insert(0, '../..')
from nets.pips2 import Pips

S, C, N = map(int, sys.argv[1:4])
m = Pips(stride=8).to('mps')
x = torch.zeros(1, S, 3, C, C, device='mps')
t = torch.zeros(1, S, N, 2, device='mps')
try:
    t0 = time.time()
    p, _, _, l = m(
        t,
        x,
        iters=6,
        trajs_g=t,
        vis_g=torch.ones(1, S, N, device='mps'),
        valids=torch.ones(1, S, N, device='mps'),
        is_train=True,
    )
    l.backward()
    torch.mps.synchronize()
    print('S%d crop %d N%d fits  %.1f s/step' % (S, C, N, time.time() - t0))
except Exception as e:
    print('S%d crop %d N%d fails' % (S, C, N), str(e)[:70])
