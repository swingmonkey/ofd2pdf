"""Basic tests for converter registry and easyofd backend."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ofd2pdf.backends import EasyOFDBackend, OFDRWBackend, TaurusxinBackend
from ofd2pdf.converter import BACKENDS, list_backends, pick_backend


def test_backends_registered():
    assert "easyofd" in BACKENDS
    assert "taurusxin" in BACKENDS
    assert "ofdrw" in BACKENDS


def test_easyofd_is_available():
    assert EasyOFDBackend.is_available() is True


def test_taurusxin_not_available_without_exe():
    with patch.dict(os.environ, {}, clear=True):
        # Ensure no bin/Ofd2Pdf.exe exists during this test
        assert TaurusxinBackend.is_available() is False


def test_ofdrw_not_available_without_jar():
    with patch.dict(os.environ, {}, clear=True):
        assert OFDRWBackend.is_available() is False


def test_list_backends():
    info = list_backends()
    assert info["easyofd"]["available"] is True
    assert info["taurusxin"]["available"] is False
    assert info["ofdrw"]["available"] is False


def test_pick_backend_easyofd():
    backend = pick_backend("easyofd")
    assert backend.name == "easyofd"


def test_pick_backend_unknown():
    with pytest.raises(ValueError):
        pick_backend("nonexistent")


def test_pick_auto_falls_back_to_easyofd():
    backend = pick_backend()
    assert backend.name == "easyofd"
