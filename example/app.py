# coding=utf8

__author__ = 'Alexander.Li'

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from persistedRmq import PersistedRmq
import asyncio
import logging


app = FastAPI()


html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var cid = getName();
            console.log('cid', cid);
            var ws = new WebSocket("ws://localhost:8000/ws/"+cid);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                //postMessage(input.value)
                ws.send(input.value);
                input.value = ''
                event.preventDefault()
            }
            function getName(){
                var query = window.location.href;
                console.log(query);
                var vars = query.split("#");
                return vars[vars.length-1];
            }
        </script>
    </body>
</html>
"""

PersistedRmq.init('redis://localhost/0')


@app.get("/")
async def get():
    return HTMLResponse(html)


async def wait_text(client: PersistedRmq, websocket: WebSocket):
    while True:
        try:
            message = await websocket.receive_text()
            await client.publish(message)
        except Exception as e:
            logging.error('连接断了！')
            return


async def wait_queue(client: PersistedRmq):
    await client.subscribe(timeout=30)


@app.websocket("/ws/{cid}")
async def websocket_endpoint(cid: str, websocket: WebSocket):
    await websocket.accept()

    async def dispatch_message(message):
        logging.error(f'{cid}获取到了消息：{message}')
        await websocket.send_text(f"Message text was: {message.decode()}")

    async with PersistedRmq('message', client_id=cid, on_message=dispatch_message) as client:
        tasks = [
            wait_text(client, websocket),
            wait_queue(client)
        ]
        try:
            await asyncio.wait(tasks)
        except Exception as e:
            logging.error(f'外层错误：{e}')
