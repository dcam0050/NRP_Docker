"""userinfo wrapper"""


class UserInfo(object):
    """Class to provide access to user properties"""
    def __init__(self, userinfo):
        """
        Args:
            userinfo(dict): dictionary which returned by IDM APIs
        """
        self.userinfo = userinfo

    @property
    def id(self):
        """user id"""
        return self.userinfo.get('id')

    @property
    def username(self):
        """username"""
        return self.userinfo.get('username')

    @property
    def email(self):
        """primary email"""
        return [email['value'] for email in self.userinfo.get('emails') if email['primary']][0]

    @property
    def emails(self):
        """primary email"""
        return [email['value'] for email in self.userinfo.get('emails')]

    @property
    def display_name(self):
        """display name"""
        return self.userinfo.get('displayName')

    @property
    def last_name(self):
        """last name"""
        return self.userinfo.get('familyName')

    @property
    def first_name(self):
        """first name"""
        return self.userinfo.get('givenName')

    def __str__(self):
        return '%s: %s' % (self.id, self.username)
