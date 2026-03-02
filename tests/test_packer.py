"""
Tests for packer utility
"""

import pytest
import zipfile
import io
from pathlib import Path

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.packer import Packer, PackResult


@pytest.fixture
def packer():
    """Create packer instance"""
    return Packer(max_size_mb=10)


def test_create_zip_from_files(packer):
    """Test creating ZIP from files dict"""
    files = {
        "index.html": "<html><body>Test</body></html>",
        "styles.css": "body { color: red; }",
        "app.js": "console.log('test');"
    }
    
    result = packer.create_zip_from_files(files)
    
    assert result.success
    assert result.file_count == 3
    assert result.size_bytes > 0
    assert result.checksum is not None
    
    # Verify ZIP contents
    zip_buffer = io.BytesIO(result.zip_bytes)
    with zipfile.ZipFile(zip_buffer, 'r') as zf:
        assert "index.html" in zf.namelist()
        assert "styles.css" in zf.namelist()
        assert "app.js" in zf.namelist()


def test_create_webapp_package(packer):
    """Test creating web app package"""
    html = "<!DOCTYPE html><html><body>Test</body></html>"
    css = "body { color: blue; }"
    js = "console.log('hello');"
    
    result = packer.create_webapp_package(
        html_content=html,
        css_content=css,
        js_content=js,
        app_name="test-app"
    )
    
    assert result.success
    assert result.file_count >= 3
    
    # Check metadata
    zip_buffer = io.BytesIO(result.zip_bytes)
    with zipfile.ZipFile(zip_buffer, 'r') as zf:
        assert "index.html" in zf.namelist()
        assert "styles.css" in zf.namelist()
        assert "app.js" in zf.namelist()
        assert "blitzdev-meta.json" in zf.namelist()
        assert "manifest.json" in zf.namelist()


def test_validate_zip(packer, tmp_path):
    """Test ZIP validation"""
    # Create a valid ZIP
    files = {
        "index.html": "<html><body>Test</body></html>"
    }
    
    zip_path = tmp_path / "test.zip"
    result = packer.create_zip_from_files(files, output_path=zip_path)
    
    assert result.success
    
    # Validate - note: create_zip_from_files auto-adds manifest.json
    validation = packer.validate_zip(zip_path)
    assert validation.success
    assert validation.file_count == 2  # index.html + manifest.json


def test_validate_zip_missing_index(packer, tmp_path):
    """Test validation fails without index.html"""
    files = {
        "other.html": "<html></html>"
    }
    
    zip_path = tmp_path / "test.zip"
    result = packer.create_zip_from_files(files, output_path=zip_path)
    
    validation = packer.validate_zip(zip_path)
    assert not validation.success
    assert "index.html" in validation.error


def test_size_limit(packer):
    """Test ZIP size limit enforcement"""
    # Create files that exceed limit
    # Size check is post-compression, so we need incompressible random data
    import random
    packer_small = Packer(max_size_mb=0.001)  # ~1KB limit
    
    # Random bytes are incompressible
    rng = random.Random(42)
    large_content = bytes(rng.getrandbits(8) for _ in range(5000))
    files = {
        "large.bin": large_content
    }
    
    result = packer_small.create_zip_from_files(files)
    
    assert not result.success
    assert "exceeds" in result.error.lower()


def test_get_zip_info(packer, tmp_path):
    """Test getting ZIP info"""
    files = {
        "index.html": "<html><body>Test content here</body></html>",
        "style.css": "body { margin: 0; }"
    }
    
    zip_path = tmp_path / "test.zip"
    packer.create_zip_from_files(files, output_path=zip_path)
    
    info = packer.get_zip_info(zip_path)
    
    assert info is not None
    assert "files" in info
    # create_zip_from_files auto-adds manifest.json → 3 files total
    assert len(info["files"]) == 3
    assert "total_size" in info
    assert "compression_ratio" in info
