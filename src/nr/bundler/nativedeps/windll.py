# Copyright (c) 2018 Niklas Rosenstein
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

try:
  from urllib.request import urlopen
except ImportError:
  from urllib2 import urlopen

from six import PY3
from ..utils import system

import appdirs
import functools
import hashlib
import logging
import io
import json
import nr.fs
import os
import pefile
import shutil
import subprocess
import sys
import tempfile
import zipfile
from ._base import Dependency


logger = logging.getLogger(__name__)

_known_dlls = [
  # https://windowssucks.wordpress.com/knowndlls/
  'wow64.dll',
  'wow64cpu.dll',
  'wow64win.dll',
  'wowarmhw.dll',
  'advapi32.dll',
  'clbcatq.dll',
  'combase.dll',
  'COMDLG32.dll',
  'coml2.dll',
  'difxapi.dll',
  'gdi32.dll',
  'gdiplus.dll',
  'IMAGEHLP.dll',
  'IMM32.dll',
  'kernel32.dll',
  'MSCTF.dll',
  'MSVCRT.dll',
  'NORMALIZ.dll',
  'NSI.dll',
  'ole32.dll',
  'OLEAUT32.dll',
  'PSAPI.DLL',
  'rpcrt4.dll',
  'sechost.dll',
  'Setupapi.dll',
  'SHCORE.dll',
  'SHELL32.dll',
  'SHLWAPI.dll',
  'user32.dll',
  'WLDAP32.dll',
  'WS2_32.dll',
 	'kernelbase.dll',
  'IMAGEHLP.dll',
  'gdi32.dll',
  'NORMALIZ.dll',
  'combase.dll',
  'ole32.dll',
  'kernel.appcore.dll',
  'cfgmgr32.dll',
  'WLDAP32.dll',
  'SHELL32.dll',
  'gdiplus.dll',
  'coml2.dll',
  'FLTLIB.DLL',
  'win32u.dll',
  'profapi.dll',
  'user32.dll',
  'MSASN1.dll',
  'powrprof.dll',
  'gdi32full.dll',
  'COMCTL32.dll',
  'CRYPT32.dll',
  'PSAPI.DLL',
  'SHCORE.dll',
  'bcryptPrimitives.dll',
  'OLEAUT32.dll',
  'advapi32.dll',
  'ntdll.dll',
  'SHLWAPI.dll',
  'msvcp_win.dll',
  'WS2_32.dll',
  'sechost.dll',
  'COMDLG32.dll',
  'difxapi.dll',
  'Setupapi.dll',
  'MSCTF.dll',
  'WINTRUST.dll',
  'IMM32.dll',
  'windows.storage.dll',
  'MSVCRT.dll',
  'clbcatq.dll',
  'rpcrt4.dll',
  'kernel32.dll',
  'NSI.dll',
  'ucrtbase.dll',  # TODO: Node packages contain this dll

  # Some manually added things
  'aclui.dll',
  'activeds.dll',
  'adsldpc.dll',
  'apphelp.dll',
  'authz.dll',
  'bcrypt.dll',
  'combase.dll',
  'devmgr.dll',
  'dbgeng.dll',
  'dbghelp.dll',
  'dcomp.dll',
  'dnsapi.dll',
  'dsparse.dll',
  'dhcpcsvc.dll',
  'dsreg.dll',
  'dwmapi.dll',
  'EDPUTIL.dll',
  'fontsub.dll',
  'FIREWALLAPI.dll',
  'gdi32.dll',
  'hid.dll',
  'IPHLPAPI.dll',
  'logoncli.dll',
  'mpr.dll',
  'mshtml.dll',
  'ncrypt.dll',
  'ntasn1.dll',
  'netutils.dll',
  'netapi32.dll',
  'propsys.dll',
  'SCECLI.dll',
  'secur32.dll',
  'SETUPAPI.dll',
  'srvcli.dll',
  'SHLWAPI.dll',
  'srpapi.dll',
  'urlmon.dll',
  'userenv.dll',
  'uxtheme.dll',
  'version.dll',
  'webio.dll',
  'winhttp.dll',
  'wintrust.dll',
  'wininet.dll',
  'wer.dll',
  'WEVTAPI.dll',
  'WLDAP32.dll',
  'wkscli.dll',
  'wpaxholder.dll',
  'winspool.drv',
  'WINMMBASE.dll',
  'winmm.dll',

  'usp10.dll',
  'd3d9.dll',
  'd3d10.dll',
  'd3d11.dll',
  'DWrite.dll',
  'dxgi.dll',
  'dxva2.dll',
]
_known_dlls = set(x.lower() for x in _known_dlls)


def is_binary(filename):
  return filename.endswith('.exe') or filename.endswith('.dll')


def get_dependencies(filename, exclude_system_deps=False):
  pe = pefile.PE(filename, fast_load=True)
  pe.parse_data_directories(
    directories=[
      pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
      pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT'],
    ],
    forwarded_exports_only=True,
    import_dllnames_only=True,
  )

  def convert_dll_name_to_str(dll_name):
    if PY3 and isinstance(dll_name, bytes):
      dll_name = dll_name.decode('utf8')
    return dll_name

  dlls = set()

  # Some libraries have no other binary dependencies. Use empty list
  # in that case. Otherwise pefile would return None.
  # e.g. C:\windows\system32\kernel32.dll on Wine
  for entry in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []):
    dll_str = convert_dll_name_to_str(entry.dll)
    dlls.add(dll_str)

  # We must also read the exports table to find forwarded symbols:
  # http://blogs.msdn.com/b/oldnewthing/archive/2006/07/19/671238.aspx
  export_symbols = getattr(pe, 'DIRECTORY_ENTRY_EXPORT', None)
  if export_symbols:
    for sym in export_symbols.symbols:
      if sym.forwarder is not None:
        # sym.forwarder is a bytes object. Convert it to a string.
        forwarder = convert_dll_name_to_str(sym.forwarder)
        # sym.forwarder is for example 'KERNEL32.EnterCriticalSection'
        dll, _ = forwarder.split('.')
        dlls.add(dll + ".dll")

  pe.close()

  if exclude_system_deps:
    dlls = set(x for x in dlls if x.lower() not in _known_dlls)

  return [Dependency(x) for x in dlls]


def resolve_dependency(dep, search_path=None):
  """
  Attempts to find the #Dependency on the system. Returns the filename of the
  native library or None if it can not be found and also assigns it to the
  passed #Dependency object.
  """

  if not dep.filename:
    dep.filename = system.find_in_path(dep.name, search_path, common_ext=False)
    if dep.filename:
      dep.filename = nr.fs.fixcase(dep.filename)
  return dep.filename
