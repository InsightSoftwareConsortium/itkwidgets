# Advanced

## Returning Values

Communication with the IPython Kernel is asynchronous, which causes challenges with Python code blocks in Jupyter cells that run synchronously. Multiple comm messages cannot be awaited during the synchronous Python code block execution. With regards to ITKWidgets this means that getter functions do not "just work" - the Python code cannot complete until the comm message has resolved with the response and the message cannot resolve until the code has completed. This creates a deadlock that prevents the kernel from progressing. This has been a [documented issue for the Jupyter ipykernel](https://github.com/ipython/ipykernel/issues/65) for many years.

Libraries like [ipython_blocking](https://github.com/kafonek/ipython_blocking) and [jupyter-ui-poll](https://github.com/Kirill888/jupyter-ui-poll) have made efforts to address this issue and their approaches have been a great source of inspiration for the custom solution that we have chosen for ITKWidgets.

Our current solution prevents deadlocks but requires that getters be requested in one cell and resolved in another. For example:

```python
viewer = view(image)
```
```python
bg_color = viewer.get_background_color()
print(bg_color)
```
would simply become:

```python
viewer = view(image)
```
```python
bg_color = viewer.get_background_color()
```
```python
print(bg_color)
```
