"""The allocator's complete IDs must survive issue ownership and validation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import unittest

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / '.specify/extensions/github-issue-canon/scripts/issue_canon_common.py'
if not COMMON.exists():
    COMMON = Path(__file__).resolve().parents[1] / 'scripts/issue_canon_common.py'
spec = importlib.util.spec_from_file_location('canon_ids', COMMON)
sys.path.insert(0, str(COMMON.parent))
import normalize_issue_canon as normalize
canon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canon)


class CompleteIDTests(unittest.TestCase):
    def test_current_feature_keeps_complete_id_and_numeric_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.specify').mkdir()
            pointer = root / '.specify/feature.json'
            for feature in ('012', '999', '6788', '10000'):
                pointer.write_text(json.dumps({'branch': f'codex/{feature}-example'}))
                self.assertEqual(canon.current_feature(root), feature)
            pointer.unlink()
            for feature in ('999', '1000', '6788', '10000'):
                (root / 'specs' / f'{feature}-example').mkdir(parents=True)
            self.assertEqual(canon.current_feature(root), '10000')

    def test_normalizer_preserves_body_feature_and_long_task(self):
        title = normalize.canonical_title({'title': 'T1000: Исправить меню',
                                          'body': 'specs/6788-example/'}, '999')
        self.assertTrue(title.startswith('[6788]'))
        self.assertTrue(title.endswith('T1000: Исправить меню'))

    def test_long_ids_preserve_all_other_validation(self):
        for feature, task in (('012', 'T001'), ('6788', 'T1000')):
            issue = {
                'title': f'[{feature}][P1][macos] {task}: Проверить запись',
                'body': '\n\n'.join(canon.REQUIRED_SECTIONS) + f'\nSpec tasks: {task}',
                'labels': [{'name': name} for name in
                           (f'feature:{feature}', 'priority:P1', 'area:macos', 'type:bug')],
            }
            self.assertEqual(canon.validate_issue(issue), [])
            issue['labels'].append({'name': 'feature:678'})
            self.assertTrue(any('conflicting feature labels' in e for e in canon.validate_issue(issue)))
        self.assertIsNone(canon.TITLE_RE.match('[67][P1][macos] T001: Недопустимый номер'))


if __name__ == '__main__':
    unittest.main()
