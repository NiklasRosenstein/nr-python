local Pipeline(package) = {
  kind: "pipeline",
  type: "docker",
  name: "default",
  steps: [
    {
      "name": "test",
      "image": "python:3.7"
      "commands": [
        "bin/dev-install --no-develop --extras test $$package",
        "cd " + package,
        "pytest"
      ]
    }
  ]
};

Pipeline("nr.algo.graph")
Pipeline("nr.collections")
Pipeline("nr.commons.api")
Pipeline("nr.databind")
Pipeline("nr.fs")
Pipeline("nr.interface")
Pipeline("nr.metaclass")
Pipeline("nr.parsing.core")
Pipeline("nr.parsing.date")
Pipeline("nr.proxy")
Pipeline("nr.pylang.ast")
Pipeline("nr.pylang.utils")
Pipeline("nr.stream")
Pipeline("nr.sumtype")
Pipeline("nr.utils.ponyorm")
Pipeline("nr.utils.process")
