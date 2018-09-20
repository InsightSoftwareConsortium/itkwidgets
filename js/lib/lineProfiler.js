const viewer = require('./viewer')
const  _ = require('lodash')
import vtkLineWidget from 'vtk.js/Sources/Interaction/Widgets/LineWidget'
import macro from 'vtk.js/Sources/macro';

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
    lineWidget.setEnabled(1)
    lineWidget.setWidgetStateToStart()
    const volumeRepresentation = viewProxy.getRepresentations()[0]
    const lineRepresentation = lineWidget.getWidgetRep()
    const lineActor = lineRepresentation.getActors()[2]
    const lineMapper = lineActor.getMapper()
    const renderWindow = viewProxy.getRenderWindow()
    lineMapper.setRelativeCoincidentTopologyLineOffsetParameters(-4, -4)
    lineMapper.setResolveCoincidentTopology(true)
    function onInteractionEvent() {
      const mode = viewProxy.getViewMode()
      const point1Position = lineRepresentation.getPoint1WorldPosition()
      const point2Position = lineRepresentation.getPoint2WorldPosition()
      switch (mode) {
      case 'XPlane':
        // Offset so it is visible
        const xPosition = volumeRepresentation.getXSlice() + 0.0 * volumeRepresentation.getPropertyDomainByName('xSlice').step
        if (point1Position[0] !== xPosition) {
          point1Position[0] = xPosition
          lineRepresentation.setPoint1WorldPosition(point1Position)
        }
        if (point2Position[0] !== xPosition) {
          point2Position[0] = xPosition
          lineRepresentation.setPoint2WorldPosition(point2Position)
        }
        renderWindow.render()
        break;
      case 'YPlane':
        const yPosition = volumeRepresentation.getYSlice() + 0.0 * volumeRepresentation.getPropertyDomainByName('ySlice').step
        if (point1Position[1] !== yPosition) {
          point1Position[1] = yPosition
          lineRepresentation.setPoint1WorldPosition(point1Position)
        }
        if (point2Position[1] !== yPosition) {
          point2Position[1] = yPosition
          lineRepresentation.setPoint2WorldPosition(point2Position)
        }
        renderWindow.render()
        break;
      case 'ZPlane':
        const zPosition = volumeRepresentation.getZSlice() + 0.0 * volumeRepresentation.getPropertyDomainByName('zSlice').step
        if (point1Position[2] !== zPosition) {
          point1Position[2] = zPosition
          lineRepresentation.setPoint1WorldPosition(point1Position)
        }
        if (point2Position[2] !== zPosition) {
          point2Position[2] = zPosition
          lineRepresentation.setPoint2WorldPosition(point2Position)
        }
        renderWindow.render()
        break;
      case 'VolumeRendering':
        break;
      default:
        vtkErrorMacro('Unexpected view mode');
      }
      console.log('InteractionEvent!')
      console.log(lineRepresentation.getPoint1WorldPosition())
    }
    const debouncedOnInteractionEvent = macro.debounce(onInteractionEvent, 200);
    lineWidget.onInteractionEvent(debouncedOnInteractionEvent)
    this.model.itkVtkViewer.subscribeViewModeChanged(debouncedOnInteractionEvent)
    this.model.itkVtkViewer.subscribeXSliceChanged(debouncedOnInteractionEvent)
    this.model.itkVtkViewer.subscribeYSliceChanged(debouncedOnInteractionEvent)
    this.model.itkVtkViewer.subscribeZSliceChanged(debouncedOnInteractionEvent)
  },

});


module.exports = {
  LineProfilerModel,
  LineProfilerView
};
