"""
    Base class for hypothesis testing.
    Tracks test statistics, computes p-values.
    Supports resampling data at each run.
"""
from multiprocessing import Pool
from functools import partial


class HypothesisTest:
    """
        Base class for hypothesis testing. Estimates the
        null distribution for the test statistic by shuffling the data

        batch_test: returns a p-value for test using all of the data
        bootstrap_test: returns a p-value for test using bootstrapped samples

        p-value: estimated probability of null hypothesis being true

        Tracks test statistics, computes p-values.
        Supports resampling data at each run.
    """
    def __init__(self, statistic, statistic_args=None):
        self.statistic = statistic
        self.statistic_args = {} if statistic_args is None else statistic_args

        # saved test statistics used in hypothesis test
        self.shuffled_statistics = None
        self.nominal_statistics = None

    def test(self, n_trials, bootstrap_size=None, n_jobs=1):
        """
            Perform hypothesis test
            * n_trials: number of times to shuffle data and recompute test statistic
            * bootstrap_size: if not None, compute test statistics using
              bootstrap resampled data of size bootstrap_size
            * n_jobs: number of shuffle instances to run in parallel

            computed test statistics can be accessed using:
                * self.bootstrap_shuffled_statistics
                * self.bootstrap_nominal_statistics
        """
        pool = Pool(processes=n_jobs)
        results = list(pool.map_async(partial(HypothesisTest.bootstrap_trial, hypothesis_test=self, bootstrap_size=bootstrap_size), range(n_trials)).get())
        pool.close()
        pool.join()

        self.shuffled_statistics = [r[1] for r in results]

        if bootstrap_size is None:
            # batch mode, single nominal value
            nominal_statistic = self.bootstrap_instance(bootstrap_size=None, shuffle=False)[1]
            self.nominal_statistics = [nominal_statistic for _ in range(n_trials)]
        else:
            # bootstrap mode
            self.nominal_statistics = [r[2] for r in results]

        return self.pvalue(self.shuffled_statistics, self.nominal_statistics)

    @staticmethod
    def bootstrap_trial(run_id, hypothesis_test, bootstrap_size=None):
        """
            Wrapper method of bootstrap_instance to enable multiprocessing
            * run_id: (integer) identifier of current trial
            * hypothesis_test: HypothesisTest object with which to compute test statistic
        """
        shuffled_statistic, nominal_statistic = hypothesis_test.bootstrap_instance(bootstrap_size)
        return (run_id, shuffled_statistic, nominal_statistic)

    @staticmethod
    def pvalue(shuffled_statistics, nominal_statistics):
        """
            Compute p-value for a bootstrapped test
            * test_results is a list of tuples:
            * shuffled_statistics: computed test statistic using shuffled bootstrap sample
            * nominal_statistics: computed test statistic using unshuffled bootstrap sample
        """
        assert len(shuffled_statistics) > 0
        assert len(shuffled_statistics) == len(nominal_statistics)
        pval = 0.
        for i, statistic in enumerate(shuffled_statistics):
            if statistic >= nominal_statistics[i]:
                pval += 1.
        return pval / len(shuffled_statistics)

    def compute_statistic(self, *data):
        """
            Call the test statistic provided, with variable arguments
        """
        return self.statistic(*data, **self.statistic_args)

    def bootstrap_instance(self, bootstrap_size=None, shuffle=True):
        """ Compute test statistic using shuffled data
            returns tuple: (shuffled_statistic, nominal_statistic)
                * shuffled_statistic: computed using shuffled bootstrapped dataset
                * nominal_statistic: computed using unshuffled bootstrapped dataset

            * bootstrap_size: if None, return None for nominal_statistic.
                Otherwise, statistics using bootstrap resample of dataset
            * shuffle: if True, perform shuffling for p-value estimation.
                Set to False to compute batch nominal statistic.
                In this case, the returned shuffle_stat will be None
        """
        raise NotImplementedError