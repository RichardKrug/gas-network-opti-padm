# gas-network-opti-padm
This repository contains the problem data, code, and results for the paper "A Consensus-Based Alternating Direction Method for Mixed-Integer and PDE-Constrained Gas Transport Problems" by Richard Krug, Günter Leugering, Alexander Martin, Martin Schmidt, and Dieter Weninger.

## Structure of this repository
### data
The problem data for the different gas networks.

Each folder contains a network file (\*.net) and an input data file (\*-InputData.json).
The network files are based on the gas network library GasLib (see M. Schmidt, D. Aßmann, R. Burlacu, J. Humpola, I. Joormann, N. Kanelakis, T. Koch, D. Oucherif, M. E. Pfetsch, L. Schewe, R. Schwarz, and M. Sirvent. “GasLib—A Library of Gas Network Instances.” In: Data 2.4 (2017). doi: 10.3390/data2040040).
The input data files contain transient boundary data for their respective network file. For transient gas network data also see https://www.trr154.fau.de/transient-data/.

### src
The python code used for the computations.

Example usage:
```console
python src/main.py -i data/GasLib-11/GasLib-11-sinus-InputData.json -t 60 -x 5000
```

To list all possbile arguments run:
```console
python src/main.py --help
```

### results
The results used in the paper in CSV format.
