import 'babel-polyfill'
import widgets from '@jupyter-widgets/base';
import _ from 'lodash';
import  base64js from 'base64-js';
import vtkITKHelper from 'vtk.js/Sources/Common/DataModel/ITKHelper';
import createViewer from 'itk-vtk-image-viewer/src/createViewer';
import IntTypes from 'itk/IntTypes'
import FloatTypes from 'itk/FloatTypes'

const serialize_itkimage = (itkimage) => {
  if (itkimage === null) {
    return null
  } else {
    const byteArray = itkimage.data
    const b64Buffer = base64js.fromByteArray(Uint8Array(byteArray.buffer))
    itkimage.data = b64Buffer
    return itkimage
  }
}

const deserialize_itkimage = (jsonitkimage) => {
  if (jsonitkimage === null) {
    return null
  } else {
    const b64Buffer = jsonitkimage.data
    let byteArray = base64js.toByteArray(b64Buffer)
    switch (jsonitkimage.imageType.componentType) {
      case IntTypes.Int8:
        byteArray = new Int8Array(byteArray.buffer)
        break
      case IntTypes.UInt8:
        // byteArray = new Uint8Array(byteArray)
        break
      case IntTypes.Int16:
        byteArray = new Int16Array(byteArray.buffer)
        break
      case IntTypes.UInt16:
        byteArray = new Uint16Array(byteArray.buffer)
        break
      case IntTypes.Int32:
        byteArray = new Int32Array(byteArray.buffer)
        break
      case IntTypes.UInt32:
        byteArray = new Uint32Array(byteArray.buffer)
        break
      // not currently defined in JavaScript
      //case IntTypes.Int64:
        //byteArray = new Int64Array(byteArray)
        //break
      //case IntTypes.UInt64:
        //byteArray = new Uint64Array(byteArray)
        //break
      case FloatTypes.Float32:
        byteArray = new Float32Array(byteArray.buffer)
        break
      case FloatTypes.Float64:
        byteArray = new Float64Array(byteArray.buffer)
        break
      default:
        console.error('Unexpected component type: ' + jsonitkimage.imageType.componentType)
    }
    jsonitkimage.data = byteArray
    return jsonitkimage
  }
}

var ViewerModel = widgets.DOMWidgetModel.extend({
  defaults: function() {
    return _.extend(widgets.DOMWidgetModel.prototype.defaults(), {
      _model_name: 'ViewerModel',
      _view_name: 'ViewerView',
      _model_module: 'itk-jupyter-widgets',
      _view_module: 'itk-jupyter-widgets',
      _model_module_version: '0.1.0',
      _view_module_version: '0.1.0',
      image: null
    })
  }}, {
  serializers: _.extend({
    image: { serialize: serialize_itkimage, deserialize: deserialize_itkimage }
  }, widgets.DOMWidgetModel.serializers)
})


// Custom View. Renders the widget model.
var ViewerView = widgets.DOMWidgetView.extend({
  render: function() {
    this.image_changed()
    this.model.on('change:image', this.image_changed, this)
  },

  image_changed: function() {
    const image = this.model.get('image')
    if(image) {
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
      this._renderingPipeline = createViewer(this.el, {
        viewerConfig: viewerConfig,
        image: imageData,
        use2D: !is3D,
      })
    }
  }
});

module.exports = {
  ViewerModel : ViewerModel,
  ViewerView : ViewerView
};
