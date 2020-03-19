local Pipeline(package, pyversion) = {
  kind: "pipeline",
  type: "docker",
  name: package + "-py" + pyversion,
  steps: [
    {
      "name": "test",
      "image": "python:" + pyversion,
      "commands": [
        "bin/dev-install --no-develop --extras test " + package,
        "pip install pytest",
        "cd " + package,
        "pytest --collect-only || if [ $? = 5 ]; then echo 'No tests found.'; exit 0; fi",
        "pytest"
      ]
    }
  ]
};

local NrPylangBundleTest(pyversion) = {
  kind: "pipeline",
  type: "docker",
  name: "nr.pylang.bundle-py" + pyversion + "-ete",
  steps: [
    {
      "name": "test",
      "image":
        if pyversion == "2.6" then "insynchq/python2.6"
        else "python:" + pyversion,
      "commands": [
        if pyversion == "2.6" then "curl https://bootstrap.pypa.io/2.6/get-pip.py -o - | PYTHONWARNINGS=ignore python -"
        else "echo void",
        "bin/dev-install --no-develop nr.pylang.bundle",
        "nr-pylang-bundle --pex bundle.pex --pex-console-script nr-pylang-bundle",
        "./bundle.pex --version",
        if (pyversion == "2.6" || pyversion == "2.7") then "pip install virtualenv && virtualenv .venv"
        else "python -m venv .venv",
        ".venv/bin/python bundle.pex --version",
      ]
    }
  ]
};

local ForPythonVersion(pyversion) = [
  Pipeline("nr.algo.graph", pyversion),
  Pipeline("nr.collections", pyversion),
  Pipeline("nr.commons.api", pyversion),
  Pipeline("nr.databind.core", pyversion),
  Pipeline("nr.databind.json", pyversion),
  Pipeline("nr.fs", pyversion),
  Pipeline("nr.interface", pyversion),
  Pipeline("nr.metaclass", pyversion),
  Pipeline("nr.parsing.core", pyversion),
  Pipeline("nr.parsing.date", pyversion),
  Pipeline("nr.proxy", pyversion),
  Pipeline("nr.pylang.ast", pyversion),
  Pipeline("nr.pylang.bundle", pyversion),
  NrPylangBundleTest(pyversion),
  Pipeline("nr.pylang.utils", pyversion),
  Pipeline("nr.stream", pyversion),
  Pipeline("nr.sumtype", pyversion),
  Pipeline("nr.utils.ponyorm", pyversion),
  Pipeline("nr.utils.process", pyversion)
];

[NrPylangBundleTest("2.6")] +
ForPythonVersion("2.7") +
ForPythonVersion("3.5") +
ForPythonVersion("3.6") +
ForPythonVersion("3.7") +
ForPythonVersion("3.8") +
ForPythonVersion("latest")
