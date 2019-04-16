# Changelog

### v1.2.0 (2019-04-16)

* Remove imports in `nr.bundler` root module
* Fix incorrect use of `nr.gitignore` in `bundle.py`
* Use `pkgutil` instead of `pkg_resources` namespace packages

### v1.1.0 (2019-04-16)

* Remove `nr.gitignore` dependency (vendor the module instead)
* Remove `requirements.txt`
* Update `setup.py` to install only the packages needed on the current OS
* Update `setup.py` to read version number from `src/nr/bundler/__init__.py`
* Update `MANIFEST.in`
* Add `name` member to `nr.bundler.utils.system` module

### v1.0.0 (2019-04-16)

* Initial release
