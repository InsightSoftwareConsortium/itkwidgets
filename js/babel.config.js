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

  const plugins =  [
    ["@babel/plugin-transform-runtime", {
      "regenerator": true
    }],
    ["@babel/plugin-proposal-decorators", { "legacy": true }],
    ["@babel/plugin-proposal-class-properties", { "loose": true }]
  ]

  return {
    presets,
    plugins
  }
}
