// Based off of 
// https://gist.github.com/lucasea777/8801440f6b622edd3553c8a7304bf94e

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdbool.h>

static PyObject* compress(PyObject* self, PyObject* args)
{
  const char* source;
  int len_source=0;
  int i=0;
  int lookback_range = 0;
  int max_copy_length = 0;
  int header_pos = 0;
  int src_pos = 0;
  int out_pos = 0;
  bool done = false;
  int best_size = 0x1000;
  int compr_stream = 0;
  char compressed_data[2][0x10000];
  int compressed_lengths[2];
  int mask = 0;
  int addendum_size = 0;
  int lookback = 0;
  int lookback_st = 0;
  int lookback_end = 0;
  int cur_len = 0;
  int best_len = 0;
  int best_len_st = 0;
  int ret_choice = 0;
  PyObject* result;
  PyObject* arg1;
  Py_buffer buffer;

  compressed_lengths[0] = compressed_lengths[1] = 0x10000;

  if (!PyArg_ParseTuple(args, "y*", &buffer))
    return NULL;

  // if (!PyObject_GetBuffer(arg1, &buffer, PyBUF_SIMPLE))
  //   return NULL;

  source = buffer.buf;
  len_source = buffer.len;

  for(i=0;i<2;i++){
    // i=0: use 0x07FF for the range, 0xF800 for the max copy length
    // i=1: use 0x0FFF for the range, 0xF000 for the max copy length
    lookback_range = 0x07FF | (i << 11);

    // max_copy_length = 0xFFFF ^ lookback_range (bits used)
    max_copy_length = (0xFFFF ^ lookback_range) >> (16-(5-i));
    max_copy_length += 3;

    src_pos = 0;
    
    // First two bytes are main body length
    // Next byte will be the first packet's header
    out_pos = 2;
    done = false;

    while (!done){
      if (out_pos >= best_size){
	break;
      }
      header_pos = out_pos;

      // compressed_data[][] was uninitialized.  This is no problem except that
      // we need to make sure that the header bytes start off as 0s.
      compressed_data[i][header_pos] = 0;
      
      out_pos += 1;

      // printf("out_pos: %04X\n", out_pos);
      for(int bit=0; bit<8; bit++){
	
	// While filling a packet we ran out of source.
	if(src_pos == len_source){
	  if(bit == 0){
	    // If bit == 0, then we ran out after filling a packet.
	    // This means no addendum.
	    compressed_data[i][header_pos] = 0xC0*(1-i);

	    // Record size
	    compressed_lengths[i] = header_pos + 1;
	  }
	  else{
	    // Otherwise, we're mid-packet.  The packet becomes the addendum
	    // Set unused bits of header for addendum header
	    mask = (0xFF << bit) & 0xFF;
	    compressed_data[i][header_pos] |= mask;

	    // shift the addendum packet down three bytes
	    addendum_size = out_pos-header_pos;
	    for(int j=addendum_size-1;j>=0;j--){
	      compressed_data[i][header_pos+3+j] = \
		compressed_data[i][header_pos+j];
	    }
		
	    // copy range + addendum length
	    compressed_data[i][header_pos] = 0xC0*(1-i) | bit;

	    // total compressed length (remember shift by 3)
	    // compressed_data[i][header_pos+1:header_pos+3] =	\
	    //   to_little_endian(out_pos+3, 2);
	    compressed_data[i][header_pos+1] = (out_pos+3) % 0x100;
	    compressed_data[i][header_pos+2] = (int)((out_pos+3) / 0x100);

	    // Truncate to used size
	    compressed_data[i][out_pos+3] = 0xC0*(1-i);
	    compressed_lengths[i] = out_pos+4;
	  }

	  // compressed_data[i][0:2] =				\
	  //   to_little_endian(header_pos-2, 2)
	  compressed_data[i][0] = (header_pos-2) % 0x100;
	  compressed_data[i][1] = (int)((header_pos-2) / 0x100);

	  done = true;
	  break;
	}

	lookback_st = (src_pos - lookback_range) > 0? \
	  (src_pos - lookback_range) : 0;
	lookback_end = src_pos;

	best_len = 0;
	best_len_st = 0;

	for(int start=lookback_st; start<lookback_end; start++){
	  cur_len = 0;

	  while((src_pos + cur_len < len_source) && \
		(cur_len < max_copy_length) && \
		source[start+cur_len] == source[src_pos+cur_len]){
	    cur_len += 1;
	  }

	  // Update best match if needed
	  if(cur_len >= best_len){
	    best_len = cur_len;
	    best_len_st = start;
	    if(cur_len == max_copy_length){
	      break;
	    }
	  } 
	}

	if(best_len > 2){
	  // We matched at least 3 bytes, so we'll use compression

	  // Mark the header to use compression for this bit
	  compressed_data[i][header_pos] |= (1 << bit);

	  lookback = src_pos - best_len_st;
	  // # print(f"\tlookback: {lookback:04X}")

	  // length is encoded with a -3 because there are always at
	  // least 3 bytes to copy.  The length is shifted to the most
	  // significant bits.  The shift depends on i.
	  // length = ((best_len-3) << (16-(5-i)));

	  compr_stream = lookback | ((best_len-3) << (16-(5-i)));

	  // compressed_data[i][out_pos:out_pos+2] =		\
	  //   to_little_endian(compr_stream, 2)
	  compressed_data[i][out_pos] = compr_stream % 0x100;
	  compressed_data[i][out_pos+1] = (int)(compr_stream / 0x100);
	  
	  out_pos += 2;
	  src_pos += best_len;
	}
	else{
	  // We failed to match 3 or more bytes, so just copy a byte
	  compressed_data[i][out_pos] = source[src_pos];
	  out_pos += 1;
	  src_pos += 1;
	}
      }
    }

    if (compressed_lengths[i] < best_size){
      best_size = compressed_lengths[i];
    }
  }

  if(compressed_lengths[0] <= compressed_lengths[1]){
    ret_choice = 0;
  }
  else{
    ret_choice = 1;
  }
  
  result = Py_BuildValue("y#",
			 &compressed_data[ret_choice][0],
			 compressed_lengths[ret_choice]);
  PyBuffer_Release(&buffer);
  return result;
}



static PyMethodDef CompressMethods[] = {
    {"compress", compress, METH_VARARGS, "compress an event."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef ctcompress =
{
    PyModuleDef_HEAD_INIT,
    "ctcompress",     /* name of module */
    "",          /* module documentation, may be NULL */
    -1,          /* size of per-interpreter state of the module, or -1 if  the module keeps state in global variables. */
    CompressMethods
};

PyMODINIT_FUNC PyInit_ctcompress(void)
{
  return PyModule_Create(&ctcompress);
}
