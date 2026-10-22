import asyncio
import copy
import unittest
from unittest.mock import Mock

from app.contracts import ContractError
from app.execution_policy import (current_policy, enforce_provider_call,
                                  execution_policy, internal_text_allowed, enforce_download,
                                  validate_external_story)


def story_fixture():
    return {'characters': [], 'shots': [
        {'uid': 'first', 'duration': 4, 'characters': [], 'dialogue': [],
         'prompt': 'integrated_multimodal_description:\n[Shot 1] A quiet room.\n\n'
                   'summary:\nA quiet room.\n\n'
                   'camera_movement:\nStill camera.\n\n'
                   'non_diegetic_music:\nNone.\n\n'
                   'diegetic_sound:\nRoom tone.\n\n'
                   'diegetic_dialogue:\nNone.'},
    ]}


class ExecutionPolicyTests(unittest.TestCase):
    def test_default_strict_context_blocks_and_failure_restores_legacy_policy(self):
        self.assertTrue(internal_text_allowed())
        with self.assertRaises(ContractError) as caught:
            with execution_policy(scope='job/example'):
                enforce_provider_call('image_prompt')
        error = caught.exception
        self.assertEqual(error.code, 'TEXT_GENERATION_FORBIDDEN')
        self.assertEqual(error.status, 409)
        self.assertEqual(error.details[0]['stage'], 'image_prompt')
        self.assertEqual(error.details[0]['scope'], 'job/example')
        self.assertFalse(error.retryable)
        self.assertTrue(internal_text_allowed())
        enforce_provider_call()

    def test_nested_allowed_cannot_bypass_forbid(self):
        with execution_policy('forbid', scope='outer'):
            with execution_policy('allowed'):
                self.assertEqual(current_policy().scope, 'outer')
                with self.assertRaises(ContractError):
                    enforce_provider_call()
            self.assertFalse(internal_text_allowed())
        self.assertTrue(internal_text_allowed())

    def test_async_requests_have_independent_policies(self):
        async def run():
            entered = asyncio.Event()
            released = asyncio.Event()

            async def strict():
                with execution_policy('forbid'):
                    entered.set()
                    await released.wait()
                    with self.assertRaises(ContractError):
                        enforce_provider_call()

            async def legacy():
                await entered.wait()
                enforce_provider_call()
                released.set()

            await asyncio.gather(strict(), legacy())
        asyncio.run(run())

    def test_invalid_policy_rejected_without_changing_context(self):
        with self.assertRaises(ValueError):
            with execution_policy('sometimes'):
                self.fail('invalid policy entered')
        self.assertTrue(internal_text_allowed())

    def test_download_guard_is_independent_nested_and_restored(self):
        with execution_policy('allowed', allow_downloads=False):
            enforce_provider_call()
            with execution_policy('allowed', allow_downloads=True):
                with self.assertRaises(ContractError) as caught:
                    enforce_download('speech_detection/model.onnx')
                self.assertEqual(caught.exception.code, 'IMPLICIT_DOWNLOAD_FORBIDDEN')
        enforce_download('speech_detection/model.onnx')

    def test_speech_missing_model_does_not_fetch_inside_agent_execution(self):
        from app.speech import ensure_model
        from unittest.mock import patch
        with patch('app.speech.Downloader') as downloader:
            downloader.return_value.verified.return_value = False
            with execution_policy(allow_downloads=False):
                with self.assertRaises(ContractError) as caught:
                    ensure_model()
                self.assertIsNone(ensure_model(download=False))
            self.assertEqual(caught.exception.code, 'IMPLICIT_DOWNLOAD_FORBIDDEN')
            downloader.return_value.fetch.assert_not_called()
            downloader.return_value.verified.return_value = True
            with execution_policy(allow_downloads=False):
                self.assertIsNotNone(ensure_model())
            downloader.return_value.fetch.assert_not_called()

    def test_legacy_speech_preparation_can_still_fetch(self):
        from app.speech import ensure_model
        from unittest.mock import patch
        with patch('app.speech.Downloader') as downloader:
            downloader.return_value.verified.return_value = False
            ensure_model()
            downloader.return_value.fetch.assert_called_once()

    def test_download_boundary_blocks_new_transfer_but_reuses_verified_files(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from app.downloads import Downloader
        loader = Downloader()
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(loader, 'verified', return_value=False) as verified, \
                patch('app.downloads.httpx.Client') as network:
            target = Path(folder) / 'model.bin'
            with execution_policy(allow_downloads=False):
                with self.assertRaises(ContractError) as caught:
                    loader.fetch('https://invalid.test/model', target, 1, 'a' * 64)
                self.assertEqual(caught.exception.code, 'IMPLICIT_DOWNLOAD_FORBIDDEN')
                self.assertFalse(target.with_name('model.bin.part.json').exists())
                verified.return_value = True
                self.assertEqual(loader.fetch('https://invalid.test/model', target, 1, 'a' * 64), target)
            network.assert_not_called()

    def test_external_validation_checks_exact_dialogue_without_mutation(self):
        from app.content import BASE_FIELDS
        story = story_fixture()
        # The production parser defines mode-specific field order.
        story['shots'][0]['prompt'] = '\n\n'.join(
            name + ':\n' + ('[Shot 1] A quiet room.' if index == 0 else 'None.')
            for index, name in enumerate(BASE_FIELDS))
        before = copy.deepcopy(story)
        resolve = Mock(return_value={})
        mode = Mock(return_value='T2VA')
        with execution_policy():
            validate_external_story(story, None, resolve, mode)
        self.assertEqual(story, before)
        story['shots'][0]['dialogue'] = [{'speaker': 'narrator', 'text': 'Hello.'}]
        with self.assertRaises(ContractError) as caught:
            validate_external_story(story, None, resolve, mode)
        self.assertEqual(caught.exception.code, 'EXTERNAL_CONTENT_REQUIRED')
        self.assertEqual(caught.exception.details[0]['uid'], 'first')

    def test_missing_prompts_are_aggregated_and_selection_is_explicit(self):
        story = story_fixture()
        story['shots'][0]['prompt'] = ''
        story['shots'].append({**story['shots'][0], 'uid': 'second'})
        resolve = Mock(return_value={})
        mode = Mock(return_value='T2VA')
        validate_external_story(story, None, resolve, mode, uids=[])
        resolve.assert_not_called()
        with self.assertRaises(ContractError) as caught:
            validate_external_story(story, None, resolve, mode)
        self.assertEqual(len(caught.exception.details), 2)
        with self.assertRaises(ContractError) as selected:
            validate_external_story(story, None, resolve, mode, uids=['second'])
        self.assertEqual([item['uid'] for item in selected.exception.details], ['second'])
        with self.assertRaises(ContractError) as missing:
            validate_external_story(story, None, resolve, mode, uids=['unknown'])
        self.assertEqual(missing.exception.code, 'SHOT_NOT_FOUND')


if __name__ == '__main__':
    unittest.main()
