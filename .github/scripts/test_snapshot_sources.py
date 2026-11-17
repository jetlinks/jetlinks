import copy
import json
from pathlib import Path
import tempfile
import unittest

from snapshot_sources import BRANCH, MODULES, PARENT, reactor, resolve, verify_publication


class SourceContractTest(unittest.TestCase):
    def setUp(self):
        self.heads = {repo: str(i) * 40 for i, repo in enumerate(sorted({PARENT, *MODULES.values()}), 1)}
        self.calls = []
        self.status = 'ahead'

    def get(self, path):
        self.calls.append(path)
        if '/compare/' in path:
            return {'status': self.status}
        repo = path.removeprefix('repos/').split('/git/ref/')[0]
        return {'object': {'sha': self.heads[repo]}}

    def test_old_notification_selects_all_current_heads(self):
        old = 'a' * 40
        manifest = resolve('jetlinks/jetlinks-core', old, BRANCH, self.get)
        self.assertEqual(manifest['trigger']['sha'], old)
        self.assertEqual({m['repository']: m['sha'] for m in manifest['modules']},
                         {repo: sha for repo, sha in self.heads.items() if repo != PARENT})
        self.assertNotEqual(manifest['modules'][0]['sha'], old)
        self.assertEqual(len(self.calls), 5)

    def test_push_and_manual_refresh_use_same_current_source_rules(self):
        manual = resolve(get=self.get)
        pushed = resolve(PARENT, self.heads[PARENT], BRANCH, self.get)
        self.assertEqual(manual['parent'], pushed['parent'])
        self.assertEqual(manual['modules'], pushed['modules'])

    def test_invalid_source_cannot_query_or_publish(self):
        for repo, sha, ref in [('other/core', 'a'*40, BRANCH),
                               (PARENT, 'a'*40, '2.21'), (PARENT, '../master', BRANCH),
                               ('', 'a'*40, BRANCH), (PARENT, '', BRANCH)]:
            with self.subTest(repo=repo, sha=sha, ref=ref):
                with self.assertRaises(ValueError):
                    resolve(repo, sha, ref, self.get)
        self.assertEqual(self.calls, [])

    def test_unmerged_commit_cannot_publish(self):
        for status in ['behind', 'diverged']:
            self.status = status
            with self.assertRaises(ValueError):
                resolve('jetlinks/jetlinks-core', 'a'*40, BRANCH, self.get)


class ReactorContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.joinpath('pom.xml').write_text('<project><artifactId>jetlinks</artifactId><version>1.3.3-SNAPSHOT</version><modules><module>core</module></modules></project>')
        self.root.joinpath('core').mkdir()
        self.module = self.root/'core/pom.xml'
        self.module.write_text('<project><parent><artifactId>jetlinks</artifactId><version>1.3.3-SNAPSHOT</version></parent><artifactId>core</artifactId></project>')

    def test_only_declared_reactor_modules_are_validated(self):
        self.root.joinpath('example').mkdir()
        self.root.joinpath('example/pom.xml').write_text('not a reactor POM')
        self.assertEqual(reactor(self.root), {'version': '1.3.3-SNAPSHOT', 'artifacts': ['core', 'jetlinks']})

    def test_cross_release_parent_or_project_version_is_rejected(self):
        self.module.write_text(self.module.read_text().replace('1.3.3-SNAPSHOT', '2.21.0-SNAPSHOT'))
        with self.assertRaises(ValueError):
            reactor(self.root)
        self.root.joinpath('pom.xml').write_text('<project><artifactId>jetlinks</artifactId><version>2.21.0-SNAPSHOT</version></project>')
        with self.assertRaises(ValueError):
            reactor(self.root)

    def test_version_validation_follows_nested_modules(self):
        self.module.write_text(self.module.read_text().replace('</project>', '<modules><module>nested</module></modules></project>'))
        self.root.joinpath('core/nested').mkdir()
        self.root.joinpath('core/nested/pom.xml').write_text('<project><parent><artifactId>core</artifactId><version>2.21.0-SNAPSHOT</version></parent><artifactId>nested</artifactId></project>')
        with self.assertRaises(ValueError):
            reactor(self.root)

    def test_publication_requires_success_and_every_correct_coordinate(self):
        manifest = {'reactor': reactor(self.root)}
        log = self.root/'deploy.log'
        def upload(artifact, version='1.3.3-SNAPSHOT'):
            return f'Uploaded to snapshots: https://nexus.jetlinks.cn/snapshots/org/jetlinks/{artifact}/{version}/{artifact}.pom\n'
        for text in ['BUILD SUCCESS\n', 'BUILD SUCCESS\n'+upload('jetlinks'),
                     'BUILD SUCCESS\n'+upload('jetlinks')+upload('core', '2.21.0-SNAPSHOT'),
                     'BUILD FAILURE\n'+upload('jetlinks')+upload('core')]:
            log.write_text(text)
            with self.assertRaises(ValueError):
                verify_publication(copy.deepcopy(manifest), log)
        log.write_text('BUILD SUCCESS\n'+upload('jetlinks')+upload('core'))
        self.assertEqual(verify_publication(manifest, log)['publication']['status'], 'success')


if __name__ == '__main__':
    unittest.main()
