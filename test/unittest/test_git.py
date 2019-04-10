# Copyright 2013-2014 Sebastian Kreft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import subprocess
import unittest

import mock

import gitlint.git as git

# pylint: disable=too-many-public-methods


class GitTest(unittest.TestCase):
    @mock.patch('subprocess.check_output', return_value=b'/home/user/repo\n')
    def test_repository_root_ok(self, check_output):
        self.assertEqual('/home/user/repo', git.repository_root())
        check_output.assert_called_once_with(
            ['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.STDOUT)

    @mock.patch('subprocess.check_output')
    def test_repository_root_error(self, check_output):
        check_output.side_effect = subprocess.CalledProcessError(1, '', '')
        self.assertEqual(None, git.repository_root())

    @mock.patch('subprocess.check_output')
    def test_modified_files(self, check_output):
        check_output.return_value = os.linesep.join([
            'A  docs/file1.txt', 'M  data/file2.json', 'D  file3.py',
            '?? file4.js', 'AM file5.txt', 'MM file6.txt'
        ]).encode('utf-8')

        self.assertEqual({
            '/home/user/repo/docs/file1.txt': 'A ',
            '/home/user/repo/data/file2.json': 'M ',
            '/home/user/repo/file4.js': '??',
            '/home/user/repo/file5.txt': 'AM',
            '/home/user/repo/file6.txt': 'MM',
        }, git.modified_files('/home/user/repo'))
        check_output.assert_called_once_with([
            'git', 'status', '--porcelain', '--untracked-files=all',
            '--ignore-submodules=all'
        ])

    @mock.patch('subprocess.check_output')
    def test_modified_files_tracked_only(self, check_output):
        check_output.return_value = os.linesep.join([
            'A  docs/file1.txt', 'M  data/file2.json', 'D  file3.py',
            '?? file4.js', 'AM file5.txt'
        ]).encode('utf-8')

        self.assertEqual({
            '/home/user/repo/docs/file1.txt': 'A ',
            '/home/user/repo/data/file2.json': 'M ',
            '/home/user/repo/file5.txt': 'AM'
        }, git.modified_files('/home/user/repo', tracked_only=True))
        check_output.assert_called_once_with([
            'git', 'status', '--porcelain', '--untracked-files=all',
            '--ignore-submodules=all'
        ])

    @mock.patch('subprocess.check_output')
    def test_modified_files_with_spaces(self, check_output):
        check_output.return_value = os.linesep.join(
            ['A  "docs/file 1.txt"', 'M  "data/file 2.json"']).encode('utf-8')

        self.assertEqual({
            '/home/user/repo/docs/file 1.txt': 'A ',
            '/home/user/repo/data/file 2.json': 'M '
        }, git.modified_files('/home/user/repo'))
        check_output.assert_called_once_with([
            'git', 'status', '--porcelain', '--untracked-files=all',
            '--ignore-submodules=all'
        ])

    @mock.patch('subprocess.check_output', return_value=b'')
    def test_modified_files_nothing_changed(self, check_output):
        self.assertEqual({}, git.modified_files('/home/user/repo'))
        check_output.assert_called_once_with([
            'git', 'status', '--porcelain', '--untracked-files=all',
            '--ignore-submodules=all'
        ])

    @mock.patch('subprocess.check_output')
    def test_modified_files_with_commit(self, check_output):
        check_output.return_value = os.linesep.join([
            'M\ttest/e2etest/data/bash/error.sh',
            'D\ttest/e2etest/data/ruby/error.rb',
            'A\ttest/e2etest/data/rubylint/error.rb',
            '',
        ]).encode('utf-8')
        commit = '0a' * 20

        self.assertEqual(
            {
                '/home/user/repo/test/e2etest/data/bash/error.sh': 'M ',
                '/home/user/repo/test/e2etest/data/rubylint/error.rb': 'A ',
            }, git.modified_files('/home/user/repo', commit=commit))
        check_output.assert_called_once_with([
            'git', 'diff-tree', '-r', '--root', '--no-commit-id',
            '--name-status', commit
        ])

    def test_modified_files_non_absolute_root(self):
        with self.assertRaises(AssertionError):
            git.modified_files('foo/bar')

    @mock.patch('subprocess.check_output')
    def test_modified_lines(self, check_output):
        check_output.return_value = os.linesep.join([
            'baz', '0000000000000000000000000000000000000000 2 2 4', 'foo',
            '0000000000000000000000000000000000000000 5 5', 'bar'
        ]).encode('utf-8')

        self.assertEqual([2, 5],
                         list(
                             git.modified_lines('/home/user/repo/foo/bar.txt',
                                                ' M')))
        self.assertEqual([2, 5],
                         list(
                             git.modified_lines('/home/user/repo/foo/bar.txt',
                                                'M ')))
        self.assertEqual([2, 5],
                         list(
                             git.modified_lines('/home/user/repo/foo/bar.txt',
                                                'MM')))
        expected_calls = [
            mock.call(
                ['git', 'blame', '--porcelain', '/home/user/repo/foo/bar.txt'])
        ] * 3
        self.assertEqual(expected_calls, check_output.call_args_list)

    @mock.patch('subprocess.check_output')
    def test_modified_lines_with_commit(self, check_output):
        check_output.return_value = os.linesep.join([
            'baz', '0123456789abcdef31410123456789abcdef3141 2 2 4', 'foo',
            '0123456789abcdef31410123456789abcdef3141 5 5', 'bar'
        ]).encode('utf-8')

        self.assertEqual(
            [2, 5],
            list(
                git.modified_lines(
                    '/home/user/repo/foo/bar.txt',
                    ' M',
                    commit='0123456789abcdef31410123456789abcdef3141')))
        self.assertEqual(
            [2, 5],
            list(
                git.modified_lines(
                    '/home/user/repo/foo/bar.txt',
                    'M ',
                    commit='0123456789abcdef31410123456789abcdef3141')))
        self.assertEqual(
            [2, 5],
            list(
                git.modified_lines(
                    '/home/user/repo/foo/bar.txt',
                    'MM',
                    commit='0123456789abcdef31410123456789abcdef3141')))
        expected_calls = [
            mock.call(
                ['git', 'blame', '--porcelain', '/home/user/repo/foo/bar.txt'])
        ] * 3
        self.assertEqual(expected_calls, check_output.call_args_list)

    def test_modified_lines_new_addition(self):
        self.assertEqual(
            None, git.modified_lines('/home/user/repo/foo/bar.txt', 'A '))

    def test_modified_lines_untracked(self):
        self.assertEqual(
            None, git.modified_lines('/home/user/repo/foo/bar.txt', '??'))

    def test_modified_lines_no_info(self):
        self.assertEqual([],
                         list(
                             git.modified_lines('/home/user/repo/foo/bar.txt',
                                                None)))

    @mock.patch('subprocess.check_output', return_value=b'0a' * 20 + b'\n')
    def test_last_commit(self, check_output):
        self.assertEqual('0a' * 20, git.last_commit())
        check_output.assert_called_once_with(
            ['git', 'rev-parse', 'HEAD'], stderr=subprocess.STDOUT)

    @mock.patch('subprocess.check_output')
    def test_last_commit_not_in_repo(self, check_output):
        check_output.side_effect = subprocess.CalledProcessError(255, '', '')
        self.assertEqual(None, git.last_commit())
