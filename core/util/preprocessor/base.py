# About:    superclass for data preprocessor
# Author:   Jianbang LIU
# Date:     2021.01.30

import os
import numpy as np
import pandas as pd


class Preprocessor(object):
    """
    superclass for all the trajectory data preprocessor
    those preprocessor will reformat the data in a single sequence and feed to the system or store them
    """
    def __init__(self, root_dir, algo="tnt", obs_horizon=20, obs_range=30):
        self.root_dir = root_dir    # root directory stored the dataset

        self.algo = algo            # the name of the algorithm
        self.obs_horizon = 20       # the number of timestampe for observation
        self.obs_range = 30         # the observation range

    def __len__(self):
        """ the total number of sequence in the dataset """
        raise NotImplementedError

    def generate(self):
        """ Generator function to iterating the dataset """
        raise NotImplementedError

    def process(self, dataframe: pd.DataFrame, map_feat=True):
        """
        select filter the data frame, output filtered data frame
        :param dataframe: DataFrame, the data frame
        :param map_feat: bool, output map feature or not
        :return: DataFrame[(same as orignal)]
        """

        agent_feats, obj_feats, lane_feats = self.extract_feature(dataframe, map_feat=map_feat)
        return self.encode_feature(agent_feats, obj_feats, lane_feats)

    def extract_feature(self, dataframe: pd.DataFrame, map_feat=True):
        """
        select and filter the data frame, output filtered frame feature
        :param dataframe: DataFrame, the data frame
        :param map_feat: bool, output map feature or not
        :return: DataFrame[(same as orignal)]
        """
        raise NotImplementedError

    def encode_feature(self, *feats):
        """
        encode the filtered features to specific format required by the algorithm
        :feats dataframe: DataFrame, the data frame containing the filtered data
        :return: DataFrame[POLYLINE_FEATURES, GT, TRAJ_ID_TO_MASK, LANE_ID_TO_MASK, TARJ_LEN, LANE_LEN]
        """
        raise NotImplementedError

    def save(self, dataframe: pd.DataFrame, set_name, file_name, dir_=None):
        """
        save the feature in the data sequence in a single csv files
        :param dataframe: DataFrame, the dataframe encoded
        :param set_name: str, the name of the folder name, exp: train, eval, test
        :param file_name: str, the name of csv file
        :param dir_: str, the directory to store the csv file
        :return:
        """
        if not isinstance(dataframe, pd.DataFrame):
            return

        if not dir_:
            dir_ = os.path.join(os.path.split(self.root_dir)[0], "intermediate", set_name + "_intermediate", "raw")
        else:
            dir_ = os.path.join(dir_, set_name + "_intermediate", "raw")
        if not os.path.exists(dir_):
            os.makedirs(dir_)

        fname = f"features_{file_name}.pkl"
        dataframe.to_pickle(os.path.join(dir_, fname))
        # print("[Preprocessor]: Saving data to {} with name: {}...".format(dir_, fname))

    def process_and_save(self, dataframe: pd.DataFrame, set_name, file_name, dir_=None, map_feat=True):
        """
        save the feature in the data sequence in a single csv files
        :param dataframe: DataFrame, the data frame
        :param set_name: str, the name of the folder name, exp: train, eval, test
        :param file_name: str, the name of csv file
        :param dir_: str, the directory to store the csv file
        :return:
        """
        raise NotImplementedError

    @staticmethod
    def uniform_candidate_sampling(sampling_range, rate=30):
        """
        uniformly sampling of the target candidate
        :param sampling_range: int, the maximum range of the sampling
        :param rate: the sampling rate (num. of samples)
        return rate^2 candidate samples
        """
        x = np.linspace(-sampling_range, sampling_range, rate)
        return np.stack(np.meshgrid(x, x), -1).reshape(-1, 2)

    # todo: uniform sampling along he land
    @staticmethod
    def lane_candidate_sampling(centerlines, n):
        """
        get sampling on the input centerlines
        :param centerlines: np.array[lines, :]
        :param n: the number of candiates
        """
        n_segment = centerlines.shape[0] - 1

        rate = n // n_segment
        n_mod = n % n_segment

        candidates = []
        if rate > 0:
            for i in range(n_segment):
                if i < n_mod:       # the rate is acturally rate + 1
                    dx = centerlines[i + 1, 0] - centerlines[i, 0] / (rate + 1)
                    dy = centerlines[i + 1, 1] - centerlines[i, 1] / (rate + 1)
                    candidates.extend([[centerlines[i, 0] + dx * j, centerlines[i, 1] + dy * j] for j in range(rate + 1)])
                else:               # the rate is rate
                    dx = centerlines[i + 1, 0] - centerlines[i, 0] / rate
                    dy = centerlines[i + 1, 1] - centerlines[i, 1] / rate
                    candidates.extend([[centerlines[i, 0] + dx * j, centerlines[i, 1] + dy * j] for j in range(rate)])
            assert len(candidates) == n, "[Preprocessor]: The number of generated candidates are not {}".format(n)
        else:
            for i in range(n_segment):
                if i < n_mod:       # the rate is acturally rate + 1
                    dx = centerlines[i + 1, 0] - centerlines[i, 0] / (rate + 1)
                    dy = centerlines[i + 1, 1] - centerlines[i, 1] / (rate + 1)
                    candidates.extend([[centerlines[i, 0] + dx / 2, centerlines[i, 1] + dy / 2]])
        return np.array(candidates)

    @staticmethod
    def get_candidate_gt(target_candidate, gt_target):
        """
        find the target candidate closest to the gt and output the one-hot ground truth
        :param target_candidate, (N, 2) candidates
        :param gt_target, (1, 2) the coordinate of final target
        """
        displacement = gt_target - target_candidate
        gt_index = np.argmin(np.power(displacement[:, 0], 2) + np.power(displacement[:, 1], 2))

        onehot = np.zeros((target_candidate.shape[0], 1))
        onehot[gt_index] = 1

        offset_xy = gt_target - target_candidate[gt_index]
        return onehot, offset_xy


# example of preprocessing scripts
if __name__ == "__main__":
    processor = Preprocessor("raw_data")

    for s_name, f_name, df in processor.generate():
        processor.save(processor.process(df), s_name, f_name)
