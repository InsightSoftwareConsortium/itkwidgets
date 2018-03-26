var extension = require('./index');
var base = require('@jupyter-widgets/base');

/**
 * Register the widget.
 */
module.exports = {
  id: 'itk-jupyter-widgets',
  requires: [base.IJupyterWidgetRegistry],
  activate: function(app, widgets) {
      widgets.registerWidget({
          name: 'itk-jupyter-widgets',
          version: extension.version,
          exports: extension
      });
    },
  autoStart: true
};
