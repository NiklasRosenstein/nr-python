# Changelog

### v1.2.3 (2019-09-19)

* Upgrade dependency on `nr.types` to `>=3.0.2`

### v1.2.2 (2019-06-24)

* Add `nr/bundler/vendor/__init__.py` to fix normal installations of the
  package (not develop mode)

### v1.2.1 (2019-04-17)

* `ModuleGraph.collect_modules()` now sparsely collects _all_ parent packages
* The `DistributionBundle.fill_namespace_modules` option now writes the
  `pkgutil` namespace package clause into the generated file
* Add `DistributionBundler.exclude_stdlib`
* Add `DistributionBundler.exclude_in_path`
* Add `DistributionBundler.do_init_bundle()`
* Add `DistributionBundler.report_module_stats()`
* Add `ModuleInfo.excludes`
* Add `ModuleInfo.is_excluded`
* Add `ModuleInfo.exclude()`
* Add `ModuleInfo.is_namespace_pkg()`
* Add `ModuleInfo.get_core_dependencies()`
* Add `nr.bundler.utils.setup` module with `load_setup_configuration()` function

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
