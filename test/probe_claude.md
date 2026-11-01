# Probe results

## Model
Sonnet 5.5 (claude-sonnet-5-5), as stated in the session environment.

## `python3 --version`
```
Python 3.11.18
```

## `pip install emoji`
```
Downloading emoji-2.16.0-py3-none-any.whl (610 kB)
Installing collected packages: emoji
Successfully installed emoji-2.16.0
WARNING: Running pip as the 'root' user can result in broken permissions and conflicting behaviour with the system package manager.
```

## `python3 -c "import emoji;print(emoji.__version__)"`
Failed, even though pip reported success (pip likely belongs to a different interpreter than `python3`):
```
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'emoji'
```

## `git --version`
```
git version 2.43.0
```
