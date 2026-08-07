
import os
import asyncio
import json
import getpass

from aiohttp import web
import aiohttp


overlay_clients = set()
base_path = os.path.dirname(os.path.abspath(__file__))

def load_config(path="config.json"):
    config = os.path.join(base_path, path)
    if not os.path.exists(config):
        raise FileNotFoundError("config.json not found")
    with open(config, "r") as f:
        return json.load(f)


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    overlay_clients.add(ws)
    print("Overlay connected")
    try:
        async for message in ws:
            pass
    finally:
        overlay_clients.discard(ws)
        print("Overlay disconnected")

    return ws


async def broadcast(data):
    if not overlay_clients:
        return

    message = json.dumps(data)
    dead = []
    for ws in overlay_clients:
        try:
            await ws.send_str(message)
        except Exception as e:
            print("WebSocket send error:", e)
            dead.append(ws)

    for ws in dead:
        overlay_clients.discard(ws)


async def handle_event(data, endpoint, key):
    raw_data = data.get("data")

    if not raw_data:
        return

    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        print("Invalid SSE JSON:", raw_data)
        return

    event = data.get("event")
    if event != "new_invoice_status":
        return
    
    invoice_id = data.get("invoice_id")
    if not invoice_id:
        print("Missing invoice_id")
        return

    headers = {
        "Authorization": f"Bearer {key}",
        "Invoice-Id": invoice_id,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{endpoint}/user/invoice",
                headers=headers,
            ) as response:

                response.raise_for_status()
                invoice = await response.json()
                social = invoice.get("social")
                if social is None:
                    return

                provider = social.get("provider")
                name = social.get("name")
                message = social.get("message")
                amount = social.get("amount")
                currecncy = social.get("currency")

                print("New Gift ! =====================")
                print(f"Provider : {provider}")
                print(f"Name : {name}")
                print(f"Message : {message}")
                print(f"Amount : {amount} {currecncy}")
                print("================================")

                await broadcast({
                    "data": social
                })

    except Exception as e:
        print("Error handling invoice event:", e)


async def listen_events(endpoint, key):
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "text/event-stream",
    }

    async with aiohttp.ClientSession(timeout=None) as session:
        async with session.get(
            f"{endpoint}/user/events",
            headers=headers,
        ) as response:

            response.raise_for_status()
            event = {}

            async for raw_line in response.content:
                line = raw_line.decode("utf-8").rstrip()
                if not line:
                    if event:
                        await handle_event(event, endpoint, key)

                    event = {}
                    continue

                if line.startswith("event:"):
                    event["event"] = line[6:].strip()
                elif line.startswith("data:"):
                    event["data"] = line[5:].strip()
                elif line.startswith("id:"):
                    event["id"] = line[3:].strip()


async def sse_loop(endpoint, key):
    while True:
        try:
            print("[SSE] Connecting...")
            await listen_events(endpoint, key)
            print("[SSE] Connection closed by server")
        except asyncio.CancelledError:
            raise

        except Exception:
            pass

        print("[SSE] Reconnecting...")
        await asyncio.sleep(1)


async def main():
    config = load_config()
    server = config.get("server", {})

    print()
    print("==========================================")
    print("         BTCZPay OBS Overlay")
    print("==========================================")

    host = server.get("host")
    if not host:
        print("[!] Host is missing from config.json")
        host = input("    Enter Host [127.0.0.1]: ").strip() or "127.0.0.1"

    port = server.get("port")
    if not port:
        print("[!] Port is missing from config.json")
        port = input("    Enter Port [8765]: ").strip() or "8765"

    endpoint = server.get("api")
    if not endpoint:
        print("[ERROR] API endpoint is missing from config.json")
        endpoint = input("    Enter API endpoint: ").strip()
        if not endpoint:
            print("[ERROR] API endpoint is required")
            return

    key = server.get("key")
    if not key:
        print("[!] Server key is missing from config.json")
        key = getpass.getpass("    Enter Server key: ").strip()
        if not key:
            print("[ERROR] Server key is required")
            return

    print()
    print("[CONFIG]")
    print(f"  Host     : {host}")
    print(f"  Port     : {port}")
    print(f"  API      : {endpoint}")
    print("[OK] Configuration loaded successfully")
    print()

    app = web.Application()
    www_path = os.path.join(base_path, "www")

    app.router.add_get(
        "/ws",
        websocket_handler,
    )
    app.router.add_static(
        "/",
        www_path,
        show_index=True,
    )

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(
        runner,
        host,
        port,
    )

    await site.start()

    print(f"Overlay: http://{host}:{port}/")
    print(f"WebSocket: ws://{host}:{port}/ws")
    print("==========================================")

    await sse_loop(endpoint, key)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass