#!/bin/bash

status=0
failed_packages=

for package in `echo $PACKAGES`; do
  echo -e "\n\n\033[36;mTesting $package ...\n-----------------------------------------------\033[0;m\n\n"
  if [[ "$IGNORE_PACKAGES" =~ *$package*~ ]]; then
    echo "Skipped."
    continue
  fi
  rm -rf .venv; $VIRTUALENV .venv --system-site-packages
  . .venv/bin/activate
  bin/dev-install $package --no-develop --extras test --quiet
  .venv/bin/python -m pytest $package && rc=$? || rc=$?
  if [ $rc != 0 ]; then
    status=1
    failed_packages="$failed_packages $package"
  fi
  deactivate
done

if [ $status != 0 ]; then
  echo -e "\n\nThe following packages failed their tests: $failed_packages\n\n"
  exit $status
fi
