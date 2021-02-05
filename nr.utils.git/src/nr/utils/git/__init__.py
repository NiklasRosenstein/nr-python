# -*- coding: utf8 -*-
# Copyright (c) 2020 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import collections
import os
import subprocess as sp
import typing as t

__author__ = 'Niklas Rosenstein <rosensteinniklas@gmail.com>'
__version__ = '0.3.0'

Branch = collections.namedtuple('Branch', 'name,current')
FileStatus = collections.namedtuple('FileStatus', 'mode,filename')
RefWithSha = collections.namedtuple('RefWithSha', 'ref,sha')


class Git:

  def __init__(self, cwd: str = None):
    self.cwd = cwd or os.getcwd()

  def check_call(self, command: t.List[str], stdout: t.Optional[int] = None) -> None:
    sp.check_call(command, cwd=self.cwd, stdout=stdout)

  def check_output(self, command: t.List[str], stderr: t.Optional[int] = None) -> bytes:
    return sp.check_output(command, cwd=self.cwd, stderr=stderr)

  def init(self) -> None:
    self.check_call(['git', 'init', '.'])

  def clone(
      self,
      clone_url: str,
      branch: str = None,
      depth: int = None,
      recursive: bool = False,
      username: str = None,
      password: str = None,
      quiet: bool = False,
  ) -> None:
    """
    Clone a Git repository to the *to_directory* from *clone_url*. If a relative path is
    specified in *to_directory*, it will be treated relative to the #Git.cwd path.
    """

    if password or username:
      if not clone_url.startswith('https://'):
        raise ValueError('cannot specify username/password for non-HTTPS clone URL.')
      schema, remainder = clone_url.partition('://')[::2]
      auth = ':'.join(t.cast(t.List[str], filter(bool, [username, password])))
      clone_url = schema + '://' + auth + '@' + remainder

    command = ['git', 'clone', clone_url, self.cwd]
    if branch:
      command += ['-b', branch]
    if depth:
      command += ['--depth', str(depth)]
    if recursive:
      command += ['--recursive']
    if quiet:
      command += ['-q']

    sp.check_call(command)

  def add(self, files: t.List[str]) -> None:
    """
    Add files to the index.
    """

    command = ['git', 'add', '--'] + files
    self.check_call(command)

  def get_branches(self) -> t.List[Branch]:
    """
    Get the branches of the repository. Returns a list of #Branch objects.
    """

    command = ['git', 'branch']
    results = []
    for line in self.check_output(command).decode().splitlines():
      current = False
      if line.startswith('*'):
        line = line[1:]
        current = True
      results.append(Branch(line.strip(), current))

    return results

  def get_branch_names(self) -> t.List[str]:
    """
    Get the branch names.
    """

    return [x.name for x in self.get_branches()]

  def get_current_branch_name(self) -> str:
    """
    Return the name of the current branch.
    """

    for branch in self.get_branches():
      if branch.current:
        return branch.name

    raise RuntimeError('no curent branch ?')

  def get_remote_refs(self, remote: str) -> t.List[RefWithSha]:
    result = []
    command = ['git', 'ls-remote', '--heads', 'origin']
    for line in self.check_output(command).decode().splitlines():
      sha, ref = line.split()
      result.append(RefWithSha(ref, sha))
    return result

  def get_remote_branch_names(self, remote: str) -> t.List[str]:
    refs = self.get_remote_refs(remote)
    return [x.ref[11:] for x in refs if x.ref.startswith('refs/heads/')]

  def rename_branch(self, current: str, new: str) -> None:
    self.check_call(['git', 'branch', '-m', current, new])

  def push(self, remote: str, *refs, force: bool = False) -> None:
    """
    Push the specified *refs* to the Git remote.
    """

    command = ['git', 'push', remote] + list(refs)
    if force:
      command.insert(2, '-f')
    self.check_call(command)

  def pull(self, remote: str = None, branch: str = None, quiet: bool = False):
    """
    Pull from the specified Git remote.
    """

    command = ['git', 'pull']
    if remote and branch:
      command += [remote, branch]
    if quiet:
      command += ['-q']
    elif remote or branch:
      raise ValueError('remote and branch arguments can only be specified together')

    self.check_call(command)

  def porcelain(self) -> t.Iterable[FileStatus]:
    """
    Returns the file status for the working tree.
    """

    for line in self.check_output(['git', 'status', '--porcelain']).decode().splitlines():
      mode, filename = line.strip().partition(' ')[::2]
      yield FileStatus(mode, filename)

  def commit(self, message: str, allow_empty: bool = False) -> None:
    """
    Commit staged files to the repository.
    """

    command = ['git', 'commit', '-m', message]
    if allow_empty:
      command.append('--allow-empty')
    self.check_call(command)

  def tag(self, tag_name: str, force: bool = False) -> None:
    """
    Create a tag.
    """

    command = ['git', 'tag', tag_name] + (['-f'] if force else [])
    self.check_call(command)

  def rev_parse(self, rev: str) -> t.Optional[str]:
    """
    Parse a Git ref into a shasum.
    """

    command = ['git', 'rev-parse', rev]
    try:
      return self.check_output(command, stderr=sp.STDOUT).decode().strip()
    except sp.CalledProcessError:
      return None

  def rev_list(self, rev: str, path: str = None) -> t.List[str]:
    """
    Return a list of all Git revisions, optionally in the specified path.
    """

    command = ['git', 'rev-list', rev]
    if path:
      command += ['--', path]
    try:
      revlist = self.check_output(command, stderr=sp.STDOUT).decode().strip().split('\n')
    except sp.CalledProcessError:
      return []
    if revlist == ['']:
      revlist = []
    return revlist

  def has_diff(self) -> bool:
    """
    Returns #True if the repository has changed files.
    """

    try:
      self.check_call(['git', 'diff', '--exit-code'], stdout=sp.PIPE)
      return False
    except sp.CalledProcessError as exc:
      if exc.returncode == 1:
        return True
      raise

  def create_branch(self, name: str, orphan: bool = False) -> None:
    """
    Creates a branch.
    """

    command = ['git', 'checkout', '-b', name]
    if orphan:
      command += ['--orphan']
    self.check_call(command)

  def checkout(self, ref: str = None, files: t.List[str] = None, quiet: bool = False):
    """
    Check out the specified ref or files.
    """

    command = ['git', 'checkout']
    if ref:
      command += [ref]
    if quiet:
      command += ['-q']
    if files:
      command += ['--'] + files
    self.check_call(command)

  def reset(self, ref: str = None, files: t.List[str] = None, hard: bool = False, quiet: bool = False):
    """
    Reset to the specified ref or reset the files.
    """

    command = ['git', 'reset']
    if ref:
      command += [ref]
    if quiet:
      command += ['-q']
    if files:
      command += ['--'] + files
    self.check_call(command)

  def get_commit_message(self, rev: str) -> str:
    """
    Returns the commit message of the specified *rev*.
    """

    return self.check_output(['git', 'log', '-1', rev, '--pretty=%B']).decode()

  def get_diff(self, files: t.List[str] = None, cached: bool = False):
    command = ['git', '--no-pager', 'diff', '--color=never']
    if cached:
      command += ['--cached']
    if files is not None:
      command += ['--'] + files
    return self.check_output(command).decode()

  def describe(self,
    all: bool = False,
    tags: bool = False,
    contains: bool = False,
    commitish: t.Optional[str] = None,
  ) -> t.Optional[str]:

    command = ['git', 'describe']
    if all:
      command.append('--all')
    if tags:
      command.append('--tags')
    if contains:
      command.append('--contains')
    if commitish:
      command.append(commitish)

    try:
      return self.check_output(command, stderr=sp.DEVNULL).decode().strip()
    except FileNotFoundError:
      raise
    except sp.CalledProcessError:
      return None
