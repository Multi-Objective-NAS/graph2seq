import math
import json
from collections import OrderedDict

import numpy as np
import torch
import torch.utils.data
import torch.nn.functional as F
## from nasbench import api

INPUT = 'input'
CONV1X1 = 'conv1x1-bn-relu'
CONV3X3 = 'conv3x3-bn-relu'
MAXPOOL3X3 = 'maxpool3x3'
OUTPUT = 'output'

"""
0: sos/eos
1: no connection
2: connection
3: CONV1X1
4: CONV3X3
5: MAXPOOL3X3
6: OUTPUT
"""

MAX_EDGE = 9
class AvgrageMeter(object):

    def __init__(self):
        self.reset()

    def reset(self):
        self.avg = 0
        self.sum = 0
        self.cnt = 0

    def update(self, val, n=1):
        self.sum += val * n
        self.cnt += n
        self.avg = self.sum / self.cnt

class ControllerDataset(torch.utils.data.Dataset):
    def __init__(self, file_path, graph_size):
        super(ControllerDataset, self).__init__()
        
        self.graph_size = graph_size
        self.adjacency_matrices = []
        self.operations = []
        self.sequences = []

        with open(file_path, "r") as f:
            for line in f.readlines():
                line = line.strip()
            
                jo = json.loads(line, object_pairs_hook=OrderedDict)

                self.adjacency_matrices.append(jo['module_adjacency'])
                self.operations.append(jo['module_operations'])
                self.sequences.append(jo['sequence'])
    
    def __getitem__(self, index):
        matrix = self.adjacency_matrices[index]
        n = len(matrix)

        g_fw_adjs = [list() for _ in range(n)]
        g_bw_adjs = [list() for _ in range(n)]
        for row in range(n):
            for col in range(row + 1, n):
                if matrix[row][col] :
                    print(row, col, matrix[row][col])
                    g_fw_adjs[row].append(col)
                    g_bw_adjs[col].append(row)

        ops = []
        for op in self.operations[index]:
            if op == CONV1X1:
                ops.append(3)
            elif op == CONV3X3:
                ops.append(4)
            elif op == MAXPOOL3X3:
                ops.append(5)
            elif op == OUTPUT:
                ops.append(6)
            if op == INPUT:
                ops.append(7)

        print(matrix)
        print(ops)
        print(g_fw_adjs)
        print(g_bw_adjs)
        print(ops)
        print(self.sequences[index])

        sample = {
            'fw_adjs': np.array(g_fw_adjs),
            'bw_adjs': np.array(g_bw_adjs),
            'operations': torch.IntTensor(ops),
            'sequence': torch.IntTensor(self.sequences[index])
        }
        return sample
    
    def __len__(self):
        return len(self.sequences)


def convert_arch_to_seq(matrix, ops):
    seq = []
    n = len(matrix)
    assert n == len(ops)
    for col in range(1, n):
        for row in range(col):
            seq.append(matrix[row][col]+1)
        if ops[col] == CONV1X1:
            seq.append(3)
        elif ops[col] == CONV3X3:
            seq.append(4)
        elif ops[col] == MAXPOOL3X3:
            seq.append(5)
        if ops[col] == OUTPUT:
            seq.append(6)
    assert len(seq) == (n+2)*(n-1)/2
    return seq


def convert_seq_to_arch(seq):
    n = int(math.floor(math.sqrt((len(seq) + 1) * 2)))
    matrix = [[0 for _ in range(n)] for _ in range(n)]
    ops = [INPUT]
    for i in range(n-1):
        offset=(i+3)*i//2
        for j in range(i+1):
            matrix[j][i+1] = seq[offset+j] - 1
        if seq[offset+i+1] == 3:
            op = CONV1X1
        elif seq[offset+i+1] == 4:
            op = CONV3X3
        elif seq[offset+i+1] == 5:
            op = MAXPOOL3X3
        elif seq[offset+i+1] == 6:
            op = OUTPUT
        ops.append(op)
    return matrix, ops

""""
def generate_arch(n, nasbench, need_perf=False):
    count = 0
    archs = []
    seqs = []
    valid_accs = []
    all_keys = list(nasbench.hash_iterator())
    np.random.shuffle(all_keys)
    for key in all_keys:
        fixed_stat, computed_stat = nasbench.get_metrics_from_hash(key)
        if len(fixed_stat['module_operations']) < 7:
            continue
        arch = api.ModelSpec(
            matrix=fixed_stat['module_adjacency'],
            ops=fixed_stat['module_operations'],
        )
        if need_perf:
            data = nasbench.query(arch)
            if data['validation_accuracy'] < 0.9:
                continue
            valid_accs.append(data['validation_accuracy'])
        archs.append(arch)
        seqs.append(convert_arch_to_seq(arch.matrix, arch.ops))
        count += 1
        if count >= n:
            return archs, seqs, valid_accs


def count_parameters(model):
    return np.sum(np.prod(v.size()) for name, v in model.named_parameters())
"""