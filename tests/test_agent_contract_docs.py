import json
import http.client
import unittest
from pathlib import Path
from unittest.mock import patch

from app import api
from app.agent_contracts import AgentCreate
from app.storage import ROOT, read_json
from tools.generate_agent_contract import contract


class AgentContractDocumentationTests(unittest.TestCase):
    def test_published_contract_matches_registered_typed_routes(self):
        self.assertEqual(contract(api.app), read_json(ROOT / 'docs/agent-api-contract.json'))

    def test_contract_does_not_depend_on_python_http_status_phrases(self):
        # Python 3.13 renamed the standard descriptions for 413 and 422. The
        # application publishes an explicit protocol description, so changing
        # interpreter defaults must not change any route/schema in the contract.
        baseline = contract(api.app)
        with patch.dict(http.client.responses, {413: 'Interpreter-specific 413', 422: 'Interpreter-specific 422'}), \
                patch.object(api.app, 'openapi_schema', None):
            self.assertEqual(contract(api.app), baseline)

    def test_task_templates_are_typed_drafts_with_external_defaults(self):
        folder = ROOT / 'agent-skills/short-drama-factory/assets'
        for path in sorted(folder.glob('agent-*.json')):
            with self.subTest(template=path.name):
                value = json.loads(path.read_text(encoding='utf-8'))
                parsed = AgentCreate.model_validate(value)
                self.assertNotIn('start', value)
                self.assertFalse(parsed.options.auto_reference)
                if parsed.options.input_mode == 'storyboard':
                    self.assertTrue(all(shot.prompt for shot in parsed.storyboard.shots))


if __name__ == '__main__':
    unittest.main()
