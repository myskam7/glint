from numpy import loadtxt
from utils import tools
from modules import methylation_data
import logging
from tests.test_tools import tools as tests_tools


class ToolsTester():
    DATA_FILE = "tests/files/datafile2"
    LOW_RANK_APPROX = "tests/utils/files/datafile2_5_rank_approx"
    EUC_DIST = "tests/utils/files/datafile2_euc_dist_first_half_second_half"
    K = 5

    def __init__(self):
        logging.info("Testing Started ToolsTester")
        self.meth_data = methylation_data.MethylationDataLoader(datafile = self.DATA_FILE)
        self.test_low_rank_approx()
        self.test_euclidean_distance()
        logging.info("Testing Finished ToolsTester")

    def test_low_rank_approx(self):
        logging.info("Testing low rank approximation")
        low_rank_approx = loadtxt(self.LOW_RANK_APPROX)
        lra_met_data = self.meth_data.copy()

        res = tools.low_rank_approximation(lra_met_data.data.transpose(), self.K)
        res = res.transpose()

        for i in range(lra_met_data.sites_size):
            assert tests_tools.correlation(res[i,:], low_rank_approx[i,:])
        
        logging.info("PASS")

    def test_euclidean_distance(self):
        logging.info("Testing euclidean distance...")
        euc_dist = loadtxt(self.EUC_DIST)
        out = tools.euclidean_distance(self.meth_data.data[:500,:].transpose(), self.meth_data.data[500:,:].transpose())

        assert tests_tools.correlation(out, euc_dist)
        logging.info("PASS")
