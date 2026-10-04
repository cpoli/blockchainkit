# Course notebooks

These notebooks are generated from `examples/plot_*.py` by Sphinx-Gallery.
Read the history chapter alongside them. Every notebook has runnable code,
explanations, a figure, assertions, and an exercise.

```bash
python -m pip install -e ".[notebooks]"
jupyter lab notebooks
```

To regenerate after editing examples, build the Sphinx HTML documentation and
run `python scripts/sync_notebooks.py`. Run `python scripts/verify_notebooks.py`
to execute all notebooks in fresh kernels; executed copies go in
`build/executed-notebooks/`.

Follow `docs/source/course.rst` for the prerequisite order, rather than assuming
filename order is the beginner route. Worked answers are in
`docs/source/solutions.rst`. The final notebook follows one payment through
pending queues, a fork, reorganization, and reinclusion.
