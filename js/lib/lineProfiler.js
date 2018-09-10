const viewer = require('./viewer')
const  _ = require('lodash')
import vtkLineWidget from 'vtk.js/Sources/Interaction/Widgets/LineWidget'

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
  initialize_viewer: function() {
    const viewProxy = this.model.itkVtkViewer.getViewProxy()
    const lineWidget = vtkLineWidget.newInstance()
    this.model.lineWidget = lineWidget
    lineWidget.setInteractor(viewProxy.getInteractor())
    lineWidget.setEnabled(1);
    lineWidget.setWidgetStateToStart()
    console.log(viewProxy)
    console.log(lineWidget)
    const volumeRepresentation = viewProxy.getRepresentations()[0]
    const lineRepresentation = lineWidget.getWidgetRep();
    console.log(volumeRepresentation)
    function onInteractionEvent() {
      const mode = viewProxy.getViewMode()
      switch (mode) {
      case 'XPlane':
        const line1Position = lineRepresentation.getPoint1WorldPosition()
        const line2Position = lineRepresentation.getPoint2WorldPosition()
        // Offset so it is visible
        const xPosition = volumeRepresentation.getXSlice() + 0.1 * volumeRepresentation.getPropertyDomainByName('xSlice').step
        if (line1Position[0] !== xPosition) {
          line1Position[0] = xPosition
          lineRepresentation.setPoint1WorldPosition(line1Position)
        }
        if (line2Position[0] !== xPosition) {
          line2Position[0] = xPosition
          lineRepresentation.setPoint2WorldPosition(line2Position)
        }
        console.log('XPlane')
        break;
      case 'YPlane':
        console.log('YPlane')
        break;
      case 'ZPlane':
        console.log('ZPlane')
        break;
      case 'VolumeRendering':
        console.log('VolumeRendering')
        break;
      default:
        vtkErrorMacro('Unexpected view mode');
      }
      console.log('InteractionEvent!')
      console.log(lineRepresentation.getPoint1DisplayPosition())
      console.log(lineRepresentation.getPoint1WorldPosition())
    }
    lineWidget.onInteractionEvent(onInteractionEvent)
    this.model.itkVtkViewer.subscribeViewModeChanged(onInteractionEvent)
  },

});


module.exports = {
  LineProfilerModel,
  LineProfilerView
};
