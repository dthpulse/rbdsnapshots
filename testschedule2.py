#!/usr/bin/env python3

import schedule
import time

def greet(name):
    print('Hello', name)

schedule.every(2).seconds.do(greet, name='Alice')
schedule.every(4).seconds.do(greet, name='Bob')

from schedule import every, repeat

@repeat(every().second, "World")
@repeat(every().day, "Mars")
def hello(planet):
    print("Hello", planet)

while True:
  schedule.run_pending()
  time.sleep(1)
