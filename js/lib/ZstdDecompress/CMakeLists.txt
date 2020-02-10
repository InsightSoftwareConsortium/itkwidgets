cmake_minimum_required(VERSION 3.10)
project(ZstdDecompress)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/zstd/lib/)
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/zstd/lib/common)

set(ZstdExeSources
  ZstdDecompress.cxx
  zstd/lib/decompress/zstd_decompress.c
  zstd/lib/decompress/huf_decompress.c
  zstd/lib/decompress/zstd_ddict.c
  zstd/lib/decompress/zstd_decompress_block.c
  zstd/lib/common/zstd_common.c
  zstd/lib/common/error_private.c
  zstd/lib/common/xxhash.c
  zstd/lib/common/entropy_common.c
  zstd/lib/common/fse_decompress.c
  )

if(EMSCRIPTEN)
  include(ITKBridgeJavaScript)
  web_add_executable(ZstdDecompress ${ZstdExeSources})
else()
  add_executable(ZstdDecompress ${ZstdExeSources})
endif()


enable_testing()
add_test(NAME ZstdDecompressTest
  COMMAND ZstdDecompress
    ${CMAKE_CURRENT_SOURCE_DIR}/input.bin.zstd
    ${CMAKE_CURRENT_BINARY_DIR}/output.bin
    36
  )
