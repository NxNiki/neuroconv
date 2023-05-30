import json
import datetime
from typing import Optional

from dateutil.parser import parse as dateparse

from ..baseimagingextractorinterface import BaseImagingExtractorInterface
from ....tools import get_package
from ....utils import FilePathType


def extract_extra_metadata(file_path) -> dict:
    ScanImageTiffReader = get_package(
        package_name="ScanImageTiffReader", installation_instructions="pip install scanimage-tiff-reader"
    )
    src_file = ScanImageTiffReader.ScanImageTiffReader(str(file_path))
    extra_metadata = {}
    for metadata_string in (src_file.description(iframe=0), src_file.metadata()):
        metadata_dict = {
            x.split("=")[0].strip(): x.split("=")[1].strip()
            for x in metadata_string.replace("\n", "\r").split("\r")
            if "=" in x
        }
        extra_metadata = dict(**extra_metadata, **metadata_dict)
    return extra_metadata


class ScanImageImagingInterface(BaseImagingExtractorInterface):
    ExtractorName = "ScanImageTiffImagingExtractor"

    @classmethod
    def get_source_schema(cls) -> dict:
        source_schema = super().get_source_schema()
        source_schema["properties"]["file_path"]["description"] = "Path to Tiff file."
        return source_schema

    def __init__(
        self,
        file_path: FilePathType,
        fallback_sampling_frequency: Optional[float] = None,
        verbose: bool = True,
    ):
        """
        DataInterface for reading Tiff files that are generated by ScanImage. This interface extracts the metadata
        from the exif of the tiff file.

        Parameters
        ----------
        file_path: str
            Path to tiff file.
        fallback_sampling_frequency: float, optional
            The sampling frequency can usually be extracted from the scanimage metadata in
            exif:ImageDescription:state.acq.frameRate. If not, use this.
        """
        self.image_metadata = extract_extra_metadata(file_path=file_path)

        if "state.acq.frameRate" in self.image_metadata:
            sampling_frequency = float(self.image_metadata["state.acq.frameRate"])
        elif "SI.hRoiManager.scanFrameRate" in self.image_metadata:
            sampling_frequency = float(self.image_metadata["SI.hRoiManager.scanFrameRate"])
        else:
            assert_msg = (
                "sampling frequency not found in image metadata, "
                "input the frequency using the argument `fallback_sampling_frequency`"
            )
            assert fallback_sampling_frequency is not None, assert_msg
            sampling_frequency = fallback_sampling_frequency

        super().__init__(file_path=file_path, sampling_frequency=sampling_frequency, verbose=verbose)

    def get_metadata(self) -> dict:
        device_number = 0  # Imaging plane metadata is a list with metadata for each plane

        metadata = super().get_metadata()

        if "state.internal.triggerTimeString" in self.image_metadata:
            extracted_session_start_time = dateparse(self.image_metadata["state.internal.triggerTimeString"])
            metadata["NWBFile"].update(session_start_time=extracted_session_start_time)
        elif "epoch" in self.image_metadata:
            # Versions of ScanImage at least as recent as 2020, and possibly earlier, store the start time under keyword
            # `epoch`, as a string encoding of a Matlab array, example `'[2022  8  8 16 56 7.329]'`
            # dateparse can't cope with this representation, so using strptime directly
            extracted_session_start_time = datetime.datetime.strptime(
                self.image_metadata["epoch"],
                '[%Y %m %d %H %M %S.%f]'
            )
            metadata["NWBFile"].update(session_start_time=extracted_session_start_time)

        # Extract many scan image properties and attach them as dic in the description
        ophys_metadata = metadata["Ophys"]
        two_photon_series_metadata = ophys_metadata["TwoPhotonSeries"][device_number]
        if self.image_metadata is not None:
            extracted_description = json.dumps(self.image_metadata)
            two_photon_series_metadata.update(description=extracted_description)

        return metadata
