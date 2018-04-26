// Based on zstd-codec:
// https://github.com/yoshihitoh/zstd-codec
//
//
#include "stdio.h"
#include "stdlib.h"
#include "limits.h"

#include "zstd.h"

#if DEBUG
# define USE_DEBUG_ERROR_HANDLER (1)
#endif


static const int ERR_UNKNOWN = -1;
static const int ERR_SIZE_TOO_LARGE = -2;

static const int ERR_ALLOCATE_CCTX = -3;
static const int ERR_ALLOCATE_DCTX = -4;

static const int ERR_LOAD_CDICT = -5;
static const int ERR_LOAD_DDICT = -6;


class IErrorHandler
{
public:
    virtual void OnZstdError(size_t rc) = 0;
    virtual void OnSizeError(size_t rc) = 0;
};


#if USE_DEBUG_ERROR_HANDLER
class DebugErrorHandler : public IErrorHandler
{
public:
    virtual void OnZstdError(size_t rc)
    {
        printf("## zstd error: %s\n", ZSTD_getErrorName(rc));
    }

    virtual void OnSizeError(size_t rc)
    {
        printf("## size error: %s\n", ZSTD_getErrorName(rc));
    }
};


static DebugErrorHandler s_debug_handler;


#endif // USE_DEBUG_ERROR_HANDLER
static int ToResult(size_t rc, IErrorHandler* error_handler = NULL)
{
#if USE_DEBUG_ERROR_HANDLER
    if (error_handler == NULL) {
        error_handler = &s_debug_handler;
    }
#endif

    if (ZSTD_isError(rc)) {
        if (error_handler != NULL) error_handler->OnZstdError(rc);
        return ERR_UNKNOWN;
    }
    else if (rc >= static_cast<size_t>(INT_MAX)) {
        if (error_handler != NULL) error_handler->OnSizeError(rc);
        return ERR_SIZE_TOO_LARGE;
    }

    return static_cast<int>(rc);
}

int decompress(void * dest, size_t destCapacity, const void * src, size_t compressedSize )
{
    const size_t rc = ZSTD_decompress(dest, destCapacity, src, compressedSize);
    return ToResult(rc);
}


int main( int argc, char * argv[] )
{
  if(argc < 4)
    {
    fprintf(stderr, "Insufficient arguments!\n");
    fprintf(stderr, "Usage: ZstdDecompress input.bin output.bin outputFileSize");
    return 1;
    }

  const char * inputFileName = argv[1];
  const char * outputFileName = argv[2];
  unsigned long outputFileLength = (unsigned long) atol(argv[3]);

  unsigned long inputFileLength;

  FILE * inputFile = fopen(inputFileName, "rb");
  if( !inputFile )
  {
    fprintf(stderr, "Unable to open file %s", inputFileName);
    return 1;
  }

  fseek(inputFile, 0, SEEK_END);
  inputFileLength = ftell(inputFile);
  fseek(inputFile, 0, SEEK_SET);

  char * inputBuffer = (char *) malloc(inputFileLength+1);
  if( !inputBuffer )
  {
    fprintf(stderr, "Memory error!");
    fclose(inputFile);
    return 1;
  }

  fread(inputBuffer, inputFileLength, 1, inputFile);
  fclose(inputFile);

  char * outputBuffer = (char *) malloc(outputFileLength+1);
  if( !outputBuffer )
  {
    fprintf(stderr, "Memory error!");
    free(inputBuffer);
    fclose(inputFile);
    return 1;
  }

  const int result = decompress( outputBuffer, outputFileLength, inputBuffer, inputFileLength );
  printf("result: %d", result);

  FILE * outputFile = fopen(outputFileName, "wb");
  if( !outputFile )
  {
    fprintf(stderr, "Unable to open file %s", outputFileName);
    free(inputBuffer);
    free(outputBuffer);
    fclose(inputFile);
    return 1;
  }

  fwrite( outputBuffer, outputFileLength, 1, outputFile );

  free(outputBuffer);
  free(inputBuffer);
  fclose(outputFile);

  return 0;
}
