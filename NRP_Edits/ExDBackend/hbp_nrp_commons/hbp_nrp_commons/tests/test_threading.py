"""
Unit tests for the killable thread implementation
"""

import unittest
import time
from hbp_nrp_commons.killable_threads import Thread

class TestThreading(unittest.TestCase):

    def test_threading(self):
        escaped = False

        def f():
            try:
                while True:
                    time.sleep(0.1)
            finally:
                escaped = True

        t = Thread(target = f)
        t.start()
        self.assertTrue(t.isAlive())
        t.terminate()
        t.join()
        self.assertFalse(t.isAlive())
