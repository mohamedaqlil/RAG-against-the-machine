from time import sleep
from tqdm import tqdm

# Wrap any iterable (like a list or range)
# for item in tqdm(range(10000)):
#     sleep(0.5)


import fire

class Calculator(object):
  """A simple calculator class."""

  def double(self, number=2):
    """double number"""
    return 2 * number

if __name__ == '__main__':
  fire.Fire(Calculator)
