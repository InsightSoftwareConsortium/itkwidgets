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
    const volumeRepresentation = viewProxy.getRepresentations()[0]
    const lineRepresentation = lineWidget.getWidgetRep();
    function onInteractionEvent() {
      const mode = viewProxy.getViewMode()
      const line1Position = lineRepresentation.getPoint1WorldPosition()
      const line2Position = lineRepresentation.getPoint2WorldPosition()
      switch (mode) {
      case 'XPlane':
        // Offset so it is visible
        const xPosition = volumeRepresentation.getXSlice() + 0.0 * volumeRepresentation.getPropertyDomainByName('xSlice').step
        if (line1Position[0] !== xPosition) {
          line1Position[0] = xPosition
          lineRepresentation.setPoint1WorldPosition(line1Position)
        }
        if (line2Position[0] !== xPosition) {
          line2Position[0] = xPosition
          lineRepresentation.setPoint2WorldPosition(line2Position)
        }
        break;
      case 'YPlane':
        const yPosition = volumeRepresentation.getYSlice() + 0.0 * volumeRepresentation.getPropertyDomainByName('ySlice').step
        if (line1Position[1] !== yPosition) {
          line1Position[1] = yPosition
          lineRepresentation.setPoint1WorldPosition(line1Position)
        }
        if (line2Position[1] !== yPosition) {
          line2Position[1] = yPosition
          lineRepresentation.setPoint2WorldPosition(line2Position)
        }
        break;
      case 'ZPlane':
        const zPosition = volumeRepresentation.getZSlice() + 0.0 * volumeRepresentation.getPropertyDomainByName('zSlice').step
        if (line1Position[2] !== zPosition) {
          line1Position[2] = zPosition
          lineRepresentation.setPoint1WorldPosition(line1Position)
        }
        if (line2Position[2] !== zPosition) {
          line2Position[2] = zPosition
          lineRepresentation.setPoint2WorldPosition(line2Position)
        }
        break;
      case 'VolumeRendering':
        break;
      default:
        vtkErrorMacro('Unexpected view mode');
      }
      console.log('InteractionEvent!')
      console.log(lineRepresentation.getPoint1WorldPosition())
    }
    lineWidget.onInteractionEvent(onInteractionEvent)
    this.model.itkVtkViewer.subscribeViewModeChanged(onInteractionEvent)
    this.model.itkVtkViewer.subscribeXSliceChanged(onInteractionEvent)
    this.model.itkVtkViewer.subscribeYSliceChanged(onInteractionEvent)
    this.model.itkVtkViewer.subscribeZSliceChanged(onInteractionEvent)
  },

});


module.exports = {
  LineProfilerModel,
  LineProfilerView
};
