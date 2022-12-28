import {
  fixed_shape_serialization,
  simplearray_serialization
} from 'jupyter-dataserializers'
import vtkITKHelper from 'vtk.js/Sources/Common/DataModel/ITKHelper'
import vtkCoordinate from 'vtk.js/Sources/Rendering/Core/Coordinate'
import vtk from 'vtk.js/Sources/vtk'
import { DataTypeByteSize } from 'vtk.js/Sources/Common/Core/DataArray/Constants'
import createViewer from 'itk-vtk-viewer/src/createViewer'
import IntTypes from 'itk/IntTypes'
import FloatTypes from 'itk/FloatTypes'
import IOTypes from 'itk/IOTypes'
import runPipelineBrowser from 'itk/runPipelineBrowser'
import WorkerPool from 'itk/WorkerPool'
import macro from 'vtk.js/Sources/macro'
const widgets = require('@jupyter-widgets/base')

const ANNOTATION_DEFAULT =
  '<table style="margin-left: 0;"><tr><td style="margin-left: auto; margin-right: 0;">Index:</td><td>${iIndex},</td><td>${jIndex},</td><td>${kIndex}</td></tr><tr><td style="margin-left: auto; margin-right: 0;">Position:</td><td>${xPosition},</td><td>${yPosition},</td><td>${zPosition}</td></tr><tr><td style="margin-left: auto; margin-right: 0;"">Value:</td><td style="text-align:center;" colspan="3">${value}</td></tr><tr ${annotationLabelStyle}><td style="margin-left: auto; margin-right: 0;">Label:</td><td style="text-align:center;" colspan="3">${annotation}</td></tr></table>'
const ANNOTATION_CUSTOM_PREFIX =
  '<table style="margin-left: 0;"><tr><td style="margin-left: auto; margin-right: 0;">Scale/Index:</td>'
const ANNOTATION_CUSTOM_POSTFIX =
  '</tr><tr><td style="margin-left: auto; margin-right: 0;">Position:</td><td>${xPosition},</td><td>${yPosition},</td><td>${zPosition}</td></tr><tr><td style="margin-left: auto; margin-right: 0;"">Value:</td><td style="text-align:center;" colspan="3">${value}</td></tr><tr ${annotationLabelStyle}><td style="margin-left: auto; margin-right: 0;">Label:</td><td style="text-align:center;" colspan="3">${annotation}</td></tr></table>'

const cores = navigator.hardwareConcurrency ? navigator.hardwareConcurrency : 4
const numberOfWorkers = cores + Math.floor(Math.sqrt(cores))
const workerPool = new WorkerPool(numberOfWorkers, runPipelineBrowser)

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

const serialize_image_point = (data) => {
  if (data === null) {
    return null
  } else {
    return {
      index: simplearray_serialization.serialize({
        shape: [3],
        array: new Int32Array([data.iIndex, data.jIndex, data.kIndex])
      }),

      position: simplearray_serialization.serialize({
        shape: [3],
        array: new Float64Array([
          data.xPosition,
          data.yPosition,
          data.zPosition
        ])
      }),
      value: simplearray_serialization.serialize({
        shape: [data.value.length],
        array: new Float64Array(data.value)
      }),
      label: data.label
    }
  }
}

const deserialize_image_point = (data) => {
  if (data === null) {
    return null
  } else {
    return {
      iIndex: data.index[0],
      jIndex: data.index[1],
      kIndex: data.index[2],
      xPosition: data.position[0],
      yPosition: data.position[1],
      zPosition: data.position[2],
      value: Array.from(data.value),
      label: data.label
    }
  }
}

const ViewerModel = widgets.DOMWidgetModel.extend(
  {
    defaults: function () {
      return Object.assign(widgets.DOMWidgetModel.prototype.defaults(), {
        _model_name: 'ViewerModel',
        _view_name: 'ViewerView',
        _model_module: 'itkwidgets',
        _view_module: 'itkwidgets',
        _model_module_version: '0.32.5',
        _view_module_version: '0.32.5',
        rendered_image: null,
        rendered_label_image: null,
        label_image_names: null,
        label_image_weights: null,
        label_image_blend: 0.5,
        _rendering_image: false,
        interpolation: true,
        cmap: null,
        lut: 'glasbey',
        _custom_cmap: { array: new Float32Array([0, 0, 0]), shape: [1,3] },
        vmin: null,
        vmax: null,
        shadow: true,
        slicing_planes: false,
        x_slice: null,
        y_slice: null,
        z_slice: null,
        clicked_slice_point: null,
        gradient_opacity: 0.2,
        sample_distance: 0.25,
        opacity_gaussians: null,
        channels: null,
        blend_mode: 'composite',
        roi: new Float64Array([0, 0, 0, 0, 0, 0]),
        _largest_roi: new Float64Array([0, 0, 0, 0, 0, 0]),
        select_roi: false,
        _reset_crop_requested: false,
        _scale_factors: new Uint8Array([1, 1, 1]),
        units: '',
        point_sets: null,
        point_set_colors: { array: new Float32Array([0, 0, 0]), shape: [1,3] },
        point_set_opacities: { array: new Float32Array([1.0]), shape: [1] },
        point_set_sizes: { array: new Uint8Array([3]), shape: [1] },
        point_set_representations: new Array(),
        geometries: null,
        geometry_colors: new Float32Array([0, 0, 0]),
        geometry_opacities: new Float32Array([1.0]),
        ui_collapsed: false,
        rotate: false,
        annotations: true,
        axes: true,
        mode: 'v',
        camera: new Float32Array(9),
        background: null
      })
    }
  },
  {
    serializers: Object.assign(
      {
        rendered_image: {
          serialize: serialize_itkimage,
          deserialize: deserialize_itkimage
        },
        rendered_label_image: {
          serialize: serialize_itkimage,
          deserialize: deserialize_itkimage
        },
        label_image_weights: simplearray_serialization,
        clicked_slice_point: {
          serialize: serialize_image_point,
          deserialize: deserialize_image_point
        },
        _custom_cmap: simplearray_serialization,
        point_sets: {
          serialize: serialize_polydata_list,
          deserialize: deserialize_polydata_list
        },
        geometries: {
          serialize: serialize_polydata_list,
          deserialize: deserialize_polydata_list
        },
        roi: fixed_shape_serialization([2, 3]),
        _largest_roi: fixed_shape_serialization([2, 3]),
        _scale_factors: fixed_shape_serialization([3]),
        camera: fixed_shape_serialization([3, 3]),
        point_set_colors: simplearray_serialization,
        point_set_opacities: simplearray_serialization,
        point_set_sizes: simplearray_serialization,
        geometry_colors: simplearray_serialization,
        geometry_opacities: simplearray_serialization
      },
      widgets.DOMWidgetModel.serializers
    )
  }
)

const createRenderingPipeline = (
  domWidgetView,
  { rendered_image, rendered_label_image, point_sets, geometries }
) => {
  const containerStyle = {
    position: 'relative',
    width: '100%',
    height: '700px',
    minHeight: '400px',
    minWidth: '400px',
    margin: '1',
    padding: '1',
    top: '0',
    left: '0',
    overflow: 'hidden',
    display: 'block-inline'
  }
  let backgroundColor = [1.0, 1.0, 1.0]
  const bodyBackground = getComputedStyle(document.body).getPropertyValue(
    'background-color'
  )
  if (bodyBackground) {
    // Separator can be , or space
    const sep = bodyBackground.indexOf(',') > -1 ? ',' : ' '
    // Turn "rgb(r,g,b)" into [r,g,b]
    const rgb = bodyBackground.substr(4).split(')')[0].split(sep)
    backgroundColor[0] = rgb[0] / 255.0
    backgroundColor[1] = rgb[1] / 255.0
    backgroundColor[2] = rgb[2] / 255.0
  }
  const backgroundTrait = domWidgetView.model.get('background')
  if (backgroundTrait && !!backgroundTrait.length) {
    backgroundColor = backgroundTrait
  }
  const viewerStyle = {
    backgroundColor,
    containerStyle: containerStyle
  }
  let is3D = true
  let imageData = null
  let labelMapData = null
  if (rendered_image) {
    imageData = vtkITKHelper.convertItkToVtkImage(rendered_image)
    is3D = rendered_image.imageType.dimension === 3
  }
  if (rendered_label_image) {
    labelMapData = vtkITKHelper.convertItkToVtkImage(rendered_label_image)
    is3D = rendered_label_image.imageType.dimension === 3
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
    labelMap: labelMapData,
    pointSets,
    geometries: vtkGeometries,
    use2D: !is3D,
    rotate: false
  })
  const viewProxy = domWidgetView.model.itkVtkViewer.getViewProxy()
  const renderWindow = viewProxy.getRenderWindow()
  // Firefox requires calling .getContext on the canvas, which is
  // performed by .initialize()
  renderWindow.getViews()[0].initialize()
  const viewCanvas = renderWindow.getViews()[0].getCanvas()
  const stream = viewCanvas.captureStream(30000 / 1001)

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
    const modelRoi = domWidgetView.model.get('roi')
    const roi = !!modelRoi.slice ? modelRoi: new Float32Array(modelRoi.buffer)
    const modelLargestRoi = domWidgetView.model.get('_largest_roi')
    const largestRoi = !!modelLargestRoi.slice ? modelLargestRoi: new Float32Array(modelLargestRoi.buffer)
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
        if (
          roi[2] < largestRoi[2] &&
          roi[1] < largestRoi[1] &&
          roi[5] > largestRoi[5] &&
          roi[4] > largestRoi[4]
        ) {
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
        if (
          roi[2] < largestRoi[2] &&
          roi[0] < largestRoi[0] &&
          roi[5] > largestRoi[5] &&
          roi[3] > largestRoi[3]
        ) {
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
        if (
          roi[0] < largestRoi[0] &&
          roi[1] < largestRoi[1] &&
          roi[3] > largestRoi[3] &&
          roi[4] > largestRoi[4]
        ) {
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

  if (rendered_image || rendered_label_image) {
    const interactor = viewProxy.getInteractor()
    interactor.onEndMouseWheel(cropROIByViewport)
    interactor.onEndPan(cropROIByViewport)
    interactor.onEndPinch(cropROIByViewport)

    if (rendered_image) {
      const dataArray = imageData.getPointData().getScalars()
      const numberOfComponents = dataArray.getNumberOfComponents()
      if (
        domWidgetView.model.use2D &&
        dataArray.getDataType() === 'Uint8Array' &&
        (numberOfComponents === 3 || numberOfComponents === 4)
      ) {
        domWidgetView.model.itkVtkViewer.setColorMap(0, 'Grayscale')
        domWidgetView.model.set('cmap', ['Grayscale'])
        domWidgetView.model.save_changes()
      }
    }
    domWidgetView.model.set('_rendering_image', false)
    domWidgetView.model.save_changes()
  }
}

function replaceRenderedImage (domWidgetView, rendered_image) {
  const imageData = vtkITKHelper.convertItkToVtkImage(rendered_image)

  domWidgetView.model.skipOnCroppingPlanesChanged = true
  domWidgetView.model.itkVtkViewer.setImage(imageData)

  // Why is this necessary?
  const viewProxy = domWidgetView.model.itkVtkViewer.getViewProxy()
  const shadow = domWidgetView.model.get('shadow')
  const representation = viewProxy.getRepresentations()[0]
  representation.setUseShadow(shadow)
  const gradientOpacity = domWidgetView.model.get('gradient_opacity')
  // Todo: Fix this in vtk.js
  representation.setEdgeGradient(representation.getEdgeGradient() + 1e-7)
  if (viewProxy.getViewMode() === 'VolumeRendering') {
    viewProxy.resetCamera()
  }

  const dataArray = imageData.getPointData().getScalars()
  const numberOfComponents = dataArray.getNumberOfComponents()
  if (
    domWidgetView.model.use2D &&
    dataArray.getDataType() === 'Uint8Array' &&
    (numberOfComponents === 3 || numberOfComponents === 4)
  ) {
    domWidgetView.model.itkVtkViewer.setColorMap(0, 'Grayscale')
    domWidgetView.model.set('cmap', ['Grayscale'])
    domWidgetView.model.save_changes()
  }
  domWidgetView.model.set('_rendering_image', false)
  domWidgetView.model.save_changes()
}

function replaceRenderedLabelMap (domWidgetView, rendered_label_image) {
  const labelMapData = vtkITKHelper.convertItkToVtkImage(rendered_label_image)

  domWidgetView.model.itkVtkViewer.setLabelMap(labelMapData)

  if (viewProxy.getViewMode() === 'VolumeRendering') {
    viewProxy.resetCamera()
  }
  domWidgetView.model.set('_rendering_image', false)
  domWidgetView.model.save_changes()
}

function replacePointSets (domWidgetView, pointSets) {
  const vtkPointSets = pointSets.map((pointSet) => vtk(pointSet))
  domWidgetView.model.itkVtkViewer.setPointSets(vtkPointSets)
  domWidgetView.point_set_colors_changed()
  domWidgetView.point_set_opacities_changed()
  domWidgetView.point_set_sizes_changed()
  domWidgetView.point_set_representations_changed()
  domWidgetView.model.itkVtkViewer.renderLater()
}

function replaceGeometries (domWidgetView, geometries) {
  const vtkGeometries = geometries.map((geometry) => vtk(geometry))
  domWidgetView.model.itkVtkViewer.setGeometries(vtkGeometries)
  domWidgetView.geometry_colors_changed()
  domWidgetView.geometry_opacities_changed()
  domWidgetView.model.itkVtkViewer.renderLater()
}

async function decompressImage (image) {
  if (image.data) {
    return image
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
      console.error(
        'Unexpected component type: ' + image.imageType.componentType
      )
  }
  const numberOfBytes = pixelCount * image.imageType.components * componentSize
  const pipelinePath = 'ZstdDecompress'
  const args = ['input.bin', 'output.bin', String(numberOfBytes)]
  const desiredOutputs = [{ path: 'output.bin', type: IOTypes.Binary }]
  const inputs = [{ path: 'input.bin', type: IOTypes.Binary, data: byteArray }]
  console.log(`input MB: ${byteArray.length / 1000 / 1000}`)
  console.log(`output MB: ${numberOfBytes / 1000 / 1000}`)
  const compressionAmount = byteArray.length / numberOfBytes
  console.log(`compression amount: ${compressionAmount}`)
  const t0 = performance.now()
  const taskArgsArray = [[pipelinePath, args, desiredOutputs, inputs]]
  const results = await workerPool.runTasks(taskArgsArray)
  const t1 = performance.now()
  const duration = Number(t1 - t0)
    .toFixed(1)
    .toString()
  console.log('decompression took ' + duration + ' milliseconds.')

  const decompressed = results[0].outputs[0].data
  switch (image.imageType.componentType) {
    case IntTypes.Int8:
      image.data = new Int8Array(decompressed.buffer)
      break
    case IntTypes.UInt8:
      image.data = decompressed
      break
    case IntTypes.Int16:
      image.data = new Int16Array(decompressed.buffer)
      break
    case IntTypes.UInt16:
      image.data = new Uint16Array(decompressed.buffer)
      break
    case IntTypes.Int32:
      image.data = new Int32Array(decompressed.buffer)
      break
    case IntTypes.UInt32:
      image.data = new Uint32Array(decompressed.buffer)
      break
    case IntTypes.Int64:
      image.data = new BigUint64Array(decompressed.buffer)
      break
    case IntTypes.UInt64:
      image.data = new BigUint64Array(decompressed.buffer)
      break
    case FloatTypes.Float32:
      image.data = new Float32Array(decompressed.buffer)
      break
    case FloatTypes.Float64:
      image.data = new Float64Array(decompressed.buffer)
      break
    default:
      console.error(
        'Unexpected component type: ' + image.imageType.componentType
      )
  }
  return image
}

function decompressDataValue (polyData, prop) {
  if (!polyData.hasOwnProperty(prop)) {
    return Promise.resolve(polyData)
  }
  const byteArray = new Uint8Array(polyData[prop].compressedValues.buffer)
  const elementSize = DataTypeByteSize[polyData[prop].dataType]
  const numberOfBytes = polyData[prop].size * elementSize
  const pipelinePath = 'ZstdDecompress'
  const args = ['input.bin', 'output.bin', String(numberOfBytes)]
  const desiredOutputs = [{ path: 'output.bin', type: IOTypes.Binary }]
  const inputs = [{ path: 'input.bin', type: IOTypes.Binary, data: byteArray }]
  console.log(`${prop} input MB: ${byteArray.length / 1000 / 1000}`)
  console.log(`${prop} output MB: ${numberOfBytes / 1000 / 1000}`)
  const compressionAmount = byteArray.length / numberOfBytes
  console.log(`${prop} compression amount: ${compressionAmount}`)
  const t0 = performance.now()
  return runPipelineBrowser(
    null,
    pipelinePath,
    args,
    desiredOutputs,
    inputs
  ).then(function ({ stdout, stderr, outputs, webWorker }) {
    webWorker.terminate()
    const t1 = performance.now()
    const duration = Number(t1 - t0)
      .toFixed(1)
      .toString()
    console.log(`${prop} decompression took ${duration} milliseconds.`)
    polyData[prop].values = new window[polyData[prop].dataType](
      outputs[0].data.buffer
    )

    return polyData
  })
}

async function decompressPolyData (polyData) {
  const props = ['points', 'verts', 'lines', 'polys', 'strips']
  const decompressedProps = []
  const taskArgsArray = []
  for (let index = 0; index < props.length; index++) {
    const prop = props[index]
    if (!polyData.hasOwnProperty(prop)) {
      continue
    }
    const byteArray = new Uint8Array(polyData[prop].compressedValues.buffer)
    const elementSize = DataTypeByteSize[polyData[prop].dataType]
    const numberOfBytes = polyData[prop].size * elementSize
    const pipelinePath = 'ZstdDecompress'
    const args = ['input.bin', 'output.bin', String(numberOfBytes)]
    const desiredOutputs = [{ path: 'output.bin', type: IOTypes.Binary }]
    const inputs = [
      { path: 'input.bin', type: IOTypes.Binary, data: byteArray }
    ]
    console.log(`${prop} input MB: ${byteArray.length / 1000 / 1000}`)
    console.log(`${prop} output MB: ${numberOfBytes / 1000 / 1000}`)
    const compressionAmount = byteArray.length / numberOfBytes
    console.log(`${prop} compression amount: ${compressionAmount}`)
    taskArgsArray.push([pipelinePath, args, desiredOutputs, inputs])
    decompressedProps.push(prop)
  }

  const decompressedPointData = []
  if (polyData.hasOwnProperty('pointData')) {
    const pointDataArrays = polyData.pointData.arrays
    for (let index = 0; index < pointDataArrays.length; index++) {
      const array = pointDataArrays[index]
      const byteArray = new Uint8Array(array.data.compressedValues.buffer)
      const elementSize = DataTypeByteSize[array.data.dataType]
      const numberOfBytes = array.data.size * elementSize
      const pipelinePath = 'ZstdDecompress'
      const args = ['input.bin', 'output.bin', String(numberOfBytes)]
      const desiredOutputs = [{ path: 'output.bin', type: IOTypes.Binary }]
      const inputs = [
        { path: 'input.bin', type: IOTypes.Binary, data: byteArray }
      ]
      console.log(`${array} input MB: ${byteArray.length / 1000 / 1000}`)
      console.log(`${array} output MB: ${numberOfBytes / 1000 / 1000}`)
      const compressionAmount = byteArray.length / numberOfBytes
      console.log(`${array} compression amount: ${compressionAmount}`)
      taskArgsArray.push([pipelinePath, args, desiredOutputs, inputs])
      decompressedPointData.push(array)
    }
  }

  const decompressedCellData = []
  if (polyData.hasOwnProperty('cellData')) {
    const cellDataArrays = polyData.cellData.arrays
    for (let index = 0; index < cellDataArrays.length; index++) {
      const array = cellDataArrays[index]
      const byteArray = new Uint8Array(array.data.compressedValues.buffer)
      const elementSize = DataTypeByteSize[array.data.dataType]
      const numberOfBytes = array.data.size * elementSize
      const pipelinePath = 'ZstdDecompress'
      const args = ['input.bin', 'output.bin', String(numberOfBytes)]
      const desiredOutputs = [{ path: 'output.bin', type: IOTypes.Binary }]
      const inputs = [
        { path: 'input.bin', type: IOTypes.Binary, data: byteArray }
      ]
      console.log(`${array} input MB: ${byteArray.length / 1000 / 1000}`)
      console.log(`${array} output MB: ${numberOfBytes / 1000 / 1000}`)
      const compressionAmount = byteArray.length / numberOfBytes
      console.log(`${array} compression amount: ${compressionAmount}`)
      taskArgsArray.push([pipelinePath, args, desiredOutputs, inputs])
      decompressedCellData.push(array)
    }
  }

  const t0 = performance.now()
  const results = await workerPool.runTasks(taskArgsArray)
  const t1 = performance.now()
  const duration = Number(t1 - t0)
    .toFixed(1)
    .toString()
  console.log(`PolyData decompression took ${duration} milliseconds.`)
  for (let index = 0; index < decompressedProps.length; index++) {
    const prop = decompressedProps[index]
    polyData[prop].values = new window[polyData[prop].dataType](
      results[index].outputs[0].data.buffer
    )
  }
  for (let index = 0; index < decompressedPointData.length; index++) {
    polyData.pointData.arrays[index].data.values = new window[
      polyData.pointData.arrays[index].data.dataType
    ](results[decompressedProps.length + index].outputs[0].data.buffer)
  }
  for (let index = 0; index < decompressedCellData.length; index++) {
    polyData.cellData.arrays[index].data.values = new window[
      polyData.cellData.arrays[index].data.dataType
    ](
      results[
        decompressedProps.length + decompressedPointData.length + index
      ].outputs[0].data.buffer
    )
  }

  return polyData
}

// Custom View. Renders the widget model.
const ViewerView = widgets.DOMWidgetView.extend({
  initialize_itkVtkViewer: function () {
    const rendered_image = this.model.get('rendered_image')
    const rendered_label_image = this.model.get('rendered_label_image')
    this.annotations_changed()
    this.axes_changed()

    const onBackgroundChanged = (background) => {
      this.model.set('background', background)
      this.model.save_changes()
    }
    this.model.itkVtkViewer.on('backgroundColorChanged', onBackgroundChanged)
    const background = this.model.get('background')
    if (background === null|| background.length === 0) {
      this.model.set('background', this.model.itkVtkViewer.getBackgroundColor())
    }

    if (rendered_image) {
      this.interpolation_changed()
      this.cmap_changed()
      this.vmin_changed()
      this.vmax_changed()
    }
    if (rendered_image || rendered_label_image) {
      this.slicing_planes_changed()
      this.x_slice_changed()
      this.y_slice_changed()
      this.z_slice_changed()
    }
    if (rendered_image) {
      this.shadow_changed()
      this.gradient_opacity_changed()
      this.sample_distance_changed()
      this.channels_changed()
      this.blend_mode_changed()
    }
    this.ui_collapsed_changed()
    this.rotate_changed()
    if (rendered_image || rendered_label_image) {
      this.select_roi_changed()
      this.scale_factors_changed()
    }
    if (rendered_label_image) {
      this.label_image_names_changed()
      this.label_image_weights_changed()
      this.label_image_blend_changed()
      this.lut_changed()
    }

    const onUserInterfaceCollapsedToggle = (collapsed) => {
      if (collapsed !== this.model.get('ui_collapsed')) {
        this.model.set('ui_collapsed', collapsed)
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('toggleUserInterfaceCollapsed',
      onUserInterfaceCollapsedToggle
    )

    const onRotateToggle = (rotate) => {
      if (rotate !== this.model.get('rotate')) {
        this.model.set('rotate', rotate)
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('toggleRotate', onRotateToggle)

    const onAnnotationsToggle = (enabled) => {
      if (enabled !== this.model.get('annotations')) {
        this.model.set('annotations', enabled)
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('toggleAnnotations', onAnnotationsToggle)

    const onAxesToggle = (enabled) => {
      if (enabled !== this.model.get('axes')) {
        this.model.set('axes', enabled)
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('toggleAxes', onAxesToggle)

    const onInterpolationToggle = (enabled) => {
      if (enabled !== this.model.get('interpolation')) {
        this.model.set('interpolation', enabled)
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('toggleInterpolation', onInterpolationToggle)

    const onSelectColorMap = (component, colorMap) => {
      let cmap = this.model.get('cmap')
      if (
        cmap !== null &&
        colorMap !== cmap[component] &&
        !this.model.colorMapLoopBreak
      ) {
        cmap[component] = colorMap
        this.model.set('cmap', cmap)
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('selectColorMap', onSelectColorMap)

    const onSelectLookupTable = (lookupTable) => {
      let lut = this.model.get('lut')
      if (
        lut !== null && lookupTable !== lut
      ) {
        this.model.set('lut', lookupTable)
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('selectLookupTable', onSelectLookupTable)

    const onColorRangesChanged = (colorRanges) => {
      let vmin = this.model.get('vmin')
      if (vmin === null) {
        vmin = []
      }
      let vmax = this.model.get('vmax')
      if (vmax === null) {
        vmax = []
      }
      const rendered_image = this.model.get('rendered_image')
      const components = rendered_image.imageType.components
      for (let component = 0; component < components; component++) {
        const colorRange = colorRanges[component]
        vmin[component] = colorRange[0]
        vmax[component] = colorRange[1]
      }
      this.model.set('vmax', vmax)
      this.model.set('vmin', vmin)
      this.model.save_changes()
    }
    this.model.itkVtkViewer.on('colorRangesChanged', onColorRangesChanged)

    const onCroppingPlanesChanged = (planes, bboxCorners) => {
      if (
        !this.model.get('_rendering_image') &&
        !this.model.skipOnCroppingPlanesChanged
      ) {
        this.model.skipOnCroppingPlanesChanged = true
        this.model.set(
          'roi',
          new Float64Array([
              bboxCorners[0][0],
              bboxCorners[0][1],
              bboxCorners[0][2],
              bboxCorners[7][0],
              bboxCorners[7][1],
              bboxCorners[7][2]
          ])
        )
        this.model.save_changes()
      } else {
        this.model.skipOnCroppingPlanesChanged = false
      }
    }
    this.model.itkVtkViewer.on('croppingPlanesChanged',
      onCroppingPlanesChanged
    )

    const onResetCrop = () => {
      this.model.set('_reset_crop_requested', true)
      this.model.save_changes()
    }
    this.model.itkVtkViewer.on('resetCrop', onResetCrop)

    const onToggleCroppingPlanes = (enabled) => {
      if (enabled !== this.model.get('select_roi')) {
        this.model.set('select_roi', enabled)
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('toggleCroppingPlanes',
      onToggleCroppingPlanes
    )

    const onLabelMapWeightsChanged = ({ weights }) => {
      const typedWeights = new Float32Array(weights)
      this.model.set('label_image_weights', { shape: [weights.length],
        array: typedWeights
      })
      this.model.save_changes()
    }
    this.model.itkVtkViewer.on('labelMapWeightsChanged',
      onLabelMapWeightsChanged
    )

    const onLabelMapBlendChanged = (blend) => {
      this.model.set('label_image_blend', blend)
      this.model.save_changes()
    }
    this.model.itkVtkViewer.on('labelMapBlendChanged',
      onLabelMapBlendChanged
    )

    const onOpacityGaussiansChanged = macro.throttle((gaussians) => {
      this.model.set('opacity_gaussians', gaussians)
      this.model.save_changes()
    }, 100)
    this.model.itkVtkViewer.on('opacityGaussiansChanged',
      onOpacityGaussiansChanged
    )
    if (rendered_image) {
      const gaussians = this.model.get('opacity_gaussians')
      if (gaussians === null || gaussians.length === 0) {
        this.model.set('opacity_gaussians', this.model.itkVtkViewer.getOpacityGaussians())
      }
      this.opacity_gaussians_changed()
    }

    const onChannelsChanged = (channels) => {
      this.model.set('channels', channels)
      this.model.save_changes()
    }
    this.model.itkVtkViewer.on('componentVisibilitiesChanged',
      onChannelsChanged
    )
    const channels = this.model.get('channels')
    if (channels === null || channels.length === 0) {
      this.model.set('channels', this.model.itkVtkViewer.getComponentVisibilities())
    }

    if (!this.model.use2D) {
      const onBlendModeChanged = (blend) => {
        let pythonMode = null
        switch (blend) {
          case 0:
            pythonMode = 'composite'
            break
          case 1:
            pythonMode = 'max'
            break
          case 2:
            pythonMode = 'min'
            break
          case 3:
            pythonMode = 'average'
            break
          default:
            throw new Error('Unknown blend mode')
        }
        if (pythonMode !== this.model.get('blend')) {
          this.model.set('blend', pythonMode)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.on('blendModeChanged', onBlendModeChanged)

      const onViewModeChanged = (mode) => {
        let pythonMode = null
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
      this.model.itkVtkViewer.on('viewModeChanged', onViewModeChanged)

      const onShadowToggle = (enabled) => {
        if (enabled !== this.model.get('shadow')) {
          this.model.set('shadow', enabled)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.on('toggleShadow', onShadowToggle)

      const onSlicingPlanesToggle = (enabled) => {
        if (enabled !== this.model.get('slicing_planes')) {
          this.model.set('slicing_planes', enabled)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.on('toggleSlicingPlanes',
        onSlicingPlanesToggle
      )

      const onXSliceChanged = (position) => {
        if (position !== this.model.get('x_slice')) {
          this.model.set('x_slice', position)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.on('xSliceChanged', onXSliceChanged)
      if (this.model.get('x_slice') === null) {
        this.model.set('x_slice', this.model.itkVtkViewer.getXSlice())
        this.model.save_changes()
      }
      const onYSliceChanged = (position) => {
        if (position !== this.model.get('y_slice')) {
          this.model.set('y_slice', position)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.on('ySliceChanged', onYSliceChanged)
      if (this.model.get('y_slice') === null) {
        this.model.set('y_slice', this.model.itkVtkViewer.getYSlice())
        this.model.save_changes()
      }
      const onZSliceChanged = (position) => {
        if (position !== this.model.get('z_slice')) {
          this.model.set('z_slice', position)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.on('zSliceChanged', onZSliceChanged)
      if (this.model.get('z_slice') === null) {
        this.model.set('z_slice', this.model.itkVtkViewer.getZSlice())
        this.model.save_changes()
      }

      const onGradientOpacityChange = (opacity) => {
        if (opacity !== this.model.get('gradient_opacity')) {
          this.model.set('gradient_opacity', opacity)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.on('gradientOpacityChanged',
        onGradientOpacityChange
      )

      const onVolumeSampleDistanceChange = (distance) => {
        if (distance !== this.model.get('sample_distance')) {
          this.model.set('sample_distance', distance)
          this.model.save_changes()
        }
      }
      this.model.itkVtkViewer.on('volumeSampleDistanceChanged',
        onVolumeSampleDistanceChange
      )
    } // end use2D

    const onCameraChanged = macro.throttle(() => {
      const camera = new Float32Array(9)
      const viewProxy = this.model.itkVtkViewer.getViewProxy()
      camera.set(viewProxy.getCameraPosition(), 0)
      camera.set(viewProxy.getCameraFocalPoint(), 3)
      camera.set(viewProxy.getCameraViewUp(), 6)
      this.model.set('camera', camera)
      this.model.save_changes()
    }, 50)
    // If view-up has not been set, set initial value to itk-vtk-viewer default
    const camera = this.model.get('camera')
    const cameraData = !!camera.slice ? camera: new Float32Array(camera.buffer)
    const viewUp = cameraData.slice(6, 9)
    if (!viewUp[0] && !viewUp[1] && !viewUp[2]) {
      onCameraChanged()
    } else {
      this.camera_changed()
    }
    const interactor = this.model.itkVtkViewer.getViewProxy().getInteractor()
    interactor.onEndMouseMove(onCameraChanged)
    interactor.onEndMouseWheel(onCameraChanged)
    interactor.onEndPan(onCameraChanged)
    interactor.onEndPinch(onCameraChanged)
    const vtkCamera = this.model.itkVtkViewer.getViewProxy().getCamera()
    vtkCamera.onModified(onCameraChanged)
    const onClickSlicePoint = (lastPickedValues) => {
      this.model.set('clicked_slice_point', lastPickedValues)
      this.model.save_changes()
    }
    this.model.itkVtkViewer
      .on('imagePicked', onClickSlicePoint)

    const point_sets = this.model.get('point_sets')
    if (point_sets) {
      this.point_set_colors_changed()
      this.point_set_opacities_changed()
      this.point_set_sizes_changed()
      this.point_set_representations_changed()
    }

    const onPointSetColorChanged = (index, color) => {
      const modelColors = this.model.get('point_set_colors')
      const modelColor = modelColors.array[index]
      if (color !== modelColor) {
        const newColors = modelColors.array.slice()
        newColors[index] = color
        this.model.set('point_set_colors', { array: newColors, shape: modelColors.shape })
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('pointSetColorChanged',
      onPointSetColorChanged
    )

    const onPointSetOpacityChanged = (index, opacity) => {
      const modelOpacities = this.model.get('point_set_opacities')
      const modelOpacity = modelOpacities.array[index]
      if (opacity !== modelOpacity) {
        const newOpacities = modelOpacities.array.slice()
        newOpacities[index] = opacity
        this.model.set('point_set_opacities', { array: newOpacities, shape: modelOpacities.shape })
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('pointSetOpacityChanged',
      onPointSetOpacityChanged
    )

    const onPointSetRepresentationChanged = (index, representation) => {
      const modelRepresentations = this.model.get('point_set_representations')
      const modelRepresentation = modelRepresentations[index]
      if (representation !== modelRepresentation) {
        modelRepresentations[index] = representation
        this.model.set('point_set_representations', modelRepresentations)
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('pointSetRepresentationChanged',
      onPointSetRepresentationChanged
    )

    const onPointSetSizeChanged = (index, size) => {
      const modelSizes = this.model.get('point_set_sizes')
      const modelSize = modelSizes.array[index]
      if (size !== modelSize) {
        const newSize = modelSizes.array.slice()
        newSize[index] = size
        this.model.set('point_set_sizes', { array: newSize, shape: modelSizes.shape })
        this.model.save_changes()
      }
    }
    this.model.itkVtkViewer.on('pointSetSizeChanged',
      onPointSetSizeChanged
    )

    const geometries = this.model.get('geometries')
    if (geometries) {
      this.geometry_colors_changed()
      this.geometry_opacities_changed()
    }
    this.mode_changed()

    this.units_changed()
  },

  render: function () {
    this.model.on('change:rendered_image', this.rendered_image_changed, this)
    this.model.on(
      'change:rendered_label_image',
      this.rendered_label_image_changed,
      this
    )
    this.model.on('change:cmap', this.cmap_changed, this)
    this.model.on('change:lut', this.lut_changed, this)
    this.model.on('change:vmin', this.vmin_changed, this)
    this.model.on('change:vmax', this.vmax_changed, this)
    this.model.on('change:shadow', this.shadow_changed, this)
    this.model.on('change:slicing_planes', this.slicing_planes_changed, this)
    this.model.on('change:x_slice', this.x_slice_changed, this)
    this.model.on('change:y_slice', this.y_slice_changed, this)
    this.model.on('change:z_slice', this.z_slice_changed, this)
    this.model.on(
      'change:gradient_opacity',
      this.gradient_opacity_changed,
      this
    )
    this.model.on(
      'change:sample_distance',
      this.sample_distance_changed,
      this
    )
    this.model.on('change:blend_mode', this.blend_mode_changed, this)
    this.model.on('change:select_roi', this.select_roi_changed, this)
    this.model.on('change:_scale_factors', this.scale_factors_changed, this)
    this.model.on('change:point_sets', this.point_sets_changed, this)
    this.model.on(
      'change:point_set_colors',
      this.point_set_colors_changed,
      this
    )
    this.model.on(
      'change:point_set_opacities',
      this.point_set_opacities_changed,
      this
    )
    this.model.on(
      'change:point_set_sizes',
      this.point_set_sizes_changed,
      this
    )
    this.model.on(
      'change:point_set_representations',
      this.point_set_representations_changed,
      this
    )
    this.model.on('change:geometries', this.geometries_changed, this)
    this.model.on('change:geometry_colors', this.geometry_colors_changed, this)
    this.model.on(
      'change:geometry_opacities',
      this.geometry_opacities_changed,
      this
    )
    this.model.on('change:interpolation', this.interpolation_changed, this)
    this.model.on('change:ui_collapsed', this.ui_collapsed_changed, this)
    this.model.on('change:rotate', this.rotate_changed, this)
    this.model.on('change:annotations', this.annotations_changed, this)
    this.model.on('change:axes', this.axes_changed, this)
    this.model.on('change:mode', this.mode_changed, this)
    this.model.on('change:units', this.units_changed, this)
    this.model.on('change:camera', this.camera_changed, this)
    this.model.on('change:background', this.background_changed, this)
    this.model.on('change:opacity_gaussians', this.opacity_gaussians_changed, this)
    this.model.on('change:channels', this.channels_changed, this)
    this.model.on('change:label_image_names', this.label_image_names_changed, this)
    this.model.on('change:label_image_blend', this.label_image_blend_changed, this)
    this.model.on('change:label_image_weights', this.label_image_weights_changed, this)

    let toDecompress = []
    const rendered_image = this.model.get('rendered_image')
    if (rendered_image) {
      toDecompress.push(decompressImage(rendered_image))
    }
    const rendered_label_image = this.model.get('rendered_label_image')
    if (rendered_label_image) {
      toDecompress.push(decompressImage(rendered_label_image))
    }
    const point_sets = this.model.get('point_sets')
    if (point_sets && !!point_sets.length) {
      toDecompress = toDecompress.concat(point_sets.map(decompressPolyData))
    }
    const geometries = this.model.get('geometries')
    if (geometries && !!geometries.length) {
      toDecompress = toDecompress.concat(geometries.map(decompressPolyData))
    }
    const domWidgetView = this
    Promise.all(toDecompress).then((decompressedData) => {
      let index = 0
      let decompressedRenderedImage = null
      let decompressedRenderedLabelMap = null
      if (rendered_image) {
        decompressedRenderedImage = decompressedData[index]
        index++
      }
      if (rendered_label_image) {
        decompressedRenderedLabelMap = decompressedData[index]
        index++
      }
      let decompressedPointSets = null
      if (point_sets && !!point_sets.length) {
        decompressedPointSets = decompressedData.slice(
          index,
          index + point_sets.length
        )
        index += point_sets.length
      }
      let decompressedGeometries = null
      if (geometries && !!geometries.length) {
        decompressedGeometries = decompressedData.slice(
          index,
          index + geometries.length
        )
        index += geometries.length
      }

      return createRenderingPipeline(domWidgetView, {
        rendered_image: decompressedRenderedImage,
        rendered_label_image: decompressedRenderedLabelMap,
        point_sets: decompressedPointSets,
        geometries: decompressedGeometries
      })
    })
  },

  rendered_image_changed: function () {
    const rendered_image = this.model.get('rendered_image')
    if (rendered_image) {
      if (!rendered_image.data) {
        const domWidgetView = this
        decompressImage(rendered_image).then((decompressed) => {
          if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
            return Promise.resolve(
              replaceRenderedImage(domWidgetView, decompressed)
            )
          } else {
            return createRenderingPipeline(domWidgetView, {
              rendered_image: decompressed
            })
          }
        })
      } else {
        if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
          return Promise.resolve(replaceRenderedImage(this, rendered_image))
        } else {
          return Promise.resolve(
            createRenderingPipeline(this, { rendered_image })
          )
        }
      }
    }
    return Promise.resolve(null)
  },

  rendered_label_image_changed: function () {
    const rendered_label_image = this.model.get('rendered_label_image')
    if (rendered_label_image) {
      if (!rendered_label_image.data) {
        const domWidgetView = this
        decompressImage(rendered_label_image).then((decompressed) => {
          if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
            return Promise.resolve(
              replaceRenderedLabelMap(domWidgetView, decompressed)
            )
          } else {
            return createRenderingPipeline(domWidgetView, {
              rendered_label_image: decompressed
            })
          }
        })
      } else {
        if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
          return Promise.resolve(
            replaceRenderedLabelMap(this, rendered_label_image)
          )
        } else {
          return Promise.resolve(
            createRenderingPipeline(this, { rendered_label_image })
          )
        }
      }
    }
    return Promise.resolve(null)
  },

  label_image_names_changed: function () {
    const label_image_names = this.model.get('label_image_names')
    if (label_image_names && this.model.hasOwnProperty('itkVtkViewer')) {
      const labelMapNames = new Map(label_image_names)
      this.model.itkVtkViewer.setLabelMapNames(labelMapNames)
    }
  },

  label_image_weights_changed: function () {
    const label_image_weights = this.model.get('label_image_weights')
    if (label_image_weights && this.model.hasOwnProperty('itkVtkViewer')) {
      const labelMapWeights = !!label_image_weights.array ? Array.from(label_image_weights.array) : Array.from(label_image_weights)
      this.model.itkVtkViewer.setLabelMapWeights(labelMapWeights)
    }
  },

  label_image_blend_changed: function () {
    const labelMapBlend = this.model.get('label_image_blend')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setLabelMapBlend(labelMapBlend)
    }
  },

  point_sets_changed: function () {
    const point_sets = this.model.get('point_sets')
    if (point_sets && !!point_sets.length) {
      if (!point_sets[0].points.values) {
        const domWidgetView = this
        return Promise.all(point_sets.map(decompressPolyData)).then(
          (decompressed) => {
            if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
              return Promise.resolve(
                replacePointSets(domWidgetView, decompressed)
              )
            } else {
              return createRenderingPipeline(domWidgetView, { decompressed })
            }
          }
        )
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

  point_set_colors_changed: function () {
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const point_set_colors = this.model.get('point_set_colors').array
      const point_sets = this.model.get('point_sets')
      if (point_sets && !!point_sets.length) {
        point_sets.forEach((point_set, index) => {
          const color = point_set_colors.slice(index * 3, (index + 1) * 3)
          this.model.itkVtkViewer.setPointSetColor(index, color)
        })
      }
    }
  },

  point_set_opacities_changed: function () {
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const point_set_opacities = this.model.get('point_set_opacities').array
      const point_sets = this.model.get('point_sets')
      if (point_sets && !!point_sets.length) {
        point_sets.forEach((point_set, index) => {
          this.model.itkVtkViewer.setPointSetOpacity(
            index,
            point_set_opacities[index]
          )
        })
      }
    }
  },

  point_set_sizes_changed: function () {
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const point_set_sizes = this.model.get('point_set_sizes').array
      const point_sets = this.model.get('point_sets')
      if (point_sets && !!point_sets.length) {
        point_sets.forEach((point_set, index) => {
          this.model.itkVtkViewer.setPointSetSize(
            index,
            point_set_sizes[index]
          )
        })
      }
    }
  },

  point_set_representations_changed: function () {
    const point_set_representations = this.model.get(
      'point_set_representations'
    )
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const point_sets = this.model.get('point_sets')
      if (point_sets && !!point_sets.length) {
        point_set_representations.forEach((representation, index) => {
          switch (representation.toLowerCase()) {
            case 'hidden':
              this.model.itkVtkViewer.setPointSetRepresentation(
                index,
                'Hidden'
              )
              break
            case 'points':
              this.model.itkVtkViewer.setPointSetRepresentation(
                index,
                'Points'
              )
              break
            case 'spheres':
              this.model.itkVtkViewer.setPointSetRepresentation(
                index,
                'Spheres'
              )
              break
            default:
              this.model.itkVtkViewer.setPointSetRepresentation(
                index,
                'Points'
              )
          }
        })
      }
    }
  },

  geometries_changed: function () {
    const geometries = this.model.get('geometries')
    if (geometries && !!geometries.length) {
      if (!geometries[0].points.values) {
        const domWidgetView = this
        return Promise.all(geometries.map(decompressPolyData)).then(
          (decompressed) => {
            if (domWidgetView.model.hasOwnProperty('itkVtkViewer')) {
              return Promise.resolve(
                replaceGeometries(domWidgetView, decompressed)
              )
            } else {
              return createRenderingPipeline(domWidgetView, { decompressed })
            }
          }
        )
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

  geometry_colors_changed: function () {
    const geometryColors = this.model.get('geometry_colors').array
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const geometries = this.model.get('geometries')
      if (geometries && !!geometries.length) {
        geometries.forEach((geometry, index) => {
          const color = geometryColors.slice(index * 3, (index + 1) * 3)
          this.model.itkVtkViewer.setGeometryColor(index, color)
        })
      }
    }
  },

  geometry_opacities_changed: function () {
    const geometryOpacities = this.model.get('geometry_opacities').array
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const geometries = this.model.get('geometries')
      if (geometries && !!geometries.length) {
        geometries.forEach((geometry, index) => {
          this.model.itkVtkViewer.setGeometryOpacity(
            index,
            geometryOpacities[index]
          )
        })
      }
    }
  },

  ui_collapsed_changed: function () {
    const uiCollapsed = this.model.get('ui_collapsed')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setUserInterfaceCollapsed(uiCollapsed)
    }
  },

  rotate_changed: function () {
    const rotate = this.model.get('rotate')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setRotateEnabled(rotate)
    }
  },

  annotations_changed: function () {
    const annotations = this.model.get('annotations')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setAnnotationsEnabled(annotations)
    }
  },

  axes_changed: function () {
    const axes = this.model.get('axes')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setAxesEnabled(axes)
    }
  },

  mode_changed: function () {
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
          const representation = viewProxy.getRepresentations()[0]
          const shadow = this.model.get('shadow')
          !!representation && representation.setUseShadow(shadow)
          break
        default:
          throw new Error('Unknown view mode')
      }
    }
  },

  units_changed: function () {
    const units = this.model.get('units')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const viewProxy = this.model.itkVtkViewer.getViewProxy()
      viewProxy.setUnits(units)
    }
  },

  camera_changed: function () {
    const camera = this.model.get('camera')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const cameraData = !!camera.slice ? camera: new Float32Array(camera.buffer)
      const viewProxy = this.model.itkVtkViewer.getViewProxy()
      viewProxy.setCameraPosition(...cameraData.subarray(0, 3))
      viewProxy.setCameraFocalPoint(...cameraData.subarray(3, 6))
      viewProxy.setCameraViewUp(...cameraData.subarray(6, 9))
      viewProxy.getCamera().computeDistance()
      viewProxy.renderLater()
    }
  },

  interpolation_changed: function () {
    const interpolation = this.model.get('interpolation')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setInterpolationEnabled(interpolation)
    }
  },

  cmap_changed: function () {
    const cmap = this.model.get('cmap')
    if (cmap !== null && this.model.hasOwnProperty('itkVtkViewer')) {
      for (let index = 0; index < cmap.length; index++) {
        if (cmap[index].startsWith('Custom')) {
          const lutProxies = this.model.itkVtkViewer.getLookupTableProxies()
          const lutProxy = lutProxies[index]
          const customCmap = this.model.get('_custom_cmap')
          const numPoints = customCmap.shape[0]
          const rgbPoints = new Array(numPoints)
          const cmapArray = customCmap.array
          const step = 1.0 / (numPoints - 1)
          let xx = 0.0
          for (let pointIndex = 0; pointIndex < numPoints; pointIndex++) {
            const rgb = cmapArray.slice(pointIndex * 3, (pointIndex + 1) * 3)
            rgbPoints[pointIndex] = [xx, rgb[0], rgb[1], rgb[2]]
            xx += step
          }
          lutProxy.setRGBPoints(rgbPoints)
        }
        this.model.colorMapLoopBreak = true
        this.model.itkVtkViewer.setColorMap(index, cmap[index])
        this.model.colorMapLoopBreak = false
      }
    }
  },

  lut_changed: function () {
    const lut = this.model.get('lut')
    if (lut !== null && this.model.hasOwnProperty('itkVtkViewer')) {
      //if (lut.startsWith('Custom')) {
      // -> from cmap, to be updated for lookup table
        //const lutProxies = this.model.itkVtkViewer.getLookupTableProxies()
        //const lutProxy = lutProxies[index]
        //const customCmap = this.model.get('_custom_cmap')
        //const numPoints = customCmap.shape[0]
        //const rgbPoints = new Array(numPoints)
        //const cmapArray = customCmap.array
        //const step = 1.0 / (numPoints - 1)
        //let xx = 0.0
        //for (let pointIndex = 0; pointIndex < numPoints; pointIndex++) {
          //const rgb = cmapArray.slice(pointIndex * 3, (pointIndex + 1) * 3)
          //rgbPoints[pointIndex] = [xx, rgb[0], rgb[1], rgb[2]]
          //xx += step
        //}
        //lutProxy.setRGBPoints(rgbPoints)
      //}
      this.model.itkVtkViewer.setLookupTable(lut)
    }
  },

  vmin_changed: function () {
    const vmin = this.model.get('vmin')
    if (vmin !== null && this.model.hasOwnProperty('itkVtkViewer')) {
      const rendered_image = this.model.get('rendered_image')
      for (let component = 0; component < rendered_image.imageType.components; component++) {
        let colorRange = this.model.itkVtkViewer.getColorRange(component)
        if (colorRange[0] && vmin.length > component) {
          colorRange[0] = vmin[component]
          this.model.itkVtkViewer.setColorRange(component, colorRange)
        }
      }
    }
  },

  vmax_changed: function () {
    const vmax = this.model.get('vmax')
    if (vmax !== null && this.model.hasOwnProperty('itkVtkViewer')) {
      const rendered_image = this.model.get('rendered_image')
      for (let component = 0; component < rendered_image.imageType.components; component++) {
        let colorRange = this.model.itkVtkViewer.getColorRange(component)
        if (colorRange[1] && vmax.length > component) {
          colorRange[1] = vmax[component]
          this.model.itkVtkViewer.setColorRange(component, colorRange)
        }
      }
    }
  },

  shadow_changed: function () {
    const shadow = this.model.get('shadow')
    if (this.model.hasOwnProperty('itkVtkViewer') && !this.model.use2D) {
      this.model.itkVtkViewer.setShadowEnabled(shadow)
    }
  },

  slicing_planes_changed: function () {
    const slicing_planes = this.model.get('slicing_planes')
    if (this.model.hasOwnProperty('itkVtkViewer') && !this.model.use2D) {
      this.model.itkVtkViewer.setSlicingPlanesEnabled(slicing_planes)
    }
  },

  x_slice_changed: function () {
    const position = this.model.get('x_slice')
    if (
      this.model.hasOwnProperty('itkVtkViewer') &&
      !this.model.use2D &&
      position !== null
    ) {
      this.model.itkVtkViewer.setXSlice(position)
    }
  },

  y_slice_changed: function () {
    const position = this.model.get('y_slice')
    if (
      this.model.hasOwnProperty('itkVtkViewer') &&
      !this.model.use2D &&
      position !== null
    ) {
      this.model.itkVtkViewer.setYSlice(position)
    }
  },

  z_slice_changed: function () {
    const position = this.model.get('z_slice')
    if (
      this.model.hasOwnProperty('itkVtkViewer') &&
      !this.model.use2D &&
      position !== null
    ) {
      this.model.itkVtkViewer.setZSlice(position)
    }
  },

  gradient_opacity_changed: function () {
    const gradient_opacity = this.model.get('gradient_opacity')
    if (this.model.hasOwnProperty('itkVtkViewer') && !this.model.use2D) {
      this.model.itkVtkViewer.setGradientOpacity(gradient_opacity)
    }
  },

  sample_distance_changed: function () {
    const sample_distance = this.model.get('sample_distance')
    if (this.model.hasOwnProperty('itkVtkViewer') && !this.model.use2D) {
      this.model.itkVtkViewer.setVolumeSampleDistance(sample_distance)
    }
  },

  opacity_gaussians_changed: function () {
    const opacity_gaussians = this.model.get('opacity_gaussians')
    if (this.model.hasOwnProperty('itkVtkViewer') && !this.model.use2D) {
      this.model.itkVtkViewer.setOpacityGaussians(opacity_gaussians)
    }
  },

  channels_changed: function () {
    const channels = this.model.get('channels')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setComponentVisibilities(channels)
    }
  },

  blend_mode_changed: function () {
    const blend = this.model.get('blend_mode')
    if (this.model.hasOwnProperty('itkVtkViewer') && !this.model.use2D) {
      switch (blend) {
        case 'composite':
          this.model.itkVtkViewer.setBlendMode(0)
          break
        case 'max':
          this.model.itkVtkViewer.setBlendMode(1)
          break
        case 'min':
          this.model.itkVtkViewer.setBlendMode(2)
          break
        case 'average':
          this.model.itkVtkViewer.setBlendMode(3)
          break
        default:
          throw new Error('Unexpected blend mode')
      }
    }
  },

  background_changed: function () {
    const background = this.model.get('background')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setBackgroundColor(background)
    }
  },

  select_roi_changed: function () {
    const select_roi = this.model.get('select_roi')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      this.model.itkVtkViewer.setCroppingPlanesEnabled(select_roi)
    }
  },

  scale_factors_changed: function () {
    let scaleFactors = this.model.get('_scale_factors')
    if (this.model.hasOwnProperty('itkVtkViewer')) {
      const viewProxy = this.model.itkVtkViewer.getViewProxy()
      if (typeof scaleFactors[0] === 'undefined') {
        scaleFactors = new Uint8Array(scaleFactors.buffer.buffer)
      }
      if (
        scaleFactors[0] === 1 &&
        scaleFactors[1] === 1 &&
        scaleFactors[2] === 1
      ) {
        viewProxy.setSeCornerAnnotation(`${ANNOTATION_DEFAULT}`)
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
        viewProxy.setSeCornerAnnotation(
          `${ANNOTATION_CUSTOM_PREFIX}${scaleIndex}${ANNOTATION_CUSTOM_POSTFIX}`
        )
      }
    }
  },

  initialize_viewer: function () {
    this.initialize_itkVtkViewer()
    // possible to override in extensions
  }
})

module.exports = {
  ViewerModel: ViewerModel,
  ViewerView: ViewerView
}
