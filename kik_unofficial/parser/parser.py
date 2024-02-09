from asyncio import StreamReader
from xml.sax import ContentHandler, ErrorHandler, SAXException

import defusedxml.sax
from bs4 import BeautifulSoup
from defusedxml.expatreader import DefusedExpatParser


class KikXmlParser:
    """
    Parses and validates incoming stanzas from the XMPP stream.
    """

    def __init__(self, reader: StreamReader, log):
        self.reader = reader
        self.handler = StanzaHandler(log)

    async def read_initial_k(self) -> BeautifulSoup:
        response = await self.reader.readuntil(separator=b">")
        if not response.startswith(b"<k "):
            raise ValueError("unexpected init stream response tag: " + response.decode("utf-8"))
        if b' ok="1"' in response or b"</k>" in response:
            return self._parse_from_bytes(response)
        else:
            response += await self.reader.readuntil(separator=b"</k>")
            return self._parse_from_bytes(response)

    async def read_next_stanza(self) -> BeautifulSoup:
        xml = b""
        parser = self._make_parser()

        while True:
            packet = await self.reader.readuntil(separator=b">")
            if xml == b"":
                if packet == b"</k>" or packet == b"</stream:stream>":
                    raise SAXException(f"stream closed: {packet.decode('utf-8')}")

            xml += packet

            try:
                parser.feed(packet)
            except StopIteration:
                return self._parse_from_bytes(xml)

    def _make_parser(self) -> DefusedExpatParser:
        parser = defusedxml.sax.make_parser()  # type: DefusedExpatParser
        parser.setContentHandler(self.handler)
        parser.setErrorHandler(self.handler)
        parser.forbid_dtd = True
        parser.forbid_entities = True
        parser.forbid_external = True
        return parser

    @staticmethod
    def _parse_from_bytes(xml: bytes) -> BeautifulSoup:
        element = BeautifulSoup(xml, features="xml", from_encoding="utf-8")
        return next(iter(element)) if len(element) > 0 else element


class StanzaHandler(ContentHandler, ErrorHandler):
    """
    This validates that a chunk of data is a complete stanza (all start tags are properly closed)

    This also handles a case where Kik sends multiple stanzas back in the same chunk of data from the socket.
    """

    def __init__(self, log):
        super().__init__()
        self.log = log
        self.depth = 0
        self.expected_name = None

    def startElement(self, name, attrs) -> None:
        self.depth += 1
        if self.expected_name is None:
            self.expected_name = name

    def endElement(self, name) -> None:
        self.depth -= 1
        if self.depth == 0:
            if self.expected_name != name:
                raise SAXException(f"end tag closed with wrong name (expected {self.expected_name}, received {name})")
            else:
                self.expected_name = None
                raise StopIteration

    def error(self, exception):
        self.log.error(exception)

    def fatalError(self, exception):
        self.log.error(exception)
        raise exception

    def warning(self, exception):
        self.log.warn(exception)
