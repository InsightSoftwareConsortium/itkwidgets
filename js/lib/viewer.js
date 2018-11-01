import 'babel-polyfill'
const widgets = require('@jupyter-widgets/base')
const  _ = require('lodash')
import {
    fixed_shape_serialization
} from "jupyter-dataserializers"
import vtkITKHelper from 'vtk.js/Sources/Common/DataModel/ITKHelper'
import createViewer from 'itk-vtk-viewer/src/createViewer'
import IntTypes from 'itk/IntTypes'
import FloatTypes from 'itk/FloatTypes'
import IOTypes from 'itk/IOTypes'
import runPipelineBrowser from 'itk/runPipelineBrowser'

const serialize_itkimage = (itkimage) => {
  if (itkimage === null) {
    return null
  } else {
    itkimage.data = null
    return itkimage
  }
}

const deserialize_itkimage = (jsonitkimage) => {
  if (jsonitkimage === null) {
    return null
  } else {
    return jsonitkimage
  }
}

const ViewerModel = widgets.DOMWidgetModel.extend({
  defaults: function() {
    return _.extend(widgets.DOMWidgetModel.prototype.defaults(), {
      _model_name: 'ViewerModel',
      _view_name: 'ViewerView',
      _model_module: 'itk-jupyter-widgets',
      _view_module: 'itk-jupyter-widgets',
      _model_module_version: '0.14.0',
      _view_module_version: '0.14.0',
      rendered_image: null,
      _rendering_image: false,
      ui_collapsed: false,
      annotations: true,
      mode: 'v',
      interpolation: true,
      cmap: 'Viridis (matplotlib)',
      shadow: true,
      slicing_planes: false,
      gradient_opacity: 0.2,
      roi: new Float64Array([0., 0., 0., 0., 0., 0.]),
      _reset_crop_requested: false,
    })
  }}, {
  serializers: _.extend({
    rendered_image: { serialize: serialize_itkimage, deserialize: deserialize_itkimage },
    roi: fixed_shape_serialization([2, 3]),
  }, widgets.DOMWidgetModel.serializers)
})


const resetRenderingStatus = (domWidgetView) => {
  const viewProxy = domWidgetView.model.itkVtkViewer.getViewProxy()
  const representation = viewProxy.getRepresentations()[0];
  let unsubscriber = null
  const onLightingActivated = () => {
    // Why is this necessary?
    const shadow = domWidgetView.model.get('shadow')
    representation.setUseShadow(shadow);
    if (viewProxy.getViewMode() == 'VolumeRendering') {
      viewProxy.resetCamera()
    }
    domWidgetView.model.set('_rendering_image', false)
    domWidgetView.model.save_changes()
    if (unsubscriber) {
      unsubscriber.unsubscribe()
    }
  }
  const volumeMapper = representation.getMapper()
  unsubscriber = volumeMapper.onLightingActivated(onLightingActivated)
}


const createRenderingPipeline = (domWidgetView, rendered_image) => {
  const containerStyle = {
    position: 'relative',
    width: '100%',
    height: '600px',
    minHeight: '400px',
    minWidth: '400px',
    margin: '1',
    padding: '1',
    top: '0',
    left: '0',
    overflow: 'hidden',
    display: 'block-inline'
  };
  const viewerStyle = {
    backgroundColor: [1.0, 1.0, 1.0],
    containerStyle: containerStyle,
  };
  const imageData = vtkITKHelper.convertItkToVtkImage(rendered_image)
  const is3D = rendered_image.imageType.dimension === 3
  domWidgetView.model.use2D = !is3D
  if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
    resetRenderingStatus(domWidgetView)
    domWidgetView.model.itkVtkViewer.setImage(imageData)
  } else {
    domWidgetView.model.itkVtkViewer = createViewer(domWidgetView.el, {
      viewerStyle: viewerStyle,
      image: imageData,
      use2D: !is3D,
    })
    resetRenderingStatus(domWidgetView)
    const viewProxy = domWidgetView.model.itkVtkViewer.getViewProxy()
    const renderWindow = viewProxy.getRenderWindow()
    // Firefox requires calling .getContext on the canvas, which is
    // performed by .initialize()
    renderWindow.getViews()[0].initialize()
    const viewCanvas = renderWindow.getViews()[0].getCanvas()
    const stream  = viewCanvas.captureStream(30000./1001.)
    // Used by ipywebrtc
    domWidgetView.model.stream = Promise.resolve(stream)
    domWidgetView.initialize_viewer()
  }
  const dataArray = imageData.getPointData().getScalars()
  if (dataArray.getNumberOfComponents() > 1) {
    domWidgetView.model.itkVtkViewer.setColorMap('Grayscale')
    domWidgetView.model.set('cmap', 'Grayscale')
    domWidgetView.model.save_changes()
  }
}


// Custom View. Renders the widget model.
const ViewerView = widgets.DOMWidgetView.extend({
  render: function() {
    this.model.on('change:rendered_image', this.rendered_image_changed, this)
    this.model.on('change:ui_collapsed', this.ui_collapsed_changed, this)
    this.model.on('change:annotations', this.annotations_changed, this)
    this.model.on('change:mode', this.mode_changed, this)
    this.model.on('change:interpolation', this.interpolation_changed, this)
    this.model.on('change:cmap', this.cmap_changed, this)
    this.model.on('change:shadow', this.shadow_changed, this)
    this.model.on('change:slicing_planes', this.slicing_planes_changed, this)
    this.model.on('change:gradient_opacity', this.gradient_opacity_changed, this)
    this.rendered_image_changed().then(() => {
      this.annotations_changed()
      this.interpolation_changed()
      this.cmap_changed()
      this.mode_changed()
      this.shadow_changed()
      this.slicing_planes_changed()
      this.gradient_opacity_changed()
      this.ui_collapsed_changed()

      const onUserInterfaceCollapsedToggle = (collapsed) => {
        if (collapsed !== this.model.get('ui_collapsed')) {
          this.model.set('ui_collapsed', collapsed)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.subscribeToggleUserInterfaceCollapsed(onUserInterfaceCollapsedToggle)

      const onAnnotationsToggle = (enabled) => {
        if (enabled !== this.model.get('annotations')) {
          this.model.set('annotations', enabled)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.subscribeToggleAnnotations(onAnnotationsToggle)

      const onInterpolationToggle = (enabled) => {
        if (enabled !== this.model.get('interpolation')) {
          this.model.set('interpolation', enabled)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.subscribeToggleInterpolation(onInterpolationToggle)

      const onSelectColorMap = (colorMap) => {
        if (colorMap !== this.model.get('cmap')) {
          this.model.set('cmap', colorMap)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.subscribeSelectColorMap(onSelectColorMap)

      const onCroppingPlanesChanged = (planes, bboxCorners) => {
        if (!this.model.get('_rendering_image')) {
          this.model.set('roi',
              new Float64Array([bboxCorners[0][0], bboxCorners[0][1], bboxCorners[0][2], bboxCorners[7][0], bboxCorners[7][1], bboxCorners[7][2]]),
            )
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.subscribeCroppingPlanesChanged(onCroppingPlanesChanged)

      const onResetCrop = () => {
        this.model.set('_reset_crop_requested', true)
        this.model.save_changes()
      }
      this.model.itkVtkViewer.subscribeResetCrop(onResetCrop)

      if (!this.model.use2D) {
        const onViewModeChanged = (mode) => {
          let pythonMode = null;
          switch (mode) {
          case 'XPlane':
            pythonMode = 'x'
            break
          case 'YPlane':
            pythonMode = 'y'
            break
          case 'ZPlane':
            pythonMode = 'z'
            break
          case 'VolumeRendering':
            pythonMode = 'v'
            break
          default:
            throw new Error('Unknown view mode')
          }
          if (pythonMode !== this.model.get('mode')) {
            this.model.set('mode', pythonMode)
            this.model.save_changes()
          }
        }
        this.model.itkVtkViewer.subscribeViewModeChanged(onViewModeChanged)

        const onShadowToggle = (enabled) => {
          if (enabled !== this.model.get('shadow')) {
            this.model.set('shadow', enabled)
            this.model.save_changes()
          }
        }
        this.model.itkVtkViewer.subscribeToggleShadow(onShadowToggle)

        const onSlicingPlanesToggle = (enabled) => {
          if (enabled !== this.model.get('slicing_planes')) {
            this.model.set('slicing_planes', enabled)
            this.model.save_changes()
          }
        }
        this.model.itkVtkViewer.subscribeToggleSlicingPlanes(onSlicingPlanesToggle)

        const onGradientOpacityChange = (opacity) => {
          if (opacity !== this.model.get('gradient_opacity')) {
            this.model.set('gradient_opacity', opacity)
            this.model.save_changes()
          }
        }
        this.model.itkVtkViewer.subscribeGradientOpacityChanged(onGradientOpacityChange)
      }
    }).catch(error => { console.error('View caught unexpected error:', error); });
  },

  rendered_image_changed: function() {
    const rendered_image = this.model.get('rendered_image')
    if(rendered_image) {
      if (!rendered_image.data) {
        const byteArray = new Uint8Array(rendered_image.compressedData.buffer)
        const reducer = (accumulator, currentValue) => accumulator * currentValue
        const pixelCount = rendered_image.size.reduce(reducer, 1)
        let componentSize = null
        switch (rendered_image.imageType.componentType) {
          case IntTypes.Int8:
            componentSize = 1
            break
          case IntTypes.UInt8:
            componentSize = 1
            break
          case IntTypes.Int16:
            componentSize = 2
            break
          case IntTypes.UInt16:
            componentSize = 2
            break
          case IntTypes.Int32:
            componentSize = 4
            break
          case IntTypes.UInt32:
            componentSize = 4
            break
          // not currently defined in JavaScript
          //case IntTypes.Int64:
            //byteArray = new Int64Array(byteArray)
            //break
          //case IntTypes.UInt64:
            //byteArray = new Uint64Array(byteArray)
            //break
          case FloatTypes.Float32:
            componentSize = 4
            break
          case FloatTypes.Float64:
            componentSize = 8
            break
          default:
            console.error('Unexpected component type: ' + rendered_image.imageType.componentType)
        }
        const numberOfBytes = pixelCount * rendered_image.imageType.components * componentSize
        const pipelinePath = 'ZstdDecompress'
        const args = ['input.bin', 'output.bin', String(numberOfBytes)]
        const desiredOutputs = [
          { path: 'output.bin', type: IOTypes.Binary }
        ]
        const inputs = [
          { path: 'input.bin', type: IOTypes.Binary, data: byteArray }
        ]
        console.log(`input MB: ${byteArray.length / 1000 / 1000}`)
        console.log(`output MB: ${numberOfBytes / 1000 / 1000 }`)
        const compressionAmount = byteArray.length / numberOfBytes
        console.log(`compression amount: ${compressionAmount}`)
        const domWidgetView = this
        const t0 = performance.now()
        return runPipelineBrowser(null, pipelinePath, args, desiredOutputs, inputs)
          .then(function ({stdout, stderr, outputs, webWorker}) {
            webWorker.terminate()
            const t1 = performance.now();
            const duration = Number(t1 - t0).toFixed(1).toString()
            console.log("decompression took " + duration + " milliseconds.")

            switch (rendered_image.imageType.componentType) {
              case IntTypes.Int8:
                rendered_image.data = new Int8Array(outputs[0].data.buffer)
                break
              case IntTypes.UInt8:
                rendered_image.data = outputs[0].data
                break
              case IntTypes.Int16:
                rendered_image.data = new Int16Array(outputs[0].data.buffer)
                break
              case IntTypes.UInt16:
                rendered_image.data = new Uint16Array(outputs[0].data.buffer)
                break
              case IntTypes.Int32:
                rendered_image.data = new Int32Array(outputs[0].data.buffer)
                break
              case IntTypes.UInt32:
                rendered_image.data = new Uint32Array(outputs[0].data.buffer)
                break
              // not currently defined in JavaScript
              //case IntTypes.Int64:
                //break
              //case IntTypes.UInt64:
                //break
              case FloatTypes.Float32:
                rendered_image.data = new Float32Array(outputs[0].data.buffer)
                break
              case FloatTypes.Float64:
                rendered_image.data = new Float64Array(outputs[0].data.buffer)
                break
              default:
                console.error('Unexpected component type: ' + rendered_image.imageType.componentType)
            }
            return createRenderingPipeline(domWidgetView, rendered_image)
          })
      } else {
        return Promise.resolve(createRenderingPipeline(this, rendered_image))
      }
    }
  },

  ui_collapsed_changed: function() {
    const uiCollapsed = this.model.get('ui_collapsed')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setUserInterfaceCollapsed(uiCollapsed)
    }
  },

  annotations_changed: function() {
    const annotations = this.model.get('annotations')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setAnnotationsEnabled(annotations)
    }
  },

  mode_changed: function() {
    const mode = this.model.get('mode')
    if (this.model.hasOwnProperty('itkVtkViewer') && !this.model.use2D) {
      switch (mode) {
      case 'x':
        this.model.itkVtkViewer.setViewMode('XPlane')
        break
      case 'y':
        this.model.itkVtkViewer.setViewMode('YPlane')
        break
      case 'z':
        this.model.itkVtkViewer.setViewMode('ZPlane')
        break
      case 'v':
        this.model.itkVtkViewer.setViewMode('VolumeRendering')
        break
      default:
        throw new Error('Unknown view mode')
      }
    }
  },

  interpolation_changed: function() {
    const interpolation = this.model.get('interpolation')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setInterpolationEnabled(interpolation)
    }
  },

  cmap_changed: function() {
    const cmap = this.model.get('cmap')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setColorMap(cmap)
    }
  },

  shadow_changed: function() {
    const shadow = this.model.get('shadow')
    if (this.model.hasOwnProperty('itkVtkViewer') && !this.model.use2D) {
      this.model.itkVtkViewer.setShadowEnabled(shadow)
    }
  },

  slicing_planes_changed: function() {
    const slicing_planes = this.model.get('slicing_planes')
    if (this.model.hasOwnProperty('itkVtkViewer') && !this.model.use2D) {
      this.model.itkVtkViewer.setSlicingPlanesEnabled(slicing_planes)
    }
  },

  gradient_opacity_changed: function() {
    const gradient_opacity = this.model.get('gradient_opacity')
    if (this.model.hasOwnProperty('itkVtkViewer') && !this.model.use2D) {
      this.model.itkVtkViewer.setGradientOpacity(gradient_opacity)
    }
  },

  initialize_viewer: function() {
    // possible to override in extensions
  },

});

module.exports = {
  ViewerModel : ViewerModel,
  ViewerView : ViewerView
};
