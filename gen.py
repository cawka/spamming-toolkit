#!/usr/bin/env python3

import sys
import yaml
import pathlib
import argparse
import ics

parser = argparse.ArgumentParser()
parser.add_argument('input', help='.yml file with announcement parameters')
parser.add_argument('command', nargs='?', help="'send' to actually send out, otherwise test run")
parser.add_argument('-s', nargs='?', default="", dest='subject_prefix', help='Prefix for the subject line, e.g., "Reminder: "')
parser.add_argument('--st', nargs='?', default="subject.txt", dest="subject_template", help='Subject template file')
parser.add_argument('-t', dest='template', default='template.html', help='HTML template for the email')

args = parser.parse_args()

template = open(args.template).read()
subject = open(args.subject_template).read()

yml = pathlib.Path(args.input)

with yml.open(encoding='utf-8') as f:
    info = yaml.load(f, yaml.SafeLoader)

for key in info:
    info[key] = info[key].replace("\n", "\n<p style='margin-top: 0.4em'>")

for key in info:
    template = template.replace("@@%s@@" % key.upper(), info[key])
    subject = subject.replace("@@%s@@" % key.upper(), info[key])

outname = yml.parts[len(yml.parts)-1].replace('.yml', '.html')
out = open(outname, "wt", encoding="utf-8")
out.write(template)
out.close()

starttime, stoptime = info['time'].split('-')

from ics import Calendar, Event
from datetime import datetime, timezone
from dateutil import parser
import pytz
import uuid

begin = datetime.strptime("%s %s" % (info['date'], starttime), "%A, %B %d, %Y %I:%M%p")
end = datetime.strptime("%s %s" % (info['date'], stoptime), "%A, %B %d, %Y %I:%M%p")
duration = end - begin

def format(date, suffix=''):
    return date.strftime('%Y%m%dT%H%M%S' + suffix)

calparams = {
    'dtstamp': format(datetime.utcnow(), 'Z'),
    'created': format(datetime.utcnow(), 'Z'),
    'last-modified': format(datetime.utcnow(), 'Z'),
    'room': info['room'],
    'subject': subject.split(" on ")[0],
    'description': '',
    'begin': format(begin),
    'end': format(end),
    'uid': str(uuid.uuid1()).upper(),
    'uid1': str(uuid.uuid1()).upper(),
    }
    
with open('ical-template.ics', 'rt') as f:
    ics = f.read()
    for key in calparams:
        ics = ics.replace("@@%s@@" % key.upper(), calparams[key])
    with open('ical-seminar-event.ics', 'wt', newline='\r\n') as outf:
        outf.write(ics)

from script import pymailer

class Args:
    test = True
    html = [outname]
    image = ['fiu-logo.png', info['image']]
    addresses = ['emails.csv']
    subject = ["%s%s" % (args.subject_prefix, subject)]
    txt = ''
    attach = [['text/calendar', 'ical-seminar-event.ics']]

mailer = pymailer.PyMailer(Args())

if args.command == "send":
    mailer.send()
else:
    mailer.send_test()
