module.exports = function (api) {
  api.cache(true)
  const presets =  [
    ['@babel/preset-env', {
      targets: {
        browsers: ['last 2 versions'],
      },
      modules: 'commonjs',
    }],
    "mobx",
  ]
  const plugins = []

  return {
    presets,
    plugins
  }
}
