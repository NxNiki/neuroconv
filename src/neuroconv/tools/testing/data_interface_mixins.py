import json
from abc import abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Callable, Union

import numpy as np
from jsonschema import validate
from jsonschema.validators import Draft7Validator
from roiextractors import NwbImagingExtractor, NwbSegmentationExtractor
from roiextractors.testing import check_imaging_equal, check_segmentations_equal
from spikeinterface.core.testing import check_recordings_equal, check_sortings_equal
from spikeinterface.extractors import NwbRecordingExtractor, NwbSortingExtractor

from ...basedatainterface import BaseDataInterface
from ...datainterfaces.ecephys.baserecordingextractorinterface import (
    BaseRecordingExtractorInterface,
)
from ...datainterfaces.ecephys.basesortingextractorinterface import (
    BaseSortingExtractorInterface,
)
from ...datainterfaces.ophys.baseimagingextractorinterface import (
    BaseImagingExtractorInterface,
)
from ...datainterfaces.ophys.basesegmentationextractorinterface import (
    BaseSegmentationExtractorInterface,
)
from ...utils import NWBMetaDataEncoder


class DataInterfaceTestMixin:
    data_interface_cls: Union[BaseDataInterface, Callable]
    interface_kwargs: Union[dict, list]
    save_directory: Path

    def test_source_schema_valid(self):
        schema = self.data_interface_cls.get_source_schema()
        Draft7Validator.check_schema(schema=schema)

    def check_conversion_options_schema_valid(self):
        schema = self.interface.get_conversion_options_schema()
        Draft7Validator.check_schema(schema=schema)

    def check_metadata_schema_valid(self):
        schema = self.interface.get_metadata_schema()
        Draft7Validator.check_schema(schema=schema)

    def check_metadata(self):
        schema = self.interface.get_metadata_schema()
        metadata = self.interface.get_metadata()
        if "session_start_time" not in metadata["NWBFile"]:
            metadata["NWBFile"].update(session_start_time=datetime.now().astimezone())
        # handle json encoding of datetimes and other tricky types
        metadata_for_validation = json.loads(json.dumps(metadata, default=NWBMetaDataEncoder))
        validate(metadata_for_validation, schema)

        self.check_extracted_metadata(metadata)

    def run_conversion(self, nwbfile_path: str):
        metadata = self.interface.get_metadata()
        metadata["NWBFile"].update(session_start_time=datetime.now().astimezone())
        self.interface.run_conversion(nwbfile_path=nwbfile_path, overwrite=True, metadata=metadata)

    @abstractmethod
    def check_read(self, nwbfile_path: str):
        pass

    def check_extracted_metadata(self, metadata: dict):
        """Override this method to make assertions about specific extracted metadata values."""
        pass

    def test_conversion_as_lone_interface(self):
        interface_kwargs = self.interface_kwargs
        if isinstance(interface_kwargs, dict):
            interface_kwargs = [interface_kwargs]
        for num, kwargs in enumerate(interface_kwargs):
            with self.subTest(str(num)):
                self.case = num
                self.interface = self.data_interface_cls(**kwargs)

                self.check_metadata_schema_valid()
                self.check_conversion_options_schema_valid()
                self.check_metadata()
                nwbfile_path = str(self.save_directory / f"{self.data_interface_cls.__name__}_{num}.nwb")
                self.run_conversion(nwbfile_path)
                self.check_read(nwbfile_path=nwbfile_path)


class RecordingExtractorInterfaceTestMixin(DataInterfaceTestMixin):
    data_interface_cls: BaseRecordingExtractorInterface

    def check_read(self, nwbfile_path: str):
        recording = self.interface.recording_extractor

        electrical_series_name = self.interface.get_metadata()["Ecephys"][self.interface.es_key]["name"]

        if recording.get_num_segments() == 1:
            # Spikeinterface behavior is to load the electrode table channel_name property as a channel_id
            nwb_recording = NwbRecordingExtractor(file_path=nwbfile_path, electrical_series_name=electrical_series_name)
            if "channel_name" in recording.get_property_keys():
                renamed_channel_ids = recording.get_property("channel_name")
            else:
                renamed_channel_ids = recording.get_channel_ids().astype("str")
            recording = recording.channel_slice(
                channel_ids=recording.get_channel_ids(), renamed_channel_ids=renamed_channel_ids
            )

            # Edge case that only occurs in testing, but should eventually be fixed nonetheless
            # The NwbRecordingExtractor on spikeinterface experiences an issue when duplicated channel_ids
            # are specified, which occurs during check_recordings_equal when there is only one channel
            if nwb_recording.get_channel_ids()[0] != nwb_recording.get_channel_ids()[-1]:
                check_recordings_equal(RX1=recording, RX2=nwb_recording, return_scaled=False)
                if recording.has_scaled_traces() and nwb_recording.has_scaled_traces():
                    check_recordings_equal(RX1=recording, RX2=nwb_recording, return_scaled=True)


class ImagingExtractorInterfaceTestMixin(DataInterfaceTestMixin):
    data_interface_cls: BaseImagingExtractorInterface

    def check_read(self, nwbfile_path: str):
        imaging = self.interface.imaging_extractor
        nwb_imaging = NwbImagingExtractor(file_path=nwbfile_path)

        exclude_channel_comparison = False
        if imaging.get_channel_names() is None:
            exclude_channel_comparison = True

        check_imaging_equal(imaging, nwb_imaging, exclude_channel_comparison)


class SegmentationExtractorInterfaceTestMixin(DataInterfaceTestMixin):
    data_interface_cls: BaseSegmentationExtractorInterface

    def check_read(self, nwbfile_path: str):
        nwb_segmentation = NwbSegmentationExtractor(file_path=nwbfile_path)
        segmentation = self.interface.segmentation_extractor
        check_segmentations_equal(segmentation, nwb_segmentation)


class SortingExtractorInterfaceTestMixin(DataInterfaceTestMixin):
    data_interface_cls: BaseSortingExtractorInterface

    def check_read(self, nwbfile_path: str):
        sorting = self.interface.sorting_extractor
        sf = sorting.get_sampling_frequency()
        if sf is None:  # need to set dummy sampling frequency since no associated acquisition in file
            sorting.set_sampling_frequency(30_000)

        # NWBSortingExtractor on spikeinterface does not yet support loading data written from multiple segment.
        if sorting.get_num_segments() == 1:
            nwb_sorting = NwbSortingExtractor(file_path=nwbfile_path, sampling_frequency=sf)
            # In the NWBSortingExtractor, since unit_names could be not unique,
            # table "ids" are loaded as unit_ids. Here we rename the original sorting accordingly
            sorting_renamed = sorting.select_units(
                unit_ids=sorting.unit_ids, renamed_unit_ids=np.arange(len(sorting.unit_ids))
            )
            check_sortings_equal(SX1=sorting_renamed, SX2=nwb_sorting)
