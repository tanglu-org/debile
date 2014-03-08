# Copyright (c) 2012-2014 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2014      Jon Severinsson <jon@severinsson.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from fnmatch import fnmatch

import xmlrpclib
import httplib
import socket
import ssl


def get_host_list(cert):
    if 'subjectAltName' in cert:
        return [x[1] for x in cert['subjectAltName'] if x[0] == 'DNS']
    else:
        return [x[0][1] for x in cert['subject'] if x[0][0] == 'commonName']

def validate(cert, hostname):
    hosts = get_host_list(cert)
    for host in hosts:
        if fnmatch(host, hostname):
            return True
    return False


class DebileHTTPSConnection(httplib.HTTPSConnection):
    def __init__(self, host, port=None, key_file=None, cert_file=None,
                 strict=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None):
        httplib.HTTPSConnection.__init__(self, host=host, port=port, key_file=key_file, cert_file=cert_file, strict=strict, timeout=timeout, source_address=source_address)

    def connect(self):
        sock = socket.create_connection((self.host, self.port),
                                        self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        self.sock = ssl.wrap_socket(sock, self.key_file, self.cert_file,
                                    do_handshake_on_connect=True,
                                    ca_certs="/etc/ssl/certs/ca-certificates.crt",
                                    cert_reqs=ssl.CERT_REQUIRED)

        if not validate(self.sock.getpeercert(), self.host):
            raise Exception("https endpint presented invalid certificate")

class DebileSafeTransport(xmlrpclib.Transport):
    def make_connection(self, host):
        if self._connection and host == self._connection[0]:
            return self._connection[1]

        chost, self._extra_headers, x509 = self.get_host_info(host)
        self._connection = host, DebileHTTPSConnection(chost, None, **(x509 or {}))
        return self._connection[1]