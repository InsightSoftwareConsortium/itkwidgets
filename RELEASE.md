- To release a new version of itkwidgets on PyPI:

export old_version=X.X.X
export version=X.X.Y

# Update _version.py (set release version, remove 'dev')
git sed "s/$old_version/$version/g"
git add -- itkwidgets/_version.py
git commit -m "ENH: Bump itk-jupyter-widgets to $version"
python setup.py sdist upload
python setup.py bdist_wheel upload
git tag -a v$version -m "itk-jupyter-widgets $version"
# Update _version.py (add 'dev' and increment minor)
git add -- itkwidgets/_version.py
git commit -m "ENH: Bump itk-jupyter-widgets version for development"
git push
git push --tags


- To release a new version of itk-jupyter-widgets on NPM:

```
# clean out the `dist` and `node_modules` directories
git clean -fdx
npm install
npm publish
```
