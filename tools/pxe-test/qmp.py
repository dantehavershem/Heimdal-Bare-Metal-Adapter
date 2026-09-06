#!/usr/bin/env python3
"""Capture the guest display or type a command through its local QMP socket."""
import argparse
import json
import socket
import time
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('socket')
parser.add_argument('--screenshot')
parser.add_argument('--key')
parser.add_argument('--type')
parser.add_argument('--keyboard-layout', choices=('us', 'de'), default='us',
                    help='Current guest keyboard layout (default: us)')
args=parser.parse_args()
connection=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
connection.settimeout(30)
connection.connect(args.socket)
stream=connection.makefile('rwb',buffering=0)
stream.readline()
sequence=0

def command(name,arguments=None):
    global sequence
    sequence+=1
    request={'execute':name,'id':sequence}
    if arguments: request['arguments']=arguments
    stream.write((json.dumps(request)+'\n').encode())
    while True:
        response=json.loads(stream.readline())
        if response.get('id')==sequence:
            if 'error' in response: raise RuntimeError(response['error'])
            return response.get('return')

command('qmp_capabilities')
if args.screenshot:
    command('screendump',{'filename':args.screenshot, 'format':'png' if args.screenshot.endswith('.png') else 'ppm'})
if args.key:
    command('human-monitor-command',{'command-line':'sendkey '+args.key})
if args.type:
    plain={' ':'spc','/':'slash','\\':'backslash','-':'minus','.':'dot',':':'shift-semicolon','%':'shift-5','(':'shift-9',')':'shift-0','@':'shift-2','"':'shift-apostrophe','_':'shift-minus','=':'equal'}
    if args.keyboard_layout == 'de':
        plain.update({'y':'z', 'z':'y', '/':'shift-7', '\\':'alt_r-minus',
                      '-':'slash', ':':'shift-dot', '(':'shift-8', ')':'shift-9',
                      '@':'alt_r-q', '"':'shift-2', '_':'shift-slash', '=':'shift-0',
                      '*':'shift-bracket_right', '>':'shift-less', '<':'less',
                      ';':'shift-comma', '&':'shift-6', '|':'alt_r-less'})
    for char in args.type:
        key=plain.get(char,plain.get(char.lower(),char.lower()))
        if char.isupper():key='shift-'+key
        command('human-monitor-command',{'command-line':'sendkey '+key+' 20'})
        time.sleep(.065)
connection.close()
