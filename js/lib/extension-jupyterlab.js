var extension = require('./index');
var base = require('@jupyter-widgets/base');

/**
 * Register the widget.
 */
module.exports = {
  id: 'itkwidgets',
  requires: [base.IJupyterWidgetRegistry],
  activate: function(app, widgets) {
      widgets.registerWidget({
          name: 'itkwidgets',
          version: extension.version,
          exports: extension
      });
    },
  autoStart: true
};
