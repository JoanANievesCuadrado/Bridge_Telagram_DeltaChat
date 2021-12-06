import imaplib, smtplib
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.parser import Parser
from email.header import decode_header
import mimetypes, threading, os
from time import sleep
from datetime import datetime, timedelta, timezone
from collections import deque
import base64

import re 
import asyncio
from functools import wraps
import numpy as np
from telethon import utils
import telethon.tl.types
import string
import random
from os.path import isfile

global msg_cola
global msg_telegram

msg_cola = deque()
msg_telegram = deque()

correo = {}
if isfile('email_config.txt'):
    lines = open('email_config.txt').readlines()
    for line in lines:
        if re.match(r'EMAIL:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)+)', line):
            correo['email'] = re.match(r'EMAIL:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)+)', line).group(1).strip()
        elif re.match(r'PASSWORD:([a-zA-Z0-9_.+-@]+)', line):
            correo['pass'] = re.match(r'PASSWORD:([a-zA-Z0-9_.+-@]+)', line).group(1).strip()
        elif re.match(r'IMAP:([a-zA-Z0-9_.+-@]+)', line):
            correo['imap'] = re.match(r'IMAP:([a-zA-Z0-9_.+-@]+)', line).group(1).strip()
        elif re.match(r'IMAP_PORT:(\d+)', line):
            correo['imap port'] = int(re.match(r'IMAP_PORT:(\w+)', line).group(1).strip())
        elif re.match(r'SSL_IMAP:(0|1|True|False)', line):
            correo['SSL imap'] = bool(re.match(r'SSL_IMAP:(0|1|True|False)', line).group(1).strip())
        elif re.match(r'SMTP:([a-zA-Z0-9_.+-@]+)', line):
            correo['smtp'] = re.match(r'SMTP:([a-zA-Z0-9_.+-@]+)', line).group(1).strip()
        elif re.match(r'SMTP_PORT:(\d+)', line):
            correo['smtp port'] = int(re.match(r'SMTP_PORT:(\d+)', line).group(1).strip())
        elif re.match(r'SSL_SMTP:(0|1|True|False)', line):
            correo['SSL smtp'] = int(re.match(r'SSL_SMTP:(0|1|True|False)', line).group(1).strip())
        else:
            print('Necesita configurar el archivo email_config.txt')
            exit()
else:
    print('Falta el archivo email_config.txt')
    exit()
firma = re.compile(r'\s{1}--.*', re.DOTALL)
forwaded = re.compile(r'^---------- Forwarded message ----------\s')
# Expresión regular para buscar las extensiones de los archivos
ext = re.compile(r'\.\w*$')
email_address = re.compile(r'.* ?<|>$')
p = Parser()

cmd = {}


def key_gen(n=11):
    return ''.join(random.choice(string.ascii_letters + string.digits) for x in range(n))

# decorador para añadir comandos del bot de correo
def command(func=None, pattern=None, users=[]):
    def _decorator_command(func):
        cmd[pattern or '/' + func.__name__] = (func, users)
        return func
    
    if func is None:
        return _decorator_command
    return _decorator_command(func)

# clase para hereditaria para clases asyncrónicas
class aobject(object):
    async def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        await instance.__init__(*args, **kwargs)
        return instance

def fileEmail(msg, avatars):
    filename = msg.get_filename()
    fname, charset = decode_header(filename)[0]
    if charset:
        filename = fname.decode(charset)
    if not filename in avatars:
        if os.path.isfile(filename):
            n = 1
            if ext.search(filename):
                extension = ext.search(filename).group()
            else:
                extension = ''
            
            nombre = filename[:-len(extension)]
            while os.path.isfile(nombre + '(' + str(n) + ')' + extension):
                n += 1
            
            filename = nombre + '(' + str(n) + ')' + extension
        try:
            file = open(filename, 'wb')
            file.write(msg.get_payload(decode=True))
            file.close()
        except Exception as e:
            print('fileEmail.save')
            print(e)
            print(type(e))
    return filename


# clase para construir un email teniendo como base otro email (pendiente unificar con classMsgT)
class classMsgR(object):
    me_email = correo['email']

    def __init__(self, msg, name = 'Bridge', body = '', body_html = ''):
        self.msg = msg
        self.sender = email_address.sub('', msg['From'])
        self.name = name
        self.From = self.name + ' <' + self.me_email + '>'
        self.To = self.makeTo()
        self.body = body
        self.body_html = body_html
        self.headers = self.makeHeaders()
        self.paths, self.rm_paths = self.makePath()
        self.text = self.makeText()

    def makeText(self):
        if not self.msg.is_multipart():
            if self.msg.get_content_type() == 'text/plain':
                return self.msg.get_payload().strip()
        else:
            for part in self.msg.get_payload():
                if part.get_content_type() == 'text/plain':
                    return part.get_payload().strip()
        return ''

    def makeHeaders(self):
        headers = {}
        headers['Chat-Version'] = '1.0'
        headers['Subject'] = 'Re:' + self.msg['Subject'] if self.msg['Subject'] != None else 'TelegramBridge'
        headers['Chat-Group-ID'] = self.msg['Chat-Group-ID']
        headers['Chat-Group-Name'] = self.msg['Chat-Group-Name']
        headers['In-Reply-To'] = self.msg['Message-ID']
        headers['Message-ID'] = str(np.random.randint(10000, 1000000))
        return headers
        
    def makeTo(self):
        to = self.msg['To'].split(',')
        for i in to:
            if self.me_email in i:
                to.remove(i)
        to.append(self.msg['From'])
        return to
    
    def makePath(self):
        paths = []
        rm = []
        avatars = []
        if self.msg['Chat-Group-Avatar']:
            avatars.append(self.msg['Chat-Group-Avatar'])
        if self.msg['Chat-User-Avatar']:
            avatars.append(self.msg['Chat-User-Avatar'])
        
        if self.msg.is_multipart():
            for part in self.msg.get_payload():
                if not part.get_content_type() in ['text/plain', 'message/disposition-notification']:
                    paths.append(fileEmail(part, avatars))
                    rm.append(True)
        else:
            if not self.msg.get_content_type() in ['text/plain', 'message/disposition-notification']:
                paths.append(fileEmail(part, avatars))
                rm.append(True)
        
        return (paths, rm)

# clase para construir un email teniendo como base un mensaje de Telegram (pendiente unificar con classMsgR)
class classMsgT(aobject):
    me_email = correo['email']

    async def __init__(self, message, name = 'Bridge', body_html = '', To = []):
        self.message = message
        self.sender = ''
        self.name = name
        
        name_from = utils.get_display_name(self.message.sender)
        name_from = base64.urlsafe_b64encode(name_from.encode('utf-8')).decode('utf-8')
        name_from = '=?UTF-8?b?{}?='.format(name_from)
        self.From = '{} <{}>'.format(name_from, self.me_email)

        self.Sender ='{} <{}>'.format(self.name, self.me_email)
        self.To = To
        self.body = await self.makeBody()
        self.body_html = ''#await self.makeBodyHtml()
        self.headers = self.makeHeaders()
        self.paths, self.rm_paths = await self.makePath()
    
    async def makeBodyHtml(self):
        body_html = utils.get_display_name(self.message.sender) + '\n'
        body_html += utils.html.unparse(self.message.message, self.message.entities) if self.message.message else ''
        
        body_html = body_html.replace('\n', '<br>\n')
        
        return body_html
    
    async def makeBody(self):
        body = self.message.message if self.message.message else ''
        
        return body
    
    async def makePath(self):
        path = []
        rm = []
        pp = ''
        
        if type(self.message.media) in [telethon.tl.types.MessageMediaPhoto, telethon.tl.types.MessageMediaDocument]:
            pp = await self.message.download_media()
            if pp:
                path.append(pp)
                rm.append(True)
        return (path, rm)
    
    def makeHeaders(self):
        headers = {}
        headers['Chat-Version'] = '1.0'
        headers['Subject'] = 'Telegram Bridge'
        headers['Chat-Group-ID'] = str(self.message.chat.id)
        dname = utils.get_display_name(self.message.chat)
        dname = base64.urlsafe_b64encode(dname.encode('utf-8')).decode('utf-8')
        dname = '=?UTF-8?b?{}?='.format(dname)
        headers['Chat-Group-Name'] = dname
        headers['In-Reply-To'] = str(self.message.reply_to.reply_to_msg_id) if self.message.reply_to else None
        headers['Message-ID'] = f'{self.message.id}_{self.message.chat.id}_{key_gen(6)}'
        headers['Sender'] = '{} <{}>'.format(self.name, self.me_email)
        return headers

# obtener el hilo mediante su nombre
def getThreadByName(name):
    threads = threading.enumerate()
    for thread in threads:
        if thread.name == name:
            return thread

# decodificar un email 
def decode_imap_email(data):
    mensaje = data[0][1].decode('utf-8')
    msg = p.parsestr(mensaje)
    
    return(msg)

# Función para iniciar una conexión con el servidor IMAP
def conn_imap(server):
    if server['SSL imap']:
        conn = imaplib.IMAP4_SSL(server['imap'])
    else:
        conn = imaplib.IMAP4(server['imap'])
        conn.starttls()
    conn.login(server['email'], server['pass'])
    code, dummy = conn.select('INBOX')
    
    return(conn)

# Función para iniciar una conexión con el servidor SMTP
def conn_smtp(server):
    try:
        if server['SSL smtp']:
            server_smtp = smtplib.SMTP_SSL(server['smtp'])
        else:
            server_smtp = smtplib.SMTP(server['smtp'])
        a = server_smtp.login(server['email'], server['pass'])
    except Exception as e:
        print('conn_smtp')
        print(e)
        sleep(2.5)
    return(server_smtp)

# Función para adjuntar archivos
def attach_mail(msg, path, remove=True):
    try:
        if path != None and os.path.isfile(path):
            ctype = mimetypes.guess_type(path)[0]
            if ctype == None:
                ctype = 'application/octate-stream'
            maintype, subtype = ctype.split('/', 1)
            if(maintype != 'text'):
                binary = open(path, 'rb').read()
            else:
                binary = open(path, 'r', errors='ignore',
                    encoding='utf-8').read()
            
            if(maintype == 'text'):
                msg_a = MIMEText(binary, _subtype=subtype,
                    _charset='utf-8')
            elif(maintype == 'image'):
                msg_a = MIMEImage(binary, _subtype=subtype)
            elif(maintype == 'audio'):
                msg_a = MIMEAudio(binary, _subtype=subtype)
            elif(maintype == 'application'):
                msg_a = MIMEApplication(binary, _subtype=subtype)
            else:
                msg_a = MIMEBase(maintype, subtype)
                msg_a.set_payload(binary)
                encoders.encode_base64(msg_a)
            msg_a.add_header('Content-Disposition', 'attachment', filename=path)
            msg.attach(msg_a)
            
            if remove:
                os.remove(path)
    except Exception as exc:
        print('attach_mail')
        print(exc)
        print(type(exc))
    
    return(msg)

# Función para enviar emails
def send_email(server, msg):
    html1 = '''\
    <html>
    <head></head>
    <body>
        <p>'''
    html2 = '''</p>
    </body>
    </html>
    '''
    if msg.paths == [] and msg.body != '' and msg.body_html == '':
        mail = MIMEText(msg.body, _charset='utf-8')
    else:
        if msg.body_html and msg.paths:
            mail = MIMEMultipart('mixed')
            mail1 = MIMEMultipart('alternative')
            if msg.body:
                mail1.attach(MIMEText(msg.body, _charset='utf-8'))
           
            body_html = html1 + msg.body_html + html2
            mail1.attach(MIMEText(body_html, 'html', _charset='utf-8'))
            mail.attach(mail1)
        elif msg.body_html:
            mail = MIMEMultipart('alternative')
            if msg.body:
                mail.attach(MIMEText(msg.body, _charset='utf-8'))

            body_html = html1 + msg.body_html + html2
            mail.attach(MIMEText(body_html, 'html', _charset='utf-8'))
        else:
            mail = MIMEMultipart()
            if msg.body:
                mail.attach(MIMEText(msg.body, _charset='utf-8'))
        
        for j, i in enumerate(msg.paths):
            rm = True
            mail = attach_mail(mail, i, remove=msg.rm_paths[j])
            
    mail['From'] = msg.From
    mail['To'] = ', '.join(msg.To)
    for i in msg.headers:
        if msg.headers[i] != None:
            mail[i] = msg.headers[i]
        
    try:
        if msg.body or msg.body_html or msg.paths:
            email_sending = {11}
            while email_sending != {}:
                server_smtp = conn_smtp(server)
                email_sending = server_smtp.sendmail(server['email'], msg.To, mail.as_string())
                server_smtp.close()
    except Exception as e:
        print('server_smtp.sendmail')
        print(e)
        print(type(e))
        raise e

def isID(cgid):
    if cgid:
        foo = cgid.split('-')[0]
        return(foo.isdecimal() or (foo[1:].isdecimal() and foo[0]=='-'))
    return False

async def crear_grupo_delta(bot, message, integrantes):
    entity_group = await bot.get_entity(message.chat)
    title = utils.get_display_name(entity_group)

    path_pic = await bot.download_profile_photo(entity_group)

    msg = await classMsgT(message)
    msg.body = f'Hola, acabo de crear el grupo "{title}" para nosotros.'
    if path_pic:
        msg.paths.append(path_pic)
        msg.rm_paths.append(True)
        msg.headers['Chat-Group-Avatar'] = os.path.split(path_pic)[-1]
    msg.To = integrantes

    global msg_cola
    msg_cola.append(msg)

async def anadir_miembro(bot, message, integrantes, new):
    entity_group = await bot.get_entity(message.chat)
    title = utils.get_display_name(message.chat)

    dname = utils.get_display_name(message.sender)
    path_pic = await bot.download_profile_photo(message.chat)

    msg = await classMsgT(message, To=integrantes)
    msg.body = f'Miembro {new} añadido por {dname}'

    if path_pic:
        msg.paths.append(path_pic)
        msg.rm_paths.append(True)
        msg.headers['Chat-Group-Avatar'] = os.path.split(path_pic)[-1]
    
    msg.headers['Chat-Group-Member-Added'] = new

    global msg_cola
    msg_cola.append(msg)

async def eliminar_miembro(message, integrantes, del_email):
    msg = await classMsgT(message, To=integrantes)
    dname = utils.get_display_name(message.sender)
    msg.body = f'Miembro {del_email} eliminado por {dname}'
    msg.headers['Chat-Group-Member-Removed'] = del_email

    global msg_cola
    msg_cola.append(msg)