#
# tstp_defaultdict.py
# Copyright 2017 Pierre-Jean Grenier
# Licensed under MIT
#
import collections
import datetime


class tstp_defaultdict(collections.defaultdict):
    """
    This is a defaultdict that remembers at what time the
    value of a key was last used.
    By "used", we mean "been added and/or changed and/or read".
    Note that function values() is not considered a usage.
    """
    def __init__(self, default_factory, from_o=None):
        if from_o:
            self.timestamp_use = from_o.timestamp_use
            return super().__init__(default_factory, from_o)
        else:
            self.timestamp_use = dict()
            return super().__init__(default_factory)

    def __repr__(self):
        return 'tstp_defaultdict(%s, %s, %s)' % (self.default_factory, dict.__repr__(self.timestamp_use), dict.__repr__(self))

    def __missing__(self, key):
        self.timestamp_use[key] = datetime.datetime.now()
        return super().__missing__(key)

    def __getitem__(self, key):
        self.timestamp_use[key] = datetime.datetime.now()
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        self.timestamp_use[key] = datetime.datetime.now()
        return super().__setitem__(key, value)

    def __delitem__(self, key):
        del self.timestamp_use[key]
        return super().__delitem__(key)

    def pop(self, key):
        del self.timestamp_use[key]
        return super().pop(key)

    def get_tstp(self, key):
        """
        Returns the timestamp of the last usage of key.
        If key is not in the dictionary, returns None.
        """
        if key in self.timestamp_use:
            return self.timestamp_use[key]
        else:
            return None
