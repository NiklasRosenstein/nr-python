Monorepository for Python libraries under the `nr` namespace.

[![Build Status](https://drone.niklasrosenstein.com/api/badges/NiklasRosenstein/nr/status.svg)](https://drone.niklasrosenstein.com/NiklasRosenstein/nr)

__A note on versioning__:

All packages that are in `0.X.Y` version should assume that breaking changes are possible
between minor version releases. It is therefore highly recommended that dependencies to
0-major versions are bounded to the next minor version release, eg. `~0.1.2` (`>=0.1.2,<0.2.0`).
