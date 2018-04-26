let prefix = document.querySelector('body').getAttribute('data-base-url') + 'nbextensions/itk-jupyter-widgets/'
if(__webpack_public_path__) {
  prefix = __webpack_public_path__
}
const itkConfig = {
  itkModulesPath: prefix + 'itk'
}

module.exports = itkConfig
