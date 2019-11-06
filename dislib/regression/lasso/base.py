"""
ADMM Lasso

@Authors: Aleksandar Armacki and Lidija Fodor
@Affiliation: Faculty of Sciences, University of Novi Sad, Serbia

This work is supported by the I-BiDaaS project, funded by the European
Commission under Grant Agreement No. 780787.
"""
import cvxpy as cp
import numpy as np
from pycompss.api.api import compss_wait_on
from pycompss.api.parameter import FILE_IN
from pycompss.api.task import task
from sklearn.base import BaseEstimator


class Lasso(BaseEstimator):
    """Lasso represents the Least Absolute Shrinkage and Selection Operator
    (Lasso) for
    regression analysis, solved in a distributed manner. 

    :param n: The number of agents used to solve the problem
    :param max_iter: The maximum number of iterations before the algorithm
    stops automatically
    :param lmbd: The regularization parameter for Lasso regression

    """

    def __init__(self, n, max_iter=500, lmbd=1e-3, optimizer=None):
        self.N = n
        self.max_iter = max_iter
        self.lmbd = lmbd
        self.optimizer = optimizer

    def fit(self, x, y):

        # file names
        rng = np.asarray(range(self.N))
        str_a = ["A" + str(i + 1) + ".dat" for i in rng]
        str_b = ["b" + str(i + 1) + ".dat" for i in rng]

        # reading the data
        data_chunk = list(map(self.read_a_data, str_a))
        data_chunk = compss_wait_on(data_chunk)
        target_chunk = list(map(self.read_b_data, str_b))
        target_chunk = compss_wait_on(target_chunk)

        # get the dimensions
        (part, n) = data_chunk[0].shape
        m = part * self.N

        # initialization
        x = [np.zeros(n) for i in range(self.N)]
        z = np.zeros(n)
        z_old = np.zeros(n)
        u = [np.zeros(n) for _ in range(self.N)]

        req_iter = self.max_iter
        frac = self.lmbd / self.optimizer.rho

        for i in range(self.max_iter):
            x, z, u, should_stop = \
                self.optimizer.step(z, data_chunk, target_chunk, u, frac,
                                    z_old, i, n, self.N)

            if should_stop:
                break

            z_old = z

        self.z = z
        return z

    def predict(self, x):
        return np.dot(x, self.z)

    def fit_predict(self, x):
        self.fit()
        return self.predict(x)

    def loss_fn(self, a, b, x):
        return 1 / 2 * cp.norm(cp.matmul(a, x) - b, p=2) ** 2

    def regularizer_x(self, x, z, u):
        return cp.norm(x - z + u, p=2) ** 2

    def objective_x(self, a, b, x, z, u, rho):
        return self.loss_fn(a, b, x) + rho / 2 * self.regularizer_x(x, z, u)

    @task(fileName=FILE_IN, returns=np.array)
    def read_a_data(self, file_name):
        # read matrix A, fileName="A"+str(i+1)+".dat"
        f = open(file_name, 'r')
        line1 = f.readline()
        dims = list(map(int, line1.split()))
        res = np.asarray(dims)
        m = res[0]
        n = res[1]
        rest = f.read()
        vecl = list(map(float, rest.split()))
        vec = np.asarray(vecl)

        return vec.reshape(n, m).T

    @task(fileName=FILE_IN, returns=np.array)
    def read_b_data(self, file_name):
        # read vector b, fileName="b"+str(i+1)+".dat"
        f = open(file_name, 'r')
        line1 = f.readline()
        dims = list(map(int, line1.split()))
        res = np.asarray(dims)
        m = res[0]
        n = res[1]
        rest = f.read()
        vecl = list(map(float, rest.split()))
        vec = np.asarray(vecl)
        return vec