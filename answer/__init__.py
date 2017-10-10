import json
from functools import partial
from wsgiref.handlers import format_date_time

import trio
import h11


class Answer:
    def __init__(self, routes={}):
        self.router = Router(routes)
        pass

    async def run(self, host='127.0.0.1', port=5000):
        handler = partial(handle_connection, answer=self)
        serve_tcp = partial(trio.serve_tcp, handler, port=port, host=host)
        async with trio.open_nursery() as nursery:
            listeners = await nursery.start(serve_tcp)

class Router:
    routes = {}

    def __init__(self, routes):
        self.routes.update(routes)

    def add_route(self, path, handler):
        self.routes[path] = handler

    def route(self, connection, request):
        print(f'Routing request: {request}')
        handler = self.routes.get(request.target)
        return handler


class Request:
    def __init__(self, method=None, target=None, headers=None, body=None):
        self.method = method
        self.target = target
        self.headers = headers
        self.body = body

    def __str__(self):
        return f'<Request method={self.method!r} target={self.target!r} headers={self.headers!r}>'

    async def read_request(self, connection, request):
        self.method = request.method.decode()
        self.target = request.target.decode()
        self.headers = dict([(name.decode(), value.decode()) for (name, value) in request.headers])
        body = ''
        while True:
            event = await connection.next_event()
            if type(event) is h11.EndOfMessage:
                break
            assert type(event) is h11.Data
            body += event.data.decode()

        return self


class Response:
    def __init__(self, body, status_code=200, content_type='text/plain', headers={}):
        self.body = body
        self.status_code = status_code
        self.content_type = content_type
        self.headers = headers


async def send_response(connection, response):
    headers = {name: value for (name, value) in connection.basic_headers()}
    headers[b'Content-Type'] = response.content_type
    headers[b'Content-Length'] = str(len(response.body))
    headers.update(response.headers)
    res = h11.Response(status_code=response.status_code, headers=headers.items())
    await connection.send(res)
    await connection.send(h11.Data(data=response.body))
    await connection.send(h11.EndOfMessage())


async def bar(request):
    return Response(b'YAAY!\n')


async def handle_connection(stream, answer):
    connection = Connection(stream)
    while True:
        assert connection.conn.states == {h11.CLIENT: h11.IDLE, h11.SERVER: h11.IDLE}
        try:
            print('main loop waiting for request')
            event = await connection.next_event()
            print(f'main loop got event: {event}')
            if type(event) is h11.Request:
                request = await Request().read_request(connection, event)
                handler = answer.router.route(connection, request)
                response = await handler(request)
                await send_response(connection, response)
        except Exception as exc:
            print("Error during response handler:", exc)
            raise

        if connection.conn.our_state is h11.MUST_CLOSE:
            await connection.shutdown_and_clean_up()
            return
        else:
            try:
                connection.conn.start_next_cycle()
            except h11.ProtocolError:
                states = connection.conn.states
                print(f'Unexpected state {states} -- bailing out')
                await connection.shutdown_and_clean_up()
                return


class Connection:
    def __init__(self, stream):
        self.stream = stream
        self.conn = h11.Connection(our_role=h11.SERVER)
        self.ident = ' '.join(['answers/0.0.0', h11.PRODUCT_ID]).encode('ascii')

    async def send(self, event):
        assert type(event) is not h11.ConnectionClosed
        data = self.conn.send(event)
        await self.stream.send_all(data)

    async def next_event(self):
        while True:
            event = self.conn.next_event()
            if event is h11.NEED_DATA:
                await self._read_from_peer()
                continue
            return event

    async def shutdown_and_clean_up(self):
        await self.stream.send_eof()
        try:
            while True:
                got = await self.stream.receive_some(4096)
                if not got:
                    break
        finally:
            await self.stream.aclose()

    def basic_headers(self):
        return [(b'Date', format_date_time(None).encode())
               ,(b'Server', self.ident)]

    async def _read_from_peer(self):
        if self.conn.they_are_waiting_for_100_continue:
            go_ahead = h11.InformationalResponse(status_code=100, headers=self.basic_headers())
            await self.send(go_ahead)
        data = await self.stream.receive_some(4096)
        self.conn.receive_data(data)
