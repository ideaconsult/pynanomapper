"""
Test Excel to NeXus conversion functionality.

This test verifies that the Excel to NeXus conversion pipeline works correctly.
"""

import pytest
import os
from pathlib import Path
from pynanomapper.datamodel.templates.template_parser import TemplateDesignerParser
from pynanomapper.datamodel.templates.excel_to_nexus import (
    excel_to_nexus,
    excel_to_protocol_application,
    excel_to_substances
)
from pyambit.nexus_writer import to_nexus 
import pyambit.datamodel as mx


# Path to test resources
TEST_DIR = Path(__file__).parent / "resources" / "data"


def test_parse_excel_with_blueprint():
    """Test parsing Excel file with hidden blueprint."""
    # Use existing test template
    test_files = list(TEST_DIR.glob("*.xlsx"))
    if not test_files:
        pytest.skip("No test Excel files found")
    
    xlsx_file = test_files[0]
    parser = TemplateDesignerParser(xlsx_file)
    
    assert parser.template_json is not None
    assert "PROTOCOL_TOP_CATEGORY" in parser.template_json or "data_sheets" in parser.template_json


def test_excel_to_protocol_application():
    """Test conversion to ProtocolApplication."""
    test_files = list(TEST_DIR.glob("*.xlsx"))
    if not test_files:
        pytest.skip("No test Excel files found")
    
    xlsx_file = test_files[0]
    pa = excel_to_protocol_application(xlsx_file)
    
    assert isinstance(pa, mx.ProtocolApplication)
    assert pa.protocol is not None
    assert pa.uuid is not None
    # Effects might be empty if no data in tables
    assert isinstance(pa.effects, list)


def test_excel_to_substances():
    """Test conversion to Substances."""
    test_files = list(TEST_DIR.glob("*.xlsx"))
    if not test_files:
        pytest.skip("No test Excel files found")
    
    xlsx_file = test_files[0]
    substances = excel_to_substances(xlsx_file)
    
    assert isinstance(substances, mx.Substances)
    assert len(substances.substance) > 0
    
    # Check first substance
    substance = substances.substance[0]
    assert substance.i5uuid is not None
    assert substance.name is not None
    
    # Check study data
    if substance.study:
        assert len(substance.study) > 0
        assert isinstance(substance.study[0], mx.ProtocolApplication)


def test_excel_to_nexus_conversion():
    """Test full Excel to NeXus conversion."""
    test_files = list(TEST_DIR.glob("*.xlsx"))
    if not test_files:
        pytest.skip("No test Excel files found")
    
    xlsx_file = test_files[0]
    output_path = TEST_DIR / "test_output.nxs"
    
    try:
        result = excel_to_nexus(xlsx_file, output_path)
        
        assert os.path.exists(result)
        assert Path(result).suffix == ".nxs"
        
        # Validate NeXus structure
        import nexusformat.nexus as nx
        nx_root = nx.nxload(result)
        assert nx_root is not None
        
    finally:
        # Cleanup
        if output_path.exists():
            output_path.unlink()


def test_excel_to_nexus_default_output():
    """Test NeXus conversion with default output path."""
    test_files = list(TEST_DIR.glob("*.xlsx"))
    if not test_files:
        pytest.skip("No test Excel files found")
    
    xlsx_file = test_files[0]
    expected_output = xlsx_file.with_suffix('.nxs')
    
    try:
        result = excel_to_nexus(xlsx_file)
        
        assert os.path.exists(result)
        assert Path(result) == expected_output
        
    finally:
        pass
        # Cleanup
        #if expected_output.exists():
        #    expected_output.unlink()
