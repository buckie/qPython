Types conversions
=================


Data types supported by q and Python are incompatible and thus require 
additional translation. This page describes rules used for converting data types
between q and Python.

The translation mechanism used in qPython library is designed to:
 - deserialized message from kdb+ can be serialized and send back to kdb+ 
   without additional processing,
 - end user can enforce type hinting for translation,
 - efficient storage for tables and lists is backed with numpy arrays.


Atoms
***** 

While parsing IPC message atom q types are translated to Python types according
to this table:

===============  ============ =====================================
 q  type          q num type   Python type        
===============  ============ =====================================
 ``bool``         -1           ``numpy.bool\_``        
 ``guid``         -2           ``UUID``
 ``byte``         -4           ``numpy.byte``         
 ``short``        -5           ``numpy.int16``        
 ``integer``      -6           ``numpy.int32``        
 ``long``         -7           ``numpy.int64``        
 ``real``         -8           ``numpy.float32``      
 ``float``        -9           ``numpy.float64``      
 ``character``    -10          single element ``str``
 ``timestamp``    -12          ``QTemporal  numpy.datetime64   ns``
 ``month``        -13          ``QTemporal  numpy.datetime64   M``
 ``date``         -14          ``QTemporal  numpy.datetime64   D``
 ``datetime``     -15          ``QTemporal  numpy.datetime64   ms``
 ``timespan``     -16          ``QTemporal  numpy.timedelta64  ns``
 ``minute``       -17          ``QTemporal  numpy.timedelta64  m``
 ``second``       -18          ``QTemporal  numpy.timedelta64  s``
 ``time``         -19          ``QTemporal  numpy.timedelta64  ms``
===============  ============ =====================================

.. note:: Temporal types in Python are represented as instances of 
          :class:`.qtemporal.QTemporal` wrapping over ``numpy.datetime64`` or
          ``numpy.timedelta64`` with specified resolution.


During the serialization to IPC protocol, Python types are mapped to q as 
described in the table:

=====================================  ================  ============
 Python type                            q type            q num type 
=====================================  ================  ============
 ``bool``                               ``bool``          -1         
 ---                                    ``byte``          -4         
 ---                                    ``short``         -5         
 ``int``                                ``int``           -6         
 ``long``                               ``long``          -7         
 ---                                    ``real``          -8         
 ``double``                             ``float``         -9         
 ``numpy.bool``                         ``bool``          -1         
 ``numpy.byte``                         ``byte``          -4         
 ``numpy.int16``                        ``short``         -5         
 ``numpy.int32``                        ``int``           -6         
 ``numpy.int64``                        ``long``          -7         
 ``numpy.float32``                      ``real``          -8         
 ``numpy.float64``                      ``float``         -9         
 single element ``str``                 ``character``     -10        
 ``QTemporal  numpy.datetime64   ns``   ``timestamp``     -12                
 ``QTemporal  numpy.datetime64   M``    ``month``         -13                
 ``QTemporal  numpy.datetime64   D``    ``date``          -14              
 ``QTemporal  numpy.datetime64   ms``   ``datetime``      -15              
 ``QTemporal  numpy.timedelta64  ns``   ``timespan``      -16              
 ``QTemporal  numpy.timedelta64  m``    ``minute``        -17              
 ``QTemporal  numpy.timedelta64  s``    ``second``        -18              
 ``QTemporal  numpy.timedelta64  ms``   ``time``          -19              
=====================================  ================  ============


String and symbols
******************

In order to distinguish symbols and strings on the Python side, following rules 
apply:

- q symbols are represented as ``numpy.string_`` type,
- q strings are mapped to plain Python strings.

::

    # `quickbrownfoxjumpsoveralazydog
    numpy.string_('quickbrownfoxjumpsoveralazydog')
    
    # "quick brown fox jumps over a lazy dog"
    'quick brown fox jumps over a lazy dog'



Lists
*****

qPython represents deserialized q lists as instances of 
:class:`.qcollection.QList` are mapped to `numpy` arrays.

::

    # (0x01;0x02;0xff)
    qlist(numpy.array([0x01, 0x02, 0xff], dtype=numpy.byte))
    
    # <class 'qpython.qcollection.QList'> 
    # numpy.dtype: int8 
    # meta.qtype: -4
    # str: [ 1  2 -1]


Generic lists are represented as a plain Python lists.

::

    # (1;`bcd;"0bc";5.5e)
    [numpy.int64(1), numpy.string_('bcd'), '0bc', numpy.float32(5.5)]


While serializing Python data to q following heuristic is applied:

- instances of :class:`.qcollection.QList` and 
  :class:`.qcollection.QTemporalList` are serialized according to type indicator 
  (``meta.qtype``)::
  
    qlist([1, 2, 3], qtype = QSHORT_LIST)
    # (1h;2h;3h)
    
    qlist([366, 121, qnull(QDATE)], qtype=QDATE_LIST)
    # '2001.01.01 2000.05.01 0Nd'
    
    qlist(numpy.array([uuid.UUID('8c680a01-5a49-5aab-5a65-d4bfddb6a661'), qnull(QGUID)]), qtype=QGUID_LIST)
    # ("G"$"8c680a01-5a49-5aab-5a65-d4bfddb6a661"; 0Ng)
  
- `numpy` arrays are serialized according to type of their `dtype` value::
 
    numpy.array([1, 2, 3], dtype=numpy.int32)
    # (1i;2i;3i)
  
- if `numpy` array `dtype` is not recognized by qPython, result q type is 
  determined by type of the first element in the array,
- Python lists and tuples are represented as q generic lists::

    [numpy.int64(42), None, numpy.string_('foo')]
    (numpy.int64(42), None, numpy.string_('foo'))
    # (42;::;`foo)
    
.. note:: `numpy` arrays with ``dtype==|S1`` are represented as atom character.


qPython provides an utility function :func:`.qcollection.qlist` 
which simplifies creation of :class:`.qcollection.QList` and 
:class:`.qcollection.QTemporalList` instances.

The :py:mod:`.qtype` module defines :py:const:`~.qtype.QSTRING_LIST` const
which simplifies creation of string lists::

    qlist(numpy.array(['quick', 'brown', 'fox', 'jumps', 'over', 'a lazy', 'dog']), qtype = QSTRING_LIST)
    qlist(['quick', 'brown', 'fox', 'jumps', 'over', 'a lazy', 'dog'], qtype = QSTRING_LIST)
    ['quick', 'brown', 'fox', 'jumps', 'over', 'a lazy', 'dog']
    # ("quick"; "brown"; "fox"; "jumps"; "over"; "a lazy"; "dog")

.. note:: ``QSTRING_LIST`` type indicator indicates that list/array has to be
          mapped to q generic list. 
    
Lists of temporal values are represented as instances of 
:class:`.qcollection.QTemporalList` class. This class wraps the raw q 
representation of temporal data (i.e. ``long``\s for ``timestamp``\s, ``int``\s 
for ``month``\s etc.) and provides accessors which allow to convert raw data to 
:class:`.qcollection.QTemporal` instances in a lazy fashion.

::

    qlist(numpy.array([to_raw_qtemporal(numpy.datetime64('2001-01-01', 'D'), qtype=QDATE), to_raw_qtemporal(numpy.datetime64('2000-05-01', 'D'), qtype=QDATE), qnull(QDATE)]), qtype=QDATE_LIST)
    qlist(array_to_raw_qtemporal(numpy.array([numpy.datetime64('2001-01-01', 'D'), numpy.datetime64('2000-05-01', 'D'), numpy.datetime64('NaT', 'D')]), qtype = QDATE_LIST), qtype = QDATE_LIST)
    qlist(numpy.array([366, 121, qnull(QDATE)]), qtype=QDATE_LIST)
    # 2001.01.01 2000.05.01 0Nd
    
    qlist(numpy.array([long(279417600000000), qnull(QTIMESTAMP)]), qtype=QTIMESTAMP_LIST)
    # 2000.01.04D05:36:57.600 0Np


The :func:`.qtemporal.array_to_raw_qtemporal` function simplifies adjusting
of `numpy.datetime64` or `numpy.timedelta64` arrays to q representation as raw
integer vectors.



Dictionaries
************

qPython represents q dictionaries with custom :class:`.qcollection.QDictionary` 
class.

Examples::

    QDictionary(qlist(numpy.array([1, 2], dtype=numpy.int64), qtype=QLONG_LIST), 
                qlist(numpy.array(['abc', 'cdefgh']), qtype = QSYMBOL_LIST))
    # q: 1 2!`abc`cdefgh
    
       
    QDictionary([numpy.int64(1), numpy.int16(2), numpy.float64(3.234), '4'], 
                [numpy.string_('one'), qlist(numpy.array([2, 3]), qtype=QLONG_LIST), '456', [numpy.int64(7), qlist(numpy.array([8, 9]), qtype=QLONG_LIST)]])
    # q: (1;2h;3.234;"4")!(`one;2 3;"456";(7;8 9))


The :class:`.qcollection.QDictionary` class implements Python collection API.
    
    
Tables
******

The q tables are translated into custom :class:`.qcollection.QTable` class. 

qPython provides an utility function :func:`.qcollection.qtable` which simplifies
creation of tables. This function also allow user to override default type
conversions for each column and provide explicit q type hinting per column.

Examples::

    qtable(qlist(numpy.array(['name', 'iq']), qtype = QSYMBOL_LIST), 
          [qlist(numpy.array(['Dent', 'Beeblebrox', 'Prefect'])), 
           qlist(numpy.array([98, 42, 126], dtype=numpy.int64))])
    
    qtable(qlist(numpy.array(['name', 'iq']), qtype = QSYMBOL_LIST),
          [qlist(['Dent', 'Beeblebrox', 'Prefect'], qtype = QSYMBOL_LIST), 
           qlist([98, 42, 126], qtype = QLONG_LIST)])
           
    qtable(['name', 'iq'],
           [['Dent', 'Beeblebrox', 'Prefect'], 
            [98, 42, 126]],
           name = QSYMBOL, iq = QLONG)       
    
    # flip `name`iq!(`Dent`Beeblebrox`Prefect;98 42 126)
    
    
    qtable(('name', 'iq', 'fullname'),
           [qlist(numpy.array(['Dent', 'Beeblebrox', 'Prefect']), qtype = QSYMBOL_LIST), 
            qlist(numpy.array([98, 42, 126]), qtype = QLONG_LIST),
            qlist(numpy.array(["Arthur Dent", "Zaphod Beeblebrox", "Ford Prefect"]), qtype = QSTRING_LIST)])
    
    # flip `name`iq`fullname!(`Dent`Beeblebrox`Prefect;98 42 126;("Arthur Dent"; "Zaphod Beeblebrox"; "Ford Prefect"))


The keyed tables are represented by :class:`.qcollection.QKeyedTable` instances,
where both keys and values are stored as a separate :class:`.qcollection.QTable` 
instances.

For example::

    # ([eid:1001 1002 1003] pos:`d1`d2`d3;dates:(2001.01.01;2000.05.01;0Nd))
    QKeyedTable(qtable(['eid'],
                       [qlist(numpy.array([1001, 1002, 1003]), qtype = QLONG_LIST)]),
                qtable(['pos', 'dates'],
                       [qlist(numpy.array(['d1', 'd2', 'd3']), qtype = QSYMBOL_LIST), 
                        qlist(numpy.array([366, 121, qnull(QDATE)]), qtype = QDATE_LIST)]))


Lambdas
*******

The q lambda is mapped to custom Python class :class:`.qtype.QLambda`::

    # {x+y}
    QLambda('{x+y}')

    # {x+y} [3]
    QLambda('{x+y}', numpy.int64(3))


Errors
******

The q errors are represented as instances of :class:`.qtype.QException` class.


Null values
***********

Please note that q ``null`` values are defined as::

    _QNULL1 = numpy.int8(-2**7)
    _QNULL2 = numpy.int16(-2**15)
    _QNULL4 = numpy.int32(-2**31)
    _QNULL8 = numpy.int64(-2**63)
    _QNAN32 = numpy.fromstring('\x00\x00\xc0\x7f', dtype=numpy.float32)[0]
    _QNAN64 = numpy.fromstring('\x00\x00\x00\x00\x00\x00\xf8\x7f', dtype=numpy.float64)[0]
    _QNULL_BOOL = numpy.bool_(False)
    _QNULL_SYM = numpy.string_('')
    _QNULL_GUID = uuid.UUID('00000000-0000-0000-0000-000000000000')


Complete null mapping between q and Python is represented in the table:

============== ============== =======================
 q type         q null value   Python representation 
============== ============== =======================
 ``bool``       ``0b``          ``_QNULL_BOOL``
 ``guid``       ``0Ng``         ``_QNULL_GUID``
 ``byte``       ``0x00``        ``_QNULL1``     
 ``short``      ``0Nh``         ``_QNULL2``     
 ``int``        ``0N``          ``_QNULL4``     
 ``long``       ``0Nj``         ``_QNULL8``     
 ``real``       ``0Ne``         ``_QNAN32``     
 ``float``      ``0n``          ``_QNAN64``     
 ``string``     ``" "``         ``' '``         
 ``symbol``     \`              ``_QNULL_SYM``
 ``timestamp``  ``0Np``         ``_QNULL8``                
 ``month``      ``0Nm``         ``_QNULL4``               
 ``date``       ``0Nd``         ``_QNULL4``                  
 ``datetime``   ``0Nz``         ``_QNAN64``                  
 ``timespan``   ``0Nn``         ``_QNULL8``                  
 ``minute``     ``0Nu``         ``_QNULL4``                  
 ``second``     ``0Nv``         ``_QNULL4``                  
 ``time``       ``0Nt``         ``_QNULL4``                  
============== ============== =======================

The :py:mod:`qtype` provides two utility functions to work with null values:

- :func:`~.qtype.qnull` - retrieves null type for specified q type code,
- :func:`~.qtype.is_null` - checks whether value is considered a null for
  specified q type code.