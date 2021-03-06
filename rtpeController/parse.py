import argparse
import re


def parse(args, file):
    ''' Set arguments according to a configuration file.

    Format of the config file: 
      key1=value1
      key2=value2
      ...

    Args:
      args: Object with the user settings.
      file: Location of the config file. 
    '''

    with open(file, 'r') as f:
        Lines = f.readlines()
        for line in Lines:
            line = line.strip()
            if not line:
                continue
            if line[0] == '#':
                continue

            split_line = re.split('=', line)
            if split_line[1][0] != '{':
                split_line = re.split('=| ', line)
                if len(split_line) > 2:
                    setattr(args, split_line[0], [split_line[1], split_line[2]])
                elif split_line[1].isdigit():
                    setattr(args, split_line[0], int(split_line[1]))
                else:
                    setattr(args, split_line[0], split_line[1])
            else:
                setattr(args, split_line[0], split_line[1])


def arguments():
    """ Handle user settings.

    Returns:
      Ans object with the user settings.
    """

    # Init
    parser = argparse.ArgumentParser(
        description='Client for control RTPengine in kubernetes with l7mp.')

    parser.add_argument('--config_file', '-c', type=str, dest='config',
                        help='Specify the config file place.')

    # Controller
    parser.add_argument('--sidecar_port', type=str, dest='sidecar_port',
                        help='The envoy sidecar\'s port.')
    parser.add_argument('--sidecar_type', type=str, dest='sidecar_type',
                        help='envoy or l7mp.')

    # Kubernetes
    parser.add_argument('--without_jsonsocket', type=str, 
                        dest='without_jsonsocket', help='If it is specified ' + 
                        'there is no jsonsocket in the cluster')
    parser.add_argument('--in_cluster', type=str, dest='in_cluster',
                        help='Run like an controller.')

    # Commands
    parser.add_argument('--ping', type=int, dest='ping', default=0, 
                        help='Play ping pong with RTPengine.')
    parser.add_argument('--offer', '-o', type=str, dest='offer',
                        help='Offer JSON file location.')
    parser.add_argument('--answer', '-a', type=str, dest='answer',
                        help='Answer JSON file location.')
    parser.add_argument('--delete', type=str, dest='delete', 
                        help='Delete a call.')
    parser.add_argument('--query', type=str, dest='query', 
                        help='Return details from a specific call.')
    parser.add_argument('--list', type=int, dest='list', 
                        help='List a specific number of call ids.')
    parser.add_argument('--start_recording', type=str, dest='start_recording',
                        help='Start the call recording.')
    parser.add_argument('--stop_recording', type=str, dest='stop_recording',
                        help='Stop the call recording.')
    parser.add_argument('--block_dtmf', type=str, dest='bloc_dtmf',
                        help='Block DTMF traffic.')
    parser.add_argument('--unblock_dtmf', type=str, dest='unblock_dtmf',
                        help='Unblock DTMF traffic.')
    parser.add_argument('--block_media', type=str, dest='block_media',
                        help='Block media packets.')
    parser.add_argument('--unblock_media', type=str, dest='unblock_media',
                        help='Unblock media packets.')
    parser.add_argument('--start_forwarding', type=str, dest='start_forwarding',
                        help='Forward PCM via TCP/TLS.')
    parser.add_argument('--stop_forwarding', type=str, dest='stop_forwarding',
                        help='Stop forwarding PCM via TCP/TLS.')
    parser.add_argument('--play_media', type=str, dest='play_media',
                        help='Play media for participants.')
    parser.add_argument('--stop_media', type=str, dest='stop_media',
                        help='Stop media play for participants.')
    parser.add_argument('--play_dtmf', type=str, dest='play_dtmf',
                        help='Play DTMF in audio stream.')
    parser.add_argument('--statistics', type=str, dest='statistics',
                        help='Receive statistics.')


    # RTPengine server args
    parser.add_argument('--port', '-p', default=22222, type=int, dest='port',
                        help='RTPengine server port.')
    parser.add_argument('--address', '-addr', default='127.0.0.1', type=str,
                        dest='addr', help='RTPengine server address.')
    parser.add_argument('--ws_port', type=int, dest='ws_port', 
                        help='RTPengine websocket port.')
    parser.add_argument('--ws_address', type=str, dest='ws_address', 
                        help='RTPengine websocket address.')

    # Client
    parser.add_argument('--bind_offer', '-bo', nargs=2,
                        default=['127.0.0.1', '2000'], dest='bind_offer',
                        help='Offer source address and port.')
    parser.add_argument('--bind_answer', '-ba', nargs=2,
                        default=['127.0.0.1', '2004'], dest='bind_answer',
                        help='Answer source address and port.')
    parser.add_argument('--file', '-f', type=str, dest='file',
                        help="A simple file to list or query")
    parser.add_argument('--audio_file', '-af', type=str, dest='audio_file',
                        help="Path of the audio to ffmpeg.")
    parser.add_argument('--generate_calls', "-gc", type=int,
                        dest='generate_calls', help='Generate certain number '
                        'of parallel calls with traffic.')
    parser.add_argument('--sdpaddress', '-saddr', type=str, dest='sdpaddr',
                        default='127.0.0.1',
                        help='This the sender local address.')
    parser.add_argument('--rtpsend', type=str, dest='rtpsend',
                        help='When it is defined the traffic genearator ' + 
                        'will use rtpsend instead of ffmpeg. Location of ' + 
                        '.rtp file.')
    parser.add_argument('--codecs', nargs=2, default=[0, 0], dest='codecs',
                        help='Codecs by number. Only two types of codecs.')

    # Send incoming traffic to RTPengine
    parser.add_argument('--server', '-s', type=int, dest='server',
                        choices=[0, 1], help='1 - proxy mode, 0 - simple mode')
    parser.add_argument('--server_address', '-sa', type=str,
                        dest='server_address', help='Listening address.')
    parser.add_argument('--server_port', '-sp', type=int, dest='server_port',
                        help='Listening port.')

    # Not fully functional
    parser.add_argument('--ffmpeg', '-ff', type=int, choices=[1], dest='ffmpeg',
                        help='If specified, it will start a certain number of'
                        'ffmpeg processes.')

    args = parser.parse_args()

    if args.config:
        parse(args, args.config)

    return args
