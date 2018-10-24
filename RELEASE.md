- To release a new version of itkwidgets on PyPI:

```
export old_version=X.X.X
export version=X.X.Y

# Update itkwidgets/_version.py (set release version, replace 'dev' with 'final')
git grep -z --full-name -l '.' | xargs -0 sed -i -e "s/$old_version/$version/g"
git diff
pip install docutils
git add -- itkwidgets/ js/
git commit -m "ENH: Bump itk-jupyter-widgets to $version"
cd js && npm install && npm run build && cd -
python setup.py sdist
python setup.py bdist_wheel
pip install --upgrade twine
# Check the README for PyPI
twine check dist/*
twine upload dist/*
git tag -a -s v$version -m "itk-jupyter-widgets $version"
# Update _version.py (replace 'final' with 'dev' and increment minor)
git add -- itkwidgets/_version.py
git commit -m "ENH: Bump itk-jupyter-widgets version for development"
git push upstream master
git push upstream v$version
```

- To release a new version of itk-jupyter-widgets on NPM:

```
# clean out the `dist` and `node_modules` directories
git clean -fdx
cd js
npm install
npm run build
npm publish
cd ..
```
