this is a python runtime implementation of NAPI. based on https://github.com/toyobayashi/emnapi and converted to python

emanapi is cloned locally into ./emnapi to let you read and search the files easily without webfetch

IMPORTANT! every time you are about to implement a new function for NAPI first read the emnapi one, in full and in detail. so you can port it to python or native code, you MUST do this to keep the implementation sane, using an existing example that we know to work instead of inventing new code.

read README to understand better the goal.

read ./IMPLEMENTATION_PLAN.md to understand how it was made.

some files inside tests are written in python and can be used to validate changes to NAPI.

if you skip code when adding the NAPI code mark these lines with TODO comments so it is easy to spot these places in the future

for all cases in python where we handle exception with `except Exception:` where you ignore the error always add a print and not only `pass`. this way we do not miss important context in logs.
