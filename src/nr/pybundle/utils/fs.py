
import os
import nr.fs
import shutil

def copy_files_checked(src, dst, force=False):
  """
  Copies the contents of directory *src* into *dst* recursively. Files that
  already exist in *dst* will be timestamp-compared to avoid unnecessary
  copying, unless *force* is specified.

  Returns the number the total number of files and the number of files
  copied.
  """

  total_files = 0
  copied_files = 0

  if os.path.isfile(src):
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

        total_files += 1
        if force or nr.fs.compare_timestamp(srcfile, dstfile):
          nr.fs.makedirs(dstroot)
          shutil.copyfile(srcfile, dstfile)
          copied_files += 1

  return total_files, copied_files

