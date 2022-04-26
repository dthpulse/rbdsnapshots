#!/usr/bin/python3

import time
from timeit import default_timer as timer
from multiprocessing import Pool, cpu_count
import multiprocessing

def square(n, b):

    time.sleep(2)

    return n * b

def squaree(n):

    time.sleep(2)

    return n * n

def forn():
    values = (2, 4, 6, 8)
    return values

def fornn():
    valuess = (100,300,500,700)
    return valuess

def main():
 
    valuess = fornn()
    values = forn()
    start = timer()

    print(f'starting computations on {cpu_count()} cores')

    values = (2, 4, 6, 8)

    with Pool(cpu_count()-15) as pool:
        # pool.map(square, values)
        res = pool.starmap(square, zip(values, valuess))
        print(res)
    with Pool(cpu_count()-15) as pool2:
        # pool.map(square, values)
        res2 = pool2.map(squaree, values)
        print(res2)
    end = timer()
    print(f'elapsed time: {end - start}')

if __name__ == '__main__':
    main()

if __name__ == '__fornn__':
    print(fornn)
