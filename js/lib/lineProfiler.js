const viewer = require('./viewer')
const  _ = require('lodash')

const LineProfilerModel = viewer.ViewerModel.extend({
  defaults: function() {
    return _.extend(viewer.ViewerModel.prototype.defaults(), {
      _model_name: 'LineProfilerModel',
      _view_name: 'LineProfilerView',
      _model_module: 'itk-jupyter-widgets',
      _view_module: 'itk-jupyter-widgets',
      _model_module_version: '0.12.2',
      _view_module_version: '0.12.2',
    })
  }},
)


// Custom View. Renders the widget model.
const LineProfilerView = viewer.ViewerView.extend({
  render: function() {
    const viewerRender = viewer.ViewerView.prototype.render.bind(this)
    viewerRender()
  },
});


module.exports = {
  LineProfilerModel,
  LineProfilerView
};
