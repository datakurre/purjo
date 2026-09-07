## 1.0b8 (unreleased)


- Fix 'pur wrap' to exclude secrets.json, and stop copying it into the task sandbox
- Fix relative 'file' secrets paths to resolve against a directory package
- Fix a Fail keyword that never ran being reported as an explicit robot failure
- Fix 'pur operaton deploy --variables -' with multiple process definitions
- Fix 'pur serve' on Python 3.14


## 1.0b7 (2026-01-23)

- Add support for pythonpath configuration in robot_toml topics
- Fix unnecessary dependency on robotframework

## 1.0b6 (2025-12-11)

- Fix pur serve for directory to also apply .wrapignore

## 1.0b5 (2025-12-11)

- robot: Add Purjo.Get Output Variables to debug log Purjo log.html

## 1.0b4 (2025-12-11)

- Fix serve to apply .wrapignore
- robot: Add Purjo.Get Output Variables to log pur execution

## 1.0b3 (2025-12-10)

- Fix 'pur wrap' to not follow symlinks

## 1.0b2 (2025-12-07)

- Fix regression where pur(jo) itself  unintentionally dependend on robotframework

## 1.0b1 (2025-12-01)

- Add initial secrets support with file and vault adapters
- Add support for creating empty forms
- Change to init Python task with 'on-fail = "FAIL"'

## 1.0.0a26 (2025-09-15)

- Add option 'pur init --python'
- Add minimal support for python tasks with name=module.function
