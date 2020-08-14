from __future__ import absolute_import
from __future__ import division
from __future__ import print_function


import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import os
import sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 
import PIL.Image

import tensorflow as tf
import logging

from sklearn import preprocessing
import random
import matplotlib.pyplot as plt
import seaborn as sns

from kaggle_environments import evaluate, make
from kaggle_environments.envs.halite.helpers import *

from IPython.display import display, HTML


seed=123
tf.compat.v1.set_random_seed(seed)
session_conf = tf.compat.v1.ConfigProto(intra_op_parallelism_threads=1, inter_op_parallelism_threads=1)
sess = tf.compat.v1.Session(graph=tf.compat.v1.get_default_graph(), config=session_conf)
tf.compat.v1.keras.backend.set_session(sess)
logging.disable(sys.maxsize)
global ship_

env = make("halite", debug=True)
env.run(["submission.py", "random", "random", "random"])
env.render(mode="ipython",width=800, height=600)
