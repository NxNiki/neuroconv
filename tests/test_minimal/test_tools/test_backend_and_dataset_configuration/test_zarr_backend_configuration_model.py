"""Unit tests for the DatasetInfo Pydantic model."""
from io import StringIO
from unittest.mock import patch

from neuroconv.tools.testing import mock_ZarrBackendConfiguration


def test_zarr_backend_configuration_print():
    """Test the printout display of a HDF5DatasetConfiguration model looks nice."""
    zarr_backend_configuration = mock_ZarrBackendConfiguration()

    with patch("sys.stdout", new=StringIO()) as out:
        print(zarr_backend_configuration)

    expected_print = """
Configurable datasets identified using the zarr backend
-------------------------------------------------------

acquisition/TestElectricalSeriesAP/data
---------------------------------------
  maxshape: (1800000, 384)
  dtype: int16

  chunk_shape: (78125, 64)
  buffer_shape: (1250000, 384)
  compression_method: gzip
  filter_methods: ['delta']

acquisition/TestElectricalSeriesLF/data
---------------------------------------
  maxshape: (75000, 384)
  dtype: int16

  chunk_shape: (37500, 128)
  buffer_shape: (75000, 384)
  compression_method: gzip
  filter_methods: ['delta']
"""
    assert out.getvalue() == expected_print
