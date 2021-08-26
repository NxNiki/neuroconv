"""Authors: Alessio Buccino."""
import spikeextractors as se

from ..baserecordingextractorinterface import BaseRecordingExtractorInterface
from ..basesortingextractorinterface import BaseSortingExtractorInterface
from ....utils.json_schema import get_base_schema, FilePathType


class SIPickleRecordingExtractorInterface(BaseRecordingExtractorInterface):
    """Primary interface for reading and converting SpikeInterface objects through Pickle files."""

    @classmethod
    def get_source_schema(cls):
        """Return partial json schema for expected input arguments."""
        return get_base_schema(required=["pkl_file"], properties=dict(pkl_file=dict(type="string")))

    def __init__(self, pkl_file: FilePathType):
        self.source_data = dict(pkl_file=pkl_file)
        self.subset_channels = None
        self.recording_extractor = se.load_extractor_from_pickle(pkl_file=pkl_file)


class SIPickleSortingExtractorInterface(BaseSortingExtractorInterface):
    """Primary interface for reading and converting SpikeInterface objects through Pickle files."""

    @classmethod
    def get_source_schema(cls):
        """Return partial json schema for expected input arguments."""
        return get_base_schema(required=["pkl_file"], properties=dict(pkl_file=dict(type="string")))

    def __init__(self, pkl_file: FilePathType):
        self.source_data = dict(pkl_file=pkl_file)
        self.sorting_extractor = se.load_extractor_from_pickle(pkl_file=pkl_file)
