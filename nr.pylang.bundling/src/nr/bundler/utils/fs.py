
import os
import nr.fs
import shutil

from . import gitignore


def copy_files_checked(src, dst, force=False, ignore=None):
  """
  Copies the contents of directory *src* into *dst* recursively. Files that
  already exist in *dst* will be timestamp-compared to avoid unnecessary
  copying, unless *force* is specified.

  If *ignore* is specified, it must be a #gitignore.IgnoreList instance.

  Returns the number the total number of files and the number of files
  copied.
  """

  if ignore:
    if not isinstance(ignore, (gitignore.IgnoreList, gitignore.IgnoreListCollection)):
      raise TypeError('ignore must be None, IgnoreList or IgnoreListCollection', type(ignore))
    def check(path, isdir):
      return not ignore.is_ignored(path, isdir)
  else:
    def check(path, isdir):
      return True

  total_files = 0
  copied_files = 0

  if os.path.isfile(src):
    if check(src, False):
      total_files += 1
      if force or nr.fs.compare_timestamp(src, dst):
        nr.fs.makedirs(os.path.dirname(dst))
        shutil.copyfile(src, dst)
        copied_files += 1
  else:
    for srcroot, dirs, files in os.walk(src):
      dstroot = os.path.join(dst, os.path.relpath(srcroot, src))
      for filename in files:
        srcfile = os.path.join(srcroot, filename)
        dstfile = os.path.join(dstroot, filename)

        if check(srcfile, False):
          total_files += 1
          if force or nr.fs.compare_timestamp(srcfile, dstfile):
            nr.fs.makedirs(dstroot)
            shutil.copyfile(srcfile, dstfile)
            copied_files += 1

  return total_files, copied_files
