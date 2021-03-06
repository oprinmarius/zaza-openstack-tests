# Copyright 2018 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Note that the unit_tests/__init__.py also mocks out two charmhelpers imports
# that have side effects that try to apt install modules:
# sys.modules['charmhelpers.contrib.openstack.utils'] = mock.MagicMock()
# sys.modules['charmhelpers.contrib.network.ip'] = mock.MagicMock()

"""Module to provide helper for writing unit tests."""

import asyncio
import contextlib
import io
import mock
import unittest


@contextlib.contextmanager
def patch_open():
    """Patch open().

    Patch open() to allow mocking both open() itself and the file that is
    yielded.

    Yields the mock for "open" and "file", respectively.
    """
    mock_open = mock.MagicMock(spec=open)
    mock_file = mock.MagicMock(spec=io.FileIO)

    @contextlib.contextmanager
    def stub_open(*args, **kwargs):
        mock_open(*args, **kwargs)
        yield mock_file

    with mock.patch('builtins.open', stub_open):
        yield mock_open, mock_file


class BaseTestCase(unittest.TestCase):
    """Base class for creating classes of unit tests."""

    def shortDescription(self):
        """Disable reporting unit test doc strings rather than names."""
        return None

    def setUp(self):
        """Run setup of patches."""
        self._patches = {}
        self._patches_start = {}

    def tearDown(self):
        """Run teardown of patches."""
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch_object(self, obj, attr, return_value=None, name=None, new=None,
                     **kwargs):
        """Patch the given object."""
        if name is None:
            name = attr
        if new is not None:
            mocked = mock.patch.object(obj, attr, new=new, **kwargs)
        else:
            mocked = mock.patch.object(obj, attr, **kwargs)
        self._patches[name] = mocked
        started = mocked.start()
        if new is None:
            started.return_value = return_value
        self._patches_start[name] = started
        setattr(self, name, started)

    def patch(self, item, return_value=None, name=None, new=None, **kwargs):
        """Patch the given item."""
        if name is None:
            raise RuntimeError("Must pass 'name' to .patch()")
        if new is not None:
            mocked = mock.patch(item, new=new, **kwargs)
        else:
            mocked = mock.patch(item, **kwargs)
        self._patches[name] = mocked
        started = mocked.start()
        if new is None:
            started.return_value = return_value
        self._patches_start[name] = started
        setattr(self, name, started)


class AioTestCase(BaseTestCase):
    def __init__(self, methodName='runTest', loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self._function_cache = {}
        super(AioTestCase, self).__init__(methodName=methodName)

    def coroutine_function_decorator(self, func):
        def wrapper(*args, **kw):
            return self.loop.run_until_complete(func(*args, **kw))
        return wrapper

    def __getattribute__(self, item):
        attr = object.__getattribute__(self, item)
        if asyncio.iscoroutinefunction(attr) and item.startswith('test_'):
            if item not in self._function_cache:
                self._function_cache[item] = (
                    self.coroutine_function_decorator(attr))
            return self._function_cache[item]
        return attr
