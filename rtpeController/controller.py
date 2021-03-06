import socket
import os
import json
import time
import sdp_transform
import bencodepy
import asyncio
import websockets
from utils import send, ws_send
from commands import Commands
from kube_api import KubernetesAPIClient
from pprint import pprint
from websocket import create_connection
from multiprocessing import Process


bc = bencodepy.Bencode(
    encoding='utf-8'
)

kubernetes_apis = []
commands = Commands()
if not os.getenv('RTPE_ADDRESS'):
    RTPE_ADDRESS = '127.0.0.1'
else:
    RTPE_ADDRESS = socket.gethostbyname_ex(os.getenv('RTPE_ADDRESS'))[2][0]
if not os.getenv('RTPE_PORT'):
    RTPE_PORT = 22221
else:
    RTPE_PORT = int(os.getenv('RTPE_PORT'))

if not os.getenv('LOCAL_ADDRESS'):
    LOCAL_ADDRESS = '127.0.0.1'
else:
    LOCAL_ADDRESS = os.getenv('LOCAL_ADDRESS')
if not os.getenv('RTPE_PORT'):
    LOCAL_PORT = 2000
else:
    LOCAL_PORT = int(os.getenv('LOCAL_PORT'))

RTPE_CONTROLLER = os.getenv('RTPE_CONTROLLER')
RTPE_PROTOCOL = os.getenv('RTPE_PROTOCOL')
WITHOUT_JSONSOCKET = os.getenv('WITHOUT_JSONSOCKET')

ws_sock = None

# https://stackoverflow.com/a/7207336/12243497
def runInParallel(*fns):
  proc = []
  for fn in fns:
    p = Process(target=fn)
    p.start()
    proc.append(p)
  for p in proc:
    p.join()

def check_delete():
    # print(len(kubernetes_apis))
    for a in kubernetes_apis:
        if RTPE_PROTOCOL == 'ws':
            query = ws_send(RTPE_PROTOCOL, RTPE_PORT, commands.query(a.call_id), sock=ws_sock)
        if RTPE_PROTOCOL == 'udp':
            query = send(RTPE_ADDRESS, RTPE_PORT, commands.query(a.call_id), LOCAL_ADDRESS, 2002)
        if query['result'] == 'error':
            a.delete_resources()      
            kubernetes_apis.remove(a)

# TODO: Fix this! kubernetes_apis always empty
def ws_check_delete():
    # global ws_sock
    while True:
        time.sleep(10)
        # try:
        #     ping = ws_send(RTPE_ADDRESS, RTPE_PORT, commands.ping(), sock=ws_sock)
        #     print(ping)
        # except:
        #     # websocket init
        #     ws_base_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #     ws_base_sock.connect((RTPE_ADDRESS, RTPE_PORT))
            
        #     host, port = ws_base_sock.getpeername()

        #     # enableTrace(True)
        #     ws_sock = create_connection(
        #         f'ws://{RTPE_ADDRESS}:{RTPE_PORT}', 
        #         subprotocols=["ng.rtpengine.com"],
        #         origin='127.0.0.1',
        #         socket=ws_base_sock
        #     )
        #     continue
        check_delete()

def parse_data(data):
    return {
        'cookie': data.decode().split(" ", 1)[0],
        **bc.decode(data.decode().split(" ", 1)[1])
    } 

def delete_kube_resources(call_id):
    global kubernetes_apis
    delete_objects = []
    print(call_id)
    for a in kubernetes_apis:
        print(a.call_id)
        if a.call_id == call_id:
            a.delete_resources()
            delete_objects.append(a)

    for a in delete_objects:
        kubernetes_apis.remove(a)

def create_resource(call_id, from_tag, to_tag):
    global kubernetes_apis

    for a in kubernetes_apis:
        if a.call_id == call_id:
            return

    if RTPE_PROTOCOL == 'udp':
        query = send(RTPE_ADDRESS, RTPE_PORT, commands.query(call_id), LOCAL_ADDRESS, 2998)
    if RTPE_PROTOCOL == 'ws':
        query = ws_send(RTPE_ADDRESS, RTPE_PORT, commands.query(call_id), sock=ws_sock)

    from_port = query['tags'][from_tag]['medias'][0]['streams'][0]['local port']
    from_c_address = query['tags'][from_tag]['medias'][0]['streams'][0]['endpoint']['address']
    from_c_port = query['tags'][from_tag]['medias'][0]['streams'][0]['endpoint']['port']
    to_port = query['tags'][to_tag]['medias'][0]['streams'][0]['local port']
    to_c_address = query['tags'][to_tag]['medias'][0]['streams'][0]['endpoint']['address']
    to_c_port = query['tags'][to_tag]['medias'][0]['streams'][0]['endpoint']['port']
    
    kubernetes_apis.append(
        KubernetesAPIClient(
            in_cluster=True,
            call_id=call_id,
            tag=from_tag,
            local_ip=from_c_address,
            local_rtp_port=from_c_port,
            local_rtcp_port=from_c_port + 1,
            remote_rtp_port=from_port,
            remote_rtcp_port=from_port + 1,
            without_jsonsocket=WITHOUT_JSONSOCKET,
            ws=True
        )
    )
    kubernetes_apis.append(
        KubernetesAPIClient(
            in_cluster=True,
            call_id=call_id,
            tag=to_tag,
            local_ip=to_c_address,
            local_rtp_port=to_c_port,
            local_rtcp_port=to_c_port + 1,
            remote_rtp_port=to_port,
            remote_rtcp_port=to_port + 1,
            without_jsonsocket=WITHOUT_JSONSOCKET,
            ws=True
        )
    )
    # for i in kubernetes_apis:
    #     print(i)

def udp_processing():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((LOCAL_ADDRESS, LOCAL_PORT))
    except Exception:
        print(Exception)
    sock.settimeout(10)
    print("Listening on %s:%d" % (LOCAL_ADDRESS, LOCAL_PORT))

    if RTPE_CONTROLLER == 'l7mp':
        while True:
            check_delete()
            try:
                data, client_address = sock.recvfrom(4096)
                data = parse_data(data)
                print(data)
            except Exception:
                continue
            
            time.sleep(1)
            response = send(RTPE_ADDRESS, RTPE_PORT, data, LOCAL_ADDRESS, 2001)
            sock.sendto(bc.encode(response), client_address) # Send back response

            if data['command'] == 'delete':
                delete_kube_resources(data['call-id'])
            if data['command'] == 'answer':
                create_resource(data['call-id'], data['from-tag'], data['to-tag'])
    if RTPE_CONTROLLER == 'envoy':
        ENVOY_MGM_ADDRESS = socket.gethostbyname_ex(os.getenv('ENVOY_MGM_ADDRESS'))[2][0]
        ENVOY_MGM_PORT = int(os.getenv('ENVOY_MGM_PORT'))
        print('ENVOY_MGM_ADDRESS: ' + str(ENVOY_MGM_ADDRESS))
        print('ENVOY_MGM_PORT: ' + str(ENVOY_MGM_PORT))
        while True:
            try:
                data, client_address = sock.recvfrom(4096)
                data = parse_data(data)
                pprint("Received command: " + data['command'])
            except Exception:
                continue
        
            time.sleep(1)

            response = send(RTPE_ADDRESS, RTPE_PORT, data, LOCAL_ADDRESS, 2001)
            sock.sendto(bc.encode(response), client_address) # Send back response
            print("Response")
            print(response)
            
            if data['command'] == 'answer':
                query = send(RTPE_ADDRESS, RTPE_PORT, commands.query(data['call-id']), LOCAL_ADDRESS, 2002)
                if not query:
                    sock.close()
                    break
                caller_port = query['tags'][data['from-tag']]['medias'][0]['streams'][0]['local port']
                callee_port = query['tags'][data['to-tag']]['medias'][0]['streams'][0]['local port']
                
                json_data = json.dumps({
                        "caller_rtp": caller_port,
                        "caller_rtcp": caller_port + 1,
                        "callee_rtp": callee_port,
                        "callee_rtcp": callee_port + 1,
                        "call_id": data['call-id']
                    }).encode('utf-8')

                sock.sendto(json_data, (ENVOY_MGM_ADDRESS, ENVOY_MGM_PORT))

async def ws_processing(websocket, path):
    global ws_sock
    if RTPE_CONTROLLER == 'l7mp':
        # websocket init
        ws_base_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ws_base_sock.connect((RTPE_ADDRESS, RTPE_PORT))

        # enableTrace(True)
        data = None
        try:
            data = parse_data(await websocket.recv())
            if "call-id" in data:
                ws_sock = create_connection(
                    f'ws://{RTPE_ADDRESS}:{RTPE_PORT}', 
                    subprotocols=["ng.rtpengine.com"],
                    origin='127.0.0.1',
                    socket=ws_base_sock,
                    header=[f'callid: {data["call-id"]}']
                )
            else:
                ws_sock = create_connection(
                    f'ws://{RTPE_ADDRESS}:{RTPE_PORT}', 
                    subprotocols=["ng.rtpengine.com"],
                    origin='127.0.0.1',
                    socket=ws_base_sock
                )
            response = ws_send(RTPE_ADDRESS, RTPE_PORT, data, sock=ws_sock)
            # pprint(response)
            if 'sdp' in response:
                response['sdp'] = response['sdp'].replace('127.0.0.1', '192.168.99.103')
            time.sleep(1)
            await websocket.send(data['cookie'] + " " + bc.encode(response).decode())
        except websockets.exceptions.ConnectionClosedError:
            pass
        
        if data['command'] == 'delete':
            delete_kube_resources(data['call-id'])
        if data['command'] == 'answer':
            create_resource(data['call-id'], data['from-tag'], data['to-tag'])

        ws_sock.close()
        ws_base_sock.close()        
    if RTPE_CONTROLLER == 'envoy':
        ENVOY_MGM_ADDRESS = socket.gethostbyname_ex(os.getenv('ENVOY_MGM_ADDRESS'))[2][0]
        ENVOY_MGM_PORT = int(os.getenv('ENVOY_MGM_PORT'))

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1', 2000))

        # websocket init
        ws_base_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ws_base_sock.connect((RTPE_ADDRESS, RTPE_PORT))

        # enableTrace(True)
        data = None
        try:
            data = parse_data(await websocket.recv())
            if "call-id" in data:
                ws_sock = create_connection(
                    f'ws://{RTPE_ADDRESS}:{RTPE_PORT}', 
                    subprotocols=["ng.rtpengine.com"],
                    origin='127.0.0.1',
                    socket=ws_base_sock,
                    header=[f'callid: {data["call-id"]}']
                )
            else:
                ws_sock = create_connection(
                    f'ws://{RTPE_ADDRESS}:{RTPE_PORT}', 
                    subprotocols=["ng.rtpengine.com"],
                    origin='127.0.0.1',
                    socket=ws_base_sock
                )
            response = ws_send(RTPE_ADDRESS, RTPE_PORT, data, sock=ws_sock)
            pprint(response)
            if 'sdp' in response:
                response['sdp'] = response['sdp'].replace('127.0.0.1', '192.168.99.103')
            time.sleep(1)
            await websocket.send(data['cookie'] + " " + bc.encode(response).decode())
        except websockets.exceptions.ConnectionClosedError:
            pass

        # if data['command'] == 'delete':
            # delete_kube_resources(data['call-id'])
        if data['command'] in ['answer', 'delete']:
            query = ws_send(RTPE_ADDRESS, RTPE_PORT, commands.query(data['call-id']), sock=ws_sock)
                
            caller_port = query['tags'][data['from-tag']]['medias'][0]['streams'][0]['local port']
            callee_port = query['tags'][data['to-tag']]['medias'][0]['streams'][0]['local port']
            
            json_data = json.dumps({
                    "caller_rtp": caller_port,
                    "caller_rtcp": caller_port + 1,
                    "callee_rtp": callee_port,
                    "callee_rtcp": callee_port + 1
                }).encode('utf-8')

            sock.sendto(json_data, (ENVOY_MGM_ADDRESS, ENVOY_MGM_PORT))
            sock.close()

        ws_sock.close()
        ws_base_sock.close()

def server():
    start_server = websockets.serve(ws_processing, "127.0.0.1", 1999, subprotocols=["ng.rtpengine.com"])
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()

def main():
    while True:
        try:
            if RTPE_PROTOCOL == 'udp':
                print('Use udp for processing...')
                udp_processing()
            if RTPE_PROTOCOL == 'ws':
                runInParallel(ws_check_delete, server)
        except:
            continue
if __name__ == '__main__':
    main()
