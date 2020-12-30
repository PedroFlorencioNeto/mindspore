# Copyright 2019-2021 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""
The sampler module provides several samplers to generate data from datasets.
The provided samplers include: DistributedSampler, PKSampler, RandomSampler,
SequentialSampler, SubsetRandomSampler, and WeightedRandomSampler.
Users can also define a custom sampler by extending from the Sampler class.
"""

import numbers
import numpy as np
import mindspore._c_dataengine as cde
import mindspore.dataset as ds


class BuiltinSampler:
    """
    Base class for BuiltinSampler.

    User should not extend this class.
    """

    def __init__(self, num_samples=None):
        self.child_sampler = None
        self.num_samples = num_samples

    def parse(self):
        pass

    def add_child(self, sampler):
        """
        Add a sub-sampler for given sampler. The sub-sampler will receive all data from the
        output of parent sampler and apply its sample logic to return new samples.

        Args:
            sampler (Sampler): Object used to choose samples from the dataset. Only builtin
                samplers(DistributedSampler, PKSampler, RandomSampler, SequentialSampler,
                SubsetRandomSampler, WeightedRandomSampler) are supported.

        Examples:
            >>> sampler = ds.SequentialSampler(start_index=0, num_samples=3)
            >>> sampler.add_child(ds.RandomSampler(num_samples=2))
            >>> dataset = ds.Cifar10Dataset(cifar10_dataset_dir, sampler=sampler)
        """
        self.child_sampler = sampler

    def get_child(self):
        return self.child_sampler

    def parse_child(self):
        c_child_sampler = None
        if self.child_sampler is not None:
            c_child_sampler = self.child_sampler.parse()
        return c_child_sampler

    def parse_child_for_minddataset(self):
        c_child_sampler = None
        if self.child_sampler is not None:
            c_child_sampler = self.child_sampler.parse_for_minddataset()
        return c_child_sampler

    def is_shuffled(self):
        raise NotImplementedError("Sampler must implement is_shuffled.")

    def is_sharded(self):
        raise NotImplementedError("Sampler must implement is_sharded.")

    def get_num_samples(self):
        """
        All samplers can contain a numeric num_samples value (or it can be set to None).
        A child sampler can exist or be None.
        If a child sampler exists, then the child sampler count can be a numeric value or None.
        These conditions impact the resultant sampler count that is used.
        The following table shows the possible results from calling this function.

        .. list-table::
           :widths: 25 25 25 25
           :header-rows: 1

           * - child sampler
             - num_samples
             - child_samples
             - result
           * - T
             - x
             - y
             - min(x, y)
           * - T
             - x
             - None
             - x
           * - T
             - None
             - y
             - y
           * - T
             - None
             - None
             - None
           * - None
             - x
             - n/a
             - x
           * - None
             - None
             - n/a
             - None

        Returns:
            int, the number of samples, or None
        """
        if self.child_sampler is not None:
            child_samples = self.child_sampler.get_num_samples()
            if self.num_samples is not None:
                if child_samples is not None:
                    return min(self.num_samples, child_samples)

                return self.num_samples

            return child_samples

        return self.num_samples


class Sampler(BuiltinSampler):
    """
    Base class for user defined sampler.
    A user defined sampler can be used with any existing dataset with sampler support.

    A required  _iter_() method should by overridden by the user for sample index generation.
    An optional reset() method can be overridden for per repeat reset,

    dataset_size and num_samples will be set by dataset once a dataset iterator is created.

    Examples:
        >>> import mindspore.dataset as ds
        >>>
        >>> class ReverseSampler(ds,Sampler):
        >>>     def __iter__(self):
        >>>         for i in range(self.dataset_size - 1, -1, -1):
        >>>             yield i
        >>>
        >>> ds = ds.ImageFolderDataset(path, sampler=ReverseSampler())
    """

    def __init__(self, num_samples=None):
        super().__init__(num_samples)
        self.dataset_size = 0
        self.child_sampler = None
        self.num_samples = num_samples

    def __iter__(self):
        """
        User defined iterator, must be overridden.
        _handshake is guaranteed to be called prior to iterator construction.
        """
        raise NotImplementedError

    def reset(self):
        """
        Per repeat reset callback, override this method if necessary
        """

    # Initialization handshake callback
    # Do not override this method!
    def _handshake(self, ds_size, num_samples):
        self.dataset_size = ds_size
        self.num_samples = num_samples

    # Indices fetcher
    # Do not override this method!
    def _get_indices(self):
        sampler_iter = iter(self)
        ret = []
        for _ in range(self.num_samples):
            try:
                idx = next(sampler_iter)
                ret.append(idx)
            except StopIteration:
                break
        return np.array(ret)

    # Instance fetcher
    # Do not override this method!
    def parse(self):
        num_samples = self.num_samples if self.num_samples is not None else 0
        c_sampler = cde.PreBuiltSamplerObj(num_samples, self)
        c_child_sampler = self.parse_child()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def add_child(self, sampler):
        self.child_sampler = sampler

    def get_child(self):
        return self.child_sampler

    def parse_child(self):
        c_child_sampler = None
        if self.child_sampler is not None:
            c_child_sampler = self.child_sampler.parse()

        return c_child_sampler

    def is_shuffled(self):
        if self.child_sampler is None:
            return False

        return self.child_sampler.is_shuffled()

    def is_sharded(self):
        if self.child_sampler is None:
            return False

        return self.child_sampler.is_sharded()

    def get_num_samples(self):
        if self.num_samples is None:
            return None
        return self._get_indices().size


class DistributedSampler(BuiltinSampler):
    """
    A sampler that accesses a shard of the dataset.

    Args:
        num_shards (int): Number of shards to divide the dataset into.
        shard_id (int): Shard ID of the current shard within num_shards.
        shuffle (bool, optional): If True, the indices are shuffled (default=True).
        num_samples (int, optional): The number of samples to draw (default=None, all elements).
        offset(int, optional): The starting shard ID where the elements in the dataset are sent to (default=-1), which
            should be no more than num_shards.

    Examples:
        >>> # creates a distributed sampler with 10 shards in total. This shard is shard 5.
        >>> sampler = ds.DistributedSampler(10, 5)
        >>> dataset = ds.ImageFolderDataset(image_folder_dataset_dir,
        ...                                 num_parallel_workers=8,
        ...                                 sampler=sampler)

    Raises:
        ValueError: If num_shards is not positive.
        ValueError: If shard_id is smaller than 0 or equal to num_shards or larger than num_shards.
        ValueError: If shuffle is not a boolean value.
        ValueError: If offset is greater than num_shards.
    """

    def __init__(self, num_shards, shard_id, shuffle=True, num_samples=None, offset=-1):
        if not isinstance(num_shards, int):
            raise ValueError("num_shards must be integer but was: {}.".format(num_shards))

        if not isinstance(shard_id, int):
            raise ValueError("shard_id must be integer but was: {}.".format(shard_id))

        if not isinstance(shuffle, bool):
            raise ValueError("shuffle should be a boolean value, but got shuffle: {}.".format(shuffle))

        self.num_shards = num_shards
        self.shard_id = shard_id
        self.shuffle = shuffle
        self.seed = 0
        self.offset = offset
        super().__init__(num_samples)

    def parse(self):
        num_samples = self.num_samples if self.num_samples is not None else 0
        shuffle = self.shuffle if self.shuffle is not None else True
        offset = self.offset if self.offset is not None else -1
        # each time user calls create_dict_iterator() (to do repeat) sampler would get a different seed to shuffle
        self.seed += 1
        c_sampler = cde.DistributedSamplerObj(self.num_shards, self.shard_id,
                                              shuffle, num_samples, self.seed, offset, True)
        c_child_sampler = self.parse_child()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def parse_for_minddataset(self):
        num_samples = self.num_samples if self.num_samples is not None else 0
        c_sampler = cde.MindrecordDistributedSampler(self.num_shards, self.shard_id, self.shuffle,
                                                     self.seed, num_samples, self.offset)
        c_child_sampler = self.parse_child_for_minddataset()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def is_shuffled(self):
        if self.child_sampler is None:
            return self.shuffle

        return self.child_sampler.is_shuffled()

    def is_sharded(self):
        if self.child_sampler is None:
            return self.num_shards > 1

        return self.child_sampler.is_sharded()

    def set_offset(self, offset):
        self.offset = offset
        return self


class PKSampler(BuiltinSampler):
    """
    Samples K elements for each P class in the dataset.

    Args:
        num_val (int): Number of elements to sample for each class.
        num_class (int, optional): Number of classes to sample (default=None, all classes).
            The parameter does not supported to specify currently.
        shuffle (bool, optional): If True, the class IDs are shuffled (default=False).
        class_column (str, optional): Name of column with class labels for MindDataset (default='label').
        num_samples (int, optional): The number of samples to draw (default=None, all elements).

    Examples:
        >>> # creates a PKSampler that will get 3 samples from every class.
        >>> sampler = ds.PKSampler(3)
        >>> dataset = ds.ImageFolderDataset(image_folder_dataset_dir,
        ...                                 num_parallel_workers=8,
        ...                                 sampler=sampler)

    Raises:
        ValueError: If num_val is not positive.
        NotImplementedError: If num_class is not None.
        ValueError: If shuffle is not boolean.
    """

    def __init__(self, num_val, num_class=None, shuffle=False, class_column='label', num_samples=None):
        if not isinstance(num_val, int):
            raise ValueError("num_val must be integer but was: {}.".format(num_val))

        if num_class is not None:
            raise NotImplementedError("Not supported to specify num_class for PKSampler.")

        if not isinstance(shuffle, bool):
            raise ValueError("shuffle should be a boolean value, but got shuffle: {}.".format(shuffle))

        self.num_val = num_val
        self.shuffle = shuffle
        self.class_column = class_column  # work for minddataset
        super().__init__(num_samples)

    def parse(self):
        num_samples = self.num_samples if self.num_samples is not None else 0
        shuffle = self.shuffle if self.shuffle is not None else False
        c_sampler = cde.PKSamplerObj(self.num_val, shuffle, num_samples)
        c_child_sampler = self.parse_child()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def is_shuffled(self):
        if self.child_sampler is None:
            return self.shuffle

        return self.child_sampler.is_shuffled()

    def is_sharded(self):
        if self.child_sampler is None:
            return False

        return self.child_sampler.is_sharded()

    def parse_for_minddataset(self):
        if not self.class_column or not isinstance(self.class_column, str):
            raise ValueError("class_column should be a not empty string value, \
                    but got class_column: {}.".format(class_column))
        num_samples = self.num_samples if self.num_samples is not None else 0
        c_sampler = cde.MindrecordPkSampler(self.num_val, self.class_column, self.shuffle, num_samples)
        c_child_sampler = self.parse_child_for_minddataset()
        c_sampler.add_child(c_child_sampler)
        return c_sampler


class RandomSampler(BuiltinSampler):
    """
    Samples the elements randomly.

    Args:
        replacement (bool, optional): If True, put the sample ID back for the next draw (default=False).
        num_samples (int, optional): Number of elements to sample (default=None, all elements).

    Examples:
        >>> # creates a RandomSampler
        >>> sampler = ds.RandomSampler()
        >>> dataset = ds.ImageFolderDataset(image_folder_dataset_dir,
        ...                                 num_parallel_workers=8,
        ...                                 sampler=sampler)

    Raises:
        ValueError: If replacement is not boolean.
        ValueError: If num_samples is not positive.
     """

    def __init__(self, replacement=False, num_samples=None):
        if not isinstance(replacement, bool):
            raise ValueError("replacement should be a boolean value, but got replacement: {}.".format(replacement))

        self.deterministic = False
        self.replacement = replacement
        self.reshuffle_each_epoch = True
        super().__init__(num_samples)

    def parse(self):
        num_samples = self.num_samples if self.num_samples is not None else 0
        replacement = self.replacement if self.replacement is not None else False
        c_sampler = cde.RandomSamplerObj(replacement, num_samples, self.reshuffle_each_epoch)
        c_child_sampler = self.parse_child()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def parse_for_minddataset(self):
        num_samples = self.num_samples if self.num_samples is not None else 0
        c_sampler = cde.MindrecordRandomSampler(num_samples, self.replacement, self.reshuffle_each_epoch)
        c_child_sampler = self.parse_child_for_minddataset()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def is_shuffled(self):
        return True

    def is_sharded(self):
        if self.child_sampler is None:
            return False

        return self.child_sampler.is_sharded()


class SequentialSampler(BuiltinSampler):
    """
    Samples the dataset elements sequentially, same as not having a sampler.

    Args:
        start_index (int, optional): Index to start sampling at. (default=None, start at first ID)
        num_samples (int, optional): Number of elements to sample (default=None, all elements).

    Examples:
        >>> # creates a SequentialSampler
        >>> sampler = ds.SequentialSampler()
        >>> dataset = ds.ImageFolderDataset(image_folder_dataset_dir,
        ...                                 num_parallel_workers=8,
        ...                                 sampler=sampler)
    """

    def __init__(self, start_index=None, num_samples=None):
        self.start_index = start_index
        super().__init__(num_samples)

    def parse(self):
        start_index = self.start_index if self.start_index is not None else 0
        num_samples = self.num_samples if self.num_samples is not None else 0
        c_sampler = cde.SequentialSamplerObj(start_index, num_samples)
        c_child_sampler = self.parse_child()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def parse_for_minddataset(self):
        start_index = self.start_index if self.start_index is not None else 0
        num_samples = self.num_samples if self.num_samples is not None else 0
        c_sampler = cde.MindrecordSequentialSampler(num_samples, start_index)
        c_child_sampler = self.parse_child_for_minddataset()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def is_shuffled(self):
        if self.child_sampler is None:
            return False

        return self.child_sampler.is_shuffled()

    def is_sharded(self):
        if self.child_sampler is None:
            return False

        return self.child_sampler.is_sharded()


class SubsetSampler(BuiltinSampler):
    """
    Samples the elements from a sequence of indices.

    Args:
        indices (list[int]): A sequence of indices.
        num_samples (int, optional): Number of elements to sample (default=None, all elements).

    Examples:
        >>> indices = [0, 1, 2, 3, 4, 5]
        >>>
        >>> # creates a SubsetRandomSampler, will sample from the provided indices
        >>> sampler = ds.SubsetRandomSampler(indices)
        >>> dataset = ds.ImageFolderDataset(image_folder_dataset_dir,
        ...                                 num_parallel_workers=8,
        ...                                 sampler=sampler)
    """

    def __init__(self, indices, num_samples=None):
        if not isinstance(indices, list):
            indices = [indices]

        for i, item in enumerate(indices):
            if not isinstance(item, numbers.Number):
                raise TypeError("type of weights element should be number, "
                                "but got w[{}]: {}, type: {}.".format(i, item, type(item)))

        self.indices = indices
        super().__init__(num_samples)

    def parse(self):
        num_samples = self.num_samples if self.num_samples is not None else 0
        c_sampler = cde.SubsetSamplerObj(self.indices, num_samples)
        c_child_sampler = self.parse_child()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def is_shuffled(self):
        return False

    def is_sharded(self):
        if self.child_sampler is None:
            return False

        return self.child_sampler.is_sharded()

    def parse_for_minddataset(self):
        c_sampler = cde.MindrecordSubsetSampler(self.indices)
        c_child_sampler = self.parse_child_for_minddataset()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def get_num_samples(self):
        num_samples = super().get_num_samples()
        if num_samples is None:
            return len(self.indices)

        return min(len(self.indices), num_samples)


class SubsetRandomSampler(SubsetSampler):
    """
    Samples the elements randomly from a sequence of indices.

    Args:
        indices (list[int]): A sequence of indices.
        num_samples (int, optional): Number of elements to sample (default=None, all elements).

    Examples:
        >>> import mindspore.dataset as ds
        >>>
        >>> dataset_dir = "path/to/imagefolder_directory"
        >>>
        >>> indices = [0, 1, 2, 3, 7, 88, 119]
        >>>
        >>> # creates a SubsetRandomSampler, will sample from the provided indices
        >>> sampler = ds.SubsetRandomSampler(indices)
        >>> data = ds.ImageFolderDataset(dataset_dir, num_parallel_workers=8, sampler=sampler)
    """

    def parse(self):
        num_samples = self.num_samples if self.num_samples is not None else 0
        c_sampler = cde.SubsetRandomSamplerObj(self.indices, num_samples)
        c_child_sampler = self.parse_child()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def is_shuffled(self):
        return True

    def parse_for_minddataset(self):
        c_sampler = cde.MindrecordSubsetSampler(self.indices, ds.config.get_seed())
        c_child_sampler = self.parse_child_for_minddataset()
        c_sampler.add_child(c_child_sampler)
        return c_sampler


class WeightedRandomSampler(BuiltinSampler):
    """
    Samples the elements from [0, len(weights) - 1] randomly with the given weights (probabilities).

    Args:
        weights (list[float, int]): A sequence of weights, not necessarily summing up to 1.
        num_samples (int, optional): Number of elements to sample (default=None, all elements).
        replacement (bool): If True, put the sample ID back for the next draw (default=True).

    Examples:
        >>> weights = [0.9, 0.01, 0.4, 0.8, 0.1, 0.1, 0.3]
        >>>
        >>> # creates a WeightedRandomSampler that will sample 4 elements without replacement
        >>> sampler = ds.WeightedRandomSampler(weights, 4)
        >>> dataset = ds.ImageFolderDataset(image_folder_dataset_dir,
        ...                                 num_parallel_workers=8,
        ...                                 sampler=sampler)

    Raises:
        ValueError: If num_samples is not positive.
        ValueError: If replacement is not boolean.
    """

    def __init__(self, weights, num_samples=None, replacement=True):
        if not isinstance(weights, list):
            weights = [weights]

        for ind, w in enumerate(weights):
            if not isinstance(w, numbers.Number):
                raise TypeError("type of weights element should be number, "
                                "but got w[{}]: {}, type: {}.".format(ind, w, type(w)))

        if not isinstance(replacement, bool):
            raise ValueError("replacement should be a boolean value, but got replacement: {}.".format(replacement))

        self.weights = weights
        self.replacement = replacement
        super().__init__(num_samples)

    def parse(self):
        num_samples = self.num_samples if self.num_samples is not None else 0
        replacement = self.replacement if self.replacement is not None else True
        c_sampler = cde.WeightedRandomSamplerObj(self.weights, num_samples, replacement)
        c_child_sampler = self.parse_child()
        c_sampler.add_child(c_child_sampler)
        return c_sampler

    def is_shuffled(self):
        return True

    def is_sharded(self):
        if self.child_sampler is None:
            return False

        return self.child_sampler.is_sharded()
