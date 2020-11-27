
> Note: This package is in the dangerous land of `0.x.y` versions and may be subject to breaking
> changes with minor version increments.

# nr.utils.git

A simple wrapper around the Git CLI.

## Example

```py
from nr.utils.git import Git

repo = Git().clone('/Volumes/git/linux', 'https://github.com/torvalds/linux')
assert repo.get_current_branch_name()  == 'master'
print(repo.rev_parse('HEAD'))
```

---

<p align="center">Copyright &copy; 2020 Niklas Rosenstein</p>
