var path = require('path');
var version = require('./package.json').version;

const CopyPlugin = require('copy-webpack-plugin');
const nodeExternals = require('webpack-node-externals');
const WebPackBar = require('webpackbar');

const vtkRules = require('vtk.js/Utilities/config/dependency.js').webpack.core.rules;
const cssRules = require('vtk.js/Utilities/config/dependency.js').webpack.css.rules;

// Custom webpack rules are generally the same for all webpack bundles, hence
// stored in a separate local variable.
var rules = [
  // itk-vtk-viewer
  {
    test: /\.svg$/,
    use: [{ loader: 'raw-loader' }],
  },
  // itk-vtk-viewer
  {
    test: /\.(png|jpg)$/,
    use: 'url-loader?limit=81920'
  },
  {
    test: /\.js$/,
    use: {
      loader: 'babel-loader'
    },
  },
].concat(vtkRules, cssRules);

const resolve = {
  modules: [path.resolve(__dirname, 'node_modules')],
  alias: {
    './itkConfig$': path.resolve(__dirname, 'lib', 'itkConfigJupyter.js'),
  },
};

const maxAssetSize = 2000000;
const performance = {
  maxAssetSize: maxAssetSize,
  maxEntrypointSize: maxAssetSize,
};
const devServer = {
  noInfo: true,
  stats: 'minimal'
}

module.exports = [
  {
    // Notebook extension
    //
    // This bundle only contains the part of the JavaScript that is run on
    // load of the notebook. This section generally only performs
    // some configuration for requirejs, and provides the legacy
    // "load_ipython_extension" function which is required for any notebook
    // extension.
    //
    node: {
      fs: 'empty',
    },
    entry: './lib/extension.js',
    output: {
      filename: 'extension.js',
      path: path.resolve(__dirname, '..', 'itkwidgets', 'static'),
      libraryTarget: 'amd',
    },
    plugins: [
      new WebPackBar(),
    ],
    resolve,
    performance,
    devServer,
  },
  {
    // Bundle for the notebook containing the custom widget views and models
    //
    // This bundle contains the implementation for the custom widget views and
    // custom widget.
    // It must be an amd module
    //
    node: {
      fs: 'empty',
    },
    entry: './lib/index.js',
    output: {
      filename: 'index.js',
      path: path.resolve(__dirname, '..', 'itkwidgets', 'static'),
      libraryTarget: 'amd',
    },
    devtool: 'source-map',
    module: {
      rules: rules,
    },
    resolve,
    plugins: [
      new CopyPlugin([
        {
          from: path.join(
            __dirname,
            'node_modules',
            'itk',
            'WebWorkers',
            'Pipeline.worker.js'
          ),
          to: path.join(
            __dirname,
            '..',
            'itkwidgets',
            'static',
            'itk',
            'WebWorkers',
            'Pipeline.worker.js'
          ),
        },
        {
          from: path.join(
            __dirname,
            'lib',
            'ZstdDecompress',
            'web-build',
            'ZstdDecompress.js'
          ),
          to: path.join(
            __dirname,
            '..',
            'itkwidgets',
            'static',
            'itk',
            'Pipelines',
            'ZstdDecompress.js'
          ),
        },
        {
          from: path.join(
            __dirname,
            'lib',
            'ZstdDecompress',
            'web-build',
            'ZstdDecompressWasm.js'
          ),
          to: path.join(
            __dirname,
            '..',
            'itkwidgets',
            'static',
            'itk',
            'Pipelines',
            'ZstdDecompressWasm.js'
          ),
        },
      ]),
      new WebPackBar(),
    ],
    externals: ['@jupyter-widgets/base'],
    performance,
    devServer,
  },
  {
    // Embeddable itk-jupyter-widgets bundle
    //
    // This bundle is generally almost identical to the notebook bundle
    // containing the custom widget views and models.
    //
    // The only difference is in the configuration of the webpack public path
    // for the static assets.
    //
    // It will be automatically distributed by unpkg to work with the static
    // widget embedder.
    //
    // The target bundle is always `dist/index.js`, which is the path required
    // by the custom widget embedder.
    //
    node: {
      fs: 'empty',
    },
    entry: './lib/embed.js',
    output: {
      filename: 'index.js',
      path: path.resolve(__dirname, 'dist'),
      libraryTarget: 'amd',
      publicPath: 'https://unpkg.com/itk-jupyter-widgets@' + version + '/dist',
    },
    devtool: 'source-map',
    module: {
      rules: rules,
    },
    resolve: {
      modules: [path.resolve(__dirname, 'node_modules')],
      alias: {
        './itkConfig$': path.resolve(__dirname, 'lib', 'itkConfigCDN.js'),
      },
    },
    plugins: [
      new CopyPlugin([
        {
          from: path.join(
            __dirname,
            'node_modules',
            'itk',
            'WebWorkers',
            'Pipeline.worker.js'
          ),
          to: path.join(
            __dirname,
            'dist',
            'itk',
            'WebWorkers',
            'Pipeline.worker.js'
          ),
        },
        {
          from: path.join(
            __dirname,
            'lib',
            'ZstdDecompress',
            'web-build',
            'ZstdDecompress.js'
          ),
          to: path.join(
            __dirname,
            'dist',
            'itk',
            'Pipelines',
            'ZstdDecompress.js'
          ),
        },
        {
          from: path.join(
            __dirname,
            'lib',
            'ZstdDecompress',
            'web-build',
            'ZstdDecompressWasm.js'
          ),
          to: path.join(
            __dirname,
            'dist',
            'itk',
            'Pipelines',
            'ZstdDecompressWasm.js'
          ),
        },
      ]),
      new WebPackBar(),
    ],
    externals: ['@jupyter-widgets/base'],
    performance,
    devServer,
  },
  {
    // Bundle for JupyterLab
    //
    // This bundle externalizes dependencies so we can build with our webpack
    // rules.
    //
    node: {
      fs: 'empty',
    },
    entry: './lib/extension-jupyterlab.js',
    output: {
      filename: 'labextension.js',
      path: path.resolve(__dirname, 'dist'),
      libraryTarget: 'amd',
      publicPath: 'https://unpkg.com/itk-jupyter-widgets@' + version + '/dist',
    },
    devtool: 'source-map',
    module: {
      rules: rules,
    },
    resolve: {
      modules: [path.resolve(__dirname, 'node_modules')],
      alias: {
        './itkConfig$': path.resolve(__dirname, 'lib', 'itkConfigCDN.js'),
      },
    },
    plugins: [
      new WebPackBar(),
    ],
    externals: [
      nodeExternals({
        whitelist: [
          /^vtk.js[\/].*/,
          /^itk[\/].*/,
          /^itk-vtk-viewer[\/].*/,
        ],
      }),
    ],
    devServer,
  },
];
