import '@babel/polyfill'
const widgets = require('@jupyter-widgets/base')
import {
  fixed_shape_serialization,
  simplearray_serialization,
} from "jupyter-dataserializers"
import vtkITKHelper from 'vtk.js/Sources/Common/DataModel/ITKHelper'
import vtkCoordinate from 'vtk.js/Sources/Rendering/Core/Coordinate'
import vtk from 'vtk.js/Sources/vtk'
import { DataTypeByteSize } from 'vtk.js/Sources/Common/Core/DataArray/Constants'
import createViewer from 'itk-vtk-viewer/src/createViewer'
import IntTypes from 'itk/IntTypes'
import FloatTypes from 'itk/FloatTypes'
import IOTypes from 'itk/IOTypes'
import runPipelineBrowser from 'itk/runPipelineBrowser'
import macro from 'vtk.js/Sources/macro'

const ANNOTATION_DEFAULT = '<table style="margin-left: 0;"><tr><td style="margin-left: auto; margin-right: 0;">Index:</td><td>${iIndex},</td><td>${jIndex},</td><td>${kIndex}</td></tr><tr><td style="margin-left: auto; margin-right: 0;">Position:</td><td>${xPosition},</td><td>${yPosition},</td><td>${zPosition}</td></tr><tr><td style="margin-left: auto; margin-right: 0;"">Value:</td><td>${value}</td></tr></table>'
const ANNOTATION_CUSTOM_PREFIX = '<table style="margin-left: 0;"><tr><td style="margin-left: auto; margin-right: 0;">Scale/Index:</td>'
const ANNOTATION_CUSTOM_POSTFIX = '</tr><tr><td style="margin-left: auto; margin-right: 0;">Position:</td><td>${xPosition},</td><td>${yPosition},</td><td>${zPosition}</td></tr><tr><td style="margin-left: auto; margin-right: 0;"">Value:</td><td>${value}</td></tr></table>'

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

const serialize_polydata_list = (polydata_list) => {
  if (polydata_list === null) {
    return null
  } else {
    polydata_list.data = null
    return polydata_list
  }
}

const deserialize_polydata_list = (jsonpolydata_list) => {
  if (jsonpolydata_list === null) {
    return null
  } else {
    return jsonpolydata_list
  }
}

const ViewerModel = widgets.DOMWidgetModel.extend({
  defaults: function() {
    return Object.assign(widgets.DOMWidgetModel.prototype.defaults(), {
      _model_name: 'ViewerModel',
      _view_name: 'ViewerView',
      _model_module: 'itkwidgets',
      _view_module: 'itkwidgets',
      _model_module_version: '0.19.0',
      _view_module_version: '0.19.0',
      rendered_image: null,
      _rendering_image: false,
      interpolation: true,
      cmap: 'Viridis (matplotlib)',
      vmin: null,
      vmax: null,
      shadow: true,
      slicing_planes: false,
      gradient_opacity: 0.2,
      roi: new Float64Array([0., 0., 0., 0., 0., 0.]),
      _largest_roi: new Float64Array([0., 0., 0., 0., 0., 0.]),
      select_roi: false,
      _reset_crop_requested: false,
      _scale_factors: new Uint8Array([1, 1, 1]),
      point_sets: null,
      point_set_colors: new Float32Array([0., 0., 0.]),
      point_set_opacities: new Float32Array([1.0]),
      point_set_representations: new Array(),
      geometries: null,
      geometry_colors: new Float32Array([0., 0., 0.]),
      geometry_opacities: new Float32Array([1.0]),
      ui_collapsed: false,
      rotate: false,
      annotations: true,
      mode: 'v',
      camera: new Float32Array(9),
    })
  }}, {
  serializers: Object.assign({
    rendered_image: { serialize: serialize_itkimage, deserialize: deserialize_itkimage },
    point_sets: { serialize: serialize_polydata_list, deserialize: deserialize_polydata_list },
    geometries: { serialize: serialize_polydata_list, deserialize: deserialize_polydata_list },
    roi: fixed_shape_serialization([2, 3]),
    _largest_roi: fixed_shape_serialization([2, 3]),
    _scale_factors: fixed_shape_serialization([3,]),
    camera: fixed_shape_serialization([3, 3]),
    point_set_colors: simplearray_serialization,
    point_set_opacities: simplearray_serialization,
    geometry_colors: simplearray_serialization,
    geometry_opacities: simplearray_serialization,
  }, widgets.DOMWidgetModel.serializers)
})


const createRenderingPipeline = (domWidgetView, { rendered_image, point_sets, geometries }) => {
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
  let is3D = true
  let imageData = null
  if (rendered_image) {
    imageData = vtkITKHelper.convertItkToVtkImage(rendered_image)
    is3D = rendered_image.imageType.dimension === 3
  }
  let pointSets = null
  if (point_sets) {
    pointSets = point_sets.map((point_set) => vtk(point_set))
  }
  let vtkGeometries = null
  if (geometries) {
    vtkGeometries = geometries.map((geometry) => vtk(geometry))
  }
  domWidgetView.model.use2D = !is3D
  domWidgetView.model.skipOnCroppingPlanesChanged = false
  domWidgetView.model.itkVtkViewer = createViewer(domWidgetView.el, {
    viewerStyle: viewerStyle,
    image: imageData,
    pointSets,
    geometries: vtkGeometries,
    use2D: !is3D,
    rotate: false,
  })
  const viewProxy = domWidgetView.model.itkVtkViewer.getViewProxy()
  const renderWindow = viewProxy.getRenderWindow()
  // Firefox requires calling .getContext on the canvas, which is
  // performed by .initialize()
  renderWindow.getViews()[0].initialize()
  const viewCanvas = renderWindow.getViews()[0].getCanvas()
  const stream  = viewCanvas.captureStream(30000./1001.)

  const renderer = viewProxy.getRenderer()
  const viewportPosition = vtkCoordinate.newInstance()
  viewportPosition.setCoordinateSystemToNormalizedViewport()

  // Used by ipywebrtc
  domWidgetView.model.stream = Promise.resolve(stream)
  domWidgetView.initialize_viewer()

  const cropROIByViewport = (event) => {
    if (domWidgetView.model.get('select_roi')) {
      return
    }

    let mode = domWidgetView.model.get('mode')
    if (mode === 'v') {
      if (domWidgetView.model.use2D) {
        mode = 'z'
      } else {
        return
      }
    }
    viewportPosition.setValue(0.0, 0.0, 0.0)
    const lowerLeft = viewportPosition.getComputedWorldValue(renderer)
    viewportPosition.setValue(1.0, 1.0, 0.0)
    const upperRight = viewportPosition.getComputedWorldValue(renderer)
    const roi = domWidgetView.model.get('roi').slice()
    const largestRoi = domWidgetView.model.get('_largest_roi')
    const padFactor = 0.5
    const xPadding = (upperRight[0] - lowerLeft[0]) * padFactor
    let yPadding = (upperRight[1] - lowerLeft[1]) * padFactor
    if (mode === 'z') {
      yPadding = (lowerLeft[1] - upperRight[1]) * padFactor
    }
    const zPadding = (upperRight[2] - lowerLeft[2]) * padFactor
    switch (mode) {
    case 'x':
      roi[1] = lowerLeft[1] - yPadding
      roi[4] = upperRight[1] + yPadding
      roi[2] = lowerLeft[2] - zPadding
      roi[5] = upperRight[2] + zPadding
      // Zoom all the way out
      if(roi[2] < largestRoi[2] &&
         roi[1] < largestRoi[1] &&
         roi[5] > largestRoi[5] &&
         roi[4] > largestRoi[4]) {
        roi[2] = largestRoi[2]
        roi[1] = largestRoi[1]
        roi[5] = largestRoi[5]
        roi[4] = largestRoi[4]
        break
      }
      break
    case 'y':
      roi[0] = lowerLeft[0] - xPadding
      roi[3] = upperRight[0] + xPadding
      roi[2] = lowerLeft[2] - zPadding
      roi[5] = upperRight[2] + zPadding
      // Zoom all the way out
      if(roi[2] < largestRoi[2] &&
         roi[0] < largestRoi[0] &&
         roi[5] > largestRoi[5] &&
         roi[3] > largestRoi[3]) {
        roi[2] = largestRoi[2]
        roi[0] = largestRoi[0]
        roi[5] = largestRoi[5]
        roi[3] = largestRoi[3]
        break
      }
      break
    case 'z':
      roi[0] = lowerLeft[0] - xPadding
      roi[3] = upperRight[0] + xPadding
      roi[1] = upperRight[1] - yPadding
      roi[4] = lowerLeft[1] + yPadding
      // Zoom all the way out
      if(roi[0] < largestRoi[0] &&
         roi[1] < largestRoi[1] &&
         roi[3] > largestRoi[3] &&
         roi[4] > largestRoi[4]) {
        roi[0] = largestRoi[0]
        roi[1] = largestRoi[1]
        roi[3] = largestRoi[3]
        roi[4] = largestRoi[4]
        break
      }
      break
    default:
      throw new Error('Unexpected view mode')
    }
    domWidgetView.model.set('roi', roi)
    domWidgetView.model.save_changes()
  }

  if (rendered_image) {
    const interactor = viewProxy.getInteractor()
    interactor.onEndMouseWheel(cropROIByViewport)
    interactor.onEndPan(cropROIByViewport)
    interactor.onEndPinch(cropROIByViewport)

    const dataArray = imageData.getPointData().getScalars()
    if (dataArray.getNumberOfComponents() > 1) {
      domWidgetView.model.itkVtkViewer.setColorMap('Grayscale')
      domWidgetView.model.set('cmap', 'Grayscale')
      domWidgetView.model.save_changes()
    }
    domWidgetView.model.set('_rendering_image', false)
    domWidgetView.model.save_changes()
  }
}


function replaceRenderedImage(domWidgetView, rendered_image) {
  const imageData = vtkITKHelper.convertItkToVtkImage(rendered_image)

  domWidgetView.model.skipOnCroppingPlanesChanged = true
  domWidgetView.model.itkVtkViewer.setImage(imageData)

  // Why is this necessary?
  const viewProxy = domWidgetView.model.itkVtkViewer.getViewProxy()
  const shadow = domWidgetView.model.get('shadow')
  const representation = viewProxy.getRepresentations()[0];
  representation.setUseShadow(shadow);
  const gradientOpacity = domWidgetView.model.get('gradient_opacity')
  // Todo: Fix this in vtk.js
  representation.setEdgeGradient(representation.getEdgeGradient() + 1e-7)
  if (viewProxy.getViewMode() === 'VolumeRendering') {
    viewProxy.resetCamera()
  }

  const dataArray = imageData.getPointData().getScalars()
  if (dataArray.getNumberOfComponents() > 1) {
    domWidgetView.model.itkVtkViewer.setColorMap('Grayscale')
    domWidgetView.model.set('cmap', 'Grayscale')
    domWidgetView.model.save_changes()
  }
  domWidgetView.model.set('_rendering_image', false)
  domWidgetView.model.save_changes()
}


function replacePointSets(domWidgetView, pointSets) {
  const vtkPointSets = pointSets.map((pointSet) => vtk(pointSet))
  domWidgetView.model.itkVtkViewer.setPointSets(vtkPointSets)
  domWidgetView.point_set_colors_changed()
  domWidgetView.point_set_opacities_changed()
  domWidgetView.point_set_representations_changed()
  domWidgetView.model.itkVtkViewer.renderLater()
}


function replaceGeometries(domWidgetView, geometries) {
  const vtkGeometries = geometries.map((geometry) => vtk(geometry))
  domWidgetView.model.itkVtkViewer.setGeometries(vtkGeometries)
  domWidgetView.geometry_colors_changed()
  domWidgetView.geometry_opacities_changed()
  domWidgetView.model.itkVtkViewer.renderLater()
}


function decompressImage(image) {
  if (!!image.data) {
    return Promise.resolve(image)
  }
  const byteArray = new Uint8Array(image.compressedData.buffer)
  const reducer = (accumulator, currentValue) => accumulator * currentValue
  const pixelCount = image.size.reduce(reducer, 1)
  let componentSize = null
  switch (image.imageType.componentType) {
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
    case IntTypes.Int64:
      componentSize = 8
      break
    case IntTypes.UInt64:
      componentSize = 8
      break
    case FloatTypes.Float32:
      componentSize = 4
      break
    case FloatTypes.Float64:
      componentSize = 8
      break
    default:
      console.error('Unexpected component type: ' + image.imageType.componentType)
  }
  const numberOfBytes = pixelCount * image.imageType.components * componentSize
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
  const t0 = performance.now()
  return runPipelineBrowser(null, pipelinePath, args, desiredOutputs, inputs)
    .then(function ({stdout, stderr, outputs, webWorker}) {
      webWorker.terminate()
      const t1 = performance.now();
      const duration = Number(t1 - t0).toFixed(1).toString()
      console.log("decompression took " + duration + " milliseconds.")

      switch (image.imageType.componentType) {
        case IntTypes.Int8:
          image.data = new Int8Array(outputs[0].data.buffer)
          break
        case IntTypes.UInt8:
          image.data = outputs[0].data
          break
        case IntTypes.Int16:
          image.data = new Int16Array(outputs[0].data.buffer)
          break
        case IntTypes.UInt16:
          image.data = new Uint16Array(outputs[0].data.buffer)
          break
        case IntTypes.Int32:
          image.data = new Int32Array(outputs[0].data.buffer)
          break
        case IntTypes.UInt32:
          image.data = new Uint32Array(outputs[0].data.buffer)
          break
        case IntTypes.Int64:
          image.data = new BigUint64Array(outputs[0].data.buffer)
          break
        case IntTypes.UInt64:
          image.data = new BigUint64Array(outputs[0].data.buffer)
          break
        case FloatTypes.Float32:
          image.data = new Float32Array(outputs[0].data.buffer)
          break
        case FloatTypes.Float64:
          image.data = new Float64Array(outputs[0].data.buffer)
          break
        default:
          console.error('Unexpected component type: ' + image.imageType.componentType)
      }
      return image
    })
}


function decompressDataValue(polyData, prop) {
  if (!polyData.hasOwnProperty(prop)) {
    return Promise.resolve(polyData)
  }
  const byteArray = new Uint8Array(polyData[prop].compressedValues.buffer)
  const elementSize = DataTypeByteSize[polyData[prop].dataType]
  const numberOfBytes = polyData[prop].size * elementSize
  const pipelinePath = 'ZstdDecompress'
  const args = ['input.bin', 'output.bin', String(numberOfBytes)]
  const desiredOutputs = [
    { path: 'output.bin', type: IOTypes.Binary }
  ]
  const inputs = [
    { path: 'input.bin', type: IOTypes.Binary, data: byteArray }
  ]
  console.log(`${prop} input MB: ${byteArray.length / 1000 / 1000}`)
  console.log(`${prop} output MB: ${numberOfBytes / 1000 / 1000 }`)
  const compressionAmount = byteArray.length / numberOfBytes
  console.log(`${prop} compression amount: ${compressionAmount}`)
  const t0 = performance.now()
  return runPipelineBrowser(null, pipelinePath, args, desiredOutputs, inputs)
    .then(function ({stdout, stderr, outputs, webWorker}) {
      webWorker.terminate()
      const t1 = performance.now();
      const duration = Number(t1 - t0).toFixed(1).toString()
      console.log(`${prop} decompression took ${duration} milliseconds.`)
      polyData[prop]['values'] = new window[polyData[prop].dataType](outputs[0].data.buffer)

      return polyData
    })
}

function decompressPolyData(polyData) {
  const props = ['points', 'verts', 'lines', 'polys', 'strips']
  return Promise.all(props.map((prop) => decompressDataValue(polyData, prop)))
    .then((result) => {
      const decompressedGeometry = result[0]
      let dataPromises = []
      if (decompressedGeometry.hasOwnProperty('pointData')) {
        const pointDataArrays = decompressedGeometry.pointData.arrays
        dataPromises = pointDataArrays.map((array) => decompressDataValue(array, 'data'))
      }
      if (decompressedGeometry.hasOwnProperty('cellData')) {
        const cellDataArrays = decompressedGeometry.cellData.arrays
        dataPromises = dataPromises.concat(cellDataArrays.map((array) => decompressDataValue(array, 'data')))
      }
      if(dataPromises.length) {
        return Promise.all(dataPromises).then((resolved) => {
          return decompressedGeometry
        })
      } else {
        return decompressedGeometry
      }
    })
}


// Custom View. Renders the widget model.
const ViewerView = widgets.DOMWidgetView.extend({
  initialize_itkVtkViewer: function() {
      const rendered_image = this.model.get('rendered_image')
      this.annotations_changed()
      if (rendered_image) {
        this.interpolation_changed()
        this.cmap_changed()
        this.vmin_changed()
        this.vmax_changed()
      }
      if (rendered_image) {
        this.shadow_changed()
        this.slicing_planes_changed()
        this.gradient_opacity_changed()
      }
      this.ui_collapsed_changed()
      this.rotate_changed()
      if (rendered_image) {
        this.select_roi_changed()
        this.scale_factors_changed()
      }

      const onUserInterfaceCollapsedToggle = (collapsed) => {
        if (collapsed !== this.model.get('ui_collapsed')) {
          this.model.set('ui_collapsed', collapsed)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.subscribeToggleUserInterfaceCollapsed(onUserInterfaceCollapsedToggle)

      const onRotateToggle = (rotate) => {
        if (rotate !== this.model.get('rotate')) {
          this.model.set('rotate', rotate)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.subscribeToggleRotate(onRotateToggle)

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

      const onChangeColorRange = (colorRange) => {
        const vmin = this.model.get('vmin')
        if (colorRange[0] !== vmin) {
          this.model.set('vmin', colorRange[0])
          this.model.save_changes()
        }
        const vmax = this.model.get('vmax')
        if (colorRange[1] !== vmax) {
          this.model.set('vmax', colorRange[1])
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.subscribeChangeColorRange(onChangeColorRange);

      const onCroppingPlanesChanged = (planes, bboxCorners) => {
        if (!this.model.get('_rendering_image') && !this.model.skipOnCroppingPlanesChanged) {
          this.model.skipOnCroppingPlanesChanged = true
          this.model.set('roi',
              new Float64Array([bboxCorners[0][0], bboxCorners[0][1], bboxCorners[0][2], bboxCorners[7][0], bboxCorners[7][1], bboxCorners[7][2]]),
            )
          this.model.save_changes()
        } else {
          this.model.skipOnCroppingPlanesChanged = false
        }
      }
      this.model.itkVtkViewer.subscribeCroppingPlanesChanged(onCroppingPlanesChanged)

      const onResetCrop = () => {
        this.model.set('_reset_crop_requested', true)
        this.model.save_changes()
      }
      this.model.itkVtkViewer.subscribeResetCrop(onResetCrop)

      const onToggleCroppingPlanes = (enabled) => {
        if (enabled !== this.model.get('select_roi')) {
          this.model.set('select_roi', enabled)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.subscribeToggleCroppingPlanes(onToggleCroppingPlanes)

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

        const onCameraChanged = () => {
          const camera = new Float32Array(9)
          const viewProxy = this.model.itkVtkViewer.getViewProxy()
          camera.set(viewProxy.getCameraPosition(), 0)
          camera.set(viewProxy.getCameraFocalPoint(), 3)
          camera.set(viewProxy.getCameraViewUp(), 6)
          this.model.set('camera', camera)
          this.model.save_changes()
        }
        // If view-up has not been set, set initial value to itk-vtk-viewer default
        const viewUp = this.model.get('camera').slice(6, 9)
        if (!!!viewUp[0] && !!!viewUp[1] && !!!viewUp[2]) {
          onCameraChanged()
        } else {
          this.camera_changed()
        }
        const interactor = this.model.itkVtkViewer.getViewProxy().getInteractor()
        interactor.onEndMouseMove(onCameraChanged)

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

      const point_sets = this.model.get('point_sets')
      if(point_sets) {
        this.point_set_colors_changed()
        this.point_set_opacities_changed()
        this.point_set_representations_changed()
      }
      const geometries = this.model.get('geometries')
      if(geometries) {
        this.geometry_colors_changed()
        this.geometry_opacities_changed()
      }
      this.mode_changed()
  },

  render: function() {
    this.model.on('change:rendered_image', this.rendered_image_changed, this)
    this.model.on('change:cmap', this.cmap_changed, this)
    this.model.on('change:vmin', this.vmin_changed, this)
    this.model.on('change:vmax', this.vmax_changed, this)
    this.model.on('change:shadow', this.shadow_changed, this)
    this.model.on('change:slicing_planes', this.slicing_planes_changed, this)
    this.model.on('change:gradient_opacity', this.gradient_opacity_changed, this)
    this.model.on('change:select_roi', this.select_roi_changed, this)
    this.model.on('change:_scale_factors', this.scale_factors_changed, this)
    this.model.on('change:point_sets', this.point_sets_changed, this)
    this.model.on('change:point_set_colors', this.point_set_colors_changed, this)
    this.model.on('change:point_set_opacities', this.point_set_opacities_changed, this)
    this.model.on('change:point_set_representations', this.point_set_representations_changed, this)
    this.model.on('change:geometries', this.geometries_changed, this)
    this.model.on('change:geometry_colors', this.geometry_colors_changed, this)
    this.model.on('change:geometry_opacities', this.geometry_opacities_changed, this)
    this.model.on('change:interpolation', this.interpolation_changed, this)
    this.model.on('change:ui_collapsed', this.ui_collapsed_changed, this)
    this.model.on('change:rotate', this.rotate_changed, this)
    this.model.on('change:annotations', this.annotations_changed, this)
    this.model.on('change:mode', this.mode_changed, this)
    this.model.on('change:camera', this.camera_changed, this)

    let toDecompress = []
    const rendered_image = this.model.get('rendered_image')
    if (rendered_image) {
      toDecompress.push(decompressImage(rendered_image))
    }
    const point_sets = this.model.get('point_sets')
    if(point_sets && !!point_sets.length) {
      toDecompress = toDecompress.concat(point_sets.map(decompressPolyData))
    }
    const geometries = this.model.get('geometries')
    if(geometries && !!geometries.length) {
      toDecompress = toDecompress.concat(geometries.map(decompressPolyData))
    }
    const domWidgetView = this
    Promise.all(toDecompress).then((decompressedData) => {
      let index = 0;
      let decompressedRenderedImage = null
      if (rendered_image) {
        decompressedRenderedImage = decompressedData[0]
        index++
      }
      let decompressedPointSets = null
      if(point_sets && !!point_sets.length) {
        decompressedPointSets = decompressedData.slice(index, index+point_sets.length)
        index += point_sets.length
      }
      let decompressedGeometries = null
      if(geometries && !!geometries.length) {
        decompressedGeometries = decompressedData.slice(index, index+geometries.length)
        index += geometries.length
      }

      return createRenderingPipeline(domWidgetView, { rendered_image: decompressedRenderedImage,
        point_sets: decompressedPointSets,
        geometries: decompressedGeometries
      })
    })
  },

  rendered_image_changed: function() {
    const rendered_image = this.model.get('rendered_image')
    if(rendered_image) {
      if (!rendered_image.data) {
        const domWidgetView = this
        decompressImage(rendered_image).then((rendered_image) => {
            if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
              return Promise.resolve(replaceRenderedImage(domWidgetView, rendered_image))
            } else {
              return createRenderingPipeline(domWidgetView, { rendered_image })
            }
          })
      } else {
        if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
          return Promise.resolve(replaceRenderedImage(this, rendered_image))
        } else {
          return Promise.resolve(createRenderingPipeline(this, { rendered_image }))
        }
      }
    }
    return Promise.resolve(null)
  },

  point_sets_changed: function() {
    const point_sets = this.model.get('point_sets')
    if(point_sets && !!point_sets.length) {
      if (!point_sets[0].points.values) {
        const domWidgetView = this
        Promise.all(point_sets.map(decompressPolyData)).then((point_sets) => {
          if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
            return Promise.resolve(replacePointSets(domWidgetView, point_sets))
          } else {
            return createRenderingPipeline(domWidgetView, { point_sets })
          }
        })
      } else {
        if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
          return Promise.resolve(replacePointSets(this, point_sets))
        } else {
          return Promise.resolve(createRenderingPipeline(this, { point_sets }))
        }
      }
    }
    return Promise.resolve(null)
  },

  point_set_colors_changed: function() {
    const point_setColors = this.model.get('point_set_colors').array
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const point_sets = this.model.get('point_sets')
      if(point_sets && !!point_sets.length) {
        point_sets.forEach((point_set, index) => {
          const color = point_setColors.slice(index * 3, (index+1)*3)
          this.model.itkVtkViewer.setPointSetColor(index, color)
        })
      }
    }
  },

  point_set_opacities_changed: function() {
    const point_setOpacities = this.model.get('point_set_opacities').array
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const point_sets = this.model.get('point_sets')
      if(point_sets && !!point_sets.length) {
        point_sets.forEach((point_set, index) => {
          this.model.itkVtkViewer.setPointSetOpacity(index, point_setOpacities[index])
        })
      }
    }
  },

  point_set_representations_changed: function() {
    const point_set_representations = this.model.get('point_set_representations')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const point_sets = this.model.get('point_sets')
      if(point_sets && !!point_sets.length) {
        point_set_representations.forEach((representation, index) => {
          switch(representation.toLowerCase()) {
          case 'hidden':
            this.model.itkVtkViewer.setPointSetRepresentation(index, 'Hidden')
            break;
          case 'points':
            this.model.itkVtkViewer.setPointSetRepresentation(index, 'Points')
            break;
          case 'spheres':
            this.model.itkVtkViewer.setPointSetRepresentation(index, 'Spheres')
            break;
          default:
            this.model.itkVtkViewer.setPointSetRepresentation(index, 'Points')
          }
        })
      }
    }
  },

  geometries_changed: function() {
    const geometries = this.model.get('geometries')
    if(geometries && !!geometries.length) {
      if (!geometries[0].points.values) {
        const domWidgetView = this
        Promise.all(geometries.map(decompressPolyData)).then((geometries) => {
          if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
            return Promise.resolve(replaceGeometries(domWidgetView, geometries))
          } else {
            return createRenderingPipeline(domWidgetView, { geometries })
          }
        })
      } else {
        if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
          return Promise.resolve(replaceGeometries(this, geometries))
        } else {
          return Promise.resolve(createRenderingPipeline(this, { geometries }))
        }
      }
    }
    return Promise.resolve(null)
  },

  geometry_colors_changed: function() {
    const geometryColors = this.model.get('geometry_colors').array
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const geometries = this.model.get('geometries')
      if(geometries && !!geometries.length) {
        geometries.forEach((geometry, index) => {
          const color = geometryColors.slice(index * 3, (index+1)*3)
          this.model.itkVtkViewer.setGeometryColor(index, color)
        })
      }
    }
  },

  geometry_opacities_changed: function() {
    const geometryOpacities = this.model.get('geometry_opacities').array
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const geometries = this.model.get('geometries')
      if(geometries && !!geometries.length) {
        geometries.forEach((geometry, index) => {
          this.model.itkVtkViewer.setGeometryOpacity(index, geometryOpacities[index])
        })
      }
    }
  },

  ui_collapsed_changed: function() {
    const uiCollapsed = this.model.get('ui_collapsed')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setUserInterfaceCollapsed(uiCollapsed)
    }
  },

  rotate_changed: function() {
    const rotate = this.model.get('rotate')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setRotateEnabled(rotate)
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
        // Why is this necessary?
        // Todo: fix in vtk.js
        const viewProxy = this.model.itkVtkViewer.getViewProxy()
        const representation = viewProxy.getRepresentations()[0];
        const shadow = this.model.get('shadow')
        representation.setUseShadow(shadow);
        break
      default:
        throw new Error('Unknown view mode')
      }
    }
  },

  camera_changed: function() {
    const camera = this.model.get('camera')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const viewProxy = this.model.itkVtkViewer.getViewProxy()
      viewProxy.setCameraPosition(...camera.subarray(0, 3))
      viewProxy.setCameraFocalPoint(...camera.subarray(3, 6))
      viewProxy.setCameraViewUp(...camera.subarray(6, 9))
      viewProxy.getCamera().computeDistance()
      viewProxy.renderLater()
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

  vmin_changed: function() {
    const vmin = this.model.get('vmin')
    if (vmin !== null && this.model.hasOwnProperty('itkVtkViewer')) {
      let colorRange = this.model.itkVtkViewer.getColorRange().slice()
      colorRange[0] = vmin
      this.model.itkVtkViewer.setColorRange(colorRange)
    }
  },

  vmax_changed: function() {
    const vmax = this.model.get('vmax')
    if (vmax !== null && this.model.hasOwnProperty('itkVtkViewer')) {
      let colorRange = this.model.itkVtkViewer.getColorRange().slice()
      colorRange[1] = vmax
      this.model.itkVtkViewer.setColorRange(colorRange)
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

  select_roi_changed: function() {
    const select_roi = this.model.get('select_roi')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setCroppingPlanesEnabled(select_roi)
    }
  },

  scale_factors_changed: function() {
    let scaleFactors = this.model.get('_scale_factors')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const viewProxy = this.model.itkVtkViewer.getViewProxy()
      if (typeof scaleFactors[0] === 'undefined') {
        scaleFactors = new Uint8Array(scaleFactors.buffer.buffer)
      }
      if (scaleFactors[0] === 1 && scaleFactors[1] === 1 && scaleFactors[2] === 1) {
        viewProxy.setCornerAnnotation('se',
          `${ANNOTATION_DEFAULT}`)
      } else {
        let scaleIndex = ''
        if (scaleFactors[0] === 1) {
          scaleIndex = `${scaleIndex}<td>\${iIndex}</td>`
        } else {
          scaleIndex = `${scaleIndex}<td>${scaleFactors[0]}X</td>`
        }
        if (scaleFactors[1] === 1) {
          scaleIndex = `${scaleIndex}<td>\${jIndex}</td>`
        } else {
          scaleIndex = `${scaleIndex}<td>${scaleFactors[1]}X</td>`
        }
        if (scaleFactors[2] === 1) {
          scaleIndex = `${scaleIndex}<td>\${kIndex}</td>`
        } else {
          scaleIndex = `${scaleIndex}<td>${scaleFactors[2]}X</td>`
        }
        viewProxy.setCornerAnnotation('se',
          `${ANNOTATION_CUSTOM_PREFIX}${scaleIndex}${ANNOTATION_CUSTOM_POSTFIX}`)
      }
    }
  },

  initialize_viewer: function() {
    this.initialize_itkVtkViewer()
    // possible to override in extensions
  },

});

module.exports = {
  ViewerModel : ViewerModel,
  ViewerView : ViewerView
};
