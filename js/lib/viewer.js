import 'babel-polyfill'
const widgets = require('@jupyter-widgets/base')
const  _ = require('lodash')
import vtkITKHelper from 'vtk.js/Sources/Common/DataModel/ITKHelper'
import createViewer from 'itk-vtk-image-viewer/src/createViewer'
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
      _model_module_version: '0.10.2',
      _view_module_version: '0.10.2',
      image: null
    })
  }}, {
  serializers: _.extend({
    image: { serialize: serialize_itkimage, deserialize: deserialize_itkimage }
  }, widgets.DOMWidgetModel.serializers)
})


const createRenderingPipeline = (domWidgetView, image) => {
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
  const viewerConfig = {
    backgroundColor: [1.0, 1.0, 1.0],
    containerStyle: containerStyle,
  };
  const imageData = vtkITKHelper.convertItkToVtkImage(image)
  const is3D = image.imageType.dimension === 3
  domWidgetView._renderingPipeline = createViewer(domWidgetView.el, {
    viewerConfig: viewerConfig,
    image: imageData,
    use2D: !is3D,
  })
}


// Custom View. Renders the widget model.
const ViewerView = widgets.DOMWidgetView.extend({
  render: function() {
    this.image_changed()
    this.model.on('change:image', this.image_changed, this)
  },

  image_changed: function() {
    const image = this.model.get('image')
    if(image) {
      if (!image.data) {
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
        const domWidgetView = this
        const t0 = performance.now()
        runPipelineBrowser(null, pipelinePath, args, desiredOutputs, inputs)
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
              // not currently defined in JavaScript
              //case IntTypes.Int64:
                //break
              //case IntTypes.UInt64:
                //break
              case FloatTypes.Float32:
                image.data = new Float32Array(outputs[0].data.buffer)
                break
              case FloatTypes.Float64:
                image.data = new Float64Array(outputs[0].data.buffer)
                break
              default:
                console.error('Unexpected component type: ' + image.imageType.componentType)
            }
            createRenderingPipeline(domWidgetView, image)
          })
      } else {
        createRenderingPipeline(this, image)
      }
    }
  }
});

module.exports = {
  ViewerModel : ViewerModel,
  ViewerView : ViewerView
};
