#!/usr/bin/env python
#
# Copyright 2010 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#

"""uauth module tests."""



import logging
logging.basicConfig(filename='/dev/null')

import mox
import stubout

from google.apputils import app
from google.apputils import basetest
from simian.mac.munki.handlers import uauth
from tests.simian.mac.common import test


class UauthModuleTest(mox.MoxTestBase):

  def setUp(self):
    mox.MoxTestBase.setUp(self)
    self.stubs = stubout.StubOutForTesting()

  def tearDown(self):
    self.mox.UnsetStubs()
    self.stubs.UnsetAll()

  def testMain(self):
    self.assertTrue(
        issubclass(uauth.NotAuthenticated, uauth.Error))
    self.assertTrue(
        issubclass(uauth.NotAuthenticated, uauth.base.NotAuthenticated))


class UserAuthTest(test.RequestHandlerTest):
  """Test UserAuth class."""

  def GetTestClassInstance(self):
    return uauth.UserAuth()

  def GetTestClassModule(self):
    return uauth

  def GetTestClassInstanceVariableName(self):
    return 'ua'

  def testGetWhenAlreadyAuthenticated(self):
    """Test get()."""
    self.MockDoMunkiAuth()

    self.mox.ReplayAll()
    self.ua.get()
    self.mox.VerifyAll()

  def testGetWhenNoUser(self):
    """Test get()."""
    self.MockDoMunkiAuth(fail=True)
    self.mox.StubOutWithMock(uauth.users, 'get_current_user')
    uauth.users.get_current_user().AndReturn(None)

    self.mox.ReplayAll()
    self.assertRaises(
        uauth.NotAuthenticated,
        self.ua.get)
    self.mox.VerifyAll()

  def testGetWhenUserNotMacAdminOrSupportUser(self):
    """Test get()."""
    user = 'foo-user-does-not-exist'
    mock_user = self.mox.CreateMockAnything()

    self.MockDoMunkiAuth(fail=True)

    self.mox.StubOutWithMock(uauth.users, 'get_current_user')
    self.mox.StubOutWithMock(uauth.auth, 'IsAdminUser')
    self.mox.StubOutWithMock(uauth.auth, 'IsSupportUser')
    uauth.users.get_current_user().AndReturn(mock_user)
    mock_user.email().AndReturn(user)
    uauth.auth.IsAdminUser(user).AndReturn(False)
    uauth.auth.IsSupportUser(user).AndReturn(False)

    self.mox.ReplayAll()
    self.assertRaises(
        uauth.NotAuthenticated,
        self.ua.get)
    self.mox.VerifyAll()

  def testGetWhenAuthTokenNotReturned(self):
    """Test get()."""
    self.mox.StubOutWithMock(uauth.users, 'get_current_user')
    self.mox.StubOutWithMock(uauth.auth, 'IsAdminUser')

    user = 'foo-user-does-not-exist'
    mock_user = self.mox.CreateMockAnything()

    self.MockDoMunkiAuth(fail=True)
    uauth.users.get_current_user().AndReturn(mock_user)
    mock_user.email().AndReturn(user)
    uauth.auth.IsAdminUser(user).AndReturn(True)

    mock_aps = self.mox.CreateMockAnything()
    self.stubs.Set(uauth.gaeserver, 'AuthSimianServer', mock_aps)
    mock_aps().AndReturn(mock_aps)
    mock_aps.SessionCreateUserAuthToken(
        user, level=uauth.gaeserver.LEVEL_ADMIN).AndReturn(None)

    self.mox.ReplayAll()
    self.assertRaises(
        uauth.NotAuthenticated,
        self.ua.get)
    self.mox.VerifyAll()

  def testGetAdminUser(self):
    """Test get() where IsAdminUser() returns True."""
    self.mox.StubOutWithMock(uauth.users, 'get_current_user')
    self.mox.StubOutWithMock(uauth.auth, 'IsAdminUser')

    user = 'foo-user-does-not-exist'
    mock_user = self.mox.CreateMockAnything()
    token = 'token'

    self.MockDoMunkiAuth(fail=True)
    uauth.users.get_current_user().AndReturn(mock_user)
    mock_user.email().AndReturn(user)
    uauth.auth.IsAdminUser(user).AndReturn(True)

    mock_aps = self.mox.CreateMockAnything()
    self.stubs.Set(uauth.gaeserver, 'AuthSimianServer', mock_aps)
    mock_aps().AndReturn(mock_aps)
    mock_aps.SessionCreateUserAuthToken(
        user, level=uauth.gaeserver.LEVEL_ADMIN).AndReturn(token)
    self.response.headers.__setitem__(
        'Set-Cookie', '%s=%s; secure; httponly;' % (
            uauth.auth_init.AUTH_TOKEN_COOKIE, token)).AndReturn(None)
    self.response.out.write(
        uauth.auth_init.AUTH_TOKEN_COOKIE).AndReturn(None)

    self.mox.ReplayAll()
    self.assertEqual(None, self.ua.get())
    self.mox.VerifyAll()

  def testGetSupportUser(self):
    """Test get() where IsSupportUser() returns True."""
    self.mox.StubOutWithMock(uauth.users, 'get_current_user')
    self.mox.StubOutWithMock(uauth.auth, 'IsAdminUser')
    self.mox.StubOutWithMock(uauth.auth, 'IsSupportUser')

    user = 'foo-user-does-not-exist'
    mock_user = self.mox.CreateMockAnything()
    token = 'token'

    self.MockDoMunkiAuth(fail=True)
    uauth.users.get_current_user().AndReturn(mock_user)
    mock_user.email().AndReturn(user)
    uauth.auth.IsAdminUser(user).AndReturn(False)
    uauth.auth.IsSupportUser(user).AndReturn(True)

    mock_aps = self.mox.CreateMockAnything()
    self.stubs.Set(uauth.gaeserver, 'AuthSimianServer', mock_aps)
    mock_aps().AndReturn(mock_aps)
    mock_aps.SessionCreateUserAuthToken(
        user, level=uauth.gaeserver.LEVEL_BASE).AndReturn(token)
    self.response.headers.__setitem__(
        'Set-Cookie', '%s=%s; secure; httponly;' % (
            uauth.auth_init.AUTH_TOKEN_COOKIE, token)).AndReturn(None)
    self.response.out.write(
        uauth.auth_init.AUTH_TOKEN_COOKIE).AndReturn(None)

    self.mox.ReplayAll()
    self.assertEqual(None, self.ua.get())
    self.mox.VerifyAll()


def main(unused_argv):
  basetest.main()


if __name__ == '__main__':
  app.run()
