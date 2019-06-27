import itk
import itkwidgets.trait_types as trait_types
import numpy as np

def test_ITKImage():
    info_text = trait_types.ITKImage.info_text
    assert(info_text.find('image') != -1)

TestPixelType = itk.ctype('unsigned char')
TestDimension = 2
TestImageType = itk.Image[TestPixelType, TestDimension]
test_image  = TestImageType.New()
test_size = (6, 6)
region = itk.ImageRegion[TestDimension](test_size)
test_image.SetRegions(region)
test_image.Allocate()
test_image.FillBuffer(0)
index = itk.Index[TestDimension]()
index.Fill(0)
test_image.SetPixel(index, 4)
index[0] = 5
test_image.SetPixel(index, 66)
index[1] = 3
test_image.SetPixel(index, 87)
index[0] = 3
test_image.SetPixel(index, 22)

def test_itkimage_to_json():
    itkimage_to_json = trait_types.itkimage_to_json
    asjson = itkimage_to_json(test_image)
    imageType = asjson['imageType']
    assert(imageType['dimension'] == TestDimension)
    assert(imageType['componentType'] == 'uint8_t')
    assert(imageType['pixelType'] == 1)
    assert(imageType['components'] == 1)
    assert(asjson['origin'] == (0.0, 0.0))
    assert(asjson['spacing'] == (1.0, 1.0))
    assert(asjson['size'] == test_size)
    assert(asjson['direction']['data'] == [1.0, 0.0, 0.0, 1.0])
    assert(asjson['direction']['rows'] == 2)
    assert(asjson['direction']['columns'] == 2)
    baseline = np.array([40,181,47,253,32,36,157,0,0,88,4,0,0,0,
        0,66,0,22,0,87,0,2,0,192,32,50,48,2], dtype=np.uint8)
    print(np.array(asjson['compressedData'], dtype=np.uint8))
    assert((np.array(asjson['compressedData'], dtype=np.uint8) == baseline).all())

def test_itkimage_from_json():
    itkimage_to_json = trait_types.itkimage_to_json
    asjson = itkimage_to_json(test_image)
    itkimage_from_json = trait_types.itkimage_from_json
    asimage = itkimage_from_json(asjson)
    assert(asimage.GetImageDimension() == TestDimension)
    assert(asimage.GetNumberOfComponentsPerPixel()== 1)
    assert(tuple(asimage.GetOrigin()) == (0.0, 0.0))
    assert(tuple(asimage.GetSpacing()) == (1.0, 1.0))
    assert(tuple(asimage.GetBufferedRegion().GetSize()) == test_size)
    assert(asimage.GetPixel((0,0)) == 4)
    assert(asimage.GetPixel((5,0)) == 66)
    assert(asimage.GetPixel((5,3)) == 87)
    assert(asimage.GetPixel((3,3)) == 22)

def test_VTKPolyData():
    info_text = trait_types.VTKPolyData.info_text
    assert(info_text.find('vtk.js') != -1)
