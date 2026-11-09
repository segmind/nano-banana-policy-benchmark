"""Model discovery, CLI compatibility and documented request contracts, offline."""
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import benchmark as b
from test_benchmark import PNG, PINNED_URL, FakeClient, response, sample_case


MODELS = {
    'nano-banana': ('gemini-2.5-flash-image', 'fal-ai/nano-banana'),
    'nano-banana-pro': ('gemini-3-pro-image', 'fal-ai/nano-banana-pro'),
    'nano-banana-2': ('gemini-3.1-flash-image', 'fal-ai/nano-banana-2'),
    'nano-banana-2-lite': ('gemini-3.1-flash-lite-image', 'google/nano-banana-2-lite'),
    'nano-banana-2.1': ('gemini-nano-banana-2.1', 'google/nano-banana-2.1'),
}


class ModelCliTests(unittest.TestCase):
    def setUp(self):
        # Discovery and planning must not inspect credentials, load .env, or
        # instantiate a network client, even when the shell has credentials.
        for name in ('credentials', 'load_env_file', 'HTTPClient'):
            mock = patch.object(b, name, side_effect=AssertionError(f'{name} is not offline'))
            mock.start()
            self.addCleanup(mock.stop)

    def invoke(self, args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = b.main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_model_and_profile_flags_produce_identical_plans_for_each_model(self):
        dataset, _ = b.load_dataset(b.ROOT/'datasets/violence')
        for model in MODELS:
            with self.subTest(model=model):
                plans = []
                for flag in ('--model', '--profile'):
                    with patch.object(b, 'make_plan', wraps=b.make_plan) as plan_inputs:
                        code, stdout, stderr = self.invoke(['plan', flag, model])
                    self.assertEqual(plan_inputs.call_args.args[2], dataset['cases'])
                    self.assertEqual(code, 0, stderr)
                    plans.append(json.loads(stdout))
                self.assertEqual(plans[0], plans[1])
                self.assertEqual(plans[0]['profile_id'], model)
                self.assertEqual(plans[0]['model_family'], MODELS[model][0])
                self.assertEqual(plans[0]['dataset_id'], 'violence')
                self.assertEqual(plans[0]['case_scope'], 'full_dataset')
                self.assertEqual(plans[0]['case_ids'], [case['id'] for case in dataset['cases']])
                self.assertEqual(plans[0]['repeats'], 3)
                self.assertEqual(plans[0]['planned_inference_requests'], 180)

    def test_model_argument_is_required_and_conflicting_flags_are_rejected(self):
        for command in ('plan', 'run'):
            for extra in ([], ['--model', 'nano-banana-2', '--profile', 'nano-banana-pro']):
                with self.subTest(command=command, extra=extra), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as caught:
                        b.main([command, *extra])
                    self.assertEqual(caught.exception.code, 2)

    def test_unknown_and_path_model_names_fail_before_credentials(self):
        for command in ('plan', 'run'):
            for model in ('missing-model', '../nano-banana-pro'):
                with self.subTest(command=command, model=model):
                    code, _, stderr = self.invoke([command, '--model', model])
                    self.assertEqual(code, 2)
                    self.assertIn('models' if model == 'missing-model' else 'not a path', stderr)

    def test_models_lists_validated_endpoints_and_settings_without_credentials_or_network(self):
        code, stdout, stderr = self.invoke(['models'])
        self.assertEqual(code, 0, stderr)
        models = json.loads(stdout)['models']
        self.assertEqual([model['id'] for model in models], sorted(MODELS))
        for model in models:
            self.assertEqual(model['providers'], b.load_profile(model['id'])['providers'])
            self.assertEqual(model['family'], MODELS[model['id']][0])
            self.assertEqual(set(model['providers']), set(b.PROVIDERS))

    def test_run_model_flag_dispatches_the_selected_profile(self):
        for flag in ('--model', '--profile'):
            with patch.object(b, 'run_benchmark', return_value=b.ROOT/'runs/test') as run, patch.object(b, 'summarize', return_value={}):
                code, _, stderr = self.invoke(['run', flag, 'nano-banana-2.1'])
            self.assertEqual(code, 0, stderr)
            self.assertEqual(run.call_args.args[4]['id'], 'nano-banana-2.1')


class CanonicalRunTests(unittest.TestCase):
    def test_default_run_schedules_every_case_three_times_for_each_active_provider(self):
        directory = b.ROOT/'datasets/violence'
        dataset, assets = b.load_dataset(directory)
        case_ids = [case['id'] for case in dataset['cases']]
        ref = b.resolve_published_ref(None) if (b.ROOT/'.git').exists() else 'a'*40
        prepared = b.prepare_assets(directory, assets, dataset['cases'], need_public_urls=True, published_ref=ref)
        public_bytes = {asset['public_url']: asset['data'] for asset in prepared.values()}
        client = FakeClient()
        auth = {provider: {'secret': 'fixture-key'} for provider in ('fal', 'segmind')}
        requests = []

        def attempt(client, provider, profile, case, assets, auth, repeat, *args):
            requests.append((provider, case['id'], repeat))
            return {'provider': provider, 'case_id': case['id'], 'repeat': repeat, 'outcome': 'policy_refusal', 'outputs': []}

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'run'
            with patch.object(b, 'resolve_published_ref', return_value=ref), patch.object(b, 'credentials', return_value=(auth, {})), patch.object(b, 'HTTPClient', return_value=client), patch.object(client, 'download', side_effect=public_bytes.__getitem__), patch.object(b, 'run_attempt', side_effect=attempt), contextlib.redirect_stdout(io.StringIO()):
                code = b.main(['run', '--model', 'nano-banana-pro', '--output', str(output)])
            self.assertEqual(code, 0)
            manifest = b.read_json(output/'run.json')
            self.assertEqual(manifest['case_scope'], 'full_dataset')
            self.assertEqual(manifest['case_ids'], case_ids)
            self.assertEqual(manifest['planned_inference_requests'], 180)
            self.assertEqual(len(requests), 180)
            self.assertEqual(set(requests), {(provider, case, repeat) for provider in auth for case in case_ids for repeat in range(1, 4)})
            self.assertEqual(client.calls, [])

    def test_default_dataset_reaches_the_selected_model_with_exact_reference_bytes(self):
        client = FakeClient([
            response({'request_id': 'req-123', 'status_url': 'https://queue.fal.run/status', 'response_url': 'https://queue.fal.run/response'}),
            response({'status': 'COMPLETED'}),
            response({'images': [{'url': 'https://example.com/output.png'}]}),
        ])
        expected = (b.ROOT/'datasets/violence/assets/C002.jpg').read_bytes()
        ref = 'a'*40
        def download(url):
            return expected if url.endswith('/C002.jpg') else PNG
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'run'
            with patch.dict(os.environ, {'FAL_KEY': 'local-test'}, clear=True), patch.object(b, 'resolve_published_ref', return_value=ref), patch.object(b, 'HTTPClient', return_value=client), patch.object(client, 'download', side_effect=download), contextlib.redirect_stdout(io.StringIO()):
                code = b.main(['run', '--model', 'nano-banana-2', '--case', 'V001', '--provider', 'fal', '--repeats', '1', '--output', str(output)])
            self.assertEqual(code, 0)
            manifest = b.read_json(output/'run.json')
            self.assertEqual(manifest['dataset_id'], 'violence')
            self.assertEqual(manifest['profile_id'], 'nano-banana-2')
            self.assertEqual(manifest['case_ids'], ['V001'])
            self.assertEqual(manifest['case_scope'], 'subset')
            submitted = client.calls[0]
            self.assertEqual(submitted[1], 'https://queue.fal.run/fal-ai/nano-banana-2/edit')
            data = base64.b64decode(submitted[3]['image_urls'][0].split(',', 1)[1])
            expected = (b.ROOT/'datasets/violence/assets/C002.jpg').read_bytes()
            self.assertEqual(data, expected)
            self.assertEqual(b.summarize(output)['outcome_counts'], {'fal': {'image_returned': 1}})


class ModelRequestTests(unittest.TestCase):
    def test_each_model_routes_both_modes_and_preserves_inputs_and_controls(self):
        assets = {'R01': {'data': PNG, 'mime_type': 'image/png', 'public_url': PINNED_URL}}
        auth = {'secret': 'local-test', 'project': 'example-project'}
        for model, (family, fal_endpoint) in MODELS.items():
            profile = b.load_profile(model)
            for edit in (False, True):
                case = sample_case() if edit else {**sample_case(), 'mode': 'text_to_image', 'reference_asset_ids': []}
                with self.subTest(model=model, edit=edit):
                    requests = {provider: b.build_request(provider, profile, case, assets, auth) for provider in b.PROVIDERS}
                    seg_url, _, seg, requested = requests['segmind']
                    self.assertEqual(seg_url, 'https://api.segmind.com/v2/'+model)
                    self.assertEqual(requested, model)
                    self.assertEqual(seg['image_urls'], [PINNED_URL] if edit else [])
                    fal_url, _, fal, requested = requests['fal']
                    self.assertEqual(requested, fal_endpoint+('/edit' if edit else ''))
                    self.assertEqual(fal_url, 'https://queue.fal.run/'+requested)
                    self.assertEqual(fal['num_images'], 1)
                    if edit:
                        self.assertEqual(base64.b64decode(fal['image_urls'][0].split(',', 1)[1]), PNG)
                    else:
                        self.assertNotIn('image_urls', fal)
                    vertex_url, _, vertex, requested = requests['vertex']
                    self.assertEqual(requested, family)
                    self.assertTrue(vertex_url.endswith('/models/'+family+':generateContent'))
                    parts = vertex['contents'][0]['parts']
                    self.assertEqual(len(parts), 2 if edit else 1)
                    if edit:
                        self.assertEqual(base64.b64decode(parts[1]['inlineData']['data']), PNG)
                    self.assertEqual(seg['prompt'], case['prompt'])
                    self.assertEqual(fal['prompt'], case['prompt'])
                    self.assertEqual(parts[0]['text'], case['prompt'])
                    image_config = vertex['generationConfig']['imageConfig']
                    if model == 'nano-banana':
                        self.assertNotIn('output_resolution', seg)
                        self.assertNotIn('resolution', fal)
                        self.assertNotIn('imageSize', image_config)
                        self.assertNotIn('output_format', seg)
                    else:
                        self.assertEqual(seg['output_resolution'], '1K')
                        self.assertEqual(seg['output_format'], 'png')
                        self.assertEqual(image_config['imageSize'], '1K')
                        if model == 'nano-banana-2-lite':
                            self.assertNotIn('resolution', fal)
                        else:
                            self.assertEqual(fal['resolution'], '1K')
                    for body in (seg, fal, vertex):
                        self.assertNotIn('safety_tolerance', body)
                        self.assertNotIn('safetySettings', body)
                        self.assertNotIn('seed', body)
                        self.assertNotIn('system_prompt', body)


if __name__ == '__main__':
    unittest.main()
