"""Dependency/model smoke tests; generated arrays are NOT research evidence."""
import numpy as np
from evaluate import choose_threshold
from isolab.comparison import confusion, split_runs, validate_predictions
from isolab.comparison_models import service_models

assert choose_threshold([0,0,1,1],np.array([.1,.2,.8,.9]))==.8
assert confusion([0,1],[0,1])['f1']==1
assert len(set(split_runs(list(range(10))).values()))==3
row=dict(method='a',runId='one',timestamp=1,split='test',label=1,score=.5)
try:
    validate_predictions([row,dict(row,method='b',label=0)])
    raise AssertionError('Mismatched observations accepted')
except ValueError:
    pass
ae,encoder,model=service_models(32,6)
x=np.zeros((2,32),dtype='float32')
ae.train_on_batch(x,x)
z=np.zeros((2,6,20),dtype='float32')
model.train_on_batch(z,np.array([0,1]))
assert model(z,training=False).numpy().shape==(2,2)
print('Model forward/backward and comparison checks passed; no experimental results generated.')
