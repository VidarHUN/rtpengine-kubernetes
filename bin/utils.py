import random
import string
import bencodepy
import socket
import subprocess
import logging
import sdp_transform
import json

bc = bencodepy.Bencode(
    encoding='utf-8'
)


def gen_cookie(length):
    """ Genarate a random for cookie. 

    Args:
        length: Length of the desired random string.

    Returns:
        A string with a given length made of random ASCII lowercase
        characters.
    """
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def send(address, port, file, bind_address, bind_port):
    """ Send a JSON file to RTPengine on the given ports.

    Args:
        address: RTPengine server IPv4 address. 
        port: RTPengine server port.
        file: A dictionary which describes the RTPengine ng commands.
        bind_address: Source IPv4 address. 
        bind_port: Source port. 

    Returns:
        An object containing the RTPengine response. 
    """

    # Generate and send ng message
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if bind_address != '127.0.0.1':
        sock.bind((bind_address, bind_port))
    
    logging.debug("Socket bound to %s, %s", str(bind_address), str(bind_port))

    cookie = gen_cookie(5)
    data = bencodepy.encode(file).decode()
    message = str(cookie) + " " + str(data)
    logging.debug("Message generated: %s", message)
    byte_sent = sock.sendto(message.encode('utf-8'), (address, port))
    logging.debug("%s, byte sent.", str(byte_sent))
    
    response = sock.recv(4096)
    data = response.decode()
    data = data.split(" ", 1)
    result = bc.decode(data[1])
    logging.debug("Received message: %s", str(result))

    sock.close()
    logging.debug("Socket closed.")
    logging.info("Message sent to RTPengine and got response.")

    return result


def ffmpeg(audio_file, cnt, offer_rtp_address, answer_rtp_address):
    """ Send RTP traffic to a given address with ffmpeg.

    With ffmpeg you can control how the media stream should be send
    out. For example you can change the codec if it is needed. 

    Args:
        audio_file: Path of the audio file.
        cnt: How many streams should be generated by ffmpeg. 
        offer_rtp_address: A list of rtp addresses with the offer port.
        answer_rtp_address: 
            A list of answer addresses with the answer port. 
    """

    processes = []
    for c in range(cnt):
        processes.append(
          subprocess.Popen(
            ["ffmpeg", "-re", "-i", audio_file, "-ar", "8000", "-ac", "1",
            "-acodec", "pcm_mulaw", "-f", "rtp", offer_rtp_address[c]
            ]
          )
        )
        processes.append(
          subprocess.Popen(
              ["ffmpeg", "-re", "-i", audio_file, "-ar", "8000", "-ac", "1",
              "-acodec", "pcm_mulaw", "-f", "rtp", answer_rtp_address[c]
              ]
          )
        )

    # Close the processes
    for process in processes:
        process.communicate()


def handle_oa(address, port, file, bind, type):
    ''' Send an offer or answer. 

    Args:
        address: RTPengine address.
        port: RTPengine port.
        file: Location of the offer or answer.
        bind: List with an IP and Port for source.
        type: "offer" or "answer"

    Returns:
        RTP port given by RTPengine.
    '''
    
    with open(file) as f:
        command = json.load(f)
    response = send(address, port, command, bind[0], int(bind[1]))
    parsed_sdp_dict = sdp_transform.parse(response.get('sdp'))
    rtp_port = parsed_sdp_dict.get('media')[0].get('port')
    rtcp_port = parsed_sdp_dict.get('media')[0].get('rtcp').get('port')
    print(f'RTP port from {type}: {rtp_port}')
    print(f'RTCP port from {type}: {rtcp_port}')
    return rtp_port
