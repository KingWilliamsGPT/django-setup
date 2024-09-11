## Searching...🔎

### Search everywhere
```bash
$ grep "Authentication credentials were not provided" --include="*.py" -r -i
env/lib/python3.10/site-packages/rest_framework/exceptions.py:    default_detail = _('Authentication credentials were not provided.')
```

### Exclude environment
```bash
$ grep "Authentication credentials were not provided" --include="*.py" --exclude-dir="env" -ir
```