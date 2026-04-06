import supereeg as se
import numpy as np
import glob
import sys
import os
from config import config

freq = sys.argv[1]
kernal = sys.argv[2]
params = sys.argv[3]

# Remove curly braces and split by comma
content = params.strip('{}')
pairs = content.split(',')

kernal_parms = {}
for pair in pairs:
    key, value = pair.split(':')
    # Clean up any whitespace
    key = key.strip()
    value = value.strip()
    
    # Try to convert to int/float if possible
    try:
        value = float(value)
    except ValueError:
        # Keep as string if not a number
        pass
    
    kernal_parms[key] = value

print(kernal_parms)  # Output: {'rbf_width': 1, 'kernel': 'rbf', 'C': 10}

model_dir = os.path.join(config['datadir'])

results_dir = config['resultsdir']
model_dir = config['datadir']

if os.path.exists(os.path.join(results_dir, 'ave_mat_' + freq +"_"+kernal)):
    print('ave mat already exists')
    exit()

try:
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
except OSError as err:
   print(err)

mos = glob.glob(os.path.join(model_dir, '*' + freq +"_" + kernal+'.mo'))

if freq == 'raw':
    freqnames = ['raw']
    mos = set(glob.glob(os.path.join(model_dir, '*')))
    for fre in freqnames:
        mos -= set(glob.glob(os.path.join(model_dir, '*' + fre + '*')))
    mos = list(mos)

print(len(mos))

if kernal == "stationary":
    mo = se.Model(mos, n_subs=len(mos),kernal=kernal,rbf_width=float(kernal_parms["rbf_width"]))
elif kernal == "density":
    mo = se.Model(mos, n_subs=len(mos),kernal=kernal,density_parms=kernal_parms)

mo.save(os.path.join(results_dir, 'ave_mat_' + freq+"_"+kernal))