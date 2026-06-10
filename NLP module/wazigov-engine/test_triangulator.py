import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock heavy/external ML dependencies before importing triangulator
mock_transformers = MagicMock()
sys.modules['transformers'] = mock_transformers
sys.modules['nltk'] = MagicMock()
sys.modules['nltk.data'] = MagicMock()

import triangulator

class TestTriangulator(unittest.TestCase):

    def test_normalise(self):
        self.assertEqual(triangulator.normalise("Nairobi City"), "nairobi city")
        self.assertEqual(triangulator.normalise("Taita-Taveta"), "taita taveta")
        self.assertEqual(triangulator.normalise("O'Brien"), "o brien")
        self.assertEqual(triangulator.normalise(" Murang'a "), "murang a")

    @patch('triangulator.Path.read_text')
    def test_parse_cob(self, mock_read_text):
        mock_read_text.return_value = (
            "3.1. County Government of Mombasa\n"
            "Some COB text here.\n"
            "3.2. County Government of Kwale\n"
            "More COB text."
        )
        sections = triangulator.parse_cob(["dummy_cob.md"])
        
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]["county"], "Mombasa")
        self.assertEqual(sections[1]["county"], "Kwale")

    @patch('triangulator.Path.read_text')
    def test_parse_oag(self, mock_read_text):
        mock_read_text.return_value = (
            "COUNTY EXECUTIVE OF MOMBASA - NO.1\n"
            "Some OAG text here.\n"
            "COUNTY EXECUTIVE OF KWALE - NO.2\n"
            "More OAG text."
        )
        sections = triangulator.parse_oag(["dummy_oag.md"])
        
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]["county"], "Mombasa")
        self.assertEqual(sections[1]["county"], "Kwale")

    def test_extract_projects(self):
        sample_text = """
        List of Development Projects with Highest Expenditure
        No. Sector Project Location Contract Sum Amount Paid (%)
        1 Health Construction of Ward Kapsabet 1,500,000 500,000 33.3
        3.1.2 Next Section
        """
        projects = triangulator.extract_projects(sample_text, "Nandi")
        
        self.assertEqual(len(projects), 1)
        self.assertIn("1 Health Construction of Ward Kapsabet", projects[0]["project_name"])
        self.assertEqual(projects[0]["contract_sum_kshs"], 1500000.0)
        self.assertEqual(projects[0]["amount_paid_kshs"], 500000.0)
        self.assertEqual(projects[0]["implementation_pct"], 33.3)
        self.assertEqual(projects[0]["source_cob"], True)

    def test_extract_oag_entities(self):
        # Configure the mocked ner_pipeline to return mock entities
        triangulator.ner_pipeline.return_value = [
            {'entity_group': 'PROJECT_NAME', 'word': 'Market Shed'},
            {'entity_group': 'KSH_AMOUNT', 'word': '1,200,000'},
            {'entity_group': 'RISK_FINDING', 'word': 'stalled'}
        ]
        
        # Configure nltk sentence tokenizer mock
        triangulator.nltk.sent_tokenize.return_value = [
            "The Market Shed project of 1,200,000 stalled and remains incomplete."
        ]
        
        findings = triangulator.extract_oag_entities("The Market Shed project of 1,200,000 stalled.", "Nandi")
        
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["project_name_extracted"], "Market Shed")
        self.assertEqual(findings[0]["amounts_kshs"], [1200000.0])
        self.assertEqual(findings[0]["risk_type"], "FLAGGED_BY_MODEL")

    def test_extract_dev_signal(self):
        dev_signal = triangulator.extract_dev_signal("dummy text", "Nandi")
        self.assertEqual(dev_signal["status"], "OK")
        self.assertEqual(dev_signal["dev_pct"], 35.0)

    def test_link(self):
        cob_projects = [{
            "project_name": "Construction of Ward Kapsabet",
            "contract_sum_kshs": 1500000.0,
            "amount_paid_kshs": 500000.0,
            "implementation_pct": 33.3,
            "absorption_flag": "NORMAL"
        }]
        
        oag_findings = [{
            "sentence": "The Construction of Ward Kapsabet was delayed.",
            "project_name_extracted": "Construction of Ward Kapsabet",
            "amounts_kshs": [],
            "risk_type": "INCOMPLETE_PROJECT"
        }]
        
        dev_signal = {"status": "OK", "dev_pct": 35.0, "metric": "Dev spend > 30%"}
        linked_projects = triangulator.link(cob_projects, oag_findings, "Nandi", dev_signal, threshold=65)
        
        self.assertEqual(len(linked_projects), 1)
        self.assertEqual(linked_projects[0]["county"], "Nandi")
        self.assertEqual(linked_projects[0]["source_oag"], True)
        self.assertEqual(linked_projects[0]["triangulation_verdict"], "CORROBORATED_PROJECT_RISK")
        self.assertIn("INCOMPLETE_PROJECT", linked_projects[0]["oag_forensics"]["risk_types"])
