# -*- coding: utf-8 -*-
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  Author: Mauro Soria

import time
import httpx

from lib.core.settings import (
    DEFAULT_ENCODING,
    ITER_CHUNK_SIZE,
    MAX_RESPONSE_SIZE,
    UNKNOWN,
)
from lib.parse.url import clean_path, parse_path
from lib.utils.common import get_readable_size, is_binary


class BaseResponse:
    def __init__(self, response):
        self.datetime = time.strftime("%Y-%m-%d %H:%M:%S")
        self.url = str(response.url)
        self.full_path = parse_path(self.url)
        self.path = clean_path(self.full_path)
        self.status = response.status_code
        self.headers = response.headers
        self.redirect = self.headers.get("location") or ""
        self.history = [str(res.url) for res in response.history]
        self.content = ""
        self.body = b""

    @property
    def type(self):
        if "content-type" in self.headers:
            return self.headers.get("content-type").split(";")[0]

        return UNKNOWN

    @property
    def length(self):
        try:
            return int(self.headers.get("content-length"))
        except TypeError:
            return len(self.body)

    @property
    def size(self):
        return get_readable_size(self.length)

    def __hash__(self):
        return hash(self.body)

    def __eq__(self, other):
        return (self.status, self.body, self.redirect) == (
            other.status,
            other.body,
            other.redirect,
        )


class Response(BaseResponse):
    def __init__(self, response):
        super().__init__(response)

        for chunk in response.iter_content(chunk_size=ITER_CHUNK_SIZE):
            self.body += chunk

            if len(self.body) >= MAX_RESPONSE_SIZE or (
                "content-length" in self.headers and is_binary(self.body)
            ):
                break

        if not is_binary(self.body):
            try:
                self.content = self.body.decode(
                    response.encoding or DEFAULT_ENCODING, errors="ignore"
                )
            except LookupError:
                self.content = self.body.decode(DEFAULT_ENCODING, errors="ignore")


class AsyncResponse(BaseResponse):
    @classmethod
    async def create(cls, response: httpx.Response) -> "AsyncResponse":
        self = cls(response)
        async for chunk in response.aiter_bytes(chunk_size=ITER_CHUNK_SIZE):
            self.body += chunk

            if len(self.body) >= MAX_RESPONSE_SIZE or (
                "content-length" in self.headers and is_binary(self.body)
            ):
                break

        if not is_binary(self.body):
            try:
                self.content = self.body.decode(
                    response.encoding or DEFAULT_ENCODING, errors="ignore"
                )
            except LookupError:
                self.content = self.body.decode(DEFAULT_ENCODING, errors="ignore")

        return self
